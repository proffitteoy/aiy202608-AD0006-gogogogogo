"""LLM-driven section writer for the report pipeline.

对应报告中的 overview / recommendations / risk-notes 三段，共用同一个 JSON
输出契约（`LLMSectionOutput`）与 OpenAI 兼容的 chat/completions 调用路径。设计
参考 ``agents/opinions.py``：streaming、response_format=json_schema、DeepSeek
provider 分派、schema 严格校验 + 二次证据 ID 白名单校验。
"""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import httpx
from pydantic import ValidationError

from risktrace.core.config import Settings
from risktrace.reports.prompts import (
    SYSTEM_PROMPTS,
    LLMSectionOutput,
    SectionKey,
    build_user_prompt,
)
from risktrace.reports.schemas import AnalysisSnapshotPayload

logger = logging.getLogger(__name__)

DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1/"
CHAT_COMPLETIONS_PATH = "chat/completions"
LLM_TIMEOUT_SECONDS = 45.0
PROMPT_VERSION = "template-report-v3"

EmitCallable = Callable[[str, dict[str, Any]], Awaitable[None]]


class ReportSectionLLMError(RuntimeError):
    """所有可预期的 LLM 失败都封装成这个异常，方便 pipeline 降级。"""


class ReportSectionAgent:
    """把 snapshot payload 交给 LLM，产出 ``LLMSectionOutput``。"""

    def __init__(
        self,
        settings: Settings,
        *,
        emit: EmitCallable | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.settings = settings
        self._emit = emit
        self.transport = transport

    async def emit(self, event: str, payload: dict[str, Any]) -> None:
        if self._emit is not None:
            await self._emit(event, payload)

    async def generate(
        self,
        section: SectionKey,
        payload: AnalysisSnapshotPayload,
    ) -> LLMSectionOutput:
        if not self.settings.llm_api_key.strip():
            raise ReportSectionLLMError("LLM api key 未配置")

        system_prompt = SYSTEM_PROMPTS[section]
        user_prompt = build_user_prompt(section, payload)

        request_body: dict[str, Any] = {
            "model": self.settings.llm_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.settings.llm_temperature,
            "max_tokens": self.settings.llm_max_tokens,
            "stream": True,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": f"report_section_{section.replace('-', '_')}",
                    "strict": True,
                    "schema": LLMSectionOutput.model_json_schema(),
                },
            },
        }
        if self.settings.llm_provider.strip().lower() == "deepseek":
            request_body["response_format"] = {"type": "json_object"}
            request_body["thinking"] = {"type": "disabled"}

        collected: list[str] = []
        try:
            async with (
                self._client() as client,
                client.stream(
                    "POST", CHAT_COMPLETIONS_PATH, json=request_body
                ) as response,
            ):
                response.raise_for_status()
                await self.emit(
                    "llm_start",
                    {"section": section, "model": self.settings.llm_model},
                )
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    text = line[5:].strip()
                    if text == "[DONE]":
                        break
                    try:
                        chunk = json.loads(text)
                    except json.JSONDecodeError:
                        continue
                    delta = self._delta_text(chunk)
                    if delta:
                        collected.append(delta)
                        await self.emit(
                            "llm_delta", {"section": section, "delta": delta}
                        )
        except httpx.HTTPStatusError as exc:
            detail = ""
            try:
                detail = (await exc.response.aread()).decode("utf-8", "replace")[
                    :500
                ].strip()
            except Exception:  # noqa: BLE001
                detail = ""
            raise ReportSectionLLMError(
                f"HTTP {exc.response.status_code}: {detail or 'empty'}"
            ) from exc
        except httpx.HTTPError as exc:
            raise ReportSectionLLMError(f"请求失败：{exc}") from exc

        content = self._strip_code_fence("".join(collected))
        if not content:
            raise ReportSectionLLMError("LLM 未返回任何内容")

        await self.emit(
            "llm_done", {"section": section, "bytes": len(content)}
        )

        try:
            return LLMSectionOutput.model_validate_json(content)
        except ValidationError as exc:
            raise ReportSectionLLMError(f"schema 校验失败：{exc}") from exc

    def _base_url(self) -> str:
        raw = self.settings.llm_base_url.strip()
        if not raw:
            return DEFAULT_OPENAI_BASE_URL
        return raw.rstrip("/") + "/"

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base_url(),
            headers={
                "Authorization": f"Bearer {self.settings.llm_api_key}",
                "Content-Type": "application/json",
            },
            timeout=LLM_TIMEOUT_SECONDS,
            transport=self.transport,
        )

    @staticmethod
    def _strip_code_fence(text: str) -> str:
        cleaned = text.strip()
        if not cleaned.startswith("```"):
            return cleaned
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines).strip()

    @staticmethod
    def _delta_text(chunk: dict[str, Any]) -> str:
        choices = chunk.get("choices")
        if not isinstance(choices, list) or not choices:
            return ""
        delta = choices[0].get("delta")
        if not isinstance(delta, dict):
            return ""
        content = delta.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str):
                        parts.append(text)
            return "".join(parts)
        return ""


class LLMStatementLike:
    """轻量结构，供 service 层再包装成 ``ReportStatement``。"""

    __slots__ = ("text", "evidence_ids")

    def __init__(self, *, text: str, evidence_ids: list[uuid.UUID]) -> None:
        self.text = text
        self.evidence_ids = evidence_ids


def valid_statements(
    output: LLMSectionOutput,
    *,
    allowed_evidence_ids: frozenset[uuid.UUID],
) -> list[LLMStatementLike]:
    """把 LLM 输出过滤到只保留 evidence_id 合法的条目。"""

    cleaned: list[LLMStatementLike] = []
    for statement in output.statements:
        legal = [eid for eid in statement.evidence_ids if eid in allowed_evidence_ids]
        if not legal:
            continue
        cleaned.append(
            LLMStatementLike(text=statement.text.strip(), evidence_ids=legal[:8])
        )
    return cleaned
