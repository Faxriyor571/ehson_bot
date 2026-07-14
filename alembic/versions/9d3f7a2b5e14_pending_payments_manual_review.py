"""replace payment_sessions with pending_payments (manual anonymous review)

Part of the redesign away from an automated ``PaymentProvider`` (there was
never a real gateway behind it) to manual Super Admin review of the bank
account. ``payment_sessions`` existed for gateway-webhook-style automatic
confirmation, which no longer applies -- it never accumulated meaningful
data in production (the mock provider self-confirmed within ~10 seconds of
creation, so nothing was ever left genuinely pending), so it is dropped
outright rather than migrated in place. ``pending_payments`` adds
``reference_code`` (the only donor-facing identifier a Super Admin ever
sees) and ``receipt_file_id`` (an optional payment screenshot).

Revision ID: 9d3f7a2b5e14
Revises: 7b1d4e9a3c56
Create Date: 2026-07-14

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9d3f7a2b5e14"
down_revision: str | None = "7b1d4e9a3c56"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_table("payment_sessions")

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


def downgrade() -> None:
    op.drop_table("pending_payments")

    op.create_table(
        "payment_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider_session_id", sa.String(255), nullable=False, unique=True),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("donor_telegram_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "pending", "paid", "cancelled", name="payment_status", native_enum=False, length=20
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
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
    )
