import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from risktrace.agents.opinion import OpinionExtractor
from risktrace.api.schemas.agents import AgentRunResponse, OpinionItem, OpinionListResponse
from risktrace.db.models import Event, OpinionRecord
from risktrace.db.session import get_db

router = APIRouter(prefix="/events", tags=["opinions"])


@router.post("/{event_id}/extract-opinions", response_model=AgentRunResponse)
async def extract_opinions(
    event_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> AgentRunResponse:
    event = await db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    extractor = OpinionExtractor(db)
    records = await extractor.extract_for_event(event_id)

    doc_ids = {r.document_id for r in records}
    return AgentRunResponse(
        status="success" if records else "empty",
        message=f"Extracted {len(records)} opinions from {len(doc_ids)} documents",
        processed_count=len(doc_ids),
        extracted_count=len(records),
        event_id=event_id,
    )


@router.get("/{event_id}/opinions", response_model=OpinionListResponse)
async def list_opinions(
    event_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> OpinionListResponse:
    event = await db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    count_q = select(func.count()).select_from(OpinionRecord).where(
        OpinionRecord.event_id == event_id
    )
    total = (await db.execute(count_q)).scalar_one()

    items_q = (
        select(OpinionRecord)
        .where(OpinionRecord.event_id == event_id)
        .order_by(OpinionRecord.created_at.desc())
    )
    records = (await db.execute(items_q)).scalars().all()

    return OpinionListResponse(
        items=[OpinionItem.model_validate(r) for r in records],
        total=total,
    )
