from dataclasses import dataclass, fields
from math import isclose

from risktrace.events.schemas import (
    AdmissionDecision,
    AdmissionInputs,
    AdmissionResult,
    MatchResult,
)


def _require_unit_interval(name: str, value: float) -> None:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class AdmissionPolicy:
    version: str = "admission-v1"
    market_weight: float = 0.20
    eventness_weight: float = 0.20
    impact_weight: float = 0.30
    novelty_weight: float = 0.20
    quality_weight: float = 0.10
    market_threshold: float = 0.50
    eventness_threshold: float = 0.60
    impact_threshold: float = 0.40
    create_threshold: float = 0.75
    direct_create_quality_threshold: float = 0.40

    def __post_init__(self) -> None:
        weights = (
            self.market_weight,
            self.eventness_weight,
            self.impact_weight,
            self.novelty_weight,
            self.quality_weight,
        )
        if not isclose(sum(weights), 1.0, abs_tol=1e-9):
            raise ValueError("admission weights must sum to 1")
        for field in fields(self):
            name = field.name
            value = getattr(self, name)
            if name.endswith(("_weight", "_threshold")):
                _require_unit_interval(name, value)

    def score(self, inputs: AdmissionInputs) -> float:
        for field in fields(inputs):
            _require_unit_interval(field.name, getattr(inputs, field.name))
        return (
            self.market_weight * inputs.market_relevance
            + self.eventness_weight * inputs.eventness
            + self.impact_weight * inputs.potential_impact
            + self.novelty_weight * inputs.novelty
            + self.quality_weight * inputs.source_quality
        )

    def evaluate(
        self,
        inputs: AdmissionInputs,
        attached_match: MatchResult | None = None,
    ) -> AdmissionResult:
        score = self.score(inputs)
        if inputs.market_relevance < self.market_threshold:
            return self._result(AdmissionDecision.DROP, score, "market_relevance_below_gate")
        if inputs.eventness < self.eventness_threshold:
            return self._result(AdmissionDecision.DROP, score, "eventness_below_gate")
        if attached_match is not None:
            return AdmissionResult(
                decision=AdmissionDecision.ATTACH,
                score=score,
                rule_version=self.version,
                reasons=("matched_existing_event",),
                matched_event_id=attached_match.event_id,
                matched_similarity=attached_match.score,
            )
        if inputs.potential_impact < self.impact_threshold:
            return self._result(AdmissionDecision.DROP, score, "potential_impact_below_gate")
        if (
            score >= self.create_threshold
            and inputs.source_quality >= self.direct_create_quality_threshold
        ):
            return self._result(AdmissionDecision.CREATE, score, "admission_threshold_met")
        reasons = ["awaiting_confirmation"]
        if score < self.create_threshold:
            reasons.append("admission_score_below_create_threshold")
        if inputs.source_quality < self.direct_create_quality_threshold:
            reasons.append("source_quality_requires_candidate_state")
        return self._result(AdmissionDecision.CANDIDATE, score, *reasons)

    def _result(
        self,
        decision: AdmissionDecision,
        score: float,
        *reasons: str,
    ) -> AdmissionResult:
        return AdmissionResult(decision, score, self.version, tuple(reasons))


@dataclass(frozen=True, slots=True)
class ConfirmationPolicy:
    version: str = "confirmation-v1"
    independent_source_weight: float = 0.40
    source_quality_weight: float = 0.35
    velocity_weight: float = 0.25
    independent_sources_saturation: int = 3
    threshold: float = 0.70

    def __post_init__(self) -> None:
        weights = (
            self.independent_source_weight,
            self.source_quality_weight,
            self.velocity_weight,
        )
        if not isclose(sum(weights), 1.0, abs_tol=1e-9):
            raise ValueError("confirmation weights must sum to 1")
        if self.independent_sources_saturation <= 0:
            raise ValueError("independent_sources_saturation must be positive")
        for name, value in (
            ("independent_source_weight", self.independent_source_weight),
            ("source_quality_weight", self.source_quality_weight),
            ("velocity_weight", self.velocity_weight),
            ("threshold", self.threshold),
        ):
            _require_unit_interval(name, value)

    def score(
        self,
        independent_source_count: int,
        best_source_quality: float,
        velocity_score: float,
    ) -> float:
        if independent_source_count < 0:
            raise ValueError("independent_source_count cannot be negative")
        _require_unit_interval("best_source_quality", best_source_quality)
        _require_unit_interval("velocity_score", velocity_score)
        source_score = min(independent_source_count / self.independent_sources_saturation, 1.0)
        return (
            self.independent_source_weight * source_score
            + self.source_quality_weight * best_source_quality
            + self.velocity_weight * velocity_score
        )

    def is_confirmed(
        self,
        independent_source_count: int,
        best_source_quality: float,
        velocity_score: float,
    ) -> bool:
        return (
            self.score(independent_source_count, best_source_quality, velocity_score)
            >= self.threshold
        )
