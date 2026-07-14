"""ReplyKeyboardMarkup builders. Every menu in the bot is built here so the
role-to-button mapping lives in one place instead of scattered across handlers.
"""
from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from ehson_bot.domain.entities import Role

BTN_STATS = "📊 Statistika"
BTN_BALANCE = "💰 Balans"
BTN_ACCOUNT = "🤲 Ehson qilish"
BTN_HELP = "ℹ️ Yordam"

BTN_ADD_DONATION = "➕ Ehson qo'shish"
BTN_ADD_EXPENSE = "➖ Xarajat qo'shish"
BTN_RECENT = "📋 Oxirgi yozuvlar"

BTN_MANAGE_TREASURERS = "👥 Xazinachilarni boshqarish"
BTN_SETTINGS = "⚙️ Sozlamalar"
BTN_APPROVE_USERS = "✅ Foydalanuvchilarni tasdiqlash"

BTN_ADD_TREASURER = "➕ Xazinachi qo'shish"
BTN_REMOVE_TREASURER = "➖ Xazinachi o'chirish"
BTN_APPROVE_BY_ID = "☑️ ID orqali tasdiqlash"

BTN_USAGE_HISTORY = "📜 Foydalanish tarixi"

BTN_PERIOD_TODAY = "📆 Bugun"
BTN_PERIOD_MONTH = "🗓 Bu oy"
BTN_PERIOD_YEAR = "📅 Bu yil"
BTN_PERIOD_ALL = "♾ Umumiy"

BTN_DELETE_ENTRY = "🗑 Yozuvni o'chirish"

BTN_EDIT_BANK_ACCOUNT = "✏️ Hisob raqamini tahrirlash"

BTN_CANCEL = "❌ Bekor qilish"
BTN_BACK = "⬅️ Orqaga"
BTN_CONFIRM = "✅ Tasdiqlash"
BTN_SKIP = "⏭ O'tkazib yuborish"


def main_menu(role: Role) -> ReplyKeyboardMarkup:
    """The persistent bottom menu, scoped to what this role may do."""
    rows: list[list[KeyboardButton]] = []

    if role in (Role.TREASURER, Role.SUPER_ADMIN):
        rows.append([KeyboardButton(text=BTN_ADD_DONATION), KeyboardButton(text=BTN_ADD_EXPENSE)])

    rows.append([KeyboardButton(text=BTN_STATS), KeyboardButton(text=BTN_BALANCE)])
    rows.append([KeyboardButton(text=BTN_ACCOUNT), KeyboardButton(text=BTN_HELP)])
    rows.append([KeyboardButton(text=BTN_USAGE_HISTORY)])

    if role in (Role.TREASURER, Role.SUPER_ADMIN):
        rows.append([KeyboardButton(text=BTN_RECENT)])

    if role is Role.SUPER_ADMIN:
        rows.append([KeyboardButton(text=BTN_MANAGE_TREASURERS), KeyboardButton(text=BTN_SETTINGS)])
        rows.append([KeyboardButton(text=BTN_APPROVE_USERS)])

    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def cancel_only() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=BTN_CANCEL)]], resize_keyboard=True)


def confirm_cancel() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_CONFIRM), KeyboardButton(text=BTN_CANCEL)]],
        resize_keyboard=True,
    )


def skip_or_cancel() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_SKIP), KeyboardButton(text=BTN_CANCEL)]],
        resize_keyboard=True,
    )


def manage_treasurers_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_ADD_TREASURER), KeyboardButton(text=BTN_REMOVE_TREASURER)],
            [KeyboardButton(text=BTN_BACK)],
        ],
        resize_keyboard=True,
    )


def stats_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_PERIOD_TODAY), KeyboardButton(text=BTN_PERIOD_MONTH)],
            [KeyboardButton(text=BTN_PERIOD_YEAR), KeyboardButton(text=BTN_PERIOD_ALL)],
            [KeyboardButton(text=BTN_BACK)],
        ],
        resize_keyboard=True,
    )


def recent_entries_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_DELETE_ENTRY)], [KeyboardButton(text=BTN_BACK)]],
        resize_keyboard=True,
    )


def settings_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_EDIT_BANK_ACCOUNT)], [KeyboardButton(text=BTN_BACK)]],
        resize_keyboard=True,
    )


def approve_users_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_APPROVE_BY_ID)], [KeyboardButton(text=BTN_BACK)]],
        resize_keyboard=True,
    )
