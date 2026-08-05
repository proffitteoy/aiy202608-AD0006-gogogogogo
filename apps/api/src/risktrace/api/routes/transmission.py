import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from risktrace.api.schemas.analysis import (
    TransmissionEdgeItem,
    TransmissionListResponse,
)
from risktrace.core.demo import get_demo_tenant_id
from risktrace.db.models import Entity, Event, TransmissionEdge
from risktrace.db.session import get_db

router = APIRouter(prefix="/events", tags=["transmission"])
DemoTenantId = Annotated[uuid.UUID, Depends(get_demo_tenant_id)]
DbSession = Annotated[AsyncSession, Depends(get_db)]


def _build_agent(session: AsyncSession):
    from risktrace.agents.transmission import TransmissionGraphAgent
    from risktrace.core.config import get_settings

    settings = get_settings()
    if not settings.llm_api_key:
        raise HTTPException(
            status_code=503,
            detail="LLM API key not configured. Set RISKTRACE_LLM_API_KEY in .env",
        )
    return TransmissionGraphAgent(session)


@router.get("/{event_id}/transmission", response_model=TransmissionListResponse)
async def list_transmission(
    event_id: uuid.UUID,
    tenant_id: DemoTenantId,
    db: DbSession,
) -> TransmissionListResponse:
    event = await db.scalar(
        select(Event).where(Event.id == event_id, Event.tenant_id == tenant_id)
    )
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    count_q = select(func.count()).select_from(TransmissionEdge).where(
        TransmissionEdge.event_id == event_id,
        TransmissionEdge.tenant_id == tenant_id,
    )
    total = (await db.execute(count_q)).scalar_one()

    items_q = (
        select(TransmissionEdge)
        .where(
            TransmissionEdge.event_id == event_id,
            TransmissionEdge.tenant_id == tenant_id,
        )
        .order_by(TransmissionEdge.created_at.desc())
    )
    edges = (await db.execute(items_q)).scalars().all()

    node_ids = {
        node_id
        for edge in edges
        for node_id in (edge.from_node_id, edge.to_node_id)
    }
    entity_rows = await db.execute(
        select(Entity).where(
            Entity.id.in_(node_ids),
            Entity.tenant_id == tenant_id,
        )
    )
    labels = {entity.id: entity.name for entity in entity_rows.scalars()}
    labels[event.id] = event.title

    return TransmissionListResponse(
        items=[
            TransmissionEdgeItem.model_validate(edge).model_copy(
                update={
                    "from_node_label": labels.get(edge.from_node_id),
                    "to_node_label": labels.get(edge.to_node_id),
                }
            )
            for edge in edges
        ],
        total=total,
    )


@router.post("/{event_id}/transmission/generate", status_code=202)
async def generate_transmission(
    event_id: uuid.UUID,
    tenant_id: DemoTenantId,
    db: DbSession,
) -> dict[str, object]:
    event = await db.scalar(
        select(Event).where(Event.id == event_id, Event.tenant_id == tenant_id)
    )
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    agent = _build_agent(db)
    try:
        edges = await agent.generate_for_event(event_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Transmission generation failed: {exc}",
        ) from exc

    return {
        "status": "generated" if edges else "skipped",
        "event_id": str(event_id),
        "edge_count": len(edges),
    }
