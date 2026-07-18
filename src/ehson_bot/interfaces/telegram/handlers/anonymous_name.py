"""An approved member picks (or is randomly assigned) an anonymous display
name, on their first arrival past the PENDING lockout.

This name is used only to personalize messages sent directly back to that
person (e.g. a donation-confirmed thank-you) — never their real Telegram
name or username, and never read anywhere a Super Admin can see who
submitted a given payment claim. If this ever grows a donor
leaderboard/achievements feature, it must be built on this field alone.

Gated by ``IsTreasurerOrAbove`` since only an already-approved member ever
reaches this flow — see ``handlers/start.py::start_anonymous_name_flow``
for where it's triggered from and why gating just three entry points
(``/start``, ``/help``, the fallback catch-all) is sufficient.
"""
from __future__ import annotations

import secrets

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from ehson_bot.domain.entities import Role
from ehson_bot.infrastructure.db.repositories import SqlAlchemyBotUserRepository
from ehson_bot.interfaces.telegram.common import esc
from ehson_bot.interfaces.telegram.filters import IsTreasurerOrAbove
from ehson_bot.interfaces.telegram.handlers.start import start_anonymous_name_flow, welcome_text
from ehson_bot.interfaces.telegram.keyboards import (
    BTN_ANON_NAME_1,
    BTN_ANON_NAME_2,
    BTN_ANON_NAME_3,
    BTN_ANON_NAME_4,
    BTN_CANCEL,
    BTN_CUSTOM_ANON_NAME,
    BTN_SKIP,
    cancel_only,
    main_menu,
)
from ehson_bot.interfaces.telegram.states import AnonymousNameStates

router = Router(name="anonymous_name")
router.message.filter(IsTreasurerOrAbove())

_PRESET_NAMES: dict[str, str] = {
    BTN_ANON_NAME_1: "TunYulduzi",
    BTN_ANON_NAME_2: "YashilBarg",
    BTN_ANON_NAME_3: "ErkinQanot",
    BTN_ANON_NAME_4: "SirliYulduz",
}

_RANDOM_NAME_ROOTS = [
    "TunYulduzi",
    "YashilBarg",
    "ErkinQanot",
    "SirliYulduz",
    "OqCho'qqi",
    "QalbNuri",
]
_MAX_CUSTOM_NAME_LENGTH = 50


def generate_random_anonymous_name() -> str:
    root = secrets.choice(_RANDOM_NAME_ROOTS)
    suffix = secrets.randbelow(900) + 100  # 100-999, matches the "SirliYulduz284" example
    return f"{root}{suffix}"


async def _finish(message: Message, state: FSMContext, session: AsyncSession, name: str) -> None:
    if message.from_user is None:
        return
    user = await SqlAlchemyBotUserRepository(session).set_anonymous_name(
        message.from_user.id, name
    )
    await state.clear()
    await message.answer(f"✅ Sizning maxfiy taxallusingiz: <b>{esc(name)}</b>")
    role = user.role if user is not None else Role.PENDING
    await message.answer(welcome_text(), reply_markup=main_menu(role))


@router.message(AnonymousNameStates.choosing, F.text.in_(_PRESET_NAMES))
async def preset_name_chosen(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if message.text is None:
        return
    await _finish(message, state, session, _PRESET_NAMES[message.text])


@router.message(AnonymousNameStates.choosing, F.text == BTN_SKIP)
async def name_skipped(message: Message, state: FSMContext, session: AsyncSession) -> None:
    await _finish(message, state, session, generate_random_anonymous_name())


@router.message(AnonymousNameStates.choosing, F.text == BTN_CUSTOM_ANON_NAME)
async def ask_custom_name(message: Message, state: FSMContext) -> None:
    await state.set_state(AnonymousNameStates.awaiting_custom_name)
    await message.answer(
        "Maxfiy taxallusingizni yozing (masalan: QalbNuri):", reply_markup=cancel_only()
    )


@router.message(AnonymousNameStates.awaiting_custom_name, F.text == BTN_CANCEL)
async def cancel_custom_name(message: Message, state: FSMContext) -> None:
    await start_anonymous_name_flow(message, state)


@router.message(AnonymousNameStates.awaiting_custom_name)
async def custom_name_entered(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    name = (message.text or "").strip()
    if not name or len(name) > _MAX_CUSTOM_NAME_LENGTH:
        await message.answer(
            f"Nom bo'sh yoki {_MAX_CUSTOM_NAME_LENGTH} belgidan uzun bo'lmasligi kerak."
        )
        return
    await _finish(message, state, session, name)


@router.message(AnonymousNameStates.choosing)
async def invalid_name_choice(message: Message) -> None:
    await message.answer(
        "Iltimos, ro'yxatdan birini tanlang, o'z nomingizni yozish uchun "
        "“✍️ Boshqa nom”ni bosing yoki o'tkazib yuboring."
    )
