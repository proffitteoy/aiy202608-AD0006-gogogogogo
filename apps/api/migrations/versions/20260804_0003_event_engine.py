"""Add traceable event admission, clustering, and metric persistence.

Revision ID: 20260804_0003
Revises: 20260804_0002
Create Date: 2026-08-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "20260804_0003"
down_revision: str | Sequence[str] | None = "20260804_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_events_status", "events", type_="check")
    op.add_column("events", sa.Column("summary", sa.Text(), nullable=True))
    op.add_column("events", sa.Column("event_type", sa.String(length=128), nullable=True))
    op.add_column("events", sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("events", sa.Column("centroid_embedding", Vector(), nullable=True))
    op.add_column(
        "events", sa.Column("centroid_weight", sa.Float(), server_default="0", nullable=False)
    )
    op.add_column("events", sa.Column("embedding_model", sa.String(length=255), nullable=True))
    op.add_column("events", sa.Column("admission_score", sa.Float(), nullable=True))
    op.add_column("events", sa.Column("confidence", sa.Float(), nullable=True))
    op.add_column("events", sa.Column("heat_score", sa.Float(), nullable=True))
    op.add_column("events", sa.Column("momentum", sa.Float(), nullable=True))
    op.add_column("events", sa.Column("risk_score", sa.Float(), nullable=True))
    op.add_column(
        "events", sa.Column("evidence_count", sa.Integer(), server_default="0", nullable=False)
    )
    op.execute("UPDATE events SET last_seen_at = first_published_at WHERE last_seen_at IS NULL")
    op.alter_column("events", "last_seen_at", nullable=False)
    op.create_check_constraint(
        "ck_events_status",
        "events",
        "status IN ('candidate', 'confirmed', 'active', 'analyzed', 'alerted', "
        "'cooling', 'closed', 'archived')",
    )
    op.create_check_constraint(
        "ck_events_normalized_scores",
        "events",
        "(admission_score IS NULL OR admission_score BETWEEN 0 AND 1) AND "
        "(confidence IS NULL OR confidence BETWEEN 0 AND 1) AND "
        "(heat_score IS NULL OR heat_score BETWEEN 0 AND 1) AND "
        "(risk_score IS NULL OR risk_score BETWEEN 0 AND 1) AND "
        "(momentum IS NULL OR momentum BETWEEN -1 AND 1) AND "
        "centroid_weight >= 0 AND evidence_count >= 0",
    )

    op.add_column("event_documents", sa.Column("similarity", sa.Float(), nullable=True))
    op.add_column(
        "event_documents",
        sa.Column("source_weight", sa.Float(), server_default="1", nullable=False),
    )
    op.add_column("event_documents", sa.Column("novelty", sa.Float(), nullable=True))
    op.add_column(
        "event_documents",
        sa.Column("is_duplicate", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "event_documents", sa.Column("duplicate_of_document_id", sa.Uuid(), nullable=True)
    )
    op.create_foreign_key(
        "fk_event_documents_duplicate_document",
        "event_documents",
        "raw_documents",
        ["duplicate_of_document_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_event_documents_cluster_values",
        "event_documents",
        "(similarity IS NULL OR similarity BETWEEN 0 AND 1) AND source_weight > 0 AND "
        "(novelty IS NULL OR novelty BETWEEN 0 AND 1)",
    )

    op.create_table(
        "event_admission_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=True),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("market_relevance", sa.Float(), nullable=False),
        sa.Column("eventness", sa.Float(), nullable=False),
        sa.Column("potential_impact", sa.Float(), nullable=False),
        sa.Column("novelty", sa.Float(), nullable=False),
        sa.Column("source_quality", sa.Float(), nullable=False),
        sa.Column("admission_score", sa.Float(), nullable=False),
        sa.Column("matched_similarity", sa.Float(), nullable=True),
        sa.Column("rule_version", sa.String(length=64), nullable=False),
        sa.Column("reasons", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "decision IN ('drop', 'attach', 'candidate', 'create')",
            name="ck_event_admission_records_decision",
        ),
        sa.CheckConstraint(
            "market_relevance BETWEEN 0 AND 1 AND eventness BETWEEN 0 AND 1 AND "
            "potential_impact BETWEEN 0 AND 1 AND novelty BETWEEN 0 AND 1 AND "
            "source_quality BETWEEN 0 AND 1 AND admission_score BETWEEN 0 AND 1 AND "
            "(matched_similarity IS NULL OR matched_similarity BETWEEN 0 AND 1)",
            name="ck_event_admission_records_scores",
        ),
        sa.ForeignKeyConstraint(["document_id"], ["raw_documents.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "rule_version", name="uq_event_admission_document_rule"),
    )
    op.create_index(
        "ix_event_admission_records_tenant_created",
        "event_admission_records",
        ["tenant_id", "created_at"],
    )

    op.create_table(
        "event_metrics",
        sa.Column("calculation_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("metric_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("bucket_minutes", sa.Integer(), nullable=False),
        sa.Column("msg_count_5m", sa.Integer(), nullable=False),
        sa.Column("msg_count_1h", sa.Integer(), nullable=False),
        sa.Column("volume", sa.Float(), nullable=False),
        sa.Column("growth_z", sa.Float(), nullable=False),
        sa.Column("growth", sa.Float(), nullable=False),
        sa.Column("engagement", sa.Float(), nullable=True),
        sa.Column("diversity", sa.Float(), nullable=True),
        sa.Column("authority", sa.Float(), nullable=True),
        sa.Column("coverage", sa.Float(), nullable=True),
        sa.Column("heat", sa.Float(), nullable=False),
        sa.Column("heat_completeness", sa.Float(), nullable=False),
        sa.Column("momentum", sa.Float(), nullable=True),
        sa.Column("risk", sa.Float(), nullable=True),
        sa.Column("risk_completeness", sa.Float(), nullable=False),
        sa.Column("rule_version", sa.String(length=64), nullable=False),
        sa.Column("input_document_ids", sa.JSON(), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "bucket_minutes > 0 AND msg_count_5m >= 0 AND msg_count_1h >= 0",
            name="ck_event_metrics_counts",
        ),
        sa.CheckConstraint(
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
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("calculation_id"),
        sa.UniqueConstraint(
            "event_id",
            "metric_at",
            "bucket_minutes",
            "rule_version",
            name="uq_event_metrics_replay",
        ),
    )
    op.create_index("ix_event_metrics_event_time", "event_metrics", ["event_id", "metric_at"])
    op.create_index("ix_event_metrics_tenant_time", "event_metrics", ["tenant_id", "metric_at"])

    op.create_table(
        "platform_baselines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("platform", sa.String(length=64), nullable=False),
        sa.Column("metric", sa.String(length=64), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.Column("empirical_distribution", sa.JSON(), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("sample_count >= 0", name="ck_platform_baselines_sample_count"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "platform",
            "metric",
            "effective_at",
            name="uq_platform_baselines_version",
        ),
    )
    op.create_index(
        "ix_platform_baselines_lookup",
        "platform_baselines",
        ["tenant_id", "platform", "metric"],
    )


def downgrade() -> None:
    op.drop_index("ix_platform_baselines_lookup", table_name="platform_baselines")
    op.drop_table("platform_baselines")
    op.drop_index("ix_event_metrics_tenant_time", table_name="event_metrics")
    op.drop_index("ix_event_metrics_event_time", table_name="event_metrics")
    op.drop_table("event_metrics")
    op.drop_index("ix_event_admission_records_tenant_created", table_name="event_admission_records")
    op.drop_table("event_admission_records")

    op.drop_constraint("ck_event_documents_cluster_values", "event_documents", type_="check")
    op.drop_constraint(
        "fk_event_documents_duplicate_document", "event_documents", type_="foreignkey"
    )
    op.drop_column("event_documents", "duplicate_of_document_id")
    op.drop_column("event_documents", "is_duplicate")
    op.drop_column("event_documents", "novelty")
    op.drop_column("event_documents", "source_weight")
    op.drop_column("event_documents", "similarity")

    op.drop_constraint("ck_events_normalized_scores", "events", type_="check")
    op.drop_constraint("ck_events_status", "events", type_="check")
    op.create_check_constraint(
        "ck_events_status",
        "events",
        "status IN ('candidate', 'active', 'analyzed', 'alerted', 'cooling', 'closed', 'archived')",
    )
    for column in (
        "evidence_count",
        "risk_score",
        "momentum",
        "heat_score",
        "confidence",
        "admission_score",
        "embedding_model",
        "centroid_weight",
        "centroid_embedding",
        "last_seen_at",
        "event_type",
        "summary",
    ):
        op.drop_column("events", column)
