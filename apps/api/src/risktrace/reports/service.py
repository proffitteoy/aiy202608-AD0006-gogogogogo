from __future__ import annotations

import hashlib
import html
import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from risktrace.agents.impact import compute_impact_matrix
from risktrace.api.schemas.events import EventScoreSummary, ScoreInterval
from risktrace.db.models import (
    AnalysisSnapshot,
    Entity,
    Event,
    EventDocument,
    EventScoreCalibration,
    OpinionRecord,
    RawDocument,
    Report,
    TransmissionEdge,
)
from risktrace.reports.schemas import (
    AnalysisSnapshotPayload,
    RenderedReport,
    ReportSection,
    ReportStatement,
    SnapshotEventSummary,
    SnapshotEvidenceItem,
    SnapshotImpactRow,
    SnapshotOpinionItem,
    SnapshotScoreSummary,
    SnapshotTransmissionEdge,
)

TEMPLATE_RENDER_ENGINE = "template-render-v1"
BRIEF_PROMPT_VERSION = "template-report-v1"

STATUS_LABELS = {
    "candidate": "候选",
    "confirmed": "已确认",
    "active": "监测中",
    "analyzed": "已分析",
    "alerted": "已告警",
    "cooling": "降温中",
    "closed": "已关闭",
    "archived": "已归档",
}
SOURCE_LABELS = {
    "fact": "事实源",
    "news": "新闻源",
    "social": "社交源",
    "market": "行情源",
}
STANCE_LABELS = {
    "bullish": "偏多",
    "bearish": "偏空",
    "neutral": "中性",
    "wait": "观望",
}
HORIZON_LABELS = {
    "immediate": "即时",
    "short": "短期",
    "medium": "中期",
    "long": "长期",
}
DIRECTION_LABELS = {
    "positive": "正向",
    "negative": "负向",
    "uncertain": "待验证",
    "neutral": "中性",
}


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash_payload(payload: object) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _format_datetime(value: datetime) -> str:
    localized = value.astimezone(UTC)
    return localized.strftime("%Y-%m-%d %H:%M UTC")


def _format_score(value: float | None) -> str:
    if value is None:
        return "--"
    return f"{value * 100:.1f}"


def _status_label(value: str) -> str:
    return STATUS_LABELS.get(value, value)


def _build_score_summary(
    event: Event,
    calibration: EventScoreCalibration | None,
) -> EventScoreSummary:
    if calibration is not None:
        return EventScoreSummary(
            status=calibration.calculation_status,
            raw_score=calibration.raw_score,
            calibrated_score=calibration.calibrated_score,
            confidence=calibration.confidence,
            score_interval=ScoreInterval(
                lower_bound=calibration.lower_bound,
                upper_bound=calibration.upper_bound,
            ),
            scoring_version=calibration.scoring_version,
            calibration_version=calibration.calibration_version,
            calculation_id=calibration.calculation_id,
            score_calculation_id=calibration.score_calculation_id,
            degradation_reasons=list(calibration.degradation_reasons),
        )

    cached_values = (
        event.raw_score,
        event.calibrated_score,
        event.score_confidence,
        event.score_lower_bound,
        event.score_upper_bound,
    )
    if all(value is None for value in cached_values):
        return EventScoreSummary(status="unavailable")

    score_interval = None
    if event.score_lower_bound is not None and event.score_upper_bound is not None:
        score_interval = ScoreInterval(
            lower_bound=event.score_lower_bound,
            upper_bound=event.score_upper_bound,
        )
    return EventScoreSummary(
        status="degraded",
        raw_score=event.raw_score,
        calibrated_score=event.calibrated_score,
        confidence=event.score_confidence,
        score_interval=score_interval,
        scoring_version=event.scoring_version,
        calibration_version=event.calibration_version,
        degradation_reasons=["calibration_record_unavailable"],
    )


