"""FSM state groups for multi-step ReplyKeyboardMarkup flows."""
from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class ManageMembersStates(StatesGroup):
    awaiting_id_to_approve = State()
    confirming_approve = State()
    awaiting_id_to_revoke = State()
    confirming_revoke = State()


class ExpenseEntryStates(StatesGroup):
    awaiting_amount = State()
    awaiting_description = State()
    awaiting_receipt = State()
    awaiting_confirm = State()


class RemoveEntryStates(StatesGroup):
    awaiting_code = State()
    confirming = State()


class BankAccountStates(StatesGroup):
    awaiting_card_number = State()
    awaiting_card_holder = State()
    awaiting_bank_name = State()
    confirming = State()


class PaymentStates(StatesGroup):
    choosing_amount = State()
    awaiting_amount = State()
    awaiting_receipt = State()
    confirming = State()


class AnonymousNameStates(StatesGroup):
    choosing = State()
    awaiting_custom_name = State()
