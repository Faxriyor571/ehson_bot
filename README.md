# Mahfiy Ehson bot

Telegram bot for a small, trusted charity group (a handful of people).
Donations are pooled anonymously — donor identity is never captured
anywhere in the system, the schema simply has no field for it. There is no
payment gateway integrated and, with only a handful of trusted members, no
manual admin review step either: an approved member picks an amount, sees
the donation card, optionally attaches a receipt photo, and presses
"✅ Pulni o'tkazdim" — that press *is* the final confirmation. It
immediately records the donation, updates the balance and statistics
(these compute live from the ledger, so there's nothing extra to update),
notifies every Super Admin privately, and posts an anonymous donation
announcement to every Super Admin's own chat. What's fully transparent is
*usage*: every expense is recorded with an amount, a required description,
and (optionally) a receipt photo, and anyone can see today's/monthly/yearly
totals and the current balance. A scheduled job posts a report to every
registered user at 23:59 (Asia/Tashkent).

## Roles

There are only three roles — no separate donor-only tier, because every
approved member of this small, trusted group is trusted both to donate on
their own say-so and to record expenses. `Treasurer` here means "approved
member," not "bookkeeper" — it grants viewing and donating, nothing
administrative or financial-management. All recording/editing/deleting and
every administrative action is Super-Admin-only.

| Role | Can |
|---|---|
| **Pending** (default) | Nothing — locked out until a Super Admin approves them. |
| **Treasurer** | A deliberately minimal menu: donate ("🤲 Ehson qilish"), balance ("💰 Balans"), statistics ("📊 Statistika"). This is the only non-admin approved role — it cannot record, edit, or delete anything, view itemized recent entries, approve users, manage roles, or touch settings. |
| **Super Admin** | Everything a Treasurer can, plus record/edit/delete expenses, view and delete a mistaken entry, approve pending users (grants Treasurer), revoke a member's access (demotes back to Pending — there's no lower tier to fall back to), and configure the donation account (card number, card holder, bank name — set via a guided 3-step flow, not free text). |

Every real Telegram user becomes `Pending` on their first `/start` and needs
a Super Admin to approve them before they can do anything — see the lockout
message for details. The first time an approved member gets past that
lockout, they're routed into choosing an anonymous display name before ever
seeing the menu — see "Anonymous display name" below.

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

## Self-service donation confirmation

No payment gateway is integrated, and with only a handful of trusted
members there is no manual admin review step either — the donor's own
confirm press *is* the approval:

1. An approved member picks an amount, sees the donation card, optionally
   attaches a receipt photo, and presses "✅ Pulni o'tkazdim" (I've
   transferred the money) — a dedicated button distinct from the generic
   "✅ Tasdiqlash" used by every other confirm screen in the bot.
2. `handlers/payments.py::confirm_payment` calls `RecordDonationUseCase`
   directly and immediately, crediting `recorded_by` to a fixed,
   documented sentinel (`SYSTEM_TREASURER_ID = 0`, never a real Telegram
   ID) since there's no human treasurer recording it on the donor's behalf
   — the donor confirmed it themselves. The optional receipt photo is
   saved on the `Donation` row itself (`receipt_file_id`).
3. The balance and statistics screens need no extra update step at all —
   they already compute live from the `donations`/`expenses` tables
   (`GetPeriodReportUseCase`), so the moment the row commits, every screen
   reflects it.
4. The bot then privately thanks the donor by their anonymous name, sends
   every Super Admin a notification (amount and record code only — never a
   Telegram ID, username, or display name), and posts an anonymous
   donation announcement to every Super Admin's own chat — donor's
   anonymous name (or "🤲 Mahfiy inson ehson qildi!" if they never chose
   one), amount, today's total, and the current balance. Every message
   here goes to a private chat with the donor or a Super Admin — there is
   no group/channel integration anywhere in the project.

## Anonymous display name

The first time an approved member gets past the PENDING lockout (`/start`,
`/help`, or any stray message via the fallback catch-all — the only three
places that would otherwise hand them the main menu), they're routed into
`handlers/anonymous_name.py` instead: pick one of four preset nicknames,
write a custom one, or skip and get one auto-generated (e.g.
`SirliYulduz284`). It's stored on `BotUser.anonymous_name`
(`bot_users.anonymous_name`, nullable) and used only to personalize
messages sent directly back to that person — e.g. "🤲 Rahmat, QalbNuri!" in
the donation-confirmed message — never their real Telegram name or
username, and never surfaced on any Super-Admin-facing screen. If a
donor-ranking/achievements feature is ever built, it must be sourced from
this field alone.

## Design note: anonymity

`Donation` rows (`infrastructure/db/models.py::DonationRow`) have no
donor-identifying column at all — not hidden by permissions, simply not
present in the schema. The donor's Telegram ID is only ever used
transiently, in-memory, during the confirm handler itself (to look up
their anonymous name for the thank-you message and the announcement), and
is never persisted anywhere alongside the donation. `Expense` rows are the
mirror image of `Donation`: a mandatory `description` so usage is always
traceable, plus an optional receipt photo.
