import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
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
from risktrace.db.session import get_db
from risktrace.reports.service import create_report_for_event, get_report_detail

router = APIRouter(prefix="/reports", tags=["reports"])
DemoTenantId = Annotated[uuid.UUID, Depends(get_demo_tenant_id)]
DbSession = Annotated[AsyncSession, Depends(get_db)]


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
