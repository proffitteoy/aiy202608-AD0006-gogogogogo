import hashlib
import json
import math
import random
import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, fields

from risktrace.scoring.confidence import credible_interval, posterior_confidence
from risktrace.scoring.schemas import (
    CalibrationStatus,
    ScoreCalibration,
    ScoreCalibrationInput,
    ScoreEvidenceUpdate,
    ScoreInterval,
)


@dataclass(frozen=True, slots=True)
class CalibrationPolicy:
    version: str = "score-calibration-v1"
    prior_strength: float = 12.0
    evidence_strength_scale: float = 4.0
    sample_count: int = 5_000
    credible_mass: float = 0.90
    confidence_reference_width: float = 0.50
    evidence_saturation: float = 4.0
    boundary_epsilon: float = 1e-6

    def __post_init__(self) -> None:
        if not self.version.strip():
            raise ValueError("calibration version is required")
        if self.sample_count <= 0:
            raise ValueError("sample_count must be positive")
        for field in fields(self):
            value = getattr(self, field.name)
            if field.name in {
                "prior_strength",
                "evidence_strength_scale",
                "confidence_reference_width",
                "evidence_saturation",
            } and (not math.isfinite(value) or value <= 0.0):
                raise ValueError(f"{field.name} must be positive and finite")
        if not 0.0 < self.credible_mass < 1.0:
            raise ValueError("credible_mass must be between 0 and 1")
        if not 0.0 < self.boundary_epsilon <= 1e-3:
            raise ValueError("boundary_epsilon must be between 0 and 0.001")


def _canonical_update(update: ScoreEvidenceUpdate) -> dict[str, object]:
    return {
        "document_id": str(update.document_id),
        "observation": update.observation,
        "information_weight": update.information_weight,
        "weight": update.weight.model_dump(mode="json"),
    }


def _effective_updates(
    updates: Iterable[ScoreEvidenceUpdate],
) -> tuple[ScoreEvidenceUpdate, ...]:
    effective = [update for update in updates if update.information_weight > 0.0]
    effective.sort(key=lambda update: str(update.document_id))
    seen: set[uuid.UUID] = set()
    for update in effective:
        if update.document_id in seen:
            raise ValueError("a document can update score calibration at most once")
        seen.add(update.document_id)
    return tuple(effective)


def _policy_parameters(policy: CalibrationPolicy) -> dict[str, object]:
    return {
        "prior_strength": policy.prior_strength,
        "evidence_strength_scale": policy.evidence_strength_scale,
        "credible_mass": policy.credible_mass,
        "confidence_reference_width": policy.confidence_reference_width,
        "evidence_saturation": policy.evidence_saturation,
        "boundary_epsilon": policy.boundary_epsilon,
        "sample_count": policy.sample_count,
        "rng": "python-random-betavariate-v1",
        "quantile": "linear-interpolation-v1",
        "seed": "sha256-first-63-bits-v1",
        "snapshot_hash": "canonical-json-sha256-v1",
        "zero_information_updates": "excluded",
    }


