"""Integration tests for SqlAlchemyBankAccountRepository against in-memory SQLite."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from ehson_bot.infrastructure.db.repositories import SqlAlchemyBankAccountRepository


async def test_get_returns_none_before_anything_is_configured(session: AsyncSession) -> None:
    repo = SqlAlchemyBankAccountRepository(session)

    assert await repo.get() is None


async def test_set_then_get_returns_the_saved_text(session: AsyncSession) -> None:
    repo = SqlAlchemyBankAccountRepository(session)

    saved = await repo.set("Bank: Ipoteka\nKarta: 1234 5678 9012 3456")

    assert saved.text == "Bank: Ipoteka\nKarta: 1234 5678 9012 3456"
    fetched = await repo.get()
    assert fetched is not None
    assert fetched.text == saved.text


async def test_set_twice_overwrites_the_singleton_row(session: AsyncSession) -> None:
    repo = SqlAlchemyBankAccountRepository(session)

    await repo.set("First version")
    await repo.set("Second version")

    account = await repo.get()
    assert account is not None
    assert account.text == "Second version"
