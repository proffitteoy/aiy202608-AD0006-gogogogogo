import enum
import math
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AdmissionDecision(enum.StrEnum):
    DROP = "drop"
    WAIT = "wait"
    ADMIT = "admit"
    ATTACH = "attach"


class ConfirmationSourceType(enum.StrEnum):
    FACT = "fact"
    NEWS = "news"
    SOCIAL = "social"


class LifecycleStatus(enum.StrEnum):
    CANDIDATE = "candidate"
    CONFIRMED = "confirmed"
    ACTIVE = "active"
    COOLING = "cooling"
    CLOSED = "closed"


class StateChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    property: str = Field(min_length=1, max_length=128)
    from_value: str | None = Field(default=None, max_length=512)
    to_value: str = Field(min_length=1, max_length=512)


class ImpactChannel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str = Field(min_length=1, max_length=64)
    score: float = Field(ge=0.0, le=1.0)
    reason: str | None = Field(default=None, max_length=1_000)


class RelatedAsset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1, max_length=64)
    relation: str = Field(min_length=1, max_length=64)


class EventClaim(BaseModel):
    """Validated semantic variables; deterministic rules still make every decision."""

    model_config = ConfigDict(extra="forbid")

    document_id: uuid.UUID
    title: str = Field(min_length=1, max_length=1_000)
    subject_entity_keys: tuple[str, ...]
    event_type: str = Field(min_length=1, max_length=128)
    state_change: StateChange
    published_at: datetime
    location: str | None = Field(default=None, max_length=255)
    market_relevance: float = Field(ge=0.0, le=1.0)
    state_change_strength: float = Field(ge=0.0, le=1.0)
    potential_impact: float = Field(ge=0.0, le=1.0)
    source_quality: float = Field(ge=0.0, le=1.0)
    data_completeness: float = Field(ge=0.0, le=1.0)
    impact_channels: tuple[ImpactChannel, ...] = ()
    related_assets: tuple[RelatedAsset, ...] = ()
    embedding: tuple[float, ...] = Field(min_length=1)

    @field_validator("published_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("published_at must include a timezone")
        return value.astimezone(UTC)

    @field_validator("subject_entity_keys")
    @classmethod
    def canonicalize_entity_keys(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        cleaned = tuple(sorted({item.strip().casefold() for item in value if item.strip()}))
        if not cleaned:
            raise ValueError("at least one subject entity is required")
        return cleaned

    @field_validator("embedding")
    @classmethod
    def require_finite_nonzero_embedding(cls, value: tuple[float, ...]) -> tuple[float, ...]:
        if any(not math.isfinite(item) for item in value):
            raise ValueError("embedding values must be finite")
        if not any(item != 0.0 for item in value):
            raise ValueError("embedding cannot be the zero vector")
        return value


@dataclass(frozen=True, slots=True)
class AdmissionInputs:
    market_relevance: float
    state_change_strength: float
    potential_impact: float
    novelty: float
    source_quality: float
    data_completeness: float


@dataclass(frozen=True, slots=True)
class AdmissionResult:
    decision: AdmissionDecision
    decision_value: float
    rule_version: str
    reasons: tuple[str, ...]
    matched_event_id: uuid.UUID | None = None
    matched_similarity: float | None = None


@dataclass(frozen=True, slots=True)
class ConfirmationEvidence:
    document_id: uuid.UUID
    source_type: ConfirmationSourceType
    source_reliability: float
    document_confidence: float
    cluster_similarity: float
    contradiction_strength: float = 0.0

    def __post_init__(self) -> None:
        for name in (
            "source_reliability",
            "document_confidence",
            "cluster_similarity",
            "contradiction_strength",
        ):
            value = getattr(self, name)
            if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be a finite number between 0 and 1")

    @property
    def support(self) -> float:
        return self.source_reliability * self.document_confidence


@dataclass(frozen=True, slots=True)
class ConfirmationResult:
    certainty: float
    fact_support: float
    news_support: float
    social_support: float
    cluster_coherence: float
    contradiction: float
    rule_version: str
    input_document_ids: tuple[uuid.UUID, ...]


@dataclass(frozen=True, slots=True)
class EventCandidate:
    id: uuid.UUID
    centroid_embedding: tuple[float, ...]
    entity_keys: frozenset[str]
    event_type: str
    last_seen_at: datetime


@dataclass(frozen=True, slots=True)
class MatchResult:
    event_id: uuid.UUID
    score: float
    semantic_similarity: float
    entity_similarity: float
    time_similarity: float
    type_similarity: float


@dataclass(frozen=True, slots=True)
class EventEvaluation:
    admission: AdmissionResult
    novelty: float
    best_match: MatchResult | None