def _snapshot_hash(
    calibration_input: ScoreCalibrationInput,
    updates: Sequence[ScoreEvidenceUpdate],
    policy: CalibrationPolicy,
) -> str:
    payload = {
        "input": calibration_input.model_dump(mode="json"),
        "calibration_version": policy.version,
        "evidence_updates": [_canonical_update(update) for update in updates],
        "parameters": _policy_parameters(policy),
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def deterministic_seed(
    event_id: uuid.UUID,
    calibration_version: str,
    evidence_snapshot_hash: str,
) -> int:
    payload = f"{event_id}:{calibration_version}:{evidence_snapshot_hash}".encode()
    raw_seed = int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")
    return raw_seed & ((1 << 63) - 1)


def _credible_interval_with_mean(
    samples: Sequence[float],
    credible_mass: float,
    analytic_mean: float,
) -> ScoreInterval:
    interval = credible_interval(samples, credible_mass)
    return ScoreInterval(
        lower=min(interval.lower, analytic_mean),
        upper=max(interval.upper, analytic_mean),
    )


@dataclass(frozen=True, slots=True)
class CalibrationEngine:
    policy: CalibrationPolicy = CalibrationPolicy()

    def calculate(
        self,
        calibration_input: ScoreCalibrationInput,
        updates: Iterable[ScoreEvidenceUpdate] = (),
    ) -> ScoreCalibration:
        effective_updates = _effective_updates(tuple(updates))
        snapshot_hash = _snapshot_hash(calibration_input, effective_updates, self.policy)
        seed = deterministic_seed(
            calibration_input.event_id,
            self.policy.version,
            snapshot_hash,
        )

        alpha = max(
            self.policy.prior_strength * calibration_input.raw_score,
            self.policy.boundary_epsilon,
        )
        beta = max(
            self.policy.prior_strength * (1.0 - calibration_input.raw_score),
            self.policy.boundary_epsilon,
        )
        total_evidence_strength = 0.0
        for update in effective_updates:
            strength = update.information_weight * self.policy.evidence_strength_scale
            alpha += strength * update.observation
            beta += strength * (1.0 - update.observation)
            total_evidence_strength += strength

        calibrated_score = alpha / (alpha + beta)
        random_generator = random.Random(seed)
        samples = [
            random_generator.betavariate(alpha, beta)
            for _ in range(self.policy.sample_count)
        ]
        interval = _credible_interval_with_mean(
            samples,
            self.policy.credible_mass,
            calibrated_score,
        )

        quality_values = [
            calibration_input.data_completeness,
            calibration_input.source_health,
        ]
        if calibration_input.market_data_completeness is not None:
            quality_values.append(calibration_input.market_data_completeness)
        confidence = posterior_confidence(
            interval,
            min(quality_values),
            total_evidence_strength,
            self.policy.confidence_reference_width,
            self.policy.evidence_saturation,
        )

        degradation_reasons: list[str] = []
        if calibration_input.data_completeness < 1.0:
            degradation_reasons.append("data_incomplete")
        if calibration_input.source_health < 1.0:
            degradation_reasons.append("source_health_degraded")
        if calibration_input.market_data_completeness is None:
            degradation_reasons.append("market_data_unavailable")
        elif calibration_input.market_data_completeness < 1.0:
            degradation_reasons.append("market_data_incomplete")
        if not effective_updates:
            degradation_reasons.append("no_independent_calibration_evidence")

        audit_parameters = _policy_parameters(self.policy)
        audit_parameters.update(
            {
                "alpha": alpha,
                "beta": beta,
                "total_evidence_strength": total_evidence_strength,
                "evidence_updates": [
                    _canonical_update(update) for update in effective_updates
                ],
            }
        )
        calculation_id = uuid.uuid5(
            uuid.NAMESPACE_URL,
            ":".join(
                (
                    "risktrace-score-calibration",
                    str(calibration_input.tenant_id),
                    str(calibration_input.event_id),
                    str(calibration_input.score_calculation_id),
                    self.policy.version,
                    snapshot_hash,
                )
            ),
        )
        return ScoreCalibration(
            calculation_id=calculation_id,
            tenant_id=calibration_input.tenant_id,
            event_id=calibration_input.event_id,
            score_calculation_id=calibration_input.score_calculation_id,
            scoring_version=calibration_input.scoring_version,
            calibration_version=self.policy.version,
            raw_score=calibration_input.raw_score,
            calibrated_score=calibrated_score,
            confidence=confidence,
            score_interval=interval,
            data_completeness=calibration_input.data_completeness,
            source_health=calibration_input.source_health,
            market_data_completeness=calibration_input.market_data_completeness,
            input_evidence_ids=tuple(update.document_id for update in effective_updates),
            evidence_snapshot_hash=snapshot_hash,
            monte_carlo_seed=seed,
            sample_count=self.policy.sample_count,
            parameters=audit_parameters,
            calculation_status=(
                CalibrationStatus.DEGRADED
                if degradation_reasons
                else CalibrationStatus.COMPLETE
            ),
            degradation_reasons=tuple(degradation_reasons),
        )
