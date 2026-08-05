from collections.abc import Iterable
from dataclasses import dataclass, fields
from math import isclose, prod

from risktrace.events.schemas import (
    AdmissionDecision,
    AdmissionInputs,
    AdmissionResult,
    ConfirmationEvidence,
    ConfirmationResult,
    ConfirmationSourceType,
    MatchResult,
)


def _require_unit_interval(name: str, value: float) -> None:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class AdmissionPolicy:
    version: str = "admission-v2"
    market_weight: float = 0.20
    state_change_weight: float = 0.20
    impact_weight: float = 0.25
    novelty_weight: float = 0.15
    quality_weight: float = 0.10
    completeness_weight: float = 0.10
    market_threshold: float = 0.50
    state_change_threshold: float = 0.60
    impact_threshold: float = 0.40
    admit_threshold: float = 0.72
    direct_admit_quality_threshold: float = 0.40
    direct_admit_completeness_threshold: float = 0.50

    def __post_init__(self) -> None:
        weights = (
            self.market_weight,
            self.state_change_weight,
            self.impact_weight,
            self.novelty_weight,
            self.quality_weight,
            self.completeness_weight,
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
            + self.state_change_weight * inputs.state_change_strength
            + self.impact_weight * inputs.potential_impact
            + self.novelty_weight * inputs.novelty
            + self.quality_weight * inputs.source_quality
            + self.completeness_weight * inputs.data_completeness
        )

    def evaluate(
        self,
        inputs: AdmissionInputs,
        attached_match: MatchResult | None = None,
    ) -> AdmissionResult:
        decision_value = self.score(inputs)
        if inputs.market_relevance < self.market_threshold:
            return self._result(
                AdmissionDecision.DROP,
                decision_value,
                "market_relevance_below_gate",
            )
        if inputs.state_change_strength < self.state_change_threshold:
            return self._result(
                AdmissionDecision.DROP,
                decision_value,
                "state_change_below_gate",
            )
        if attached_match is not None:
            return AdmissionResult(
                decision=AdmissionDecision.ATTACH,
                decision_value=decision_value,
                rule_version=self.version,
                reasons=("matched_existing_event",),
                matched_event_id=attached_match.event_id,
                matched_similarity=attached_match.score,
            )
        if inputs.potential_impact < self.impact_threshold:
            return self._result(
                AdmissionDecision.DROP,
                decision_value,
                "potential_impact_below_gate",
            )
        if (
            decision_value >= self.admit_threshold
            and inputs.source_quality >= self.direct_admit_quality_threshold
            and inputs.data_completeness >= self.direct_admit_completeness_threshold
        ):
            return self._result(
                AdmissionDecision.ADMIT,
                decision_value,
                "admission_threshold_met",
            )
        reasons = ["awaiting_confirmation"]
        if decision_value < self.admit_threshold:
            reasons.append("decision_value_below_admit_threshold")
        if inputs.source_quality < self.direct_admit_quality_threshold:
            reasons.append("source_quality_requires_wait")
        if inputs.data_completeness < self.direct_admit_completeness_threshold:
            reasons.append("data_completeness_requires_wait")
        return self._result(AdmissionDecision.WAIT, decision_value, *reasons)

    def _result(
        self,
        decision: AdmissionDecision,
        decision_value: float,
        *reasons: str,
    ) -> AdmissionResult:
        return AdmissionResult(decision, decision_value, self.version, tuple(reasons))


@dataclass(frozen=True, slots=True)
class ConfirmationPolicy:
    version: str = "confirmation-v2"
    news_cap: float = 0.75
    social_cap: float = 0.35
    coherence_floor: float = 0.85
    coherence_weight: float = 0.15
    threshold: float = 0.70

    def __post_init__(self) -> None:
        for name, value in (
            ("news_cap", self.news_cap),
            ("social_cap", self.social_cap),
            ("coherence_floor", self.coherence_floor),
            ("coherence_weight", self.coherence_weight),
            ("threshold", self.threshold),
        ):
            _require_unit_interval(name, value)
        if not isclose(self.coherence_floor + self.coherence_weight, 1.0, abs_tol=1e-9):
            raise ValueError("coherence floor and weight must sum to 1")

    def calculate(self, evidence: Iterable[ConfirmationEvidence]) -> ConfirmationResult:
        items = tuple(sorted(evidence, key=lambda item: str(item.document_id)))
        document_ids = tuple(item.document_id for item in items)
        if len(set(document_ids)) != len(document_ids):
            raise ValueError("confirmation evidence must contain independent documents")

        fact_support = self._accumulate(
            item.support
            for item in items
            if item.source_type is ConfirmationSourceType.FACT
        )
        news_support = self._accumulate(
            item.support
            for item in items
            if item.source_type is ConfirmationSourceType.NEWS
        )
        social_support = self._accumulate(
            item.support
            for item in items
            if item.source_type is ConfirmationSourceType.SOCIAL
        )
        evidence_support = 1.0 - (
            (1.0 - fact_support)
            * (1.0 - self.news_cap * news_support)
            * (1.0 - self.social_cap * social_support)
        )
        total_support = sum(item.support for item in items)
        cluster_coherence = (
            sum(item.support * item.cluster_similarity for item in items) / total_support
            if total_support > 0.0
            else 0.0
        )
        contradiction = self._accumulate(
            item.contradiction_strength * item.support for item in items
        )
        certainty = (
            evidence_support
            * (self.coherence_floor + self.coherence_weight * cluster_coherence)
            * (1.0 - contradiction)
        )
        return ConfirmationResult(
            certainty=certainty,
            fact_support=fact_support,
            news_support=news_support,
            social_support=social_support,
            cluster_coherence=cluster_coherence,
            contradiction=contradiction,
            rule_version=self.version,
            input_document_ids=document_ids,
        )

    def score(self, evidence: Iterable[ConfirmationEvidence]) -> float:
        return self.calculate(evidence).certainty

    def is_confirmed(self, evidence: Iterable[ConfirmationEvidence]) -> bool:
        return self.score(evidence) >= self.threshold

    @staticmethod
    def _accumulate(values: Iterable[float]) -> float:
        return 1.0 - prod(1.0 - value for value in values)
