"""Integration tests for SqlAlchemyBotUserRepository against in-memory SQLite."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from ehson_bot.domain.entities import Role
from ehson_bot.infrastructure.db.repositories import SqlAlchemyBotUserRepository


async def test_upsert_creates_new_user_with_default_role(session: AsyncSession) -> None:
    repo = SqlAlchemyBotUserRepository(session)

    user = await repo.upsert(telegram_id=111, display_name="Ali")

    assert user.telegram_id == 111
    assert user.role is Role.USER
    assert user.display_name == "Ali"


async def test_upsert_refreshes_display_name_without_changing_role(
    session: AsyncSession,
) -> None:
    repo = SqlAlchemyBotUserRepository(session)
    await repo.upsert(telegram_id=111, display_name="Ali")
    await repo.set_role(111, Role.TREASURER)

    user = await repo.upsert(telegram_id=111, display_name="Ali Karimov")

    assert user.display_name == "Ali Karimov"
    assert user.role is Role.TREASURER


async def test_set_role_returns_none_for_unknown_user(session: AsyncSession) -> None:
    repo = SqlAlchemyBotUserRepository(session)

    assert await repo.set_role(999, Role.TREASURER) is None


async def test_list_by_role_filters_correctly(session: AsyncSession) -> None:
    repo = SqlAlchemyBotUserRepository(session)
    await repo.upsert(telegram_id=1, display_name="A")
    await repo.upsert(telegram_id=2, display_name="B")
    await repo.set_role(2, Role.TREASURER)

    treasurers = await repo.list_by_role(Role.TREASURER)

    assert [t.telegram_id for t in treasurers] == [2]


async def test_get_returns_none_when_missing(session: AsyncSession) -> None:
    repo = SqlAlchemyBotUserRepository(session)

    assert await repo.get(42) is None


async def test_list_all_returns_every_user_in_join_order(session: AsyncSession) -> None:
    repo = SqlAlchemyBotUserRepository(session)
    await repo.upsert(telegram_id=1, display_name="A")
    await repo.upsert(telegram_id=2, display_name="B")

    all_users = await repo.list_all()

    assert [u.telegram_id for u in all_users] == [1, 2]
