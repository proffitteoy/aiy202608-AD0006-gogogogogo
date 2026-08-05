"""SSE endpoint that streams AnalysisPipeline stage events to the workbench.

The route runs the pipeline inside an ``asyncio.Task`` and forwards every
``(event_name, payload)`` tuple over ``text/event-stream`` using the standard
SSE framing. A heartbeat comment is emitted every few seconds so intermediate
proxies (nginx, next.js proxy route) do not close the connection.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from risktrace.agents.pipeline import AnalysisPipeline
from risktrace.core.demo import get_demo_tenant_id
from risktrace.db.models import Event
from risktrace.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["pipeline"])
DemoTenantId = Annotated[uuid.UUID, Depends(get_demo_tenant_id)]
DbSession = Annotated[AsyncSession, Depends(get_db)]

HEARTBEAT_INTERVAL_SECONDS = 5.0
SENTINEL: tuple[str, dict[str, Any]] = ("__done__", {})


def _sse(event: str, data: dict[str, Any]) -> bytes:
    body = json.dumps(data, ensure_ascii=False, default=str)
    return f"event: {event}\ndata: {body}\n\n".encode("utf-8")


@router.post("/{event_id}/analyze/stream")
async def analyze_stream(
    event_id: uuid.UUID,
    tenant_id: DemoTenantId,
    db: DbSession,
    request: Request,
    force: bool = False,
) -> StreamingResponse:
    event = await db.scalar(
        select(Event).where(Event.id == event_id, Event.tenant_id == tenant_id)
    )
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    queue: asyncio.Queue[tuple[str, dict[str, Any]]] = asyncio.Queue(maxsize=128)

    async def emit(event_name: str, payload: dict[str, Any]) -> None:
        await queue.put((event_name, payload))

    pipeline = AnalysisPipeline(session=db, event_id=event_id, emit=emit, force=force)

    async def run_and_close() -> None:
        try:
            await pipeline.run()
        except Exception as exc:  # noqa: BLE001 -- surface via SSE, do not raise into loop
            logger.exception("Pipeline task crashed")
            try:
                await queue.put(("fatal", {"error": str(exc)}))
            except Exception:  # noqa: BLE001
                pass
        finally:
            await queue.put(SENTINEL)

    async def event_stream():
        task = asyncio.create_task(run_and_close())
        try:
            while True:
                if await request.is_disconnected():
                    task.cancel()
                    break
                try:
                    event_name, payload = await asyncio.wait_for(
                        queue.get(),
                        timeout=HEARTBEAT_INTERVAL_SECONDS,
                    )
                except asyncio.TimeoutError:
                    # keep-alive comment; browsers ignore lines starting with ":"
                    yield b": heartbeat\n\n"
                    continue

                if event_name == SENTINEL[0]:
                    break
                yield _sse(event_name, payload)
        finally:
            if not task.done():
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):  # noqa: BLE001
                    pass

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
