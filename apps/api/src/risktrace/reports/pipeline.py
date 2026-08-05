"""Report generation pipeline with SSE stage events.

Wires the LLM section agent into the existing template render so the UI can
observe report generation stage-by-stage, similar to ``agents/pipeline.py``.
Stages emit ``stage_start`` / ``stage_progress`` / ``stage_done`` /
``stage_error`` events; ``done`` at the very end carries ``report_id``.

LLM stages (``overview`` / ``recommendations`` / ``risk-notes``) degrade
silently to the baseline template on any failure — the pipeline never fails
just because the LLM is down.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from risktrace.core.config import get_settings
from risktrace.db.models import Report
from risktrace.reports.agent import (
    ReportSectionAgent,
    ReportSectionLLMError,
    valid_statements,
)
from risktrace.reports.prompts import SectionKey
from risktrace.reports.schemas import (
    AnalysisSnapshotPayload,
    RenderedReport,
    SnapshotEventSummary,
    SnapshotEvidenceItem,
    SnapshotImpactRow,
    SnapshotOpinionItem,
    SnapshotScoreSummary,
    SnapshotTransmissionEdge,
)
from risktrace.reports.service import (
    BRIEF_PROMPT_VERSION,
    TEMPLATE_RENDER_ENGINE,
    _freeze_snapshot,
    build_llm_section,
    finalize_report,
    render_baseline,
    replace_section,
)

logger = logging.getLogger(__name__)

EmitCallable = Callable[[str, dict[str, Any]], Awaitable[None]]

STAGES: list[tuple[str, str]] = [
    ("freeze", "冻结分析快照"),
    ("overview", "AI 撰写事件摘要"),
    ("opinions", "整理市场观点"),
    ("transmission", "梳理传导路径"),
    ("impact", "汇总影响对象"),
    ("recommendations", "AI 生成研究建议"),
    ("counter-evidence", "整理反向证据"),
    ("risk-notes", "AI 撰写风险提示"),
    ("persist", "写入报告存档"),
]
STAGE_LABELS = {key: label for key, label in STAGES}
LLM_STAGES: set[str] = {"overview", "recommendations", "risk-notes"}


class ReportPipeline:
    """负责跑完一次报告生成，并 emit SSE 阶段事件。"""

    def __init__(
        self,
        *,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        event_id: uuid.UUID,
        emit: EmitCallable,
        agent: ReportSectionAgent | None = None,
    ) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.event_id = event_id
        self.emit = emit
        self.settings = get_settings()
        self.agent = agent or ReportSectionAgent(self.settings, emit=emit)
        self._started_at: float | None = None

    async def _stage_start(self, stage: str, **extra: Any) -> None:
        payload = {"stage": stage, "label": STAGE_LABELS[stage], **extra}
        await self.emit("stage_start", payload)

    async def _stage_progress(self, stage: str, **extra: Any) -> None:
        await self.emit("stage_progress", {"stage": stage, **extra})

    async def _stage_done(self, stage: str, **extra: Any) -> None:
        elapsed_ms = int((time.perf_counter() - (self._started_at or 0)) * 1000)
        await self.emit(
            "stage_done",
            {"stage": stage, "elapsed_ms": elapsed_ms, **extra},
        )

    async def _stage_error(self, stage: str, error: str) -> None:
        await self.emit("stage_error", {"stage": stage, "error": error})

    async def run(self) -> dict[str, Any]:
        self._started_at = time.perf_counter()

        # ---------- Stage 1: freeze snapshot + baseline ----------
        await self._stage_start("freeze")
        try:
            snapshot = await _freeze_snapshot(
                self.session, self.tenant_id, self.event_id
            )
            payload = _load_payload(snapshot)
            baseline = render_baseline(payload)
        except Exception as exc:  # noqa: BLE001
            await self._stage_error("freeze", str(exc))
            raise
        await self._stage_done(
            "freeze",
            snapshot_id=str(snapshot.id),
            evidence_count=len(payload.evidence),
        )

        rendered = baseline
        extra_degradation: list[str] = []
        allowed = frozenset(item.id for item in payload.evidence)
        score_calc_ids = [
            value
            for value in (
                payload.score.calculation_id,
                payload.score.score_calculation_id,
            )
            if value is not None
        ]

        # ---------- Stage 2: overview (LLM) ----------
        rendered, extra_degradation = await self._run_llm_stage(
            rendered=rendered,
            section_key="overview",
            section_title="事件摘要",
            payload=payload,
            allowed_evidence_ids=allowed,
            score_calc_ids=score_calc_ids,
            extra_degradation=extra_degradation,
        )

        # ---------- Stage 3-5: template sections (opinions / transmission / impact) ----------
        for stage_key in ("opinions", "transmission", "impact"):
            await self._stage_start(stage_key)
            section = _find_section(rendered, stage_key)
            await self._stage_progress(
                stage_key,
                statements=len(section.items) if section else 0,
            )
            await self._stage_done(
                stage_key,
                statements=len(section.items) if section else 0,
                source="template",
            )

        # ---------- Stage 6: recommendations (LLM) ----------
        rendered, extra_degradation = await self._run_llm_stage(
            rendered=rendered,
            section_key="recommendations",
            section_title="研究建议",
            payload=payload,
            allowed_evidence_ids=allowed,
            score_calc_ids=score_calc_ids,
            extra_degradation=extra_degradation,
        )

        # ---------- Stage 7: counter-evidence (template) ----------
        await self._stage_start("counter-evidence")
        counter = _find_section(rendered, "counter-evidence")
        await self._stage_done(
            "counter-evidence",
            statements=len(counter.items) if counter else 0,
            source="template",
        )

        # ---------- Stage 8: risk-notes (LLM) ----------
        rendered, extra_degradation = await self._run_llm_stage(
            rendered=rendered,
            section_key="risk-notes",
            section_title="风险提示",
            payload=payload,
            allowed_evidence_ids=allowed,
            score_calc_ids=score_calc_ids,
            extra_degradation=extra_degradation,
        )

        # ---------- Stage 9: persist ----------
        rendered = finalize_report(rendered, extra_degradation=extra_degradation)
        await self._stage_start("persist")
        report = await self._persist(snapshot_id=snapshot.id, rendered=rendered)
        await self._stage_done(
            "persist",
            report_id=str(report.id),
            status=report.status,
        )

        elapsed_ms = int((time.perf_counter() - self._started_at) * 1000)
        await self.emit(
            "done",
            {
                "report_id": str(report.id),
                "status": report.status,
                "elapsed_ms": elapsed_ms,
                "degradation_reasons": list(report.degradation_reasons),
            },
        )
        return {"report_id": str(report.id), "status": report.status}

    async def _run_llm_stage(
        self,
        *,
        rendered: RenderedReport,
        section_key: SectionKey,
        section_title: str,
        payload: AnalysisSnapshotPayload,
        allowed_evidence_ids: frozenset[uuid.UUID],
        score_calc_ids: list[uuid.UUID],
        extra_degradation: list[str],
    ) -> tuple[RenderedReport, list[str]]:
        await self._stage_start(section_key, uses_llm=True)
        try:
            output = await self.agent.generate(section_key, payload)
            cleaned = valid_statements(
                output, allowed_evidence_ids=allowed_evidence_ids
            )
            if not cleaned:
                raise ReportSectionLLMError("LLM 输出无合法 evidence_id")
            new_section = build_llm_section(
                section_id=section_key,
                title=section_title,
                statements=cleaned,
                fallback_status="complete",
                score_calculation_ids=score_calc_ids,
            )
            rendered = replace_section(rendered, new_section)
            await self._stage_done(
                section_key,
                source="llm",
                statements=len(cleaned),
            )
        except ReportSectionLLMError as exc:
            reason = f"{section_key}_llm_unavailable: {exc}"
            logger.warning("Report LLM stage %s degraded: %s", section_key, exc)
            extra_degradation = list(extra_degradation) + [reason]
            await self._stage_progress(
                section_key,
                warning="AI 生成失败，已回退到模板文本",
                error=str(exc),
            )
            await self._stage_done(
                section_key,
                source="template-fallback",
                error=str(exc),
            )
        return rendered, extra_degradation

    async def _persist(
        self, *, snapshot_id: uuid.UUID, rendered: RenderedReport
    ) -> Report:
        existing = await self.session.scalar(
            select(Report).where(
                Report.snapshot_id == snapshot_id,
                Report.format == "html",
                Report.render_engine == TEMPLATE_RENDER_ENGINE,
            )
        )
        if existing is not None:
            # 覆盖旧的模板产物，让 UI 拿到本次 AI 内容。
            existing.title = rendered.title
            existing.summary = rendered.summary
            existing.status = rendered.status
            existing.body_html = rendered.body_html
            existing.brief_prompt_version = BRIEF_PROMPT_VERSION
            existing.sections = [
                section.model_dump(mode="json") for section in rendered.sections
            ]
            existing.evidence_ids = [str(value) for value in rendered.evidence_ids]
            existing.calculation_ids = [
                str(value) for value in rendered.calculation_ids
            ]
            existing.degradation_reasons = rendered.degradation_reasons
            await self.session.commit()
            await self.session.refresh(existing)
            return existing

        report = Report(
            tenant_id=self.tenant_id,
            event_id=self.event_id,
            snapshot_id=snapshot_id,
            format="html",
            status=rendered.status,
            title=rendered.title,
            summary=rendered.summary,
            render_engine=TEMPLATE_RENDER_ENGINE,
            brief_prompt_version=BRIEF_PROMPT_VERSION,
            body_html=rendered.body_html,
            sections=[section.model_dump(mode="json") for section in rendered.sections],
            evidence_ids=[str(value) for value in rendered.evidence_ids],
            calculation_ids=[str(value) for value in rendered.calculation_ids],
            degradation_reasons=rendered.degradation_reasons,
        )
        self.session.add(report)
        await self.session.commit()
        await self.session.refresh(report)
        return report


def _find_section(rendered: RenderedReport, section_id: str):
    for section in rendered.sections:
        if section.id == section_id:
            return section
    return None


def _load_payload(snapshot) -> AnalysisSnapshotPayload:  # noqa: ANN001
    return AnalysisSnapshotPayload(
        event=SnapshotEventSummary.model_validate(snapshot.event_payload),
        score=SnapshotScoreSummary.model_validate(snapshot.score_payload),
        evidence=[
            SnapshotEvidenceItem.model_validate(item)
            for item in snapshot.evidence_payload
        ],
        opinions=[
            SnapshotOpinionItem.model_validate(item)
            for item in snapshot.opinion_payload
        ],
        transmission=[
            SnapshotTransmissionEdge.model_validate(item)
            for item in snapshot.transmission_payload
        ],
        impact_matrix=[
            SnapshotImpactRow.model_validate(item)
            for item in snapshot.impact_payload
        ],
    )
