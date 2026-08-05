import uuid
from datetime import UTC, datetime

from risktrace.main import create_app
from risktrace.reports.schemas import (
    AnalysisSnapshotPayload,
    SnapshotEventSummary,
    SnapshotEvidenceItem,
    SnapshotImpactRow,
    SnapshotOpinionItem,
    SnapshotScoreInterval,
    SnapshotScoreSummary,
    SnapshotTransmissionEdge,
)
from risktrace.reports.service import _render_report


def _payload() -> AnalysisSnapshotPayload:
    evidence_id = uuid.UUID("10000000-0000-0000-0000-000000000001")
    calculation_id = uuid.UUID("20000000-0000-0000-0000-000000000001")
    return AnalysisSnapshotPayload(
        event=SnapshotEventSummary(
            id=uuid.UUID("30000000-0000-0000-0000-000000000001"),
            title="测试事件",
            status="active",
            first_published_at=datetime(2026, 8, 5, 1, 0, tzinfo=UTC),
            source_count=3,
            authoritative_source_count=1,
            source_breakdown={"fact": 1, "news": 1, "social": 1},
        ),
        score=SnapshotScoreSummary(
            status="complete",
            raw_score=0.62,
            calibrated_score=0.71,
            confidence=0.76,
            score_interval=SnapshotScoreInterval(lower_bound=0.6, upper_bound=0.82),
            scoring_version="deterministic-scoring-v1",
            calibration_version="score-calibration-v1",
            calculation_id=calculation_id,
            score_calculation_id=uuid.UUID("21000000-0000-0000-0000-000000000001"),
            degradation_reasons=[],
        ),
        evidence=[
            SnapshotEvidenceItem(
                id=evidence_id,
                title="事实源标题",
                source_type="fact",
                platform="disclosure",
                published_at=datetime(2026, 8, 5, 1, 0, tzinfo=UTC),
                collected_at=datetime(2026, 8, 5, 1, 5, tzinfo=UTC),
                source_url="https://example.com/fact",
                engagement=None,
                raw_text_preview="事实源正文",
                collection_method="authorized_api",
                license_scope="internal_research",
            )
        ],
        opinions=[
            SnapshotOpinionItem(
                id=uuid.UUID("40000000-0000-0000-0000-000000000001"),
                document_id=evidence_id,
                target_entity_id=None,
                stance="bullish",
                emotion="optimistic",
                reason="订单恢复快于预期",
                claim_type="opinion",
                evidence_span="订单恢复快于预期",
                model_confidence=0.81,
                created_at=datetime(2026, 8, 5, 1, 10, tzinfo=UTC),
            )
        ],
        transmission=[
            SnapshotTransmissionEdge(
                id=uuid.UUID("50000000-0000-0000-0000-000000000001"),
                from_node_type="event",
                from_node_id=uuid.UUID("30000000-0000-0000-0000-000000000001"),
                to_node_type="entity",
                to_node_id=uuid.UUID("60000000-0000-0000-0000-000000000001"),
                from_node_label="测试事件",
                to_node_label="测试公司",
                mechanism="供给恢复带动出货预期回升",
                direction="positive",
                horizon="short",
                evidence_ids=[evidence_id],
                knowledge_ids=[],
                model_confidence=0.73,
                status="candidate",
                created_at=datetime(2026, 8, 5, 1, 15, tzinfo=UTC),
            )
        ],
        impact_matrix=[
            SnapshotImpactRow(
                entity_id=uuid.UUID("60000000-0000-0000-0000-000000000001"),
                entity_name="测试公司",
                entity_type="company",
                direction="positive",
                impact_strength=0.74,
                business_exposure=0.63,
                opinion_support=0.66,
                fact_support=0.5,
                time_horizon="short",
                composite_confidence=0.69,
                edge_count=1,
                opinion_count=1,
                evidence_count=1,
                evidence_ids=[evidence_id],
            )
        ],
    )


def test_report_render_keeps_evidence_and_calculation_references() -> None:
    rendered = _render_report(_payload())
    recommendation_section = next(
        section for section in rendered.sections if section.id == "recommendations"
    )

    assert rendered.status == "complete"
    assert rendered.evidence_ids
    assert rendered.calculation_ids
    assert len(recommendation_section.items) == 2
    assert recommendation_section.status == "complete"
    assert any(item.evidence_ids for item in recommendation_section.items)
    assert any(item.calculation_ids for item in recommendation_section.items)
    assert any(item.evidence_ids for section in rendered.sections for item in section.items)
    assert any(
        item.calculation_ids for section in rendered.sections for item in section.items
    )
    assert "evidence_id" in rendered.body_html
    assert "calculation_id" in rendered.body_html


def test_openapi_exposes_report_creation_and_read_routes() -> None:
    paths = create_app().openapi()["paths"]

    assert "/api/reports" in paths
    assert "/api/reports/{report_id}" in paths
