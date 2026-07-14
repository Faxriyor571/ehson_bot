"""role 'user' -> 'treasurer'; add payment_sessions table

Part of the payment-automation pivot: donations are no longer recorded
manually, so donation-taking no longer needs its own role gate -- the
payment provider's confirmation is what protects it, not a role check on
who's allowed to ask for a payment. There is therefore no separate
donor-only tier: the base "approved" role is TREASURER itself (this is a
small, trusted group where every approved member is also trusted to record
expenses), so existing baseline-approved users are promoted directly from
"user" to "treasurer" here rather than through an intermediate "donor" role
that was never deployed.

``payment_sessions`` tracks each payment attempt through a provider (mock
today, Click/Payme later) independently of the ``Donation`` it may produce
-- ``donor_telegram_id`` is only ever non-null while a session is PENDING,
scrubbed by the repository the moment it is confirmed or cancelled, so this
table never becomes a permanent donor-to-donation link.

Revision ID: 7b1d4e9a3c56
Revises: 5e8a3f2c7d19
Create Date: 2026-07-14

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7b1d4e9a3c56"
down_revision: str | None = "5e8a3f2c7d19"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("UPDATE bot_users SET role = 'treasurer' WHERE role = 'user'")

    op.create_table(
        "payment_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider_session_id", sa.String(255), nullable=False, unique=True),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("donor_telegram_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("pending", "paid", "cancelled", name="payment_status", native_enum=False, length=20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "donation_id", sa.Integer(), sa.ForeignKey("donations.id"), nullable=True
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("payment_sessions")
    # Lossy: rows promoted from "user" by this migration and rows that were
    # already legitimately "treasurer" beforehand are no longer
    # distinguishable, so this cannot be inverted precisely -- every
    # treasurer is demoted to "user". Re-promote real treasurers manually
    # afterward if this downgrade is ever actually run.
    op.execute("UPDATE bot_users SET role = 'user' WHERE role = 'treasurer'")
