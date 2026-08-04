import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from risktrace.agents.transmission import TransmissionGraphAgent
from risktrace.api.schemas.agents import (
    AgentRunResponse,
    TransmissionEdgeItem,
    TransmissionListResponse,
)
from risktrace.db.models import Event, TransmissionEdge
from risktrace.db.session import get_db

router = APIRouter(prefix="/events", tags=["transmission"])


@router.post("/{event_id}/generate-transmission", response_model=AgentRunResponse)
async def generate_transmission(
    event_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> AgentRunResponse:
    event = await db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    agent = TransmissionGraphAgent(db)
    edges = await agent.generate_for_event(event_id)

    return AgentRunResponse(
        status="success" if edges else "empty",
        message=f"Generated {len(edges)} candidate transmission edges",
        processed_count=len(edges),
        extracted_count=len(edges),
        event_id=event_id,
    )


@router.get("/{event_id}/transmission", response_model=TransmissionListResponse)
async def list_transmission(
    event_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> TransmissionListResponse:
    event = await db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    count_q = select(func.count()).select_from(TransmissionEdge).where(
        TransmissionEdge.event_id == event_id
    )
    total = (await db.execute(count_q)).scalar_one()

    items_q = (
        select(TransmissionEdge)
        .where(TransmissionEdge.event_id == event_id)
        .order_by(TransmissionEdge.created_at.desc())
    )
    edges = (await db.execute(items_q)).scalars().all()

    return TransmissionListResponse(
        items=[TransmissionEdgeItem.model_validate(e) for e in edges],
        total=total,
    )
