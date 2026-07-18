"""add bot_users.anonymous_name

A self-chosen (or randomly assigned) nickname used only to personalize
messages sent directly back to that person -- never their real Telegram
name or username, and never read by any Super-Admin-facing screen.
Nullable and backfilled lazily: existing rows get one the next time their
owner interacts with the bot, not via a bulk migration step.

Revision ID: b7c2e9f14a83
Revises: 9d3f7a2b5e14
Create Date: 2026-07-15

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7c2e9f14a83"
down_revision: str | None = "9d3f7a2b5e14"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "bot_users", sa.Column("anonymous_name", sa.String(64), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("bot_users", "anonymous_name")
