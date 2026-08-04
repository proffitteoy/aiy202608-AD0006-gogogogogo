import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from risktrace.db.base import Base


class SourceType(str, enum.Enum):
    FACT = "fact"
    NEWS = "news"
    SOCIAL = "social"
    MARKET = "market"


class EventStatus(str, enum.Enum):
    CANDIDATE = "candidate"
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
            "status IN ('candidate', 'active', 'analyzed', 'alerted', 'cooling', "
            "'closed', 'archived')",
            name="ck_events_status",
        ),
        Index("ix_events_tenant_status", "tenant_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default=EventStatus.CANDIDATE.value)
    first_published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
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
    )

    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), primary_key=True
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("raw_documents.id", ondelete="RESTRICT"), primary_key=True
    )
    weight: Mapped[float] = mapped_column(nullable=False, default=1.0)
    added_at: Mapped[datetime] = mapped_column(
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
