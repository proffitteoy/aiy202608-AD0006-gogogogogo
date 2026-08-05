"""Entity extraction over an OpenAI-compatible chat API.

Reads the documents linked to an event, asks the LLM to enumerate the
"涉事主体" (companies / industries / regulators / other organizations) that the
event actually acts on, and either matches each result against an existing
``entities`` row for the current tenant or creates a new one.

The agent obeys the same constraints as ``TransmissionGraphAgent``:

- every claimed entity must cite at least one ``document_id`` that the caller
  supplied — the LLM cannot invent evidence,
- output goes through a strict Pydantic schema before it ever touches the
  database,
- streaming ``llm_start`` / ``llm_delta`` / ``llm_done`` events are surfaced
  through the shared ``emit`` callback so the pipeline can drive a live UI,
- re-runs are idempotent because entities are matched by (tenant, type, name)
  against existing rows; only genuinely new names are inserted.
"""

from __future__ import annotations

import json
import logging
import unicodedata
import uuid
from collections.abc import Awaitable, Callable, Iterable
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from risktrace.core.config import get_settings
from risktrace.core.demo import get_demo_tenant_id
from risktrace.db.models import Entity, Event, EventDocument, RawDocument

logger = logging.getLogger(__name__)

MAX_ENTITIES = 12
AGENT_VERSION = "0.1.0"
PROMPT_VERSION = "v1"
DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1/"
CHAT_COMPLETIONS_PATH = "chat/completions"
LLM_TIMEOUT_SECONDS = 45.0

EntityType = Literal["company", "industry", "organization", "person", "sector"]


