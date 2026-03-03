"""institutional memory store

Revision ID: 0004
Revises: 0003
Create Date: 2024-01-04 00:00:00.000000

Adds three tables that power the Institutional Memory feature:
  - patterns    : clustered decision rules keyed by sponsor × study_type × flag_type
  - briefings   : cached LLM-generated study briefings
  - audit_exports: immutable 21 CFR Part 11-compatible export records
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── patterns ──────────────────────────────────────────────────────────
    op.create_table(
        "patterns",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sponsor_id", sa.String(100), nullable=False),
        sa.Column("study_type", sa.String(100), nullable=False),
        sa.Column("flag_type", sa.String(100), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("dominant_action", sa.String(50), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("action_distribution", sa.JSON(), nullable=True),
        sa.Column("common_override_values", sa.JSON(), nullable=True),
        sa.Column("rule_text", sa.Text(), nullable=False),
        sa.Column("last_rebuilt_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sponsor_id", "study_type", "flag_type", name="uq_pattern_key"),
    )
    op.create_index("ix_patterns_sponsor_id", "patterns", ["sponsor_id"])
    op.create_index("ix_patterns_study_type",  "patterns", ["study_type"])
    op.create_index("ix_patterns_flag_type",   "patterns", ["flag_type"])

    # ── briefings ─────────────────────────────────────────────────────────
    op.create_table(
        "briefings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("study_id", sa.Integer(), nullable=False),
        sa.Column("briefing_text", sa.Text(), nullable=False),
        sa.Column("model_used", sa.String(50), nullable=False, server_default="template"),
        sa.Column("pattern_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("generated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["study_id"], ["studies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_briefings_study_id", "briefings", ["study_id"])

    # ── audit_exports ─────────────────────────────────────────────────────
    op.create_table(
        "audit_exports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("study_id", sa.Integer(), nullable=False),
        sa.Column("export_ref", sa.String(36), nullable=False),
        sa.Column("exported_by", sa.String(100), nullable=False),
        sa.Column("exported_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("record_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("export_format", sa.String(10), nullable=False, server_default="json"),
        sa.Column("system_version", sa.String(100), nullable=False, server_default="decision-tracker/1.0"),
        sa.Column("reason", sa.Text(), nullable=False, server_default="routine_audit"),
        sa.ForeignKeyConstraint(["study_id"], ["studies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("export_ref", name="uq_export_ref"),
    )
    op.create_index("ix_audit_exports_study_id",   "audit_exports", ["study_id"])
    op.create_index("ix_audit_exports_export_ref",  "audit_exports", ["export_ref"])


def downgrade() -> None:
    op.drop_table("audit_exports")
    op.drop_table("briefings")
    op.drop_table("patterns")
