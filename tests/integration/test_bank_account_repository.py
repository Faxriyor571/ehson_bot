"""Integration tests for SqlAlchemyBankAccountRepository against in-memory SQLite."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from ehson_bot.infrastructure.db.repositories import SqlAlchemyBankAccountRepository


async def test_get_returns_none_before_anything_is_configured(session: AsyncSession) -> None:
    repo = SqlAlchemyBankAccountRepository(session)

    assert await repo.get() is None


async def test_set_then_get_returns_the_saved_fields(session: AsyncSession) -> None:
    repo = SqlAlchemyBankAccountRepository(session)

    saved = await repo.set(
        card_number="1234 5678 9012 3456", card_holder="Falonchi Falonchiyev", bank_name="Ipoteka"
    )

    assert saved.card_number == "1234 5678 9012 3456"
    assert saved.card_holder == "Falonchi Falonchiyev"
    assert saved.bank_name == "Ipoteka"
    fetched = await repo.get()
    assert fetched is not None
    assert fetched.card_number == saved.card_number
    assert fetched.card_holder == saved.card_holder
    assert fetched.bank_name == saved.bank_name


async def test_set_twice_overwrites_the_singleton_row(session: AsyncSession) -> None:
    repo = SqlAlchemyBankAccountRepository(session)

    await repo.set(card_number="1111", card_holder="First Holder", bank_name="First Bank")
    await repo.set(card_number="2222", card_holder="Second Holder", bank_name="Second Bank")

    account = await repo.get()
    assert account is not None
    assert account.card_number == "2222"
    assert account.card_holder == "Second Holder"
    assert account.bank_name == "Second Bank"
