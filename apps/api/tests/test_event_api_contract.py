import uuid
from datetime import UTC, datetime

from risktrace.api.routes.events import _score_summary
from risktrace.db.models import Event, EventScoreCalibration


TENANT_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
EVENT_ID = uuid.UUID("e1000000-0000-0000-0000-000000000001")
SCORE_CALCULATION_ID = uuid.UUID("10000000-0000-0000-0000-000000000001")
CALIBRATION_ID = uuid.UUID("20000000-0000-0000-0000-000000000001")
NOW = datetime(2026, 8, 5, 8, 0, tzinfo=UTC)


def event(**overrides: object) -> Event:
    values: dict[str, object] = {
        "id": EVENT_ID,
        "tenant_id": TENANT_ID,
        "title": "测试事件",
        "status": "active",
        "first_published_at": NOW,
        "last_seen_at": NOW,
    }
    values.update(overrides)
    return Event(**values)


def test_event_score_is_unavailable_without_rule3_or_rule4_output() -> None:
    summary = _score_summary(event(), None)

    assert summary.status == "unavailable"
    assert summary.raw_score is None
    assert summary.calibrated_score is None
    assert summary.degradation_reasons == []


def test_cached_score_without_calibration_record_is_explicitly_degraded() -> None:
    summary = _score_summary(
        event(
            raw_score=0.64,
            calibrated_score=0.68,
            score_confidence=0.72,
            score_lower_bound=0.55,
            score_upper_bound=0.79,
            scoring_version="deterministic-scoring-v1",
            calibration_version="score-calibration-v1",
        ),
        None,
    )

    assert summary.status == "degraded"
    assert summary.score_interval is not None
    assert summary.score_interval.lower_bound == 0.55
    assert summary.degradation_reasons == ["calibration_record_unavailable"]


def test_latest_calibration_exposes_traceable_rule3_and_rule4_fields() -> None:
    calibration = EventScoreCalibration(
        calculation_id=CALIBRATION_ID,
        tenant_id=TENANT_ID,
        event_id=EVENT_ID,
        score_calculation_id=SCORE_CALCULATION_ID,
        snapshot_at=NOW,
        scoring_version="deterministic-scoring-v1",
        calibration_version="score-calibration-v1",
        raw_score=0.64,
        calibrated_score=0.70,
        confidence=0.76,
        lower_bound=0.58,
        upper_bound=0.81,
        data_completeness=0.9,
        source_health=1.0,
        market_data_completeness=0.8,
        input_evidence_ids=[str(uuid.uuid4())],
        evidence_snapshot_hash="a" * 64,
        monte_carlo_seed=1,
        sample_count=500,
        parameters={},
        calculation_status="complete",
        degradation_reasons=[],
    )

    summary = _score_summary(event(), calibration)

    assert summary.status == "complete"
    assert summary.raw_score == 0.64
    assert summary.calibrated_score == 0.70
    assert summary.confidence == 0.76
    assert summary.calculation_id == CALIBRATION_ID
    assert summary.score_calculation_id == SCORE_CALCULATION_ID
