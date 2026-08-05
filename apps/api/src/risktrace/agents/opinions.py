"""Opinion extraction over an OpenAI-compatible chat API.

Reads the documents linked to an event, asks the LLM to enumerate the
"归因观点" (stance / emotion / claim type + a concrete evidence span) that each
opinionated piece of text is expressing, and writes them into
``opinion_records`` with full provenance.

Design mirrors ``TransmissionGraphAgent``:

- every opinion must reference a ``document_id`` that the caller supplied,
- optional ``target_entity_id`` must resolve against the current tenant's
  ``entities`` table, otherwise it is dropped,
- strict Pydantic schema is enforced before touching the database,
- streaming events (``llm_start`` / ``llm_delta`` / ``llm_done`` /
  ``opinion_accepted``) flow through the shared ``emit`` callback,
- an ``input_hash`` fingerprints (event, document set) — re-running with the
  same inputs is a no-op instead of duplicating rows.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from collections.abc import Awaitable, Callable, Iterable
from datetime import UTC, datetime
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from risktrace.core.config import get_settings
from risktrace.core.demo import get_demo_tenant_id
from risktrace.db.models import (
    Entity,
    Event,
    EventDocument,
    OpinionRecord,
    RawDocument,
)

logger = logging.getLogger(__name__)

MAX_OPINIONS = 12
AGENT_VERSION = "0.1.0"
PROMPT_VERSION = "v1"
DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1/"
CHAT_COMPLETIONS_PATH = "chat/completions"
LLM_TIMEOUT_SECONDS = 45.0

Stance = Literal["bullish", "bearish", "neutral", "wait"]
ClaimType = Literal["fact", "opinion", "speculation"]


class OpinionItem(BaseModel):
    document_id: uuid.UUID
    target_entity_id: uuid.UUID | None = None
    stance: Stance
    emotion: str = Field(min_length=1, max_length=32)
    claim_type: ClaimType
    reason: str = Field(min_length=1, max_length=400)
    evidence_span: str = Field(min_length=1, max_length=400)
    confidence: float = Field(ge=0.0, le=1.0)


class OpinionExtraction(BaseModel):
    opinions: list[OpinionItem] = Field(max_length=MAX_OPINIONS)


def _build_system_prompt() -> str:
    return (
        "你是金融事件观点抽取助手。"
        "请从用户给出的事件描述与文档中，抽取表达明确立场/情绪的观点，"
        "每条观点必须能对应到具体一段文字（evidence_span）。\n\n"
        "规则：\n"
        "- document_id 必须来自输入的文档列表；不要引用未提供的文档。\n"
        "- target_entity_id 只能来自可用主体列表；如果无法从文档确定具体主体，"
        "请设为 null，不要瞎猜。\n"
        "- stance 只能是 bullish、bearish、neutral、wait。\n"
        "- claim_type 只能是 fact、opinion、speculation；纯事实陈述用 fact，"
        "主观判断用 opinion，未落实的预测/传闻用 speculation。\n"
        "- emotion 用一个中文情绪词，例如 乐观、悲观、观望、恐慌、兴奋、担忧、中性。\n"
        "- reason 用一句中文说明为什么这段文字表达了该立场。\n"
        "- evidence_span 必须是文档正文里的一段原文（可裁剪，但不要改写）。\n"
        "- 最多输出 12 条观点，优先保留立场清晰、证据完整的候选。\n"
        "- 根值必须是 JSON 对象，且结构严格为 {\"opinions\": [...]}。\n"
        "- opinions 中每项只能使用 document_id、target_entity_id、stance、"
        "emotion、claim_type、reason、evidence_span、confidence 字段。\n"
        "- 只输出严格 JSON，不要附带 Markdown、解释或代码块。"
    )


def _build_user_prompt(event_title: str, entity_lines: str, doc_text: str) -> str:
    return (
        f"事件标题：{event_title}\n\n"
        f"可用主体（ID: 名称）:\n{entity_lines or '  （暂无已登记主体）'}\n\n"
        f"可用文档:\n{doc_text}\n\n"
        "请抽取该事件的归因观点。"
    )


EmitFn = Callable[[str, dict[str, Any]], Awaitable[None]]


async def _noop_emit(event: str, payload: dict[str, Any]) -> None:  # noqa: ARG001
    return None


class OpinionExtractionAgent:
    def __init__(
        self,
        session: AsyncSession,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        emit: EmitFn | None = None,
    ) -> None:
        self.session = session
        self.settings = get_settings()
        self.transport = transport
        self.emit: EmitFn = emit or _noop_emit
        self.model_version = f"{self.settings.llm_provider}:{self.settings.llm_model}"

    @staticmethod
    def _input_hash(event_id: uuid.UUID, doc_ids: list[uuid.UUID]) -> str:
        payload = json.dumps(
            {"event_id": str(event_id), "doc_ids": sorted(str(d) for d in doc_ids)},
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()

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

    @staticmethod
    def _message_text(payload: dict[str, Any]) -> str:
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise RuntimeError("LLM 未返回可解析的候选结果。")

        message = choices[0].get("message")
        if not isinstance(message, dict):
            raise RuntimeError("LLM 返回缺少 message 字段。")

        refusal = message.get("refusal")
        if isinstance(refusal, str) and refusal.strip():
            raise RuntimeError(f"LLM 拒绝生成结果：{refusal.strip()}")

        content = message.get("content")
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if not isinstance(item, dict):
                    continue
                inner = item.get("text")
                if isinstance(inner, str):
                    parts.append(inner)
            text = "".join(parts)
        else:
            text = ""

        text = OpinionExtractionAgent._strip_code_fence(text)
        if not text:
            raise RuntimeError("LLM 返回内容为空。")
        return text

    async def _run_llm(
        self,
        *,
        event_title: str,
        entity_lines: str,
        doc_text: str,
    ) -> OpinionExtraction:
        request_body: dict[str, Any] = {
            "model": self.settings.llm_model,
            "messages": [
                {"role": "system", "content": _build_system_prompt()},
                {
                    "role": "user",
                    "content": _build_user_prompt(event_title, entity_lines, doc_text),
                },
            ],
            "temperature": self.settings.llm_temperature,
            "max_tokens": self.settings.llm_max_tokens,
            "stream": True,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "opinion_extraction",
                    "strict": True,
                    "schema": OpinionExtraction.model_json_schema(),
                },
            },
        }
        if self.settings.llm_provider.strip().lower() == "deepseek":
            request_body["response_format"] = {"type": "json_object"}
            request_body["thinking"] = {"type": "disabled"}

        collected: list[str] = []
        try:
            async with self._client() as client:
                async with client.stream(
                    "POST", CHAT_COMPLETIONS_PATH, json=request_body
                ) as response:
                    response.raise_for_status()
                    await self.emit(
                        "llm_start",
                        {"model": self.settings.llm_model},
                    )
                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data:"):
                            continue
                        payload_text = line[5:].strip()
                        if payload_text == "[DONE]":
                            break
                        try:
                            chunk = json.loads(payload_text)
                        except json.JSONDecodeError:
                            logger.debug(
                                "skipping non-json stream frame: %s",
                                payload_text[:80],
                            )
                            continue
                        delta = self._delta_text(chunk)
                        if delta:
                            collected.append(delta)
                            await self.emit("llm_delta", {"delta": delta})
        except httpx.HTTPStatusError as exc:
            detail = ""
            try:
                detail = (await exc.response.aread()).decode("utf-8", "replace")[:500].strip()
            except Exception:  # noqa: BLE001
                detail = ""
            raise RuntimeError(
                f"LLM 接口返回 HTTP {exc.response.status_code}: {detail or 'empty response'}"
            ) from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"LLM 请求失败：{exc}") from exc

        content = self._strip_code_fence("".join(collected))
        if not content:
            raise RuntimeError("LLM 未返回可解析的内容。")

        await self.emit("llm_done", {"bytes": len(content)})

        try:
            return OpinionExtraction.model_validate_json(content)
        except ValidationError as exc:
            raise RuntimeError(f"LLM 输出未通过 schema 校验：{exc}") from exc

    @staticmethod
    def _valid_opinions(
        items: Iterable[OpinionItem],
        *,
        valid_doc_ids: frozenset[uuid.UUID],
        valid_entity_ids: frozenset[uuid.UUID],
    ) -> list[OpinionItem]:
        cleaned: list[OpinionItem] = []
        for index, item in enumerate(items):
            if item.document_id not in valid_doc_ids:
                logger.warning(
                    "opinion[%d] document_id=%s not in doc registry, skipping",
                    index,
                    item.document_id,
                )
                continue
            target = item.target_entity_id
            if target is not None and target not in valid_entity_ids:
                logger.warning(
                    "opinion[%d] target_entity_id=%s not in tenant entity registry, "
                    "clearing target",
                    index,
                    target,
                )
                item = item.model_copy(update={"target_entity_id": None})
            cleaned.append(item)

        cleaned.sort(key=lambda item: item.confidence, reverse=True)
        return cleaned[:MAX_OPINIONS]

    async def extract_for_event(self, event_id: uuid.UUID) -> list[OpinionRecord]:
        tenant_id = get_demo_tenant_id()

        event = await self.session.scalar(
            select(Event).where(Event.id == event_id, Event.tenant_id == tenant_id)
        )
        if event is None:
            raise ValueError(f"Event {event_id} not found")

        links = (
            await self.session.execute(
                select(EventDocument).where(EventDocument.event_id == event_id)
            )
        ).scalars().all()
        doc_ids = [link.document_id for link in links]
        if not doc_ids:
            raise ValueError("当前事件没有关联文档，无法抽取归因观点。")

        doc_rows = (
            await self.session.execute(
                select(RawDocument).where(
                    RawDocument.id.in_(doc_ids),
                    RawDocument.tenant_id == tenant_id,
                )
            )
        ).scalars().all()
        docs_by_id = {doc.id: doc for doc in doc_rows}
        if not docs_by_id:
            raise ValueError("当前事件缺少可读取的原始文档，无法抽取归因观点。")

        valid_doc_ids = frozenset(docs_by_id.keys())

        input_hash = self._input_hash(event_id, doc_ids)
        existing = await self.session.execute(
            select(OpinionRecord).where(
                OpinionRecord.event_id == event_id,
                OpinionRecord.tenant_id == tenant_id,
                OpinionRecord.input_hash == input_hash,
            )
        )
        if existing.scalars().first() is not None:
            logger.info(
                "OpinionExtraction: opinions already exist for input_hash=%s",
                input_hash[:12],
            )
            return []

        entity_rows = (
            await self.session.execute(
                select(Entity).where(Entity.tenant_id == tenant_id)
            )
        ).scalars().all()
        valid_entity_ids = frozenset(row.id for row in entity_rows)
        entity_lines = "\n".join(
            f"  {row.id}: {row.name} ({row.entity_type})" for row in entity_rows
        )

        doc_text_parts: list[str] = []
        for doc_id in doc_ids:
            doc = docs_by_id.get(doc_id)
            if doc is None:
                continue
            title = doc.title or "（无标题）"
            preview = (doc.raw_text or "").strip()[:280]
            if not preview:
                preview = title
            doc_text_parts.append(
                f"[{doc_id}] ({doc.source_type}, {doc.platform}) {title}: {preview}"
            )
            await self.emit(
                "doc_seen",
                {
                    "doc_id": str(doc_id),
                    "title": title[:80],
                    "source": doc.source_type,
                    "platform": doc.platform,
                },
            )

        if not doc_text_parts:
            raise ValueError("当前事件没有可供分析的文档正文，无法抽取归因观点。")

        doc_text = "\n".join(doc_text_parts)
        output = await self._run_llm(
            event_title=event.title,
            entity_lines=entity_lines,
            doc_text=doc_text,
        )
        valid_items = self._valid_opinions(
            output.opinions,
            valid_doc_ids=valid_doc_ids,
            valid_entity_ids=valid_entity_ids,
        )

        now = datetime.now(UTC)
        rows = [
            OpinionRecord(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                event_id=event_id,
                document_id=item.document_id,
                target_entity_id=item.target_entity_id,
                stance=item.stance,
                emotion=item.emotion,
                reason=item.reason,
                claim_type=item.claim_type,
                evidence_span=item.evidence_span,
                model_confidence=item.confidence,
                model_version=self.model_version,
                prompt_version=f"{PROMPT_VERSION}/{AGENT_VERSION}",
                input_hash=input_hash,
                created_at=now,
            )
            for item in valid_items
        ]

        if rows:
            self.session.add_all(rows)
            await self.session.commit()

        for row in rows:
            await self.emit(
                "opinion_accepted",
                {
                    "id": str(row.id),
                    "stance": row.stance,
                    "emotion": row.emotion,
                    "claim_type": row.claim_type,
                    "confidence": float(row.model_confidence),
                    "target_entity_id": (
                        str(row.target_entity_id) if row.target_entity_id else None
                    ),
                    "reason": row.reason,
                },
            )

        logger.info(
            "OpinionExtraction: generated %d opinions for event %s",
            len(rows),
            event_id,
        )
        return rows

