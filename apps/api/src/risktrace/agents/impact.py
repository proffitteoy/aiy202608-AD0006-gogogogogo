"""Impact matrix — deterministic computation from transmission edges + opinions."""

from __future__ import annotations

import asyncio
import uuid
from collections import Counter
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from risktrace.core.demo import get_demo_tenant_id
from risktrace.db.models import (
    Entity,
    Event,
    EventDocument,
    OpinionRecord,
    RawDocument,
    TransmissionEdge,
)

EmitFn = Callable[[str, dict[str, Any]], Awaitable[None]]

DIRECTION_ORDER = {"positive": 0, "uncertain": 1, "negative": 2}
HORIZON_ORDER = {"immediate": 0, "short": 1, "medium": 2, "long": 3}


def _normalize_uuid(value: uuid.UUID | str) -> uuid.UUID | None:
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        return None


@dataclass(frozen=True, slots=True)
class ImpactRow:
    entity_id: uuid.UUID
    entity_name: str
    entity_type: str
    direction: str  # positive | negative | uncertain | neutral
    impact_strength: float  # 0-1
    business_exposure: float  # 0-1
    opinion_support: float  # 0-1
    fact_support: float  # 0-1
    time_horizon: str  # immediate | short | medium | long | unknown
    composite_confidence: float  # 0-1
    edge_count: int
    opinion_count: int
    evidence_count: int
    evidence_ids: list[uuid.UUID]


async def compute_impact_matrix(
    event_id: uuid.UUID,
    session: AsyncSession,
    *,
    emit: EmitFn | None = None,
    row_delay: float = 0.0,
) -> list[ImpactRow]:
    tenant_id = get_demo_tenant_id()

    event = await session.scalar(
        select(Event).where(Event.id == event_id, Event.tenant_id == tenant_id)
    )
    if event is None:
        raise ValueError(f"Event {event_id} not found")

    edges = (
        await session.execute(
            select(TransmissionEdge).where(
                TransmissionEdge.event_id == event_id,
                TransmissionEdge.tenant_id == tenant_id,
            )
        )
    ).scalars().all()

    opinions = (
        await session.execute(
            select(OpinionRecord).where(
                OpinionRecord.event_id == event_id,
                OpinionRecord.tenant_id == tenant_id,
            )
        )
    ).scalars().all()

    event_docs = (
        await session.execute(
            select(EventDocument).where(EventDocument.event_id == event_id)
        )
    ).scalars().all()
    event_doc_ids = {ed.document_id for ed in event_docs}

    all_entity_ids: set[uuid.UUID] = set()
    for edge in edges:
        all_entity_ids.add(edge.from_node_id)
        all_entity_ids.add(edge.to_node_id)
    for op in opinions:
        if op.target_entity_id:
            all_entity_ids.add(op.target_entity_id)

    entity_rows = (
        await session.execute(
            select(Entity).where(
                Entity.id.in_(all_entity_ids),
                Entity.tenant_id == tenant_id,
            )
        )
    ).scalars().all()
    entities_by_id = {e.id: e for e in entity_rows}

    total_edges = len(edges)
    max_edge_count = max(1, total_edges)

    entity_edge_map: dict[uuid.UUID, list[TransmissionEdge]] = {}
    for edge in edges:
        entity_edge_map.setdefault(edge.from_node_id, []).append(edge)
        entity_edge_map.setdefault(edge.to_node_id, []).append(edge)

    entity_opinion_map: dict[uuid.UUID, list[OpinionRecord]] = {}
    for op in opinions:
        if op.target_entity_id:
            entity_opinion_map.setdefault(op.target_entity_id, []).append(op)

    doc_rows = (
        await session.execute(
            select(RawDocument).where(
                RawDocument.id.in_(event_doc_ids),
                RawDocument.tenant_id == tenant_id,
            )
        )
    ).scalars().all()
    fact_doc_ids = {d.id for d in doc_rows if d.source_type in ("fact", "news")}

    rows: list[ImpactRow] = []
    ordered_entities = sorted(all_entity_ids, key=str)
    total_candidates = len(ordered_entities)
    if emit is not None:
        await emit(
            "matrix_scan_start",
            {"total": total_candidates},
        )

    for cursor, entity_id in enumerate(ordered_entities, start=1):
        entity = entities_by_id.get(entity_id)
        if entity is None:
            continue

        entity_edges = entity_edge_map.get(entity_id, [])
        entity_ops = entity_opinion_map.get(entity_id, [])

        if not entity_edges and not entity_ops:
            if emit is not None:
                await emit(
                    "entity_skipped",
                    {"name": entity.name, "index": cursor, "total": total_candidates},
                )
            continue

        incoming_dirs = [
            e.direction
            for e in entity_edges
            if e.to_node_id == entity_id
        ]
        if not incoming_dirs:
            direction = "neutral"
        else:
            dir_counter = Counter(incoming_dirs)
            direction = dir_counter.most_common(1)[0][0]

        edge_count = len(entity_edges)
        impact_strength = round(
            sum(e.model_confidence for e in entity_edges) / max(1, edge_count),
            2,
        )
        business_exposure = round(edge_count / max_edge_count, 2)

        opinion_count = len(entity_ops)
        if opinion_count > 0:
            bullish = sum(1 for o in entity_ops if o.stance == "bullish")
            bearish = sum(1 for o in entity_ops if o.stance == "bearish")
            opinion_support = round(abs(bullish - bearish) / opinion_count, 2)
        else:
            opinion_support = 0.0

        evidence_ids = sorted(
            {
                normalized
                for edge in entity_edges
                for raw_evidence_id in (edge.evidence_ids or [])
                if (
                    normalized := _normalize_uuid(raw_evidence_id)
                ) is not None
                and normalized in event_doc_ids
            },
            key=str,
        )
        fact_count = sum(1 for evidence_id in evidence_ids if evidence_id in fact_doc_ids)
        fact_support = round(fact_count / max(1, edge_count * 2), 2)
        fact_support = min(fact_support, 1.0)

        horizons = [e.horizon for e in entity_edges]
        if horizons:
            time_horizon = min(horizons, key=lambda h: HORIZON_ORDER.get(h, 99))
        else:
            time_horizon = "unknown"

        composite_confidence = round(
            (
                impact_strength * 0.30
                + business_exposure * 0.20
                + opinion_support * 0.25
                + fact_support * 0.25
            ),
            2,
        )

        row = ImpactRow(
            entity_id=entity_id,
            entity_name=entity.name,
            entity_type=entity.entity_type,
            direction=direction,
            impact_strength=impact_strength,
            business_exposure=business_exposure,
            opinion_support=opinion_support,
            fact_support=fact_support,
            time_horizon=time_horizon,
            composite_confidence=composite_confidence,
            edge_count=edge_count,
            opinion_count=opinion_count,
            evidence_count=len(evidence_ids),
            evidence_ids=evidence_ids,
        )
        rows.append(row)

        if emit is not None:
            await emit(
                "entity_scored",
                {
                    "index": cursor,
                    "total": total_candidates,
                    "name": entity.name,
                    "direction": direction,
                    "score": composite_confidence,
                    "edge_count": edge_count,
                    "opinion_count": opinion_count,
                },
            )
            if row_delay > 0:
                await asyncio.sleep(row_delay)

    rows.sort(key=lambda r: r.composite_confidence, reverse=True)
    return rows
