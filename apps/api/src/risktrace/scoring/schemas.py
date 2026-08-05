import enum
import uuid
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EvidenceWeightComponents(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_reliability: float = Field(ge=0.0, le=1.0)
    independence: float = Field(ge=0.0, le=1.0)
    score_relevance: float = Field(ge=0.0, le=1.0)
    freshness: float = Field(ge=0.0, le=1.0)
    data_quality: float = Field(ge=0.0, le=1.0)


class ScoreEvidenceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    document_id: uuid.UUID
    observation: float = Field(ge=0.0, le=1.0)
    weight: EvidenceWeightComponents

    @property
    def information_weight(self) -> float:
        from risktrace.scoring.evidence_weight import information_weight

        return information_weight(self.weight)


class ScoreInterval(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    lower: float = Field(ge=0.0, le=1.0)
    upper: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def require_ordered_bounds(self) -> Self:
        if self.lower > self.upper:
            raise ValueError("interval lower bound cannot exceed upper bound")
        return self

    @property
    def width(self) -> float:
        return self.upper - self.lower


class ScoreCalibrationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    tenant_id: uuid.UUID
    event_id: uuid.UUID
    score_calculation_id: uuid.UUID
    raw_score: float = Field(ge=0.0, le=1.0)
    scoring_version: str = Field(min_length=1, max_length=64)
    data_completeness: float = Field(ge=0.0, le=1.0)
    source_health: float = Field(ge=0.0, le=1.0)
    market_data_completeness: float | None = Field(default=None, ge=0.0, le=1.0)


class CalibrationStatus(enum.StrEnum):
    COMPLETE = "complete"
    DEGRADED = "degraded"


class ScoreCalibration(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    calculation_id: uuid.UUID
    tenant_id: uuid.UUID
    event_id: uuid.UUID
    score_calculation_id: uuid.UUID
    scoring_version: str = Field(min_length=1, max_length=64)
    calibration_version: str = Field(min_length=1, max_length=64)
    raw_score: float = Field(ge=0.0, le=1.0)
    calibrated_score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    score_interval: ScoreInterval
    data_completeness: float = Field(ge=0.0, le=1.0)
    source_health: float = Field(ge=0.0, le=1.0)
    market_data_completeness: float | None = Field(default=None, ge=0.0, le=1.0)
    input_evidence_ids: tuple[uuid.UUID, ...]
    evidence_snapshot_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    monte_carlo_seed: int = Field(ge=0)
    sample_count: int = Field(gt=0)
    parameters: dict[str, object]
    calculation_status: CalibrationStatus
    degradation_reasons: tuple[str, ...] = ()

    @model_validator(mode="after")
    def require_consistent_state(self) -> Self:
        if not self.score_interval.lower <= self.calibrated_score <= self.score_interval.upper:
            raise ValueError("score interval must contain calibrated_score")
        if self.calculation_status is CalibrationStatus.COMPLETE:
            if self.degradation_reasons:
                raise ValueError("complete calibration cannot contain degradation reasons")
        elif not self.degradation_reasons:
            raise ValueError("degraded calibration requires at least one reason")
        return self
