import asyncio
import contextlib
import json
import logging
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from risktrace.api.schemas.events import EvidenceItem
from risktrace.api.schemas.reports import (
    ReportCreateRequest,
    ReportCreateResponse,
    ReportDetailResponse,
    ReportEventSummary,
    ReportScoreInterval,
    ReportScoreSummary,
    ReportSectionItem,
    ReportStatementItem,
    SnapshotSummary,
)
from risktrace.core.demo import get_demo_tenant_id
from risktrace.db.models import Event
from risktrace.db.session import get_db
from risktrace.reports.pipeline import ReportPipeline
from risktrace.reports.service import create_report_for_event, get_report_detail

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])
DemoTenantId = Annotated[uuid.UUID, Depends(get_demo_tenant_id)]
DbSession = Annotated[AsyncSession, Depends(get_db)]

HEARTBEAT_INTERVAL_SECONDS = 5.0
SENTINEL: tuple[str, dict[str, Any]] = ("__done__", {})


def _sse(event: str, data: dict[str, Any]) -> bytes:
    body = json.dumps(data, ensure_ascii=False, default=str)
    return f"event: {event}\ndata: {body}\n\n".encode()


@router.post("", response_model=ReportCreateResponse, status_code=201)
async def create_report(
    request: ReportCreateRequest,
    tenant_id: DemoTenantId,
    db: DbSession,
) -> ReportCreateResponse:
    try:
        report = await create_report_for_event(
            db,
            tenant_id,
            request.event_id,
            format=request.format,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if "not found" in detail.lower() else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc

    return ReportCreateResponse.model_validate(report)


@router.get("/{report_id}", response_model=ReportDetailResponse)
async def get_report(
    report_id: uuid.UUID,
    tenant_id: DemoTenantId,
    db: DbSession,
) -> ReportDetailResponse:
    try:
        report, payload, snapshot = await get_report_detail(db, tenant_id, report_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    score_interval = None
    if payload.score.score_interval is not None:
        score_interval = ReportScoreInterval(
            lower_bound=payload.score.score_interval.lower_bound,
            upper_bound=payload.score.score_interval.upper_bound,
        )

    return ReportDetailResponse(
        id=report.id,
        event_id=report.event_id,
        snapshot_id=report.snapshot_id,
        format=report.format,
        status=report.status,
        title=report.title,
        summary=report.summary,
        render_engine=report.render_engine,
        brief_prompt_version=report.brief_prompt_version,
        body_html=report.body_html,
        evidence_ids=[uuid.UUID(value) for value in report.evidence_ids],
        calculation_ids=[uuid.UUID(value) for value in report.calculation_ids],
        degradation_reasons=list(report.degradation_reasons),
        created_at=report.created_at,
        snapshot=SnapshotSummary(
            id=snapshot.id,
            event_id=snapshot.event_id,
            snapshot_at=snapshot.snapshot_at,
            analysis_version=snapshot.analysis_version,
            score_status=snapshot.score_status,
            evidence_count=snapshot.evidence_count,
            source_count=snapshot.source_count,
            scoring_version=snapshot.scoring_version,
            calibration_version=snapshot.calibration_version,
        ),
        event=ReportEventSummary(
            id=payload.event.id,
            title=payload.event.title,
            status=payload.event.status,
            first_published_at=payload.event.first_published_at,
            source_count=payload.event.source_count,
            authoritative_source_count=payload.event.authoritative_source_count,
            source_breakdown=payload.event.source_breakdown,
            score=ReportScoreSummary(
                status=payload.score.status,
                raw_score=payload.score.raw_score,
                calibrated_score=payload.score.calibrated_score,
                confidence=payload.score.confidence,
                score_interval=score_interval,
                scoring_version=payload.score.scoring_version,
                calibration_version=payload.score.calibration_version,
                calculation_id=payload.score.calculation_id,
                score_calculation_id=payload.score.score_calculation_id,
                degradation_reasons=payload.score.degradation_reasons,
            ),
        ),
        sections=[
            ReportSectionItem(
                id=section["id"],
                title=section["title"],
                status=section["status"],
                items=[
                    ReportStatementItem.model_validate(item)
                    for item in section["items"]
                ],
            )
            for section in report.sections
        ],
        evidence=[
            EvidenceItem.model_validate(item.model_dump(mode="json"))
            for item in payload.evidence
        ],
    )


@router.post("/stream")
async def create_report_stream(
    request: Request,
    body: ReportCreateRequest,
    tenant_id: DemoTenantId,
    db: DbSession,
) -> StreamingResponse:
    """SSE 流：把报告生成的 9 个阶段实时推给前端。

    产生的事件类型与 ``/events/{id}/analyze/stream`` 保持一致：
    ``stage_start`` / ``stage_progress`` / ``stage_done`` / ``stage_error`` /
    ``llm_start`` / ``llm_delta`` / ``llm_done`` / ``done`` / ``fatal``。
    ``done`` 的 payload 里带 ``report_id``，供前端拿去 push 到详情页。
    """

    event = await db.scalar(
        select(Event).where(Event.id == body.event_id, Event.tenant_id == tenant_id)
    )
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    queue: asyncio.Queue[tuple[str, dict[str, Any]]] = asyncio.Queue(maxsize=128)

    async def emit(event_name: str, payload: dict[str, Any]) -> None:
        await queue.put((event_name, payload))

    pipeline = ReportPipeline(
        session=db,
        tenant_id=tenant_id,
        event_id=body.event_id,
        emit=emit,
    )

    async def run_and_close() -> None:
        try:
            await pipeline.run()
        except Exception as exc:  # noqa: BLE001 -- surface via SSE, no crash
            logger.exception("Report pipeline crashed")
            with contextlib.suppress(Exception):
                await queue.put(("fatal", {"error": str(exc)}))
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
                except TimeoutError:
                    yield b": heartbeat\n\n"
                    continue

                if event_name == SENTINEL[0]:
                    break
                yield _sse(event_name, payload)
        finally:
            if not task.done():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await task

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
