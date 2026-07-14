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

BTN_AMOUNT_50K = "50 000 so'm"
BTN_AMOUNT_100K = "100 000 so'm"
BTN_AMOUNT_200K = "200 000 so'm"
BTN_AMOUNT_500K = "500 000 so'm"
BTN_OTHER_AMOUNT = "✍️ Boshqa summa"

BTN_ADD_EXPENSE = "➖ Xarajat qo'shish"
BTN_RECENT = "📋 Oxirgi yozuvlar"

BTN_MANAGE_MEMBERS = "👥 A'zolarni boshqarish"
BTN_SETTINGS = "⚙️ Sozlamalar"
BTN_PENDING_PAYMENTS = "🕒 Kutilayotgan ehsonlar"

BTN_APPROVE_MEMBER = "✅ A'zoni tasdiqlash"
BTN_REVOKE_ACCESS = "🚫 Kirishni bekor qilish"

BTN_REVIEW_PAYMENT = "🔎 Kod bo'yicha ko'rib chiqish"
BTN_REJECT_PAYMENT = "🚫 Rad etish"

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

    if role is Role.SUPER_ADMIN:
        rows.append([KeyboardButton(text=BTN_ADD_EXPENSE)])

    rows.append([KeyboardButton(text=BTN_STATS), KeyboardButton(text=BTN_BALANCE)])
    rows.append([KeyboardButton(text=BTN_ACCOUNT), KeyboardButton(text=BTN_HELP)])
    rows.append([KeyboardButton(text=BTN_USAGE_HISTORY)])

    if role in (Role.TREASURER, Role.SUPER_ADMIN):
        rows.append([KeyboardButton(text=BTN_RECENT)])

    if role is Role.SUPER_ADMIN:
        rows.append([KeyboardButton(text=BTN_MANAGE_MEMBERS), KeyboardButton(text=BTN_SETTINGS)])
        rows.append([KeyboardButton(text=BTN_PENDING_PAYMENTS)])

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


def amount_choice_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_AMOUNT_50K), KeyboardButton(text=BTN_AMOUNT_100K)],
            [KeyboardButton(text=BTN_AMOUNT_200K), KeyboardButton(text=BTN_AMOUNT_500K)],
            [KeyboardButton(text=BTN_OTHER_AMOUNT)],
            [KeyboardButton(text=BTN_CANCEL)],
        ],
        resize_keyboard=True,
    )


def manage_members_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_APPROVE_MEMBER), KeyboardButton(text=BTN_REVOKE_ACCESS)],
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


def recent_entries_menu(can_delete: bool = False) -> ReplyKeyboardMarkup:
    """``can_delete`` gates the delete affordance: approved members (Treasurer)
    can view recent entries, but only Super Admin may act on them.
    """
    rows = [[KeyboardButton(text=BTN_DELETE_ENTRY)]] if can_delete else []
    rows.append([KeyboardButton(text=BTN_BACK)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def settings_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_EDIT_BANK_ACCOUNT)], [KeyboardButton(text=BTN_BACK)]],
        resize_keyboard=True,
    )


def pending_payments_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_REVIEW_PAYMENT)], [KeyboardButton(text=BTN_BACK)]],
        resize_keyboard=True,
    )


def confirm_reject_cancel() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_CONFIRM), KeyboardButton(text=BTN_REJECT_PAYMENT)],
            [KeyboardButton(text=BTN_CANCEL)],
        ],
        resize_keyboard=True,
    )