async def _load_snapshot_payload(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    event_id: uuid.UUID,
) -> tuple[AnalysisSnapshotPayload, EventScoreCalibration | None]:
    event = await session.scalar(
        select(Event).where(Event.id == event_id, Event.tenant_id == tenant_id)
    )
    if event is None:
        raise ValueError(f"Event {event_id} not found")

    documents = (
        await session.execute(
            select(RawDocument)
            .join(EventDocument, EventDocument.document_id == RawDocument.id)
            .where(
                EventDocument.event_id == event_id,
                RawDocument.tenant_id == tenant_id,
            )
            .order_by(RawDocument.published_at.asc())
        )
    ).scalars().all()
    source_breakdown: dict[str, int] = {}
    for document in documents:
        source_breakdown[document.source_type] = source_breakdown.get(document.source_type, 0) + 1

    calibration = await session.scalar(
        select(EventScoreCalibration)
        .where(
            EventScoreCalibration.event_id == event_id,
            EventScoreCalibration.tenant_id == tenant_id,
        )
        .order_by(
            EventScoreCalibration.snapshot_at.desc(),
            EventScoreCalibration.created_at.desc(),
        )
        .limit(1)
    )
    score = _build_score_summary(event, calibration)

    opinions = (
        await session.execute(
            select(OpinionRecord)
            .where(
                OpinionRecord.event_id == event_id,
                OpinionRecord.tenant_id == tenant_id,
            )
            .order_by(OpinionRecord.model_confidence.desc(), OpinionRecord.created_at.asc())
        )
    ).scalars().all()

    transmission_edges = (
        await session.execute(
            select(TransmissionEdge)
            .where(
                TransmissionEdge.event_id == event_id,
                TransmissionEdge.tenant_id == tenant_id,
            )
            .order_by(TransmissionEdge.model_confidence.desc(), TransmissionEdge.created_at.asc())
        )
    ).scalars().all()

    node_ids = {
        node_id
        for edge in transmission_edges
        for node_id in (edge.from_node_id, edge.to_node_id)
    }
    entities = (
        await session.execute(
            select(Entity).where(Entity.id.in_(node_ids), Entity.tenant_id == tenant_id)
        )
    ).scalars().all()
    labels = {entity.id: entity.name for entity in entities}
    labels[event.id] = event.title

    impact_rows = await compute_impact_matrix(event_id, session)

    payload = AnalysisSnapshotPayload(
        event=SnapshotEventSummary(
            id=event.id,
            title=event.title,
            status=event.status,
            first_published_at=event.first_published_at,
            source_count=len(documents),
            authoritative_source_count=source_breakdown.get("fact", 0),
            source_breakdown=source_breakdown,
        ),
        score=SnapshotScoreSummary.model_validate(score.model_dump(mode="json")),
        evidence=[
            SnapshotEvidenceItem(
                id=document.id,
                title=document.title,
                source_type=document.source_type,
                platform=document.platform,
                published_at=document.published_at,
                collected_at=document.collected_at,
                source_url=document.source_url,
                engagement=document.engagement,
                raw_text_preview=(document.raw_text or "")[:500],
                collection_method=document.collection_method,
                license_scope=document.license_scope,
            )
            for document in documents
        ],
        opinions=[
            SnapshotOpinionItem(
                id=opinion.id,
                document_id=opinion.document_id,
                target_entity_id=opinion.target_entity_id,
                stance=opinion.stance,
                emotion=opinion.emotion,
                reason=opinion.reason,
                claim_type=opinion.claim_type,
                evidence_span=opinion.evidence_span,
                model_confidence=opinion.model_confidence,
                created_at=opinion.created_at,
            )
            for opinion in opinions
        ],
        transmission=[
            SnapshotTransmissionEdge(
                id=edge.id,
                from_node_type=edge.from_node_type,
                from_node_id=edge.from_node_id,
                to_node_type=edge.to_node_type,
                to_node_id=edge.to_node_id,
                from_node_label=labels.get(edge.from_node_id),
                to_node_label=labels.get(edge.to_node_id),
                mechanism=edge.mechanism,
                direction=edge.direction,
                horizon=edge.horizon,
                evidence_ids=edge.evidence_ids or [],
                knowledge_ids=edge.knowledge_ids or [],
                model_confidence=edge.model_confidence,
                status=edge.status,
                created_at=edge.created_at,
            )
            for edge in transmission_edges
        ],
        impact_matrix=[
            SnapshotImpactRow(
                entity_id=row.entity_id,
                entity_name=row.entity_name,
                entity_type=row.entity_type,
                direction=row.direction,
                impact_strength=row.impact_strength,
                business_exposure=row.business_exposure,
                opinion_support=row.opinion_support,
                fact_support=row.fact_support,
                time_horizon=row.time_horizon,
                composite_confidence=row.composite_confidence,
                edge_count=row.edge_count,
                opinion_count=row.opinion_count,
                evidence_count=row.evidence_count,
                evidence_ids=row.evidence_ids,
            )
            for row in impact_rows
        ],
    )
    return payload, calibration


