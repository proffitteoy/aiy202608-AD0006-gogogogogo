import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from risktrace.agents.impact import compute_impact_matrix
from risktrace.api.schemas.impact import ImpactMatrixResponse, ImpactRowItem
from risktrace.core.demo import get_demo_tenant_id
from risktrace.db.models import Event
from risktrace.db.session import get_db

router = APIRouter(prefix="/events", tags=["impact"])
DemoTenantId = Annotated[uuid.UUID, Depends(get_demo_tenant_id)]
DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("/{event_id}/impact", response_model=ImpactMatrixResponse)
async def get_impact_matrix(
    event_id: uuid.UUID,
    tenant_id: DemoTenantId,
    db: DbSession,
) -> ImpactMatrixResponse:
    from sqlalchemy import select

    event = await db.scalar(
        select(Event).where(Event.id == event_id, Event.tenant_id == tenant_id)
    )
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    rows = await compute_impact_matrix(event_id, db)
    items = [ImpactRowItem.model_validate(r) for r in rows]
    return ImpactMatrixResponse(items=items, total=len(items))
