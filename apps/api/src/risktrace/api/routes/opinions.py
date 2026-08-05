import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from risktrace.api.schemas.analysis import OpinionItem, OpinionListResponse
from risktrace.core.demo import get_demo_tenant_id
from risktrace.db.models import Event, OpinionRecord
from risktrace.db.session import get_db

router = APIRouter(prefix="/events", tags=["opinions"])
DemoTenantId = Annotated[uuid.UUID, Depends(get_demo_tenant_id)]
DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("/{event_id}/opinions", response_model=OpinionListResponse)
async def list_opinions(
    event_id: uuid.UUID,
    tenant_id: DemoTenantId,
    db: DbSession,
) -> OpinionListResponse:
    event = await db.scalar(
        select(Event).where(Event.id == event_id, Event.tenant_id == tenant_id)
    )
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    count_q = select(func.count()).select_from(OpinionRecord).where(
        OpinionRecord.event_id == event_id,
        OpinionRecord.tenant_id == tenant_id,
    )
    total = (await db.execute(count_q)).scalar_one()

    items_q = (
        select(OpinionRecord)
        .where(
            OpinionRecord.event_id == event_id,
            OpinionRecord.tenant_id == tenant_id,
        )
        .order_by(OpinionRecord.created_at.desc())
    )
    records = (await db.execute(items_q)).scalars().all()

    return OpinionListResponse(
        items=[OpinionItem.model_validate(r) for r in records],
        total=total,
    )