async def _freeze_snapshot(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    event_id: uuid.UUID,
) -> AnalysisSnapshot:
    payload, calibration = await _load_snapshot_payload(session, tenant_id, event_id)
    dumped = payload.model_dump(mode="json")
    evidence_snapshot_hash = _hash_payload(
        sorted(str(item["id"]) for item in dumped["evidence"])
    )
    snapshot_hash = _hash_payload(dumped)

    existing = await session.scalar(
        select(AnalysisSnapshot).where(
            AnalysisSnapshot.tenant_id == tenant_id,
            AnalysisSnapshot.event_id == event_id,
            AnalysisSnapshot.snapshot_hash == snapshot_hash,
        )
    )
    if existing is not None:
        return existing

    snapshot_at = datetime.now(UTC)
    analysis_version = f"snapshot-{snapshot_at.strftime('%Y%m%d%H%M%S')}"
    snapshot = AnalysisSnapshot(
        tenant_id=tenant_id,
        event_id=event_id,
        score_calibration_id=calibration.calculation_id if calibration else None,
        snapshot_kind="report",
        analysis_version=analysis_version,
        snapshot_hash=snapshot_hash,
        evidence_snapshot_hash=evidence_snapshot_hash,
        score_status=payload.score.status,
        evidence_count=len(payload.evidence),
        source_count=payload.event.source_count,
        scoring_version=payload.score.scoring_version,
        calibration_version=payload.score.calibration_version,
        event_payload=payload.event.model_dump(mode="json"),
        score_payload=payload.score.model_dump(mode="json"),
        evidence_payload=[item.model_dump(mode="json") for item in payload.evidence],
        opinion_payload=[item.model_dump(mode="json") for item in payload.opinions],
        transmission_payload=[item.model_dump(mode="json") for item in payload.transmission],
        impact_payload=[item.model_dump(mode="json") for item in payload.impact_matrix],
        snapshot_at=snapshot_at,
    )
    session.add(snapshot)
    await session.flush()
    return snapshot


def _statement(
    statement_id: str,
    text: str,
    *,
    evidence_ids: list[uuid.UUID] | None = None,
    calculation_ids: list[uuid.UUID] | None = None,
) -> ReportStatement:
    return ReportStatement(
        id=statement_id,
        text=text,
        evidence_ids=evidence_ids or [],
        calculation_ids=calculation_ids or [],
    )


def _render_html(title: str, summary: str, sections: list[ReportSection]) -> str:
    parts = [
        "<article class=\"risktrace-report\">",
        f"<h1>{html.escape(title)}</h1>",
        f"<p>{html.escape(summary)}</p>",
    ]
    for section in sections:
        parts.append("<section>")
        parts.append(f"<h2>{html.escape(section.title)}</h2>")
        parts.append("<ul>")
        for item in section.items:
            parts.append("<li>")
            parts.append(f"<p>{html.escape(item.text)}</p>")
            refs: list[str] = []
            if item.evidence_ids:
                refs.append(
                    "evidence_id: "
                    + ", ".join(html.escape(str(value)) for value in item.evidence_ids)
                )
            if item.calculation_ids:
                refs.append(
                    "calculation_id: "
                    + ", ".join(html.escape(str(value)) for value in item.calculation_ids)
                )
            if refs:
                parts.append(f"<small>{' | '.join(refs)}</small>")
            parts.append("</li>")
        parts.append("</ul>")
        parts.append("</section>")
    parts.append("</article>")
    return "".join(parts)


