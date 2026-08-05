from collections.abc import Iterable
from dataclasses import dataclass, field

from risktrace.events.admission import AdmissionPolicy
from risktrace.events.matching import MatchingPolicy
from risktrace.events.schemas import (
    AdmissionInputs,
    EventCandidate,
    EventClaim,
    EventEvaluation,
)


@dataclass(frozen=True, slots=True)
class EventEngine:
    """Runs Rule 1 matching before Rule 2 admission without delegating to an LLM."""

    admission_policy: AdmissionPolicy = field(default_factory=AdmissionPolicy)
    matching_policy: MatchingPolicy = field(default_factory=MatchingPolicy)

    def evaluate(
        self,
        claim: EventClaim,
        candidates: Iterable[EventCandidate],
    ) -> EventEvaluation:
        best_match = self.matching_policy.find_best(
            claim.embedding,
            claim.subject_entity_keys,
            claim.event_type,
            claim.published_at,
            candidates,
        )
        novelty = 1.0 if best_match is None else 1.0 - best_match.score
        attached_match = (
            best_match
            if best_match is not None and best_match.score >= self.matching_policy.attach_threshold
            else None
        )
        admission = self.admission_policy.evaluate(
            AdmissionInputs(
                market_relevance=claim.market_relevance,
                state_change_strength=claim.state_change_strength,
                potential_impact=claim.potential_impact,
                novelty=novelty,
                source_quality=claim.source_quality,
                data_completeness=claim.data_completeness,
            ),
            attached_match=attached_match,
        )
        return EventEvaluation(admission=admission, novelty=novelty, best_match=best_match)
