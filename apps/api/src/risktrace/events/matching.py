import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from risktrace.events.schemas import EventCandidate, MatchResult


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or not left:
        raise ValueError("embeddings must be non-empty and have equal dimensions")
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    raw = sum(a * b for a, b in zip(left, right, strict=True)) / (left_norm * right_norm)
    return min(max(raw, 0.0), 1.0)


def entity_similarity(left: Iterable[str], right: Iterable[str]) -> float:
    left_set = frozenset(left)
    right_set = frozenset(right)
    union = left_set | right_set
    if not union:
        return 0.0
    return len(left_set & right_set) / len(union)


def time_similarity(left: datetime, right: datetime, decay_hours: float = 6.0) -> float:
    if left.tzinfo is None or right.tzinfo is None:
        raise ValueError("event timestamps must include timezones")
    if decay_hours <= 0:
        raise ValueError("decay_hours must be positive")
    delta_hours = abs((left - right).total_seconds()) / 3_600
    return math.exp(-delta_hours / decay_hours)


@dataclass(frozen=True, slots=True)
class MatchingPolicy:
    version: str = "event-match-v1"
    semantic_weight: float = 0.55
    entity_weight: float = 0.20
    time_weight: float = 0.15
    type_weight: float = 0.10
    time_decay_hours: float = 6.0
    candidate_window_hours: float = 48.0
    attach_threshold: float = 0.78

    def __post_init__(self) -> None:
        weight_sum = self.semantic_weight + self.entity_weight + self.time_weight + self.type_weight
        if not math.isclose(weight_sum, 1.0, abs_tol=1e-9):
            raise ValueError("matching weights must sum to 1")
        if self.time_decay_hours <= 0 or self.candidate_window_hours <= 0:
            raise ValueError("matching time parameters must be positive")
        if not 0.0 <= self.attach_threshold <= 1.0:
            raise ValueError("attach_threshold must be between 0 and 1")

    def score(
        self,
        embedding: Sequence[float],
        entity_keys: Iterable[str],
        event_type: str,
        published_at: datetime,
        candidate: EventCandidate,
    ) -> MatchResult:
        semantic = cosine_similarity(embedding, candidate.centroid_embedding)
        entity = entity_similarity(entity_keys, candidate.entity_keys)
        temporal = time_similarity(published_at, candidate.last_seen_at, self.time_decay_hours)
        same_type = float(event_type == candidate.event_type)
        total = (
            self.semantic_weight * semantic
            + self.entity_weight * entity
            + self.time_weight * temporal
            + self.type_weight * same_type
        )
        return MatchResult(candidate.id, total, semantic, entity, temporal, same_type)

    def find_best(
        self,
        embedding: Sequence[float],
        entity_keys: Iterable[str],
        event_type: str,
        published_at: datetime,
        candidates: Iterable[EventCandidate],
    ) -> MatchResult | None:
        window = timedelta(hours=self.candidate_window_hours)
        if published_at.tzinfo is None or published_at.utcoffset() is None:
            raise ValueError("published_at must include a timezone")
        eligible: list[EventCandidate] = []
        for candidate in candidates:
            if candidate.last_seen_at.tzinfo is None or candidate.last_seen_at.utcoffset() is None:
                raise ValueError("candidate last_seen_at must include a timezone")
            if abs(published_at - candidate.last_seen_at) <= window:
                eligible.append(candidate)
        if not eligible:
            return None
        results = [
            self.score(embedding, entity_keys, event_type, published_at, candidate)
            for candidate in eligible
        ]
        return min(results, key=lambda result: (-result.score, str(result.event_id)))


def update_centroid(
    current_centroid: Sequence[float],
    current_weight: float,
    evidence_embedding: Sequence[float],
    evidence_weight: float,
) -> tuple[tuple[float, ...], float]:
    if len(current_centroid) != len(evidence_embedding) or not current_centroid:
        raise ValueError("embeddings must be non-empty and have equal dimensions")
    if current_weight < 0 or evidence_weight <= 0:
        raise ValueError("centroid weight must be non-negative and evidence weight positive")
    combined_weight = current_weight + evidence_weight
    centroid = tuple(
        (current_weight * old + evidence_weight * new) / combined_weight
        for old, new in zip(current_centroid, evidence_embedding, strict=True)
    )
    return centroid, combined_weight


def initial_centroid(
    embedding: Sequence[float], evidence_weight: float
) -> tuple[tuple[float, ...], float]:
    if not embedding or evidence_weight <= 0:
        raise ValueError("embedding and positive evidence weight are required")
    return tuple(float(value) for value in embedding), evidence_weight


def evidence_weight(
    source_quality: float,
    *,
    is_original: bool | None,
    is_duplicate: bool,
    originality_boost: float = 1.25,
    duplicate_multiplier: float = 0.10,
) -> float:
    if not 0.0 <= source_quality <= 1.0:
        raise ValueError("source_quality must be between 0 and 1")
    weight = source_quality
    if is_original is True:
        weight *= originality_boost
    if is_duplicate:
        weight *= duplicate_multiplier
    return max(weight, 0.01)
