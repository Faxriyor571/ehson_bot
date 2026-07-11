"""bot_users.role defaults to 'pending', not 'user'

New registrations must start with no access until a Super Admin approves
them. Existing rows are untouched — this only changes the default applied
to future inserts that don't specify a role explicitly.

Revision ID: 9c4f2a1e6b7d
Revises: 6a2e9c5d8f01
Create Date: 2026-07-11

"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9c4f2a1e6b7d"
down_revision: str | None = "6a2e9c5d8f01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("bot_users", "role", server_default="pending")


def downgrade() -> None:
    op.alter_column("bot_users", "role", server_default="user")
