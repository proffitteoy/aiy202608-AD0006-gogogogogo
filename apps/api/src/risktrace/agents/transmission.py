"""Transmission graph generation over an OpenAI-compatible chat API.

Evidence-constrained output: every edge must reference node IDs and document IDs
that already exist in the database for the current event context.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from collections.abc import Iterable
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
    TransmissionEdge,
)

logger = logging.getLogger(__name__)

MAX_EDGES = 8
AGENT_VERSION = "0.3.0"
PROMPT_VERSION = "v3"
DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1/"
CHAT_COMPLETIONS_PATH = "chat/completions"
LLM_TIMEOUT_SECONDS = 45.0

TransmissionNodeType = Literal["entity", "sector", "event"]
TransmissionDirection = Literal["positive", "negative", "uncertain"]
TransmissionHorizon = Literal["immediate", "short", "medium", "long"]


class TransmissionEdgeItem(BaseModel):
    from_node_type: TransmissionNodeType
    from_node_id: uuid.UUID
    to_node_type: TransmissionNodeType
    to_node_id: uuid.UUID
    mechanism: str = Field(min_length=1, max_length=400)
    direction: TransmissionDirection
    horizon: TransmissionHorizon
    evidence_doc_ids: list[uuid.UUID] = Field(min_length=1, max_length=6)
    confidence: float = Field(ge=0.0, le=1.0)


class TransmissionOutput(BaseModel):
    edges: list[TransmissionEdgeItem] = Field(max_length=MAX_EDGES)


def _build_system_prompt() -> str:
    return (
        "你是金融事件传导分析助手。"
        "请基于给定事件、节点列表、文档和观点标记，输出事件可能如何沿产业链、供应链或市场情绪传导。"
        "\n\n规则：\n"
        "- 只能引用输入里已经出现的 node ID 和 document ID。\n"
        "- 每条边至少引用 1 个 document ID，且不要超过 6 个。\n"
        "- mechanism 用中文简洁描述传导机制，1 到 2 句话。\n"
        "- direction 只能是 positive、negative、uncertain。\n"
        "- horizon 只能是 immediate、short、medium、long。\n"
        "- from_node_type / to_node_type 只能是 entity、sector、event。\n"
        "- 最多输出 8 条边，优先保留置信度最高、证据最直接的候选。\n"
        "- 根值必须是 JSON 对象，且结构严格为 {\"edges\": [...]}。\n"
        "- edges 中每项只能使用 from_node_type、from_node_id、to_node_type、"
        "to_node_id、mechanism、direction、horizon、evidence_doc_ids、confidence 字段。\n"
        "- 只输出严格 JSON，不要附带 Markdown、解释或代码块。"
    )


def _build_user_prompt(event_title: str, node_lines: str, doc_text: str) -> str:
    return (
        f"事件标题：{event_title}\n\n"
        f"可用节点（ID: 名称）:\n{node_lines}\n\n"
        f"可用文档:\n{doc_text}\n\n"
        "请输出该事件的传导候选边。"
    )


class TransmissionGraphAgent:
    def __init__(
        self,
        session: AsyncSession,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.session = session
        self.settings = get_settings()
        self.transport = transport
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
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
            text = "".join(parts)
        else:
            text = ""

        text = TransmissionGraphAgent._strip_code_fence(text)
        if not text:
            raise RuntimeError("LLM 返回内容为空。")
        return text

    async def _run_llm(
        self,
        *,
        event_title: str,
        node_lines: str,
        doc_text: str,
    ) -> TransmissionOutput:
        request_body: dict[str, Any] = {
            "model": self.settings.llm_model,
            "messages": [
                {"role": "system", "content": _build_system_prompt()},
                {
                    "role": "user",
                    "content": _build_user_prompt(event_title, node_lines, doc_text),
                },
            ],
            "temperature": self.settings.llm_temperature,
            "max_tokens": self.settings.llm_max_tokens,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "transmission_output",
                    "strict": True,
                    "schema": TransmissionOutput.model_json_schema(),
                },
            },
        }
        if self.settings.llm_provider.strip().lower() == "deepseek":
            request_body["response_format"] = {"type": "json_object"}
            request_body["thinking"] = {"type": "disabled"}

        try:
            async with self._client() as client:
                response = await client.post(CHAT_COMPLETIONS_PATH, json=request_body)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text.strip()[:500]
            raise RuntimeError(
                f"LLM 接口返回 HTTP {exc.response.status_code}: {detail or 'empty response'}"
            ) from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"LLM 请求失败：{exc}") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise RuntimeError("LLM 返回了非 JSON 响应。") from exc

        content = self._message_text(payload)
        try:
            return TransmissionOutput.model_validate_json(content)
        except ValidationError as exc:
            raise RuntimeError(f"LLM 输出未通过 schema 校验：{exc}") from exc

    @staticmethod
    def _valid_edges(
        items: Iterable[TransmissionEdgeItem],
        *,
        valid_node_ids: frozenset[uuid.UUID],
        valid_doc_ids: frozenset[uuid.UUID],
    ) -> list[TransmissionEdgeItem]:
        valid_items: list[TransmissionEdgeItem] = []

        for index, edge in enumerate(items):
            if edge.from_node_id not in valid_node_ids:
                logger.warning(
                    "edge[%d] from_node_id=%s not in node registry, skipping",
                    index,
                    edge.from_node_id,
                )
                continue
            if edge.to_node_id not in valid_node_ids:
                logger.warning(
                    "edge[%d] to_node_id=%s not in node registry, skipping",
                    index,
                    edge.to_node_id,
                )
                continue

            invalid_docs = [
                doc_id for doc_id in edge.evidence_doc_ids if doc_id not in valid_doc_ids
            ]
            if invalid_docs:
                logger.warning(
                    "edge[%d] contains invalid evidence ids %s, skipping",
                    index,
                    ",".join(str(doc_id) for doc_id in invalid_docs),
                )
                continue

            valid_items.append(edge)

        valid_items.sort(key=lambda item: item.confidence, reverse=True)
        return valid_items[:MAX_EDGES]

    async def generate_for_event(self, event_id: uuid.UUID) -> list[TransmissionEdge]:
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
            raise ValueError("当前事件没有关联文档，无法生成传导假设。")

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
            raise ValueError("当前事件缺少可读取的原始文档，无法生成传导假设。")

        entity_rows = (
            await self.session.execute(
                select(Entity).where(Entity.tenant_id == tenant_id)
            )
        ).scalars().all()
        entity_labels = {entity.id: entity.name for entity in entity_rows}
        node_labels = {event.id: event.title, **entity_labels}
        valid_node_ids = frozenset(node_labels.keys())
        valid_doc_ids = frozenset(docs_by_id.keys())

        input_hash = self._input_hash(event_id, doc_ids)
        existing = await self.session.execute(
            select(TransmissionEdge).where(
                TransmissionEdge.event_id == event_id,
                TransmissionEdge.tenant_id == tenant_id,
                TransmissionEdge.input_hash == input_hash,
            )
        )
        if existing.scalars().first() is not None:
            logger.info(
                "TransmissionGraph: edges already exist for input_hash=%s",
                input_hash[:12],
            )
            return []

        opinion_rows = (
            await self.session.execute(
                select(OpinionRecord).where(
                    OpinionRecord.event_id == event_id,
                    OpinionRecord.tenant_id == tenant_id,
                )
            )
        ).scalars().all()
        opinion_docs = {opinion.document_id for opinion in opinion_rows}

        doc_text_parts: list[str] = []
        for doc_id in doc_ids:
            doc = docs_by_id.get(doc_id)
            if doc is None:
                continue
            title = doc.title or "（无标题）"
            preview = (doc.raw_text or "").strip()[:240]
            if not preview:
                preview = title
            opinion_marker = " [含观点标注]" if doc_id in opinion_docs else ""
            doc_text_parts.append(
                f"[{doc_id}] ({doc.source_type}, {doc.platform}){opinion_marker} "
                f"{title}: {preview}"
            )

        if not doc_text_parts:
            raise ValueError("当前事件没有可供分析的文档正文，无法生成传导假设。")

        node_lines = "\n".join(
            f"  {node_id}: {node_labels.get(node_id, 'unknown')}"
            for node_id in sorted(valid_node_ids, key=str)
        )
        doc_text = "\n".join(doc_text_parts)

        output = await self._run_llm(
            event_title=event.title,
            node_lines=node_lines,
            doc_text=doc_text,
        )
        valid_items = self._valid_edges(
            output.edges,
            valid_node_ids=valid_node_ids,
            valid_doc_ids=valid_doc_ids,
        )

        now = datetime.now(UTC)
        edges = [
            TransmissionEdge(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                event_id=event_id,
                from_node_type=item.from_node_type,
                from_node_id=item.from_node_id,
                to_node_type=item.to_node_type,
                to_node_id=item.to_node_id,
                mechanism=item.mechanism,
                direction=item.direction,
                horizon=item.horizon,
                evidence_ids=[str(doc_id) for doc_id in item.evidence_doc_ids],
                knowledge_ids=[],
                model_confidence=item.confidence,
                status="candidate",
                model_version=self.model_version,
                prompt_version=f"{PROMPT_VERSION}/{AGENT_VERSION}",
                input_hash=input_hash,
                created_at=now,
            )
            for item in valid_items
        ]

        if edges:
            self.session.add_all(edges)
            await self.session.commit()

        logger.info(
            "TransmissionGraph: generated %d edges for event %s",
            len(edges),
            event_id,
        )
        return edges
