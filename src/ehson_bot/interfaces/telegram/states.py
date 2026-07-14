"""FSM state groups for multi-step ReplyKeyboardMarkup flows."""
from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class ManageTreasurerStates(StatesGroup):
    awaiting_id_to_add = State()
    awaiting_id_to_remove = State()
    confirming_add = State()
    confirming_remove = State()


class DonationEntryStates(StatesGroup):
    awaiting_amount = State()
    awaiting_note = State()
    awaiting_confirm = State()


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


class ApproveUserStates(StatesGroup):
    awaiting_id = State()
    confirming = State()
