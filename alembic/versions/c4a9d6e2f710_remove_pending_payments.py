"""remove pending_payments; add donations.receipt_file_id

Only a handful of trusted donors use this bot, so the manual Super-Admin
review step is no longer needed: the donor's own "✅ Pulni o'tkazdim" press
is now the single, final confirmation, and the ``Donation`` is created
immediately from that action. ``pending_payments`` held no data worth
migrating forward (it only ever existed for the review step being removed
here), so it is dropped outright. ``donations.receipt_file_id`` replaces
what ``pending_payments.receipt_file_id`` used to carry, since a donation
can now be recorded with an optional transfer screenshot attached directly.

Revision ID: c4a9d6e2f710
Revises: b7c2e9f14a83
Create Date: 2026-07-16

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4a9d6e2f710"
down_revision: str | None = "b7c2e9f14a83"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_table("pending_payments")
    op.add_column(
        "donations", sa.Column("receipt_file_id", sa.String(255), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("donations", "receipt_file_id")

    op.create_table(
        "pending_payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("reference_code", sa.String(32), nullable=False, unique=True),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("donor_telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("receipt_file_id", sa.String(255), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "confirmed",
                "rejected",
                name="pending_payment_status",
                native_enum=False,
                length=20,
            ),
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
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
    )
