import enum
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from risktrace.db.base import Base


class SourceType(enum.StrEnum):
    FACT = "fact"
    NEWS = "news"
    SOCIAL = "social"
    MARKET = "market"


class SourceHealthStatus(enum.StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class EventStatus(enum.StrEnum):
    CANDIDATE = "candidate"
    CONFIRMED = "confirmed"
    ACTIVE = "active"
    ANALYZED = "analyzed"
    ALERTED = "alerted"
    COOLING = "cooling"
    CLOSED = "closed"
    ARCHIVED = "archived"


class RawDocument(Base):
    __tablename__ = "raw_documents"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "platform",
            "source_id",
            name="uq_raw_documents_tenant_platform_source",
        ),
        CheckConstraint(
            "source_type IN ('fact', 'news', 'social', 'market')",
            name="ck_raw_documents_source_type",
        ),
        CheckConstraint(
            "source_level IN ('official', 'professional_media', "
            "'public_discussion', 'market_data')",
            name="ck_raw_documents_source_level",
        ),
        Index("ix_raw_documents_published_at", "published_at"),
        Index("ix_raw_documents_tenant_id", "tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)
    source_level: Mapped[str] = mapped_column(String(32), nullable=False)
    platform: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    replay_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    author_id_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String(16), nullable=False)
    engagement: Mapped[dict[str, int]] = mapped_column(JSON, default=dict, nullable=False)
    is_original: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    collection_method: Mapped[str] = mapped_column(String(128), nullable=False)
    license_scope: Mapped[str] = mapped_column(String(128), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    raw_payload_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_metadata: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class IngestionReceipt(Base):
    __tablename__ = "ingestion_receipts"
    __table_args__ = (
        CheckConstraint(
            "outcome IN ('inserted', 'duplicate')",
            name="ck_ingestion_receipts_outcome",
        ),
        CheckConstraint(
            "processing_status IN ('pending_enrichment')",
            name="ck_ingestion_receipts_processing_status",
        ),
        Index("ix_ingestion_receipts_document_received", "document_id", "received_at"),
        Index("ix_ingestion_receipts_tenant_received", "tenant_id", "received_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("raw_documents.id", ondelete="RESTRICT"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    stream: Mapped[str] = mapped_column(String(128), nullable=False, default="default")
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    replay_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    processing_status: Mapped[str] = mapped_column(
        String(32), default="pending_enrichment", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SourceCheckpoint(Base):
    __tablename__ = "source_checkpoints"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "provider",
            "stream",
            name="uq_source_checkpoints_stream",
        ),
        Index("ix_source_checkpoints_tenant_provider", "tenant_id", "provider"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    stream: Mapped[str] = mapped_column(String(128), nullable=False, default="default")
    cursor: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class SourceHealth(Base):
    __tablename__ = "source_health"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "provider",
            "stream",
            name="uq_source_health_stream",
        ),
        CheckConstraint(
            "status IN ('healthy', 'degraded', 'unavailable')",
            name="ck_source_health_status",
        ),
        CheckConstraint(
            "source_type IN ('fact', 'news', 'social', 'market')",
            name="ck_source_health_source_type",
        ),
        CheckConstraint(
            "consecutive_failures >= 0",
            name="ck_source_health_failure_count",
        ),
        Index("ix_source_health_tenant_status", "tenant_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    stream: Mapped[str] = mapped_column(String(128), nullable=False, default="default")
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), default=SourceHealthStatus.HEALTHY.value, nullable=False
    )
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_success_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_failure_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        CheckConstraint(
            "status IN ('candidate', 'confirmed', 'active', 'analyzed', 'alerted', "
            "'cooling', 'closed', 'archived')",
            name="ck_events_status",
        ),
        CheckConstraint(
            "(admission_decision_value IS NULL OR admission_decision_value BETWEEN 0 AND 1) AND "
            "(score_confidence IS NULL OR score_confidence BETWEEN 0 AND 1) AND "
            "(heat_score IS NULL OR heat_score BETWEEN 0 AND 1) AND "
            "(raw_score IS NULL OR raw_score BETWEEN 0 AND 1) AND "
            "(calibrated_score IS NULL OR calibrated_score BETWEEN 0 AND 1) AND "
            "((score_lower_bound IS NULL AND score_upper_bound IS NULL) OR "
            "(score_lower_bound BETWEEN 0 AND 1 AND score_upper_bound BETWEEN 0 AND 1 AND "
            "score_lower_bound <= score_upper_bound AND "
            "calibrated_score BETWEEN score_lower_bound AND score_upper_bound)) AND "
            "(momentum IS NULL OR momentum BETWEEN -1 AND 1) AND "
            "centroid_weight >= 0 AND evidence_count >= 0",
            name="ck_events_normalized_scores",
        ),
        Index("ix_events_tenant_status", "tenant_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default=EventStatus.CANDIDATE.value)
    first_published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    centroid_embedding: Mapped[list[float] | None] = mapped_column(Vector(), nullable=True)
    centroid_weight: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    embedding_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    admission_decision_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    heat_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    momentum: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    calibrated_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_lower_bound: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_upper_bound: Mapped[float | None] = mapped_column(Float, nullable=True)
    scoring_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    calibration_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    evidence_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Entity(Base):
    __tablename__ = "entities"
    __table_args__ = (
        UniqueConstraint("tenant_id", "entity_type", "name", name="uq_entities_identity"),
        Index("ix_entities_tenant_id", "tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    canonical_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class EventDocument(Base):
    __tablename__ = "event_documents"
    __table_args__ = (
        UniqueConstraint("event_id", "document_id", name="uq_event_documents_pair"),
        CheckConstraint(
            "(similarity IS NULL OR similarity BETWEEN 0 AND 1) AND source_weight > 0 AND "
            "(novelty IS NULL OR novelty BETWEEN 0 AND 1)",
            name="ck_event_documents_cluster_values",
        ),
    )

    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), primary_key=True
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("raw_documents.id", ondelete="RESTRICT"), primary_key=True
    )
    weight: Mapped[float] = mapped_column(nullable=False, default=1.0)
    similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    novelty: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    duplicate_of_document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            "raw_documents.id",
            name="fk_event_documents_duplicate_document",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class EventAdmissionRecord(Base):
    __tablename__ = "event_admission_records"
    __table_args__ = (
        UniqueConstraint("document_id", "rule_version", name="uq_event_admission_document_rule"),
        CheckConstraint(
            "decision IN ('drop', 'wait', 'admit', 'attach')",
            name="ck_event_admission_records_decision",
        ),
        CheckConstraint(
            "market_relevance BETWEEN 0 AND 1 AND state_change_strength BETWEEN 0 AND 1 AND "
            "potential_impact BETWEEN 0 AND 1 AND novelty BETWEEN 0 AND 1 AND "
            "source_quality BETWEEN 0 AND 1 AND data_completeness BETWEEN 0 AND 1 AND "
            "decision_value BETWEEN 0 AND 1 AND "
            "(matched_similarity IS NULL OR matched_similarity BETWEEN 0 AND 1)",
            name="ck_event_admission_records_scores",
        ),
        Index("ix_event_admission_records_tenant_created", "tenant_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("raw_documents.id", ondelete="RESTRICT"), nullable=False
    )
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("events.id", ondelete="SET NULL"), nullable=True
    )
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    market_relevance: Mapped[float] = mapped_column(Float, nullable=False)
    state_change_strength: Mapped[float] = mapped_column(Float, nullable=False)
    potential_impact: Mapped[float] = mapped_column(Float, nullable=False)
    novelty: Mapped[float] = mapped_column(Float, nullable=False)
    source_quality: Mapped[float] = mapped_column(Float, nullable=False)
    data_completeness: Mapped[float] = mapped_column(Float, nullable=False)
    decision_value: Mapped[float] = mapped_column(Float, nullable=False)
    matched_similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    rule_version: Mapped[str] = mapped_column(String(64), nullable=False)
    reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class EventMetric(Base):
    __tablename__ = "event_metrics"
    __table_args__ = (
        UniqueConstraint(
            "event_id",
            "metric_at",
            "bucket_minutes",
            "scoring_version",
            name="uq_event_metrics_replay",
        ),
        Index("ix_event_metrics_event_time", "event_id", "metric_at"),
        Index("ix_event_metrics_tenant_time", "tenant_id", "metric_at"),
        CheckConstraint(
            "bucket_minutes > 0 AND msg_count_5m >= 0 AND msg_count_1h >= 0",
            name="ck_event_metrics_counts",
        ),
        CheckConstraint(
            "volume BETWEEN 0 AND 1 AND growth BETWEEN 0 AND 1 AND "
            "(engagement IS NULL OR engagement BETWEEN 0 AND 1) AND "
            "(diversity IS NULL OR diversity BETWEEN 0 AND 1) AND "
            "(authority IS NULL OR authority BETWEEN 0 AND 1) AND "
            "(coverage IS NULL OR coverage BETWEEN 0 AND 1) AND heat BETWEEN 0 AND 1 AND "
            "heat_completeness BETWEEN 0 AND 1 AND "
            "(momentum IS NULL OR momentum BETWEEN -1 AND 1) AND "
            "(raw_score IS NULL OR raw_score BETWEEN 0 AND 1) AND "
            "scoring_completeness BETWEEN 0 AND 1",
            name="ck_event_metrics_scores",
        ),
    )

    calculation_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    metric_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    bucket_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    msg_count_5m: Mapped[int] = mapped_column(Integer, nullable=False)
    msg_count_1h: Mapped[int] = mapped_column(Integer, nullable=False)
    volume: Mapped[float] = mapped_column(Float, nullable=False)
    growth_z: Mapped[float] = mapped_column(Float, nullable=False)
    growth: Mapped[float] = mapped_column(Float, nullable=False)
    engagement: Mapped[float | None] = mapped_column(Float, nullable=True)
    diversity: Mapped[float | None] = mapped_column(Float, nullable=True)
    authority: Mapped[float | None] = mapped_column(Float, nullable=True)
    coverage: Mapped[float | None] = mapped_column(Float, nullable=True)
    heat: Mapped[float] = mapped_column(Float, nullable=False)
    heat_completeness: Mapped[float] = mapped_column(Float, nullable=False)
    momentum: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    scoring_completeness: Mapped[float] = mapped_column(Float, nullable=False)
    scoring_version: Mapped[str] = mapped_column(String(64), nullable=False)
    input_document_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    parameters: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class PlatformBaseline(Base):
    __tablename__ = "platform_baselines"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "platform",
            "metric",
            "effective_at",
            name="uq_platform_baselines_version",
        ),
        Index("ix_platform_baselines_lookup", "tenant_id", "platform", "metric"),
        CheckConstraint("sample_count >= 0", name="ck_platform_baselines_sample_count"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    platform: Mapped[str] = mapped_column(String(64), nullable=False)
    metric: Mapped[str] = mapped_column(String(64), nullable=False)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False)
    empirical_distribution: Mapped[list[float]] = mapped_column(JSON, nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class EvidenceLink(Base):
    __tablename__ = "evidence_links"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "conclusion_type",
            "conclusion_id",
            "document_id",
            name="uq_evidence_links_reference",
        ),
        Index("ix_evidence_links_conclusion", "conclusion_type", "conclusion_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    conclusion_type: Mapped[str] = mapped_column(String(64), nullable=False)
    conclusion_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("raw_documents.id", ondelete="RESTRICT"), nullable=False
    )
    evidence_span: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class OpinionRecord(Base):
    __tablename__ = "opinion_records"
    __table_args__ = (
        Index("ix_opinion_records_event_id", "event_id"),
        Index("ix_opinion_records_document_id", "document_id"),
        CheckConstraint(
            "stance IN ('bullish', 'bearish', 'neutral', 'wait')",
            name="ck_opinion_records_stance",
        ),
        CheckConstraint(
            "claim_type IN ('fact', 'opinion', 'speculation')",
            name="ck_opinion_records_claim_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("raw_documents.id", ondelete="RESTRICT"), nullable=False
    )
    target_entity_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    stance: Mapped[str] = mapped_column(String(16), nullable=False)
    emotion: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    claim_type: Mapped[str] = mapped_column(String(16), nullable=False)
    evidence_span: Mapped[str] = mapped_column(Text, nullable=False)
    model_confidence: Mapped[float] = mapped_column(nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False, default="0.1.0")
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False, default="v1")
    input_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class TransmissionEdge(Base):
    __tablename__ = "transmission_edges"
    __table_args__ = (
        Index("ix_transmission_edges_event_id", "event_id"),
        CheckConstraint(
            "direction IN ('positive', 'negative', 'uncertain')",
            name="ck_transmission_edges_direction",
        ),
        CheckConstraint(
            "horizon IN ('immediate', 'short', 'medium', 'long')",
            name="ck_transmission_edges_horizon",
        ),
        CheckConstraint(
            "status IN ('candidate', 'confirmed', 'rejected')",
            name="ck_transmission_edges_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    from_node_type: Mapped[str] = mapped_column(String(32), nullable=False)
    from_node_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    to_node_type: Mapped[str] = mapped_column(String(32), nullable=False)
    to_node_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    mechanism: Mapped[str] = mapped_column(Text, nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    horizon: Mapped[str] = mapped_column(String(16), nullable=False)
    evidence_ids: Mapped[list[uuid.UUID]] = mapped_column(JSON, default=list, nullable=False)
    knowledge_ids: Mapped[list[uuid.UUID]] = mapped_column(JSON, default=list, nullable=False)
    model_confidence: Mapped[float] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="candidate", nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False, default="0.1.0")
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False, default="v1")
    input_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class EventScoreCalibration(Base):
    __tablename__ = "event_score_calibrations"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "event_id",
            "score_calculation_id",
            "evidence_snapshot_hash",
            "calibration_version",
            name="uq_event_score_calibrations_replay",
        ),
        Index("ix_event_score_calibrations_event_snapshot", "event_id", "snapshot_at"),
        Index("ix_event_score_calibrations_tenant_snapshot", "tenant_id", "snapshot_at"),
        CheckConstraint(
            "calculation_status IN ('complete', 'degraded')",
            name="ck_event_score_calibrations_status",
        ),
        CheckConstraint(
            "raw_score BETWEEN 0 AND 1 AND calibrated_score BETWEEN 0 AND 1 AND "
            "confidence BETWEEN 0 AND 1 AND lower_bound BETWEEN 0 AND 1 AND "
            "upper_bound BETWEEN 0 AND 1 AND lower_bound <= calibrated_score AND "
            "calibrated_score <= upper_bound AND data_completeness BETWEEN 0 AND 1 AND "
            "source_health BETWEEN 0 AND 1 AND "
            "(market_data_completeness IS NULL OR "
            "market_data_completeness BETWEEN 0 AND 1) AND sample_count > 0 AND "
            "monte_carlo_seed >= 0",
            name="ck_event_score_calibrations_values",
        ),
        CheckConstraint(
            "(calculation_status = 'complete' AND json_array_length(degradation_reasons) = 0) OR "
            "(calculation_status = 'degraded' AND json_array_length(degradation_reasons) > 0)",
            name="ck_event_score_calibrations_degradation_state",
        ),
    )

    calculation_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("events.id", ondelete="RESTRICT"), nullable=False
    )
    score_calculation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("event_metrics.calculation_id", ondelete="RESTRICT"), nullable=False
    )
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scoring_version: Mapped[str] = mapped_column(String(64), nullable=False)
    calibration_version: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_score: Mapped[float] = mapped_column(Float, nullable=False)
    calibrated_score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    lower_bound: Mapped[float] = mapped_column(Float, nullable=False)
    upper_bound: Mapped[float] = mapped_column(Float, nullable=False)
    data_completeness: Mapped[float] = mapped_column(Float, nullable=False)
    source_health: Mapped[float] = mapped_column(Float, nullable=False)
    market_data_completeness: Mapped[float | None] = mapped_column(Float, nullable=True)
    input_evidence_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    evidence_snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    monte_carlo_seed: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False)
    parameters: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    calculation_status: Mapped[str] = mapped_column(String(16), nullable=False)
    degradation_reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AnalysisSnapshot(Base):
    __tablename__ = "analysis_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "event_id",
            "snapshot_hash",
            name="uq_analysis_snapshots_event_hash",
        ),
        CheckConstraint(
            "snapshot_kind IN ('report')",
            name="ck_analysis_snapshots_kind",
        ),
        CheckConstraint(
            "evidence_count >= 0 AND source_count >= 0",
            name="ck_analysis_snapshots_counts",
        ),
        Index("ix_analysis_snapshots_event_time", "event_id", "snapshot_at"),
        Index("ix_analysis_snapshots_tenant_time", "tenant_id", "snapshot_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    score_calibration_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("event_score_calibrations.calculation_id", ondelete="SET NULL"),
        nullable=True,
    )
    snapshot_kind: Mapped[str] = mapped_column(String(16), nullable=False, default="report")
    analysis_version: Mapped[str] = mapped_column(String(64), nullable=False)
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    score_status: Mapped[str] = mapped_column(String(16), nullable=False)
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    scoring_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    calibration_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    score_payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    evidence_payload: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    opinion_payload: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    transmission_payload: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    impact_payload: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (
        UniqueConstraint(
            "snapshot_id",
            "format",
            "render_engine",
            name="uq_reports_snapshot_format_engine",
        ),
        CheckConstraint(
            "format IN ('html')",
            name="ck_reports_format",
        ),
        CheckConstraint(
            "status IN ('complete', 'degraded')",
            name="ck_reports_status",
        ),
        Index("ix_reports_event_created", "event_id", "created_at"),
        Index("ix_reports_tenant_created", "tenant_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("analysis_snapshots.id", ondelete="CASCADE"), nullable=False
    )
    format: Mapped[str] = mapped_column(String(16), nullable=False, default="html")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="complete")
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    render_engine: Mapped[str] = mapped_column(String(64), nullable=False)
    brief_prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    body_html: Mapped[str] = mapped_column(Text, nullable=False)
    sections: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    evidence_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    calculation_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    degradation_reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
