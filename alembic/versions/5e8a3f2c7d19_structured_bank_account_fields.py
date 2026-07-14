"""bank_account_settings: structured fields instead of one text blob

Replaces the single free-text column with card_number/card_holder/bank_name
so the display screen can format each consistently (e.g. tap-to-copy on the
card number) instead of echoing back whatever an admin once typed.

The one existing row (a single unstructured text blob, e.g. "Karta: ...
egasi: ...") does not cleanly split into three fields, so it is dropped —
this is admin configuration, not donor transaction data, and the Super
Admin just re-enters it once via the new guided flow.

Revision ID: 5e8a3f2c7d19
Revises: 9c4f2a1e6b7d
Create Date: 2026-07-14

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5e8a3f2c7d19"
down_revision: str | None = "9c4f2a1e6b7d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DELETE FROM bank_account_settings")
    op.drop_column("bank_account_settings", "text")
    op.add_column(
        "bank_account_settings", sa.Column("card_number", sa.String(64), nullable=False)
    )
    op.add_column(
        "bank_account_settings", sa.Column("card_holder", sa.String(255), nullable=False)
    )
    op.add_column(
        "bank_account_settings", sa.Column("bank_name", sa.String(255), nullable=False)
    )


def downgrade() -> None:
    op.execute("DELETE FROM bank_account_settings")
    op.drop_column("bank_account_settings", "bank_name")
    op.drop_column("bank_account_settings", "card_holder")
    op.drop_column("bank_account_settings", "card_number")
    op.add_column("bank_account_settings", sa.Column("text", sa.String(1000), nullable=False))
