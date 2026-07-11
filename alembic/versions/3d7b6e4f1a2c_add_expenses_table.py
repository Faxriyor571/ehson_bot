"""add expenses table

Revision ID: 3d7b6e4f1a2c
Revises: 8f3c1a9d2b4e
Create Date: 2026-07-11

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3d7b6e4f1a2c"
down_revision: str | None = "8f3c1a9d2b4e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "expenses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("recorded_by_id", sa.BigInteger(), nullable=False),
        sa.Column("receipt_file_id", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("expenses")
