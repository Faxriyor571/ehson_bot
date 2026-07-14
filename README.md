# Mahfiy Ehson bot

Telegram bot for a small charity group. Donations are pooled anonymously —
donor identity is never captured anywhere in the system, the schema simply
has no field for it. There is no payment gateway integrated, so a Super
Admin manually verifies every donation against the bank account by eye —
but that Super Admin must never learn *who* paid. An approved member picks
an amount, sees the donation card, optionally attaches a receipt photo, and
submits; the bot generates a random public `reference_code` (e.g.
`EH-8F42K`) and that is the *only* donor-facing identifier the Super Admin
ever sees, in a notification containing nothing else identifying. The
donor's Telegram ID is held only *transiently*, in `pending_payments`, to
route the private confirm/reject message, and is scrubbed the instant a
Super Admin decides. What's fully transparent is *usage*: every expense is
recorded with an amount, a required description, and (optionally) a
receipt photo, and anyone can see today's/monthly/yearly totals and the
current balance. A scheduled job posts a report to every registered user
at 23:59 (Asia/Tashkent).

## Roles

There are only three roles — no separate donor-only tier, because donating
no longer depends on a role check at all: what actually protects a donation
from being fabricated is a Super Admin manually verifying the bank account,
not who's allowed to press the button. `Treasurer` here means "approved
member," not "bookkeeper" — it grants viewing and donating, nothing
administrative or financial-management. All recording/editing/deleting and
every administrative action is Super-Admin-only.

| Role | Can |
|---|---|
| **Pending** (default) | Nothing — locked out until a Super Admin approves them. |
| **Treasurer** | View statistics, balance, reports, and recent donation/expense entries; donate via "🤲 Ehson qilish". This is the only non-admin approved role — it cannot record, edit, or delete anything, approve users, manage roles, review payments, or touch settings. |
| **Super Admin** | Everything a Treasurer can, plus record/edit/delete expenses, delete a mistaken entry, approve pending users (grants Treasurer), revoke a member's access (demotes back to Pending — there's no lower tier to fall back to), configure the donation account (card number, card holder, bank name — set via a guided 3-step flow, not free text), and manually confirm/reject a pending payment by its reference code — never by donor identity, which this screen structurally cannot look up. |

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

## Manual payment review

No payment gateway is integrated, so a Super Admin has to look at the bank
account and decide whether a claimed donation actually arrived — but that
Super Admin must never be able to tell who claimed it. The flow:

1. An approved member picks an amount, sees the donation card, optionally
   attaches a receipt photo, and confirms.
2. `SubmitPendingPaymentUseCase` creates a `PendingPayment` with a random
   `reference_code` (e.g. `EH-8F42K`) and notifies every Super Admin with
   *only* that code, a generic non-identifying label, the amount, the time,
   and the receipt if one was attached — never a Telegram ID, username, or
   display name.
3. The Super Admin checks the bank account by eye, then confirms or rejects
   by typing the reference code back to the bot (`handlers/admin.py`'s
   "🕒 Kutilayotgan ehsonlar" screen) — there is no repository method that
   looks a claim up by donor, so a donor-lookup screen is structurally
   impossible to build here, not just absent from the UI.
4. Confirming calls `ConfirmPendingPaymentUseCase`, which creates the
   `Donation` (crediting `recorded_by` to the *confirming Super Admin's own*
   Telegram ID — a real person verified this one, so that field means what
   it always meant) and privately thanks the donor. Rejecting notifies the
   donor privately instead. The bot never posts anywhere but a private chat
   with the donor or a Super Admin — there is no group/channel integration
   anywhere in the project.

With multiple Super Admins, two people can open the same reference code at
once. `PendingPaymentRepository.try_claim` is a single atomic conditional
write (`UPDATE ... WHERE status = 'pending'`), not a read-then-write, so at
most one of them can ever win — the other's confirm/reject is a safe,
idempotent no-op ("already reviewed"), and at most one `Donation` is ever
created per reference code no matter how the two requests interleave.

## Design note: anonymity

`Donation` rows (`infrastructure/db/models.py::DonationRow`) have no
donor-identifying column at all — not hidden by permissions, simply not
present in the schema. `pending_payments` is the only place a donor's
Telegram ID is ever stored, and only *transiently* — the repository scrubs
it (`donor_telegram_id = NULL`) the instant a Super Admin confirms or
rejects, so it never becomes a permanent donor-to-donation link. `Expense`
rows are the mirror image of `Donation`: a mandatory `description` so usage
is always traceable, plus an optional receipt photo.
