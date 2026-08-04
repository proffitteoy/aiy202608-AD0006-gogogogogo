"""Create the first traceability data tables.

Revision ID: 20260804_0001
Revises: None
Create Date: 2026-08-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260804_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "raw_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column("source_type", sa.String(length=16), nullable=False),
        sa.Column("platform", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=255), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("author_id_hash", sa.String(length=128), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("engagement", sa.JSON(), nullable=False),
        sa.Column("is_original", sa.Boolean(), nullable=True),
        sa.Column("collection_method", sa.String(length=128), nullable=False),
        sa.Column("license_scope", sa.String(length=128), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("raw_payload_ref", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "source_type IN ('fact', 'news', 'social', 'market')",
            name="ck_raw_documents_source_type",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "platform", "source_id", name="uq_raw_documents_platform_source"
        ),
    )
    op.create_index("ix_raw_documents_published_at", "raw_documents", ["published_at"])
    op.create_index("ix_raw_documents_tenant_id", "raw_documents", ["tenant_id"])

    op.create_table(
        "events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("first_published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('candidate', 'active', 'analyzed', 'alerted', 'cooling', "
            "'closed', 'archived')",
            name="ck_events_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_events_tenant_status", "events", ["tenant_id", "status"])

    op.create_table(
        "entities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("canonical_code", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "entity_type", "name", name="uq_entities_identity"
        ),
    )
    op.create_index("ix_entities_tenant_id", "entities", ["tenant_id"])

    op.create_table(
        "event_documents",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column(
            "added_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["document_id"], ["raw_documents.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("event_id", "document_id"),
        sa.UniqueConstraint("event_id", "document_id", name="uq_event_documents_pair"),
    )

    op.create_table(
        "evidence_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("conclusion_type", sa.String(length=64), nullable=False),
        sa.Column("conclusion_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_span", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["document_id"], ["raw_documents.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "conclusion_type",
            "conclusion_id",
            "document_id",
            name="uq_evidence_links_reference",
        ),
    )
    op.create_index(
        "ix_evidence_links_conclusion",
        "evidence_links",
        ["conclusion_type", "conclusion_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_evidence_links_conclusion", table_name="evidence_links")
    op.drop_table("evidence_links")
    op.drop_table("event_documents")
    op.drop_index("ix_entities_tenant_id", table_name="entities")
    op.drop_table("entities")
    op.drop_index("ix_events_tenant_status", table_name="events")
    op.drop_table("events")
    op.drop_index("ix_raw_documents_tenant_id", table_name="raw_documents")
    op.drop_index("ix_raw_documents_published_at", table_name="raw_documents")
    op.drop_table("raw_documents")
