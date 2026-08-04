"""Add opinion_records and transmission_edges tables.

Revision ID: 20260804_0004
Revises: 20260804_0003
Create Date: 2026-08-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260804_0004"
down_revision: str | Sequence[str] | None = "20260804_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "opinion_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("target_entity_id", sa.Uuid(), nullable=True),
        sa.Column("stance", sa.String(length=16), nullable=False),
        sa.Column("emotion", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("claim_type", sa.String(length=16), nullable=False),
        sa.Column("evidence_span", sa.Text(), nullable=False),
        sa.Column("model_confidence", sa.Float(), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=False, server_default="0.1.0"),
        sa.Column("prompt_version", sa.String(length=64), nullable=False, server_default="v1"),
        sa.Column("input_hash", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "stance IN ('bullish', 'bearish', 'neutral', 'wait')",
            name="ck_opinion_records_stance",
        ),
        sa.CheckConstraint(
            "claim_type IN ('fact', 'opinion', 'speculation')",
            name="ck_opinion_records_claim_type",
        ),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["raw_documents.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_opinion_records_event_id", "opinion_records", ["event_id"])
    op.create_index("ix_opinion_records_document_id", "opinion_records", ["document_id"])

    op.create_table(
        "transmission_edges",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("from_node_type", sa.String(length=32), nullable=False),
        sa.Column("from_node_id", sa.Uuid(), nullable=False),
        sa.Column("to_node_type", sa.String(length=32), nullable=False),
        sa.Column("to_node_id", sa.Uuid(), nullable=False),
        sa.Column("mechanism", sa.Text(), nullable=False),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("horizon", sa.String(length=16), nullable=False),
        sa.Column("evidence_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("knowledge_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("model_confidence", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="candidate"),
        sa.Column("model_version", sa.String(length=64), nullable=False, server_default="0.1.0"),
        sa.Column("prompt_version", sa.String(length=64), nullable=False, server_default="v1"),
        sa.Column("input_hash", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "direction IN ('positive', 'negative', 'uncertain')",
            name="ck_transmission_edges_direction",
        ),
        sa.CheckConstraint(
            "horizon IN ('immediate', 'short', 'medium', 'long')",
            name="ck_transmission_edges_horizon",
        ),
        sa.CheckConstraint(
            "status IN ('candidate', 'confirmed', 'rejected')",
            name="ck_transmission_edges_status",
        ),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transmission_edges_event_id", "transmission_edges", ["event_id"])


def downgrade() -> None:
    op.drop_index("ix_transmission_edges_event_id", table_name="transmission_edges")
    op.drop_table("transmission_edges")
    op.drop_index("ix_opinion_records_document_id", table_name="opinion_records")
    op.drop_index("ix_opinion_records_event_id", table_name="opinion_records")
    op.drop_table("opinion_records")
