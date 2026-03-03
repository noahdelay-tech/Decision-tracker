"""dataset ingest columns

Revision ID: 0003
Revises: 0002
Create Date: 2024-01-03 00:00:00.000000

Adds column_mappings, unmapped_columns, and preview_rows JSON columns
to the datasets table to support the /ingest endpoint.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite ALTER TABLE only supports ADD COLUMN
    op.add_column("datasets", sa.Column("column_mappings", sa.JSON(), nullable=True))
    op.add_column("datasets", sa.Column("unmapped_columns", sa.JSON(), nullable=True))
    op.add_column("datasets", sa.Column("preview_rows", sa.JSON(), nullable=True))


def downgrade() -> None:
    # SQLite does not support DROP COLUMN natively; recreate the table
    with op.batch_alter_table("datasets") as batch_op:
        batch_op.drop_column("preview_rows")
        batch_op.drop_column("unmapped_columns")
        batch_op.drop_column("column_mappings")
