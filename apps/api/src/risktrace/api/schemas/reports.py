from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from risktrace.api.schemas.events import EvidenceItem


class ReportCreateRequest(BaseModel):
    event_id: uuid.UUID
    format: Literal["html"] = "html"


class ReportStatementItem(BaseModel):
    id: str
    text: str
    evidence_ids: list[uuid.UUID] = Field(default_factory=list)
    calculation_ids: list[uuid.UUID] = Field(default_factory=list)


class ReportSectionItem(BaseModel):
    id: str
    title: str
    status: str
    items: list[ReportStatementItem] = Field(default_factory=list)


class ReportScoreInterval(BaseModel):
    lower_bound: float
    upper_bound: float


class ReportScoreSummary(BaseModel):
    status: str
    raw_score: float | None = None
    calibrated_score: float | None = None
    confidence: float | None = None
    score_interval: ReportScoreInterval | None = None
    scoring_version: str | None = None
    calibration_version: str | None = None
    calculation_id: uuid.UUID | None = None
    score_calculation_id: uuid.UUID | None = None
    degradation_reasons: list[str] = Field(default_factory=list)


class ReportEventSummary(BaseModel):
    id: uuid.UUID
    title: str
    status: str
    first_published_at: datetime
    source_count: int
    authoritative_source_count: int
    source_breakdown: dict[str, int] = Field(default_factory=dict)
    score: ReportScoreSummary


class SnapshotSummary(BaseModel):
    id: uuid.UUID
    event_id: uuid.UUID
    snapshot_at: datetime
    analysis_version: str
    score_status: str
    evidence_count: int
    source_count: int
    scoring_version: str | None = None
    calibration_version: str | None = None


class ReportCreateResponse(BaseModel):
    id: uuid.UUID
    event_id: uuid.UUID
    snapshot_id: uuid.UUID
    format: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ReportDetailResponse(BaseModel):
    id: uuid.UUID
    event_id: uuid.UUID
    snapshot_id: uuid.UUID
    format: str
    status: str
    title: str
    summary: str
    render_engine: str
    brief_prompt_version: str
    body_html: str
    evidence_ids: list[uuid.UUID] = Field(default_factory=list)
    calculation_ids: list[uuid.UUID] = Field(default_factory=list)
    degradation_reasons: list[str] = Field(default_factory=list)
    created_at: datetime
    snapshot: SnapshotSummary
    event: ReportEventSummary
    sections: list[ReportSectionItem] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
