from datetime import timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from risktrace.api.schemas.events import (
    EventDetail,
    EventListResponse,
    EventScoreSummary,
    EventSummary,
    EvidenceItem,
    EvidenceListResponse,
    LinkedDocument,
    ScoreInterval,
    TimelineBucket,
    WorkspaceResponse,
)
from risktrace.core.demo import get_demo_tenant_id
from risktrace.db.models import Event, EventDocument, EventScoreCalibration, RawDocument
from risktrace.db.session import get_db

router = APIRouter(prefix="/events", tags=["events"])
DemoTenantId = Annotated[UUID, Depends(get_demo_tenant_id)]
DbSession = Annotated[AsyncSession, Depends(get_db)]


def _score_summary(
    event: Event,
    calibration: EventScoreCalibration | None,
) -> EventScoreSummary:
    if calibration is not None:
        return EventScoreSummary(
            status=calibration.calculation_status,
            raw_score=calibration.raw_score,
            calibrated_score=calibration.calibrated_score,
            confidence=calibration.confidence,
            score_interval=ScoreInterval(
                lower_bound=calibration.lower_bound,
                upper_bound=calibration.upper_bound,
            ),
            scoring_version=calibration.scoring_version,
            calibration_version=calibration.calibration_version,
            calculation_id=calibration.calculation_id,
            score_calculation_id=calibration.score_calculation_id,
            degradation_reasons=list(calibration.degradation_reasons),
        )

    cached_values = (
        event.raw_score,
        event.calibrated_score,
        event.score_confidence,
        event.score_lower_bound,
        event.score_upper_bound,
    )
    if all(value is None for value in cached_values):
        return EventScoreSummary(status="unavailable")

    score_interval = None
    if event.score_lower_bound is not None and event.score_upper_bound is not None:
        score_interval = ScoreInterval(
            lower_bound=event.score_lower_bound,
            upper_bound=event.score_upper_bound,
        )
    return EventScoreSummary(
        status="degraded",
        raw_score=event.raw_score,
        calibrated_score=event.calibrated_score,
        confidence=event.score_confidence,
        score_interval=score_interval,
        scoring_version=event.scoring_version,
        calibration_version=event.calibration_version,
        degradation_reasons=["calibration_record_unavailable"],
    )


