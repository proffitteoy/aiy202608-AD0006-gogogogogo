import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from risktrace.scoring import (
    CalibrationEngine,
    CalibrationPolicy,
    CalibrationStatus,
    EvidenceWeightComponents,
    ScoreCalibrationInput,
    ScoreEvidenceUpdate,
    calibration_record,
)

TENANT_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
EVENT_ID = uuid.UUID("e1000000-0000-0000-0000-000000000001")
SCORE_CALCULATION_ID = uuid.UUID("c1000000-0000-0000-0000-000000000001")
DOCUMENT_ID = uuid.UUID("d1000000-0000-0000-0000-000000000001")


def calibration_input(**overrides: object) -> ScoreCalibrationInput:
    values: dict[str, object] = {
        "tenant_id": TENANT_ID,
        "event_id": EVENT_ID,
        "score_calculation_id": SCORE_CALCULATION_ID,
        "raw_score": 0.70,
        "scoring_version": "deterministic-scoring-v1",
        "data_completeness": 1.0,
        "source_health": 1.0,
        "market_data_completeness": 1.0,
    }
    values.update(overrides)
    return ScoreCalibrationInput(**values)


def evidence_update(
    *,
    document_id: uuid.UUID = DOCUMENT_ID,
    observation: float = 0.90,
    independence: float = 1.0,
) -> ScoreEvidenceUpdate:
    return ScoreEvidenceUpdate(
        document_id=document_id,
        observation=observation,
        weight=EvidenceWeightComponents(
            source_reliability=0.95,
            independence=independence,
            score_relevance=0.90,
            freshness=0.90,
            data_quality=0.95,
        ),
    )


def test_rule4_is_replayable_and_calibrates_rule3_raw_score() -> None:
    engine = CalibrationEngine(CalibrationPolicy(sample_count=1_000))
    first = engine.calculate(calibration_input(), [evidence_update()])
    second = engine.calculate(calibration_input(), [evidence_update()])

    assert first == second
    assert first.raw_score == pytest.approx(0.70)
    assert first.calibrated_score > first.raw_score
    assert first.score_interval.lower <= first.calibrated_score <= first.score_interval.upper
    assert first.confidence > 0.0
    assert first.calculation_status is CalibrationStatus.COMPLETE


def test_duplicate_or_dependent_evidence_adds_no_information() -> None:
    engine = CalibrationEngine(CalibrationPolicy(sample_count=500))
    baseline = engine.calculate(calibration_input(), [])
    duplicate_only = engine.calculate(
        calibration_input(),
        [evidence_update(independence=0.0)],
    )

    assert duplicate_only == baseline
    assert duplicate_only.input_evidence_ids == ()
    assert duplicate_only.confidence == 0.0
    assert "no_independent_calibration_evidence" in duplicate_only.degradation_reasons


def test_source_degradation_caps_confidence_without_changing_agent_fields() -> None:
    engine = CalibrationEngine(CalibrationPolicy(sample_count=1_000))
    healthy = engine.calculate(calibration_input(), [evidence_update()])
    degraded = engine.calculate(
        calibration_input(source_health=0.40),
        [evidence_update()],
    )

    assert degraded.confidence < healthy.confidence
    assert degraded.calculation_status is CalibrationStatus.DEGRADED
    assert "source_health_degraded" in degraded.degradation_reasons


def test_rule4_contract_rejects_agent_score_inputs() -> None:
    with pytest.raises(ValidationError, match="Extra inputs"):
        ScoreCalibrationInput(
            **calibration_input().model_dump(),
            agent_proposed_score=0.99,
        )


def test_calibration_persistence_keeps_versions_and_frozen_evidence() -> None:
    calculation = CalibrationEngine(CalibrationPolicy(sample_count=500)).calculate(
        calibration_input(),
        [evidence_update()],
    )
    record = calibration_record(
        calculation,
        snapshot_at=datetime(2026, 8, 5, 6, 0, tzinfo=UTC),
    )

    assert record.calculation_id == calculation.calculation_id
    assert record.score_calculation_id == SCORE_CALCULATION_ID
    assert record.raw_score == calculation.raw_score
    assert record.calibrated_score == calculation.calibrated_score
    assert record.input_evidence_ids == [str(DOCUMENT_ID)]
    assert record.scoring_version == "deterministic-scoring-v1"
    assert record.calibration_version == "score-calibration-v1"