def _render_report(payload: AnalysisSnapshotPayload) -> RenderedReport:
    sections: list[ReportSection] = []
    degradation_reasons = list(payload.score.degradation_reasons)

    summary_evidence_ids = [item.id for item in payload.evidence[:8]]
    score_calculation_ids = [
        value
        for value in (payload.score.calculation_id, payload.score.score_calculation_id)
        if value is not None
    ]
    source_breakdown = " / ".join(
        f"{SOURCE_LABELS.get(source, source)} {count} 条"
        for source, count in sorted(payload.event.source_breakdown.items())
    )
    overview_items = [
        _statement(
            "event-status",
            (
                f"{payload.event.title} 当前处于{_status_label(payload.event.status)}状态，"
                f"首条冻结证据时间为 {_format_datetime(payload.event.first_published_at)}。"
            ),
            evidence_ids=summary_evidence_ids,
        ),
        _statement(
            "event-coverage",
            (
                f"当前 snapshot 冻结了 {payload.event.source_count} 条证据，"
                "其中事实源 "
                f"{payload.event.authoritative_source_count} 条；来源覆盖为 "
                f"{source_breakdown or '无可用来源统计'}。"
            ),
            evidence_ids=summary_evidence_ids,
        ),
    ]
    if payload.score.status != "unavailable":
        interval = payload.score.score_interval
        interval_text = (
            f"{_format_score(interval.lower_bound)}-{_format_score(interval.upper_bound)}"
            if interval is not None
            else "--"
        )
        overview_items.append(
            _statement(
                "event-score",
                (
                    f"Rule 4 校准分为 {_format_score(payload.score.calibrated_score)}，"
                    f"置信度 {_format_score(payload.score.confidence)}，评分区间 {interval_text}。"
                ),
                calculation_ids=score_calculation_ids,
            )
        )
    else:
        degradation_reasons.append("score_unavailable")
        overview_items.append(
            _statement(
                "event-score-unavailable",
                "当前 snapshot 未冻结可用的 Rule 4 评分结果，报告只展示证据与结构化产物。",
                evidence_ids=summary_evidence_ids,
            )
        )
    sections.append(
        ReportSection(
            id="overview",
            title="事件摘要",
            status="degraded" if payload.score.status != "complete" else "complete",
            items=overview_items,
        )
    )

    opinion_items = [
        _statement(
            f"opinion-{index}",
            (
                f"观点 {index + 1}：{STANCE_LABELS.get(opinion.stance, opinion.stance)} / "
                f"{opinion.emotion}，理由为“{opinion.reason}”。"
            ),
            evidence_ids=[opinion.document_id],
        )
        for index, opinion in enumerate(payload.opinions[:3])
    ]
    if not opinion_items:
        degradation_reasons.append("opinions_not_generated")
        opinion_items.append(
            _statement(
                "opinion-missing",
                "当前 snapshot 没有可验证的观点归因产物，报告不补造主导观点。",
                evidence_ids=summary_evidence_ids[:3],
            )
        )
    sections.append(
        ReportSection(
            id="opinions",
            title="市场主导观点",
            status="complete" if payload.opinions else "degraded",
            items=opinion_items,
        )
    )

    transmission_items = [
        _statement(
            f"transmission-{index}",
            (
                f"{edge.from_node_label or '未解析主体'} 通过“{edge.mechanism}”传导至 "
                f"{edge.to_node_label or '未解析主体'}，方向为 "
                f"{DIRECTION_LABELS.get(edge.direction, edge.direction)}，"
                f"期限为 {HORIZON_LABELS.get(edge.horizon, edge.horizon)}。"
            ),
            evidence_ids=edge.evidence_ids[:6],
        )
        for index, edge in enumerate(payload.transmission[:3])
    ]
    if not transmission_items:
        degradation_reasons.append("transmission_not_generated")
        transmission_items.append(
            _statement(
                "transmission-missing",
                "当前 snapshot 没有可验证的传导候选，报告不推断产业链影响路径。",
                evidence_ids=summary_evidence_ids[:3],
            )
        )
    sections.append(
        ReportSection(
            id="transmission",
            title="传导路径",
            status="complete" if payload.transmission else "degraded",
            items=transmission_items,
        )
    )

    impact_items = [
        _statement(
            f"impact-{index}",
            (
                f"{row.entity_name} 的方向为 "
                f"{DIRECTION_LABELS.get(row.direction, row.direction)}，"
                f"综合置信度 {_format_score(row.composite_confidence)}，"
                f"证据数 {row.evidence_count}。"
            ),
            evidence_ids=row.evidence_ids[:6],
        )
        for index, row in enumerate(payload.impact_matrix[:3])
    ]
    if not impact_items:
        degradation_reasons.append("impact_not_generated")
        impact_items.append(
            _statement(
                "impact-missing",
                "当前 snapshot 没有热力矩阵对象，影响对象部分保持空白而不补造结论。",
                evidence_ids=summary_evidence_ids[:3],
            )
        )
    sections.append(
        ReportSection(
            id="impact",
            title="影响对象",
            status="complete" if payload.impact_matrix else "degraded",
            items=impact_items,
        )
    )

    counter_items: list[ReportStatement] = []
    for index, opinion in enumerate(
        [item for item in payload.opinions if item.stance in {"neutral", "wait"}][:2]
    ):
        counter_items.append(
            _statement(
                f"counter-opinion-{index}",
                (
                    f"存在{STANCE_LABELS.get(opinion.stance, opinion.stance)}线索："
                    f"“{opinion.reason}”，需与主导观点一起复核。"
                ),
                evidence_ids=[opinion.document_id],
            )
        )
    for index, edge in enumerate(
        [item for item in payload.transmission if item.direction == "uncertain"][
            : max(0, 2 - len(counter_items))
        ]
    ):
        counter_items.append(
            _statement(
                f"counter-edge-{index}",
                (
                    f"存在待验证传导边：{edge.from_node_label or '未解析主体'} → "
                    f"{edge.to_node_label or '未解析主体'}。"
                ),
                evidence_ids=edge.evidence_ids[:6],
            )
        )
    if not counter_items:
        counter_items.append(
            _statement(
                "counter-none",
                "当前 snapshot 未冻结明确的反向证据条目，研究员仍应复核原始证据。",
                evidence_ids=summary_evidence_ids[:3],
            )
        )
    sections.append(
        ReportSection(
            id="counter-evidence",
            title="反向证据",
            status="complete" if counter_items else "degraded",
            items=counter_items,
        )
    )

    risk_items: list[ReportStatement] = []
    if payload.score.degradation_reasons:
        risk_items.append(
            _statement(
                "risk-score-degraded",
                "评分链存在降级原因：" + "、".join(payload.score.degradation_reasons) + "。",
                calculation_ids=score_calculation_ids,
            )
        )
    if not payload.opinions:
        risk_items.append(
            _statement(
                "risk-no-opinion",
                "观点归因未生成，当前报告对市场情绪与立场变化的覆盖不完整。",
                evidence_ids=summary_evidence_ids[:3],
            )
        )
    if not payload.transmission:
        risk_items.append(
            _statement(
                "risk-no-transmission",
                "传导候选未生成，行业与公司层面的影响链仍需人工补充。",
                evidence_ids=summary_evidence_ids[:3],
            )
        )
    if not risk_items:
        risk_items.append(
            _statement(
                "risk-review",
                "本报告基于冻结 snapshot 渲染，重大结论仍需研究员复核后再对外使用。",
                evidence_ids=summary_evidence_ids[:3],
            )
        )
    sections.append(
        ReportSection(
            id="risk-notes",
            title="风险提示",
            status="degraded" if degradation_reasons else "complete",
            items=risk_items,
        )
    )

    all_evidence_ids = sorted(
        {
            evidence_id
            for section in sections
            for item in section.items
            for evidence_id in item.evidence_ids
        },
        key=str,
    )
    all_calculation_ids = sorted(
        {
            calculation_id
            for section in sections
            for item in section.items
            for calculation_id in item.calculation_ids
        },
        key=str,
    )
    summary = (
        f"{payload.event.title} 的冻结报告已生成；当前状态 {_status_label(payload.event.status)}，"
        f"共引用 {len(all_evidence_ids)} 条证据。"
    )
    title = f"{payload.event.title} · 风险简报"
    status = "degraded" if degradation_reasons else "complete"
    body_html = _render_html(title, summary, sections)

    return RenderedReport(
        title=title,
        summary=summary,
        status=status,
        sections=sections,
        evidence_ids=all_evidence_ids,
        calculation_ids=all_calculation_ids,
        degradation_reasons=sorted(set(degradation_reasons)),
        body_html=body_html,
    )


