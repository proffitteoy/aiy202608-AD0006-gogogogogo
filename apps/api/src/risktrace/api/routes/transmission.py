import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
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
PLACEHOLDER_LLM_KEYS = frozenset(
    {
        "sk-your-key-here",
        "your-api-key",
        "changeme",
    }
)


def _load_agent_class():
    from risktrace.agents.transmission import TransmissionGraphAgent
    return TransmissionGraphAgent


def _has_usable_llm_api_key(value: str) -> bool:
    cleaned = value.strip()
    return bool(cleaned) and cleaned not in PLACEHOLDER_LLM_KEYS


def _is_llm_unavailable_error(exc: RuntimeError) -> bool:
    detail = str(exc)
    return (
        "LLM 请求失败" in detail
        or "All connection attempts failed" in detail
        or "Connection refused" in detail
        or "Name or service not known" in detail
        or "nodename nor servname provided" in detail
        or "Temporary failure in name resolution" in detail
        or "LLM 接口返回 HTTP 5" in detail
    )


def _build_agent(session: AsyncSession):
    from risktrace.core.config import get_settings

    settings = get_settings()
    if not _has_usable_llm_api_key(settings.llm_api_key):
        raise HTTPException(
            status_code=503,
            detail=(
                "当前环境未配置可用的 LLM API Key，"
                "请先在 .env 中设置真实的 RISKTRACE_LLM_API_KEY。"
            ),
        )
    return _load_agent_class()(session)


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

    try:
        agent = _build_agent(db)
        edges = await agent.generate_for_event(event_id)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        if _is_llm_unavailable_error(exc):
            raise HTTPException(
                status_code=503,
                detail=f"当前 LLM 服务不可达，传导候选暂时无法生成：{exc}",
            ) from exc
        raise HTTPException(
            status_code=502,
            detail=f"传导假设生成失败：{exc}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"传导假设生成失败：{exc}",
        ) from exc

    return {
        "status": "generated" if edges else "skipped",
        "event_id": str(event_id),
        "edge_count": len(edges),
    }


class TransmissionEdgeStatusUpdate(BaseModel):
    status: Literal["candidate", "confirmed", "rejected"]


@router.patch(
    "/{event_id}/transmission/{edge_id}",
    response_model=TransmissionEdgeItem,
)
async def update_transmission_edge(
    event_id: uuid.UUID,
    edge_id: uuid.UUID,
    payload: TransmissionEdgeStatusUpdate,
    tenant_id: DemoTenantId,
    db: DbSession,
) -> TransmissionEdgeItem:
    event = await db.scalar(
        select(Event).where(Event.id == event_id, Event.tenant_id == tenant_id)
    )
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    edge = await db.scalar(
        select(TransmissionEdge).where(
            TransmissionEdge.id == edge_id,
            TransmissionEdge.event_id == event_id,
            TransmissionEdge.tenant_id == tenant_id,
        )
    )
    if edge is None:
        raise HTTPException(status_code=404, detail="Transmission edge not found")

    edge.status = payload.status
    await db.commit()
    await db.refresh(edge)

    node_ids = {edge.from_node_id, edge.to_node_id}
    entity_rows = await db.execute(
        select(Entity).where(
            Entity.id.in_(node_ids),
            Entity.tenant_id == tenant_id,
        )
    )
    labels = {entity.id: entity.name for entity in entity_rows.scalars()}
    labels[event.id] = event.title

    return TransmissionEdgeItem.model_validate(edge).model_copy(
        update={
            "from_node_label": labels.get(edge.from_node_id),
            "to_node_label": labels.get(edge.to_node_id),
        }
    )
