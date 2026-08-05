"""Add analysis snapshots and frozen report persistence.

Revision ID: 20260805_0007
Revises: 20260805_0006
Create Date: 2026-08-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260805_0007"
down_revision: str | Sequence[str] | None = "20260805_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analysis_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("score_calibration_id", sa.Uuid(), nullable=True),
        sa.Column("snapshot_kind", sa.String(length=16), nullable=False),
        sa.Column("analysis_version", sa.String(length=64), nullable=False),
        sa.Column("snapshot_hash", sa.String(length=64), nullable=False),
        sa.Column("evidence_snapshot_hash", sa.String(length=64), nullable=False),
        sa.Column("score_status", sa.String(length=16), nullable=False),
        sa.Column("evidence_count", sa.Integer(), nullable=False),
        sa.Column("source_count", sa.Integer(), nullable=False),
        sa.Column("scoring_version", sa.String(length=64), nullable=True),
        sa.Column("calibration_version", sa.String(length=64), nullable=True),
        sa.Column("event_payload", sa.JSON(), nullable=False),
        sa.Column("score_payload", sa.JSON(), nullable=False),
        sa.Column("evidence_payload", sa.JSON(), nullable=False),
        sa.Column("opinion_payload", sa.JSON(), nullable=False),
        sa.Column("transmission_payload", sa.JSON(), nullable=False),
        sa.Column("impact_payload", sa.JSON(), nullable=False),
        sa.Column("snapshot_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "snapshot_kind IN ('report')",
            name="ck_analysis_snapshots_kind",
        ),
        sa.CheckConstraint(
            "evidence_count >= 0 AND source_count >= 0",
            name="ck_analysis_snapshots_counts",
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["events.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["score_calibration_id"],
            ["event_score_calibrations.calculation_id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "event_id",
            "snapshot_hash",
            name="uq_analysis_snapshots_event_hash",
        ),
    )
    op.create_index(
        "ix_analysis_snapshots_event_time",
        "analysis_snapshots",
        ["event_id", "snapshot_at"],
    )
    op.create_index(
        "ix_analysis_snapshots_tenant_time",
        "analysis_snapshots",
        ["tenant_id", "snapshot_at"],
    )

    op.create_table(
        "reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("format", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("render_engine", sa.String(length=64), nullable=False),
        sa.Column("brief_prompt_version", sa.String(length=64), nullable=False),
        sa.Column("body_html", sa.Text(), nullable=False),
        sa.Column("sections", sa.JSON(), nullable=False),
        sa.Column("evidence_ids", sa.JSON(), nullable=False),
        sa.Column("calculation_ids", sa.JSON(), nullable=False),
        sa.Column("degradation_reasons", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "format IN ('html')",
            name="ck_reports_format",
        ),
        sa.CheckConstraint(
            "status IN ('complete', 'degraded')",
            name="ck_reports_status",
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["events.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["analysis_snapshots.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "snapshot_id",
            "format",
            "render_engine",
            name="uq_reports_snapshot_format_engine",
        ),
    )
    op.create_index(
        "ix_reports_event_created",
        "reports",
        ["event_id", "created_at"],
    )
    op.create_index(
        "ix_reports_tenant_created",
        "reports",
        ["tenant_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_reports_tenant_created", table_name="reports")
    op.drop_index("ix_reports_event_created", table_name="reports")
    op.drop_table("reports")

    op.drop_index(
        "ix_analysis_snapshots_tenant_time",
        table_name="analysis_snapshots",
    )
    op.drop_index(
        "ix_analysis_snapshots_event_time",
        table_name="analysis_snapshots",
    )
    op.drop_table("analysis_snapshots")
