import enum
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
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
        UniqueConstraint("platform", "source_id", name="uq_raw_documents_platform_source"),
        CheckConstraint(
            "source_type IN ('fact', 'news', 'social', 'market')",
            name="ck_raw_documents_source_type",
        ),
        Index("ix_raw_documents_published_at", "published_at"),
        Index("ix_raw_documents_tenant_id", "tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)
    platform: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
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
            "(admission_score IS NULL OR admission_score BETWEEN 0 AND 1) AND "
            "(confidence IS NULL OR confidence BETWEEN 0 AND 1) AND "
            "(heat_score IS NULL OR heat_score BETWEEN 0 AND 1) AND "
            "(risk_score IS NULL OR risk_score BETWEEN 0 AND 1) AND "
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
    admission_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    heat_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    momentum: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
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
            "decision IN ('drop', 'attach', 'candidate', 'create')",
            name="ck_event_admission_records_decision",
        ),
        CheckConstraint(
            "market_relevance BETWEEN 0 AND 1 AND eventness BETWEEN 0 AND 1 AND "
            "potential_impact BETWEEN 0 AND 1 AND novelty BETWEEN 0 AND 1 AND "
            "source_quality BETWEEN 0 AND 1 AND admission_score BETWEEN 0 AND 1 AND "
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
    eventness: Mapped[float] = mapped_column(Float, nullable=False)
    potential_impact: Mapped[float] = mapped_column(Float, nullable=False)
    novelty: Mapped[float] = mapped_column(Float, nullable=False)
    source_quality: Mapped[float] = mapped_column(Float, nullable=False)
    admission_score: Mapped[float] = mapped_column(Float, nullable=False)
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
            "rule_version",
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
            "(risk IS NULL OR risk BETWEEN 0 AND 1) AND risk_completeness BETWEEN 0 AND 1",
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
    risk: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_completeness: Mapped[float] = mapped_column(Float, nullable=False)
    rule_version: Mapped[str] = mapped_column(String(64), nullable=False)
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
