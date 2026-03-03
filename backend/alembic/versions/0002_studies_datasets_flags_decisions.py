"""studies, datasets, flags, decisions

Revision ID: 0002
Revises: 0001
Create Date: 2024-01-02 00:00:00.000000

Replaces the generic decisions table from 0001 with the full
study → dataset → flag → decision review workflow schema.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Drop old generic decisions table ──────────────────────────────────
    op.drop_index("ix_decisions_id", table_name="decisions", if_exists=True)
    op.drop_table("decisions")

    # ── studies ───────────────────────────────────────────────────────────
    op.create_table(
        "studies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("sponsor_id", sa.String(100), nullable=False),
        sa.Column("study_type", sa.String(100), nullable=False),
        sa.Column("species", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_studies_id"), "studies", ["id"], unique=False)
    op.create_index(op.f("ix_studies_sponsor_id"), "studies", ["sponsor_id"], unique=False)

    # ── datasets ──────────────────────────────────────────────────────────
    op.create_table(
        "datasets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("study_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("upload_status", sa.String(50), server_default="pending", nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["study_id"], ["studies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_datasets_id"), "datasets", ["id"], unique=False)
    op.create_index(op.f("ix_datasets_study_id"), "datasets", ["study_id"], unique=False)

    # ── flags ─────────────────────────────────────────────────────────────
    op.create_table(
        "flags",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dataset_id", sa.Integer(), nullable=False),
        sa.Column("row_index", sa.Integer(), nullable=False),
        sa.Column("column_name", sa.String(100), nullable=False),
        sa.Column("raw_value", sa.String(500), nullable=False),
        sa.Column("proposed_value", sa.String(500), nullable=True),
        sa.Column("flag_type", sa.String(100), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("biological_reasoning", sa.Text(), nullable=False),
        sa.Column("status", sa.String(50), server_default="pending", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_flags_id"), "flags", ["id"], unique=False)
    op.create_index(op.f("ix_flags_dataset_id"), "flags", ["dataset_id"], unique=False)

    # ── decisions (new) ───────────────────────────────────────────────────
    op.create_table(
        "decisions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("flag_id", sa.Integer(), nullable=False),
        sa.Column("reviewer_name", sa.String(100), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("override_value", sa.String(500), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["flag_id"], ["flags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_decisions_id"), "decisions", ["id"], unique=False)
    op.create_index(op.f("ix_decisions_flag_id"), "decisions", ["flag_id"], unique=False)


def downgrade() -> None:
    # Tear down in reverse FK order
    op.drop_index(op.f("ix_decisions_flag_id"), table_name="decisions")
    op.drop_index(op.f("ix_decisions_id"), table_name="decisions")
    op.drop_table("decisions")

    op.drop_index(op.f("ix_flags_dataset_id"), table_name="flags")
    op.drop_index(op.f("ix_flags_id"), table_name="flags")
    op.drop_table("flags")

    op.drop_index(op.f("ix_datasets_study_id"), table_name="datasets")
    op.drop_index(op.f("ix_datasets_id"), table_name="datasets")
    op.drop_table("datasets")

    op.drop_index(op.f("ix_studies_sponsor_id"), table_name="studies")
    op.drop_index(op.f("ix_studies_id"), table_name="studies")
    op.drop_table("studies")

    # Restore original generic decisions table
    op.create_table(
        "decisions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), server_default="pending", nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("priority", sa.String(20), server_default="medium", nullable=False),
        sa.Column("outcome", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_decisions_id"), "decisions", ["id"], unique=False)