class EntityItem(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    entity_type: EntityType
    canonical_code: str | None = Field(default=None, max_length=128)
    evidence_doc_ids: list[uuid.UUID] = Field(min_length=1, max_length=6)
    confidence: float = Field(ge=0.0, le=1.0)


class EntityExtraction(BaseModel):
    entities: list[EntityItem] = Field(max_length=MAX_ENTITIES)


class AcceptedEntity(BaseModel):
    """Return payload for the caller — always references a persisted row."""

    entity_id: uuid.UUID
    name: str
    entity_type: str
    canonical_code: str | None
    evidence_doc_ids: list[uuid.UUID]
    confidence: float
    reused: bool  # True when we matched an existing entities row


def _build_system_prompt() -> str:
    return (
        "你是金融事件涉事主体识别助手。"
        "请只根据用户给出的事件描述与文档，判断该事件直接作用于哪些"
        "公司、行业、监管机构或组织。\n\n"
        "规则：\n"
        "- 只输出确实在文档正文里被提及且与事件直接相关的主体，不要脑补。\n"
        "- entity_type 只能是 company、industry、organization、person、sector。\n"
        "- name 使用文档中最常见的中文全称，不要缩写、不要英文别名。\n"
        "- canonical_code 若无法从文档确认，请留空。\n"
        "- evidence_doc_ids 至少 1 个、最多 6 个，且必须来自输入的文档列表。\n"
        "- 最多输出 12 个主体，按相关性和证据强度排序。\n"
        "- 根值必须是 JSON 对象，且结构严格为 {\"entities\": [...]}。\n"
        "- entities 中每项只能使用 name、entity_type、canonical_code、"
        "evidence_doc_ids、confidence 字段。\n"
        "- 只输出严格 JSON，不要附带 Markdown、解释或代码块。"
    )


def _build_user_prompt(event_title: str, doc_text: str) -> str:
    return (
        f"事件标题：{event_title}\n\n"
        f"可用文档:\n{doc_text}\n\n"
        "请列出该事件的涉事主体候选。"
    )


EmitFn = Callable[[str, dict[str, Any]], Awaitable[None]]


async def _noop_emit(event: str, payload: dict[str, Any]) -> None:  # noqa: ARG001
    return None


def _normalize_name(name: str) -> str:
    """Fold width variants and whitespace so LLM-emitted names match seeded rows."""

    folded = unicodedata.normalize("NFKC", name).strip()
    return "".join(folded.split())


class EntityExtractionAgent:
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

        text = EntityExtractionAgent._strip_code_fence(text)
        if not text:
            raise RuntimeError("LLM 返回内容为空。")
        return text

    async def _run_llm(
        self,
        *,
        event_title: str,
        doc_text: str,
    ) -> EntityExtraction:
        request_body: dict[str, Any] = {
            "model": self.settings.llm_model,
            "messages": [
                {"role": "system", "content": _build_system_prompt()},
                {"role": "user", "content": _build_user_prompt(event_title, doc_text)},
            ],
            "temperature": self.settings.llm_temperature,
            "max_tokens": self.settings.llm_max_tokens,
            "stream": True,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "entity_extraction",
                    "strict": True,
                    "schema": EntityExtraction.model_json_schema(),
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
                                "skipping non-json stream frame: %s", payload_text[:80]
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
            return EntityExtraction.model_validate_json(content)
        except ValidationError as exc:
            raise RuntimeError(f"LLM 输出未通过 schema 校验：{exc}") from exc

    @staticmethod
    def _valid_entities(
        items: Iterable[EntityItem],
        *,
        valid_doc_ids: frozenset[uuid.UUID],
    ) -> list[EntityItem]:
        valid_items: list[EntityItem] = []
        seen_names: set[str] = set()
        for index, item in enumerate(items):
            invalid_docs = [
                doc_id for doc_id in item.evidence_doc_ids if doc_id not in valid_doc_ids
            ]
            if invalid_docs:
                logger.warning(
                    "entity[%d] name=%s references unknown docs %s, skipping",
                    index,
                    item.name,
                    ",".join(str(d) for d in invalid_docs),
                )
                continue
            key = _normalize_name(item.name)
            if not key or key in seen_names:
                continue
            seen_names.add(key)
            valid_items.append(item)

        valid_items.sort(key=lambda item: item.confidence, reverse=True)
        return valid_items[:MAX_ENTITIES]

    async def extract_for_event(self, event_id: uuid.UUID) -> list[AcceptedEntity]:
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
            raise ValueError("当前事件没有关联文档，无法抽取涉事主体。")

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
            raise ValueError("当前事件缺少可读取的原始文档，无法抽取涉事主体。")

        valid_doc_ids = frozenset(docs_by_id.keys())

        doc_text_parts: list[str] = []
        for doc_id in doc_ids:
            doc = docs_by_id.get(doc_id)
            if doc is None:
                continue
            title = doc.title or "（无标题）"
            preview = (doc.raw_text or "").strip()[:240]
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
            raise ValueError("当前事件没有可供分析的文档正文，无法抽取涉事主体。")

        doc_text = "\n".join(doc_text_parts)
        output = await self._run_llm(event_title=event.title, doc_text=doc_text)
        valid_items = self._valid_entities(output.entities, valid_doc_ids=valid_doc_ids)

        existing_rows = (
            await self.session.execute(
                select(Entity).where(Entity.tenant_id == tenant_id)
            )
        ).scalars().all()
        existing_by_norm: dict[tuple[str, str], Entity] = {
            (row.entity_type, _normalize_name(row.name)): row for row in existing_rows
        }

        accepted: list[AcceptedEntity] = []
        new_rows: list[Entity] = []
        for item in valid_items:
            norm = _normalize_name(item.name)
            key = (item.entity_type, norm)
            row = existing_by_norm.get(key)
            reused = row is not None
            if row is None:
                row = Entity(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    entity_type=item.entity_type,
                    name=item.name.strip(),
                    canonical_code=(item.canonical_code or None),
                )
                new_rows.append(row)
                existing_by_norm[key] = row

            accepted.append(
                AcceptedEntity(
                    entity_id=row.id,
                    name=row.name,
                    entity_type=row.entity_type,
                    canonical_code=row.canonical_code,
                    evidence_doc_ids=list(item.evidence_doc_ids),
                    confidence=item.confidence,
                    reused=reused,
                )
            )

        if new_rows:
            self.session.add_all(new_rows)
            await self.session.commit()

        for entry in accepted:
            await self.emit(
                "entity_accepted",
                {
                    "id": str(entry.entity_id),
                    "name": entry.name,
                    "type": entry.entity_type,
                    "canonical_code": entry.canonical_code,
                    "confidence": entry.confidence,
                    "reused": entry.reused,
                },
            )

        logger.info(
            "EntityExtraction: accepted %d entities (%d new) for event %s",
            len(accepted),
            len(new_rows),
            event_id,
        )
        return accepted
