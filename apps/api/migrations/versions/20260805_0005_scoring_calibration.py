"""Align Rule 2 decisions and add Rule 3/4 score calibration storage.

Revision ID: 20260805_0005
Revises: 20260804_0004
Create Date: 2026-08-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260805_0005"
down_revision: str | Sequence[str] | None = "20260804_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_events_normalized_scores", "events", type_="check")
    op.alter_column("events", "admission_score", new_column_name="admission_decision_value")
    op.alter_column("events", "confidence", new_column_name="score_confidence")
    op.alter_column("events", "risk_score", new_column_name="raw_score")
    op.add_column("events", sa.Column("calibrated_score", sa.Float(), nullable=True))
    op.add_column("events", sa.Column("score_lower_bound", sa.Float(), nullable=True))
    op.add_column("events", sa.Column("score_upper_bound", sa.Float(), nullable=True))
    op.add_column("events", sa.Column("scoring_version", sa.String(length=64), nullable=True))
    op.add_column(
        "events", sa.Column("calibration_version", sa.String(length=64), nullable=True)
    )
    op.create_check_constraint(
        "ck_events_normalized_scores",
        "events",
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
    )

    op.drop_constraint(
        "ck_event_admission_records_decision",
        "event_admission_records",
        type_="check",
    )
    op.drop_constraint(
        "ck_event_admission_records_scores",
        "event_admission_records",
        type_="check",
    )
    op.alter_column(
        "event_admission_records",
        "eventness",
        new_column_name="state_change_strength",
    )
    op.alter_column(
        "event_admission_records",
        "admission_score",
        new_column_name="decision_value",
    )
    op.add_column(
        "event_admission_records",
        sa.Column(
            "data_completeness",
            sa.Float(),
            server_default=sa.text("1"),
            nullable=False,
        ),
    )
    op.alter_column("event_admission_records", "data_completeness", server_default=None)
    op.create_check_constraint(
        "ck_event_admission_records_decision",
        "event_admission_records",
        "decision IN ('drop', 'wait', 'admit', 'attach')",
    )
    op.create_check_constraint(
        "ck_event_admission_records_scores",
        "event_admission_records",
        "market_relevance BETWEEN 0 AND 1 AND state_change_strength BETWEEN 0 AND 1 AND "
        "potential_impact BETWEEN 0 AND 1 AND novelty BETWEEN 0 AND 1 AND "
        "source_quality BETWEEN 0 AND 1 AND data_completeness BETWEEN 0 AND 1 AND "
        "decision_value BETWEEN 0 AND 1 AND "
        "(matched_similarity IS NULL OR matched_similarity BETWEEN 0 AND 1)",
    )

    op.drop_constraint("ck_event_metrics_scores", "event_metrics", type_="check")
    op.alter_column("event_metrics", "risk", new_column_name="raw_score")
    op.alter_column(
        "event_metrics",
        "risk_completeness",
        new_column_name="scoring_completeness",
    )
    op.alter_column("event_metrics", "rule_version", new_column_name="scoring_version")
    op.create_check_constraint(
        "ck_event_metrics_scores",
        "event_metrics",
        "volume BETWEEN 0 AND 1 AND growth BETWEEN 0 AND 1 AND "
        "(engagement IS NULL OR engagement BETWEEN 0 AND 1) AND "
        "(diversity IS NULL OR diversity BETWEEN 0 AND 1) AND "
        "(authority IS NULL OR authority BETWEEN 0 AND 1) AND "
        "(coverage IS NULL OR coverage BETWEEN 0 AND 1) AND heat BETWEEN 0 AND 1 AND "
        "heat_completeness BETWEEN 0 AND 1 AND "
        "(momentum IS NULL OR momentum BETWEEN -1 AND 1) AND "
        "(raw_score IS NULL OR raw_score BETWEEN 0 AND 1) AND "
        "scoring_completeness BETWEEN 0 AND 1",
    )

    op.create_table(
        "event_score_calibrations",
        sa.Column("calculation_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("score_calculation_id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scoring_version", sa.String(length=64), nullable=False),
        sa.Column("calibration_version", sa.String(length=64), nullable=False),
        sa.Column("raw_score", sa.Float(), nullable=False),
        sa.Column("calibrated_score", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("lower_bound", sa.Float(), nullable=False),
        sa.Column("upper_bound", sa.Float(), nullable=False),
        sa.Column("data_completeness", sa.Float(), nullable=False),
        sa.Column("source_health", sa.Float(), nullable=False),
        sa.Column("market_data_completeness", sa.Float(), nullable=True),
        sa.Column("input_evidence_ids", sa.JSON(), nullable=False),
        sa.Column("evidence_snapshot_hash", sa.String(length=64), nullable=False),
        sa.Column("monte_carlo_seed", sa.BigInteger(), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("calculation_status", sa.String(length=16), nullable=False),
        sa.Column("degradation_reasons", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "calculation_status IN ('complete', 'degraded')",
            name="ck_event_score_calibrations_status",
        ),
        sa.CheckConstraint(
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
        sa.CheckConstraint(
            "(calculation_status = 'complete' AND json_array_length(degradation_reasons) = 0) "
            "OR (calculation_status = 'degraded' AND "
            "json_array_length(degradation_reasons) > 0)",
            name="ck_event_score_calibrations_degradation_state",
        ),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["score_calculation_id"],
            ["event_metrics.calculation_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("calculation_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "event_id",
            "score_calculation_id",
            "evidence_snapshot_hash",
            "calibration_version",
            name="uq_event_score_calibrations_replay",
        ),
    )
    op.create_index(
        "ix_event_score_calibrations_event_snapshot",
        "event_score_calibrations",
        ["event_id", "snapshot_at"],
    )
    op.create_index(
        "ix_event_score_calibrations_tenant_snapshot",
        "event_score_calibrations",
        ["tenant_id", "snapshot_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_event_score_calibrations_tenant_snapshot",
        table_name="event_score_calibrations",
    )
    op.drop_index(
        "ix_event_score_calibrations_event_snapshot",
        table_name="event_score_calibrations",
    )
    op.drop_table("event_score_calibrations")

    op.drop_constraint("ck_event_metrics_scores", "event_metrics", type_="check")
    op.alter_column("event_metrics", "scoring_version", new_column_name="rule_version")
    op.alter_column(
        "event_metrics",
        "scoring_completeness",
        new_column_name="risk_completeness",
    )
    op.alter_column("event_metrics", "raw_score", new_column_name="risk")
    op.create_check_constraint(
        "ck_event_metrics_scores",
        "event_metrics",
        "volume BETWEEN 0 AND 1 AND growth BETWEEN 0 AND 1 AND "
        "(engagement IS NULL OR engagement BETWEEN 0 AND 1) AND "
        "(diversity IS NULL OR diversity BETWEEN 0 AND 1) AND "
        "(authority IS NULL OR authority BETWEEN 0 AND 1) AND "
        "(coverage IS NULL OR coverage BETWEEN 0 AND 1) AND heat BETWEEN 0 AND 1 AND "
        "heat_completeness BETWEEN 0 AND 1 AND "
        "(momentum IS NULL OR momentum BETWEEN -1 AND 1) AND "
        "(risk IS NULL OR risk BETWEEN 0 AND 1) AND risk_completeness BETWEEN 0 AND 1",
    )

    op.drop_constraint(
        "ck_event_admission_records_scores",
        "event_admission_records",
        type_="check",
    )
    op.drop_constraint(
        "ck_event_admission_records_decision",
        "event_admission_records",
        type_="check",
    )
    op.drop_column("event_admission_records", "data_completeness")
    op.alter_column(
        "event_admission_records",
        "decision_value",
        new_column_name="admission_score",
    )
    op.alter_column(
        "event_admission_records",
        "state_change_strength",
        new_column_name="eventness",
    )
    op.create_check_constraint(
        "ck_event_admission_records_decision",
        "event_admission_records",
        "decision IN ('drop', 'attach', 'candidate', 'create')",
    )
    op.create_check_constraint(
        "ck_event_admission_records_scores",
        "event_admission_records",
        "market_relevance BETWEEN 0 AND 1 AND eventness BETWEEN 0 AND 1 AND "
        "potential_impact BETWEEN 0 AND 1 AND novelty BETWEEN 0 AND 1 AND "
        "source_quality BETWEEN 0 AND 1 AND admission_score BETWEEN 0 AND 1 AND "
        "(matched_similarity IS NULL OR matched_similarity BETWEEN 0 AND 1)",
    )

    op.drop_constraint("ck_events_normalized_scores", "events", type_="check")
    op.drop_column("events", "calibration_version")
    op.drop_column("events", "scoring_version")
    op.drop_column("events", "score_upper_bound")
    op.drop_column("events", "score_lower_bound")
    op.drop_column("events", "calibrated_score")
    op.alter_column("events", "raw_score", new_column_name="risk_score")
    op.alter_column("events", "score_confidence", new_column_name="confidence")
    op.alter_column("events", "admission_decision_value", new_column_name="admission_score")
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
