# Mahfiy Ehson bot

Telegram bot for a small charity group. Donations are pooled anonymously —
donor identity is never captured anywhere in the system, the schema simply
has no field for it. What's fully transparent is *usage*: every expense is
recorded with an amount, a required description, and (optionally) a receipt
photo, and anyone can see today's/monthly/yearly totals and the current
balance. A scheduled job posts a report to every registered user at 23:59
(Asia/Tashkent).

## Roles

| Role | Can |
|---|---|
| **User** (default) | View statistics, balance, and the donation account. Cannot edit anything. |
| **Treasurer** | Everything a User can, plus record donations/expenses and correct mistaken entries. |
| **Super Admin** | Everything a Treasurer can, plus grant/revoke the Treasurer role and edit the donation account text. |

Every real Telegram user becomes a `User` the first time they press
`/start` — there is no "unauthorized" wall; viewing reports is intentionally
open to everyone in the group.

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
Admin exists, further Treasurer/Super Admin management happens from within
the bot itself ("👥 Xazinachilarni boshqarish"), not by editing `.env` again.

Note: Treasurer promotion (as opposed to this Super Admin bootstrap) *does*
require the target user to have pressed `/start` at least once, since that
flow looks up an existing user rather than creating one.

## Development

```bash
pytest
ruff check src tests
mypy src
```

## Design note: anonymity

`Donation` rows (`infrastructure/db/models.py::DonationRow`) have no
donor-identifying column at all — not hidden by permissions, simply not
present in the schema. `recorded_by_id` tracks which *treasurer* logged an
entry, for their own accountability, and is never surfaced next to a donor.
`Expense` rows are the mirror image: a mandatory `description` so usage is
always traceable, plus an optional receipt photo.