async def create_report_for_event(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    event_id: uuid.UUID,
    *,
    format: str = "html",
) -> Report:
    if format != "html":
        raise ValueError(f"Unsupported report format: {format}")

    snapshot = await _freeze_snapshot(session, tenant_id, event_id)
    existing = await session.scalar(
        select(Report).where(
            Report.snapshot_id == snapshot.id,
            Report.format == format,
            Report.render_engine == TEMPLATE_RENDER_ENGINE,
        )
    )
    if existing is not None:
        return existing

    payload = AnalysisSnapshotPayload(
        event=SnapshotEventSummary.model_validate(snapshot.event_payload),
        score=SnapshotScoreSummary.model_validate(snapshot.score_payload),
        evidence=[SnapshotEvidenceItem.model_validate(item) for item in snapshot.evidence_payload],
        opinions=[SnapshotOpinionItem.model_validate(item) for item in snapshot.opinion_payload],
        transmission=[
            SnapshotTransmissionEdge.model_validate(item)
            for item in snapshot.transmission_payload
        ],
        impact_matrix=[SnapshotImpactRow.model_validate(item) for item in snapshot.impact_payload],
    )
    rendered = _render_report(payload)
    report = Report(
        tenant_id=tenant_id,
        event_id=event_id,
        snapshot_id=snapshot.id,
        format=format,
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
    session.add(report)
    await session.commit()
    await session.refresh(report)
    return report


async def get_report_detail(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    report_id: uuid.UUID,
) -> tuple[Report, AnalysisSnapshotPayload, AnalysisSnapshot]:
    report = await session.scalar(
        select(Report).where(Report.id == report_id, Report.tenant_id == tenant_id)
    )
    if report is None:
        raise ValueError(f"Report {report_id} not found")

    snapshot = await session.scalar(
        select(AnalysisSnapshot).where(
            AnalysisSnapshot.id == report.snapshot_id,
            AnalysisSnapshot.tenant_id == tenant_id,
        )
    )
    if snapshot is None:
        raise ValueError(f"Snapshot {report.snapshot_id} not found")

    payload = AnalysisSnapshotPayload(
        event=SnapshotEventSummary.model_validate(snapshot.event_payload),
        score=SnapshotScoreSummary.model_validate(snapshot.score_payload),
        evidence=[SnapshotEvidenceItem.model_validate(item) for item in snapshot.evidence_payload],
        opinions=[SnapshotOpinionItem.model_validate(item) for item in snapshot.opinion_payload],
        transmission=[
            SnapshotTransmissionEdge.model_validate(item)
            for item in snapshot.transmission_payload
        ],
        impact_matrix=[SnapshotImpactRow.model_validate(item) for item in snapshot.impact_payload],
    )
    return report, payload, snapshot
