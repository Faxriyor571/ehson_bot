# Mahfiy Ehson bot

Telegram bot for a small charity group. Donations are pooled anonymously —
donor identity is never captured anywhere in the system, the schema simply
has no field for it; a donor's Telegram ID is only ever held *transiently*,
in `payment_sessions`, while their payment is outstanding, purely to route
the thank-you message, and is scrubbed the moment the payment confirms.
Donations happen automatically: any approved member presses "🤲 Ehson
qilish", enters an amount, and pays through a provider (`MockPaymentProvider`
today; Click/Payme later, without changing this flow) — no one manually
records a donation anymore. What's fully transparent is *usage*: every
expense is recorded with an amount, a required description, and
(optionally) a receipt photo, and anyone can see today's/monthly/yearly
totals and the current balance. A scheduled job posts a report to every
registered user at 23:59 (Asia/Tashkent).

## Roles

There are only three roles — no separate donor-only tier, because donating
no longer depends on a role check at all: what actually protects a donation
from being fabricated is the payment provider's confirmation, not who's
allowed to press the button. `Treasurer` here means "approved member," not
"bookkeeper" — it grants viewing and donating, nothing administrative or
financial-management. All recording/editing/deleting and every
administrative action is Super-Admin-only.

| Role | Can |
|---|---|
| **Pending** (default) | Nothing — locked out until a Super Admin approves them. |
| **Treasurer** | View statistics, balance, reports, and recent donation/expense entries; donate via "🤲 Ehson qilish". This is the only non-admin approved role — it cannot record, edit, or delete anything, approve users, manage roles, or touch settings. |
| **Super Admin** | Everything a Treasurer can, plus record/edit/delete expenses, delete a mistaken entry, approve pending users (grants Treasurer), revoke a member's access (demotes back to Pending — there's no lower tier to fall back to), and configure the donation account (card number, card holder, bank name — set via a guided 3-step flow, not free text; shown as a manual fallback alongside the "Pay Now" button). |

Every real Telegram user becomes `Pending` on their first `/start` and needs
a Super Admin to approve them before they can do anything — see the lockout
message for details.

## Stack

- Python 3.13, [aiogram](https://docs.aiogram.dev/) 3.x (async), FSM-driven
  ReplyKeyboardMarkup flows (no slash commands beyond `/start`/`/help`)
- SQLAlchemy 2.0 (async) + PostgreSQL, schema owned by Alembic
- APScheduler for the daily 23:59 report

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[dev]"

copy .env.example .env
# Edit .env: BOT_TOKEN (from @BotFather), SUPER_ADMIN_IDS (Telegram numeric
# user IDs to bootstrap as Super Admin, comma-separated — get your own from
# @userinfobot), TIMEZONE (default Asia/Tashkent)

docker compose up -d      # starts Postgres
alembic upgrade head
```

## Run

```bash
python -m ehson_bot
```

## Bootstrapping the first Super Admin

`SUPER_ADMIN_IDS` in `.env` is re-applied on every startup: those Telegram
IDs are (re-)promoted to Super Admin, creating the user row if it doesn't
exist yet — you don't need to press `/start` first. Once at least one Super
Admin exists, further member/Super Admin management happens from within the
bot itself ("👥 A'zolarni boshqarish"), not by editing `.env` again.

Note: approving a member (as opposed to this Super Admin bootstrap) *does*
require the target user to have pressed `/start` at least once, since that
flow looks up an existing PENDING row rather than creating one.

## Development

```bash
pytest
ruff check src tests
mypy src
```

## Design note: anonymity

`Donation` rows (`infrastructure/db/models.py::DonationRow`) have no
donor-identifying column at all — not hidden by permissions, simply not
present in the schema. Now that donations are payment-originated,
`recorded_by_id` is set to a fixed, documented sentinel
(`SYSTEM_TREASURER_ID = 0`, never a real Telegram id) rather than a human
treasurer, since no one manually recorded it. `payment_sessions` is the only
place a donor's Telegram ID is ever stored, and only *transiently* — the
repository scrubs it (`donor_telegram_id = NULL`) the instant a session
leaves PENDING, so it never becomes a permanent donor-to-donation link.
`Expense` rows are the mirror image of `Donation`: a mandatory `description`
so usage is always traceable, plus an optional receipt photo.
