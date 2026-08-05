"""Add tenant-scoped unified source ingestion persistence.

Revision ID: 20260805_0006
Revises: 20260805_0005
Create Date: 2026-08-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260805_0006"
down_revision: str | Sequence[str] | None = "20260805_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "raw_documents",
        sa.Column("source_level", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "raw_documents",
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "raw_documents",
        sa.Column("replay_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "raw_documents",
        sa.Column("source_metadata", sa.JSON(), nullable=True),
    )
    op.execute(
        """
        UPDATE raw_documents
        SET source_level = CASE source_type
            WHEN 'fact' THEN 'official'
            WHEN 'news' THEN 'professional_media'
            WHEN 'social' THEN 'public_discussion'
            WHEN 'market' THEN 'market_data'
        END,
        received_at = collected_at,
        source_metadata = '{}'::json
        """
    )
    op.alter_column(
        "raw_documents",
        "source_level",
        existing_type=sa.String(length=32),
        nullable=False,
    )
    op.alter_column(
        "raw_documents",
        "received_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
    )
    op.alter_column(
        "raw_documents",
        "source_metadata",
        existing_type=sa.JSON(),
        nullable=False,
    )
    op.create_check_constraint(
        "ck_raw_documents_source_level",
        "raw_documents",
        "source_level IN ('official', 'professional_media', "
        "'public_discussion', 'market_data')",
    )
    op.drop_constraint(
        "uq_raw_documents_platform_source",
        "raw_documents",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_raw_documents_tenant_platform_source",
        "raw_documents",
        ["tenant_id", "platform", "source_id"],
    )

    op.create_table(
        "ingestion_receipts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("stream", sa.String(length=128), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("replay_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("processing_status", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "outcome IN ('inserted', 'duplicate')",
            name="ck_ingestion_receipts_outcome",
        ),
        sa.CheckConstraint(
            "processing_status IN ('pending_enrichment')",
            name="ck_ingestion_receipts_processing_status",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["raw_documents.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ingestion_receipts_document_received",
        "ingestion_receipts",
        ["document_id", "received_at"],
    )
    op.create_index(
        "ix_ingestion_receipts_tenant_received",
        "ingestion_receipts",
        ["tenant_id", "received_at"],
    )

    op.create_table(
        "source_checkpoints",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("stream", sa.String(length=128), nullable=False),
        sa.Column("cursor", sa.Text(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "provider",
            "stream",
            name="uq_source_checkpoints_stream",
        ),
    )
    op.create_index(
        "ix_source_checkpoints_tenant_provider",
        "source_checkpoints",
        ["tenant_id", "provider"],
    )

    op.create_table(
        "source_health",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("stream", sa.String(length=128), nullable=False),
        sa.Column("source_type", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('healthy', 'degraded', 'unavailable')",
            name="ck_source_health_status",
        ),
        sa.CheckConstraint(
            "source_type IN ('fact', 'news', 'social', 'market')",
            name="ck_source_health_source_type",
        ),
        sa.CheckConstraint(
            "consecutive_failures >= 0",
            name="ck_source_health_failure_count",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "provider",
            "stream",
            name="uq_source_health_stream",
        ),
    )
    op.create_index(
        "ix_source_health_tenant_status",
        "source_health",
        ["tenant_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_source_health_tenant_status", table_name="source_health")
    op.drop_table("source_health")
    op.drop_index(
        "ix_source_checkpoints_tenant_provider",
        table_name="source_checkpoints",
    )
    op.drop_table("source_checkpoints")
    op.drop_index(
        "ix_ingestion_receipts_tenant_received",
        table_name="ingestion_receipts",
    )
    op.drop_index(
        "ix_ingestion_receipts_document_received",
        table_name="ingestion_receipts",
    )
    op.drop_table("ingestion_receipts")

    op.drop_constraint(
        "uq_raw_documents_tenant_platform_source",
        "raw_documents",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_raw_documents_platform_source",
        "raw_documents",
        ["platform", "source_id"],
    )
    op.drop_constraint(
        "ck_raw_documents_source_level",
        "raw_documents",
        type_="check",
    )
    op.drop_column("raw_documents", "source_metadata")
    op.drop_column("raw_documents", "replay_at")
    op.drop_column("raw_documents", "received_at")
    op.drop_column("raw_documents", "source_level")
