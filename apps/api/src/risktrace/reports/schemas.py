from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SnapshotScoreInterval(BaseModel):
    lower_bound: float
    upper_bound: float


class SnapshotScoreSummary(BaseModel):
    status: str
    raw_score: float | None = None
    calibrated_score: float | None = None
    confidence: float | None = None
    score_interval: SnapshotScoreInterval | None = None
    scoring_version: str | None = None
    calibration_version: str | None = None
    calculation_id: uuid.UUID | None = None
    score_calculation_id: uuid.UUID | None = None
    degradation_reasons: list[str] = Field(default_factory=list)


class SnapshotEventSummary(BaseModel):
    id: uuid.UUID
    title: str
    status: str
    first_published_at: datetime
    source_count: int
    authoritative_source_count: int
    source_breakdown: dict[str, int] = Field(default_factory=dict)


class SnapshotEvidenceItem(BaseModel):
    id: uuid.UUID
    title: str | None = None
    source_type: str
    platform: str
    published_at: datetime
    collected_at: datetime
    source_url: str | None = None
    engagement: dict[str, object] | None = None
    raw_text_preview: str
    collection_method: str
    license_scope: str


class SnapshotOpinionItem(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    target_entity_id: uuid.UUID | None = None
    stance: str
    emotion: str
    reason: str
    claim_type: str
    evidence_span: str
    model_confidence: float
    created_at: datetime


class SnapshotTransmissionEdge(BaseModel):
    id: uuid.UUID
    from_node_type: str
    from_node_id: uuid.UUID
    to_node_type: str
    to_node_id: uuid.UUID
    from_node_label: str | None = None
    to_node_label: str | None = None
    mechanism: str
    direction: str
    horizon: str
    evidence_ids: list[uuid.UUID] = Field(default_factory=list)
    knowledge_ids: list[uuid.UUID] = Field(default_factory=list)
    model_confidence: float
    status: str
    created_at: datetime


class SnapshotImpactRow(BaseModel):
    entity_id: uuid.UUID
    entity_name: str
    entity_type: str
    direction: str
    impact_strength: float
    business_exposure: float
    opinion_support: float
    fact_support: float
    time_horizon: str
    composite_confidence: float
    edge_count: int
    opinion_count: int
    evidence_count: int
    evidence_ids: list[uuid.UUID] = Field(default_factory=list)


class AnalysisSnapshotPayload(BaseModel):
    event: SnapshotEventSummary
    score: SnapshotScoreSummary
    evidence: list[SnapshotEvidenceItem] = Field(default_factory=list)
    opinions: list[SnapshotOpinionItem] = Field(default_factory=list)
    transmission: list[SnapshotTransmissionEdge] = Field(default_factory=list)
    impact_matrix: list[SnapshotImpactRow] = Field(default_factory=list)


class ReportStatement(BaseModel):
    id: str
    text: str
    evidence_ids: list[uuid.UUID] = Field(default_factory=list)
    calculation_ids: list[uuid.UUID] = Field(default_factory=list)


class ReportSection(BaseModel):
    id: str
    title: str
    status: str
    items: list[ReportStatement] = Field(default_factory=list)


class RenderedReport(BaseModel):
    title: str
    summary: str
    status: str
    sections: list[ReportSection]
    evidence_ids: list[uuid.UUID]
    calculation_ids: list[uuid.UUID]
    degradation_reasons: list[str]
    body_html: str
