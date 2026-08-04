from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from risktrace.api.schemas.events import (
    EventDetail,
    EventListResponse,
    EventSummary,
    EvidenceItem,
    EvidenceListResponse,
    LinkedDocument,
    TimelineBucket,
    WorkspaceResponse,
)
from risktrace.db.models import Event, EventDocument, RawDocument
from risktrace.db.session import get_db

router = APIRouter(prefix="/events", tags=["events"])


async def _build_event_summary(session: AsyncSession, event: Event) -> EventSummary:
    doc_count_result = await session.execute(
        select(func.count(EventDocument.document_id)).where(
            EventDocument.event_id == event.id
        )
    )
    doc_count = doc_count_result.scalar() or 0

    breakdown_result = await session.execute(
        select(RawDocument.source_type, func.count(RawDocument.id))
        .join(EventDocument, EventDocument.document_id == RawDocument.id)
        .where(EventDocument.event_id == event.id)
        .group_by(RawDocument.source_type)
    )
    source_breakdown = {row[0]: row[1] for row in breakdown_result.all()}

    latest_result = await session.execute(
        select(func.max(RawDocument.published_at))
        .join(EventDocument, EventDocument.document_id == RawDocument.id)
        .where(EventDocument.event_id == event.id)
    )
    latest_activity = latest_result.scalar()

    return EventSummary(
        id=event.id,
        title=event.title,
        status=event.status,
        first_published_at=event.first_published_at,
        document_count=doc_count,
        source_breakdown=source_breakdown,
        latest_activity=latest_activity,
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


@router.get("", response_model=EventListResponse)
async def list_events(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> EventListResponse:
    query = select(Event).order_by(Event.first_published_at.desc())
    if status:
        query = query.where(Event.status == status)

    count_query = select(func.count()).select_from(Event)
    if status:
        count_query = count_query.where(Event.status == status)
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * page_size
    result = await session.execute(query.offset(offset).limit(page_size))
    events = result.scalars().all()

    items = []
    for event in events:
        summary = await _build_event_summary(session, event)
        items.append(summary)

    return EventListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{event_id}", response_model=EventDetail)
async def get_event(
    event_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> EventDetail:
    event = await session.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="事件未找到")
    return await _build_event_summary(session, event)


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
    session: AsyncSession = Depends(get_db),
) -> WorkspaceResponse:
    event = await session.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="事件未找到")

    result = await session.execute(
        select(RawDocument)
        .join(EventDocument, EventDocument.document_id == RawDocument.id)
        .where(EventDocument.event_id == event_id)
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

    event_summary = await _build_event_summary(session, event)
    return WorkspaceResponse(event=event_summary, timeline=timeline, linked_documents=linked)


@router.get("/{event_id}/evidence", response_model=EvidenceListResponse)
async def list_evidence(
    event_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    source_type: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> EvidenceListResponse:
    event = await session.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="事件未找到")

    count_base = (
        select(func.count(RawDocument.id))
        .join(EventDocument, EventDocument.document_id == RawDocument.id)
        .where(EventDocument.event_id == event_id)
    )
    query_base = (
        select(RawDocument)
        .join(EventDocument, EventDocument.document_id == RawDocument.id)
        .where(EventDocument.event_id == event_id)
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
            source_url=d.source_url,
            engagement=d.engagement,
            raw_text_preview=(d.raw_text or "")[:500],
        )
        for d in documents
    ]

    return EvidenceListResponse(items=items, total=total, page=page, page_size=page_size)
