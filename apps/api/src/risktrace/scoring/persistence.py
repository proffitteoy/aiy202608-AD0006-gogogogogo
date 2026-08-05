from datetime import UTC, datetime

from risktrace.db.models import EventScoreCalibration
from risktrace.scoring.schemas import ScoreCalibration


def calibration_record(
    calculation: ScoreCalibration,
    *,
    snapshot_at: datetime,
) -> EventScoreCalibration:
    if snapshot_at.tzinfo is None or snapshot_at.utcoffset() is None:
        raise ValueError("snapshot_at must include a timezone")
    return EventScoreCalibration(
        calculation_id=calculation.calculation_id,
        tenant_id=calculation.tenant_id,
        event_id=calculation.event_id,
        score_calculation_id=calculation.score_calculation_id,
        snapshot_at=snapshot_at.astimezone(UTC),
        scoring_version=calculation.scoring_version,
        calibration_version=calculation.calibration_version,
        raw_score=calculation.raw_score,
        calibrated_score=calculation.calibrated_score,
        confidence=calculation.confidence,
        lower_bound=calculation.score_interval.lower,
        upper_bound=calculation.score_interval.upper,
        data_completeness=calculation.data_completeness,
        source_health=calculation.source_health,
        market_data_completeness=calculation.market_data_completeness,
        input_evidence_ids=[
            str(evidence_id) for evidence_id in calculation.input_evidence_ids
        ],
        evidence_snapshot_hash=calculation.evidence_snapshot_hash,
        monte_carlo_seed=calculation.monte_carlo_seed,
        sample_count=calculation.sample_count,
        parameters=calculation.parameters,
        calculation_status=calculation.calculation_status.value,
        degradation_reasons=list(calculation.degradation_reasons),
    )
