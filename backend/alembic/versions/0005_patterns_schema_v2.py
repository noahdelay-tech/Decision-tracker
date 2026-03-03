"""patterns schema v2

Revision ID: 0005
Revises: 0004
Create Date: 2024-01-05 00:00:00.000000

Replaces the v1 patterns table (keyed by sponsor×study_type×flag_type) with a
more granular v2 schema keyed by sponsor×flag_type×column_name.

New columns:
  column_name        – adds column granularity to the grouping key
  occurrence_count   – replaces sample_count
  confirmation_rate  – replaces confidence (proportion of confirmed decisions)
  common_override    – single most-frequent override value (replaces JSON list)
  example_reasonings – JSON list of up to 3 sample biological_reasoning strings
  last_updated       – replaces last_rebuilt_at

Removed columns: study_type, dominant_action, action_distribution,
                 common_override_values, rule_text
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("patterns")

    op.create_table(
        "patterns",
        sa.Column("id",                sa.Integer(),     nullable=False),
        sa.Column("sponsor_id",        sa.String(100),   nullable=False),
        sa.Column("flag_type",         sa.String(100),   nullable=False),
        sa.Column("column_name",       sa.String(100),   nullable=False),
        sa.Column("occurrence_count",  sa.Integer(),     nullable=False, server_default="0"),
        sa.Column("confirmation_rate", sa.Float(),       nullable=False, server_default="0.0"),
        sa.Column("common_override",   sa.Text(),        nullable=True),
        sa.Column("example_reasonings", sa.JSON(),       nullable=True),
        sa.Column("last_updated",      sa.DateTime(),    server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sponsor_id", "flag_type", "column_name", name="uq_pattern_key"),
    )
    op.create_index("ix_patterns_sponsor_id",  "patterns", ["sponsor_id"])
    op.create_index("ix_patterns_flag_type",   "patterns", ["flag_type"])
    op.create_index("ix_patterns_column_name", "patterns", ["column_name"])


def downgrade() -> None:
    op.drop_table("patterns")

    op.create_table(
        "patterns",
        sa.Column("id",                     sa.Integer(),  nullable=False),
        sa.Column("sponsor_id",             sa.String(100), nullable=False),
        sa.Column("study_type",             sa.String(100), nullable=False),
        sa.Column("flag_type",              sa.String(100), nullable=False),
        sa.Column("sample_count",           sa.Integer(),  nullable=False, server_default="0"),
        sa.Column("dominant_action",        sa.String(50), nullable=False),
        sa.Column("confidence",             sa.Float(),    nullable=False, server_default="0.0"),
        sa.Column("action_distribution",    sa.JSON(),     nullable=True),
        sa.Column("common_override_values", sa.JSON(),     nullable=True),
        sa.Column("rule_text",              sa.Text(),     nullable=False),
        sa.Column("last_rebuilt_at",        sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sponsor_id", "study_type", "flag_type", name="uq_pattern_key"),
    )
