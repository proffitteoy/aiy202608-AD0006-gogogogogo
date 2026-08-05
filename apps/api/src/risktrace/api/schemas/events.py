from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from risktrace.api.schemas.common import PaginatedResponse


class ScoreInterval(BaseModel):
    lower_bound: float = Field(ge=0.0, le=1.0)
    upper_bound: float = Field(ge=0.0, le=1.0)


class EventScoreSummary(BaseModel):
    status: Literal["complete", "degraded", "unavailable"]
    raw_score: float | None = Field(default=None, ge=0.0, le=1.0)
    calibrated_score: float | None = Field(default=None, ge=0.0, le=1.0)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    score_interval: ScoreInterval | None = None
    scoring_version: str | None = None
    calibration_version: str | None = None
    calculation_id: UUID | None = None
    score_calculation_id: UUID | None = None
    degradation_reasons: list[str] = Field(default_factory=list)


class EventSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    status: str
    first_published_at: datetime
    document_count: int
    source_breakdown: dict[str, int]
    latest_activity: datetime | None = None
    score: EventScoreSummary
    created_at: datetime
    updated_at: datetime


class EventDetail(EventSummary):
    pass


class EventListResponse(PaginatedResponse[EventSummary]):
    pass


class TimelineBucket(BaseModel):
    bucket_start: datetime
    bucket_end: datetime
    counts: dict[str, int]


class LinkedDocument(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str | None = None
    source_type: str
    platform: str
    published_at: datetime
    weight: float
    engagement: dict | None = None


class WorkspaceResponse(BaseModel):
    event: EventSummary
    timeline: list[TimelineBucket]
    linked_documents: list[LinkedDocument]


class EvidenceItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str | None = None
    source_type: str
    platform: str
    published_at: datetime
    collected_at: datetime
    source_url: str | None = None
    engagement: dict | None = None
    raw_text_preview: str
    collection_method: str
    license_scope: str


class EvidenceListResponse(PaginatedResponse[EvidenceItem]):
    pass