async def _build_event_summary(
    session: AsyncSession,
    event: Event,
    tenant_id: UUID,
) -> EventSummary:
    doc_count_result = await session.execute(
        select(func.count(EventDocument.document_id))
        .join(RawDocument, RawDocument.id == EventDocument.document_id)
        .where(
            EventDocument.event_id == event.id,
            RawDocument.tenant_id == tenant_id,
        )
    )
    doc_count = doc_count_result.scalar() or 0

    breakdown_result = await session.execute(
        select(RawDocument.source_type, func.count(RawDocument.id))
        .join(EventDocument, EventDocument.document_id == RawDocument.id)
        .where(
            EventDocument.event_id == event.id,
            RawDocument.tenant_id == tenant_id,
        )
        .group_by(RawDocument.source_type)
    )
    source_breakdown = {row[0]: row[1] for row in breakdown_result.all()}

    latest_result = await session.execute(
        select(func.max(RawDocument.published_at))
        .join(EventDocument, EventDocument.document_id == RawDocument.id)
        .where(
            EventDocument.event_id == event.id,
            RawDocument.tenant_id == tenant_id,
        )
    )
    latest_activity = latest_result.scalar()

    calibration = await session.scalar(
        select(EventScoreCalibration)
        .where(
            EventScoreCalibration.event_id == event.id,
            EventScoreCalibration.tenant_id == tenant_id,
        )
        .order_by(
            EventScoreCalibration.snapshot_at.desc(),
            EventScoreCalibration.created_at.desc(),
        )
        .limit(1)
    )

    return EventSummary(
        id=event.id,
        title=event.title,
        status=event.status,
        first_published_at=event.first_published_at,
        document_count=doc_count,
        source_breakdown=source_breakdown,
        latest_activity=latest_activity,
        score=_score_summary(event, calibration),
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


@router.get("", response_model=EventListResponse)
async def list_events(
    tenant_id: DemoTenantId,
    session: DbSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
) -> EventListResponse:
    query = (
        select(Event)
        .where(Event.tenant_id == tenant_id)
        .order_by(Event.first_published_at.desc())
    )
    if status:
        query = query.where(Event.status == status)

    count_query = (
        select(func.count()).select_from(Event).where(Event.tenant_id == tenant_id)
    )
    if status:
        count_query = count_query.where(Event.status == status)
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * page_size
    result = await session.execute(query.offset(offset).limit(page_size))
    events = result.scalars().all()

    items = []
    for event in events:
        summary = await _build_event_summary(session, event, tenant_id)
        items.append(summary)

    return EventListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{event_id}", response_model=EventDetail)
async def get_event(
    event_id: UUID,
    tenant_id: DemoTenantId,
    session: DbSession,
) -> EventDetail:
    event = await session.scalar(
        select(Event).where(Event.id == event_id, Event.tenant_id == tenant_id)
    )
    if not event:
        raise HTTPException(status_code=404, detail="事件未找到")
    return await _build_event_summary(session, event, tenant_id)


def _compute_timeline(
    documents: list[RawDocument],
    num_buckets: int = 6,
) -> list[TimelineBucket]:
    if not documents:
        return []

    start = min(d.published_at for d in documents)
    end = max(d.published_at for d in documents)
    if start == end:
        end = start + timedelta(hours=1)

    span = (end - start) / num_buckets
    buckets: list[TimelineBucket] = []
    for i in range(num_buckets):
        bucket_start = start + span * i
        bucket_end = bucket_start + span
        counts: dict[str, int] = {}
        for d in documents:
            if bucket_start <= d.published_at < bucket_end or (
                i == num_buckets - 1 and d.published_at == bucket_end
            ):
                counts[d.source_type] = counts.get(d.source_type, 0) + 1
        buckets.append(
            TimelineBucket(
                bucket_start=bucket_start,
                bucket_end=bucket_end,
                counts=counts,
            )
        )
    return buckets


@router.get("/{event_id}/workspace", response_model=WorkspaceResponse)
async def get_workspace(
    event_id: UUID,
    tenant_id: DemoTenantId,
    session: DbSession,
) -> WorkspaceResponse:
    event = await session.scalar(
        select(Event).where(Event.id == event_id, Event.tenant_id == tenant_id)
    )
    if not event:
        raise HTTPException(status_code=404, detail="事件未找到")

    result = await session.execute(
        select(RawDocument)
        .join(EventDocument, EventDocument.document_id == RawDocument.id)
        .where(
            EventDocument.event_id == event_id,
            RawDocument.tenant_id == tenant_id,
        )
        .order_by(RawDocument.published_at.asc())
    )
    documents = result.scalars().all()

    timeline = _compute_timeline(list(documents))
    linked = [
        LinkedDocument(
            id=d.id,
            title=d.title,
            source_type=d.source_type,
            platform=d.platform,
            published_at=d.published_at,
            weight=1.0,
            engagement=d.engagement,
        )
        for d in documents
    ]

    event_summary = await _build_event_summary(session, event, tenant_id)
    return WorkspaceResponse(event=event_summary, timeline=timeline, linked_documents=linked)


@router.get("/{event_id}/evidence", response_model=EvidenceListResponse)
async def list_evidence(
    event_id: UUID,
    tenant_id: DemoTenantId,
    session: DbSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    source_type: str | None = Query(default=None),
) -> EvidenceListResponse:
    event = await session.scalar(
        select(Event).where(Event.id == event_id, Event.tenant_id == tenant_id)
    )
    if not event:
        raise HTTPException(status_code=404, detail="事件未找到")

    count_base = (
        select(func.count(RawDocument.id))
        .join(EventDocument, EventDocument.document_id == RawDocument.id)
        .where(
            EventDocument.event_id == event_id,
            RawDocument.tenant_id == tenant_id,
        )
    )
    query_base = (
        select(RawDocument)
        .join(EventDocument, EventDocument.document_id == RawDocument.id)
        .where(
            EventDocument.event_id == event_id,
            RawDocument.tenant_id == tenant_id,
        )
        .order_by(RawDocument.published_at.asc())
    )
    if source_type:
        count_base = count_base.where(RawDocument.source_type == source_type)
        query_base = query_base.where(RawDocument.source_type == source_type)

    total_result = await session.execute(count_base)
    total = total_result.scalar() or 0

    offset = (page - 1) * page_size
    result = await session.execute(query_base.offset(offset).limit(page_size))
    documents = result.scalars().all()

    items = [
        EvidenceItem(
            id=d.id,
            title=d.title,
            source_type=d.source_type,
            platform=d.platform,
            published_at=d.published_at,
            collected_at=d.collected_at,
            source_url=d.source_url,
            engagement=d.engagement,
            raw_text_preview=(d.raw_text or "")[:500],
            collection_method=d.collection_method,
            license_scope=d.license_scope,
        )
        for d in documents
    ]

    return EvidenceListResponse(items=items, total=total, page=page, page_size=page_size)
