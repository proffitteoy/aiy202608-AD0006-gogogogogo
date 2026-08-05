"""Agent C: Transmission Graph — LLM-powered causal-transmission edge generation.

Evidence-constrained output: every edge must reference entity IDs and
document IDs that exist in the database.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field
from pydantic_ai import Agent
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
AGENT_VERSION = "0.2.0"
PROMPT_VERSION = "v2"


class TransmissionEdgeItem(BaseModel):
    from_node_type: str = Field(description="entity | sector | event")
    from_node_id: uuid.UUID
    to_node_type: str = Field(description="entity | sector | event")
    to_node_id: uuid.UUID
    mechanism: str = Field(description="1-2 sentence causal mechanism in Chinese")
    direction: str = Field(description="positive | negative | uncertain")
    horizon: str = Field(description="immediate | short | medium | long")
    evidence_doc_ids: list[uuid.UUID] = Field(description="document UUIDs backing this edge")
    confidence: float = Field(ge=0.0, le=1.0)


class TransmissionOutput(BaseModel):
    edges: list[TransmissionEdgeItem] = Field(max_length=MAX_EDGES)


def _build_system_prompt() -> str:
    return (
        "你是一个金融事件传导分析专家。给定一个事件、相关实体、文档和观点，"
        "推断事件影响会如何通过产业链、供应链或市场情绪传导。\n\n"
        "规则:\n"
        "- 每一条边必须引用至少一个真实存在的 document ID 作为证据\n"
        "- 每条边的 from/to entity ID 必须在提供的实体列表中\n"
        "- mechanism 用中文写，1-2句话描述传导机制\n"
        "- direction: positive(利好), negative(利空), uncertain(不确定)\n"
        "- horizon: immediate(即时), short(短期), medium(中期), long(长期)\n"
        "- 最多输出 8 条边，按置信度从高到低排列\n"
        "- 优先推断产业链上下游传导，其次考虑市场情绪传导"
    )


def _build_user_prompt(
    event_title: str,
    entity_lines: str,
    doc_text: str,
) -> str:
    return (
        f"事件: {event_title}\n\n"
        f"可用实体 (ID: 名称):\n{entity_lines}\n\n"
        f"可用文档:\n{doc_text}\n\n"
        "请推断事件影响传导路径，输出每条边的 from/to/mechanism/direction/horizon/evidence_doc_ids/confidence。"
    )


class TransmissionGraphAgent:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        settings = get_settings()

        import os

        os.environ.setdefault("OPENAI_API_KEY", settings.llm_api_key)
        os.environ.setdefault("OPENAI_BASE_URL", settings.llm_base_url)

        model_name = f"{settings.llm_provider}:{settings.llm_model}"
        self.agent: Agent[None, TransmissionOutput] = Agent(
            model=model_name,
            output_type=TransmissionOutput,
            system_prompt=_build_system_prompt(),
            model_settings={
                "temperature": settings.llm_temperature,
                "max_tokens": settings.llm_max_tokens,
            },
        )

    def _input_hash(self, event_id: uuid.UUID, doc_ids: list[uuid.UUID]) -> str:
        payload = json.dumps(
            {"event_id": str(event_id), "doc_ids": sorted(str(d) for d in doc_ids)},
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()

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

        doc_rows = (
            await self.session.execute(
                select(RawDocument).where(RawDocument.id.in_(doc_ids))
            )
        ).scalars().all()
        docs_by_id = {doc.id: doc for doc in doc_rows}

        entity_rows = (
            await self.session.execute(
                select(Entity).where(Entity.tenant_id == tenant_id)
            )
        ).scalars().all()
        entity_labels = {e.id: e.name for e in entity_rows}
        valid_entity_ids = frozenset(entity_labels.keys())
        valid_doc_ids = frozenset(docs_by_id.keys())

        input_hash = self._input_hash(event_id, doc_ids)
        existing = await self.session.execute(
            select(TransmissionEdge).where(
                TransmissionEdge.event_id == event_id,
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
                select(OpinionRecord).where(OpinionRecord.event_id == event_id)
            )
        ).scalars().all()
        opinion_docs = {op.document_id for op in opinion_rows}

        doc_text_parts: list[str] = []
        for doc_id in doc_ids:
            doc = docs_by_id.get(doc_id)
            if doc is None:
                continue
            has_opinions = " [含观点标注]" if doc_id in opinion_docs else ""
            doc_text_parts.append(
                f"[{doc_id}] ({doc.source_type}, {doc.platform}){has_opinions} "
                f"{doc.title}: {doc.raw_text[:240]}"
            )

        entity_lines = "\n".join(
            f"  {eid}: {entity_labels.get(eid, 'unknown')}"
            for eid in sorted(valid_entity_ids)
        )
        doc_text = "\n".join(doc_text_parts)

        prompt = _build_user_prompt(event.title, entity_lines, doc_text)

        # Validate result entities/docs against the registry
        result = await self.agent.run(prompt)
        output = result.output

        for i, edge in enumerate(output.edges):
            if edge.from_node_id not in valid_entity_ids:
                logger.warning(
                    "edge[%d] from_node_id=%s not in entity registry, skipping",
                    i, edge.from_node_id,
                )
                continue
            if edge.to_node_id not in valid_entity_ids:
                logger.warning(
                    "edge[%d] to_node_id=%s not in entity registry, skipping",
                    i, edge.to_node_id,
                )
                continue
            for doc_id in edge.evidence_doc_ids:
                if doc_id not in valid_doc_ids:
                    logger.warning(
                        "edge[%d] evidence_doc_id=%s not in available docs, skipping",
                        i, doc_id,
                    )
                    continue

        now = datetime.now(UTC)
        edges: list[TransmissionEdge] = []
        for item in output.edges:
            if item.from_node_id not in valid_entity_ids:
                continue
            if item.to_node_id not in valid_entity_ids:
                continue
            if any(doc_id not in valid_doc_ids for doc_id in item.evidence_doc_ids):
                continue

            edges.append(
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
                    evidence_ids=[str(d) for d in item.evidence_doc_ids],
                    knowledge_ids=[],
                    model_confidence=item.confidence,
                    status="candidate",
                    model_version=AGENT_VERSION,
                    prompt_version=PROMPT_VERSION,
                    input_hash=input_hash,
                    created_at=now,
                )
            )

        self.session.add_all(edges)
        await self.session.commit()
        logger.info(
            "TransmissionGraph: generated %d edges for event %s", len(edges), event_id
        )
        return edges
