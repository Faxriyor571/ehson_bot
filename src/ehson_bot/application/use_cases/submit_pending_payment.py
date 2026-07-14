"""Use case: a donor submits a claim of having paid, awaiting manual review.

No real payment gateway is integrated, so this is the only way money ever
becomes a ``Donation`` -- a Super Admin will later check the bank account by
eye and decide. The public ``reference_code`` exists precisely so that
decision never has to touch the donor's identity.
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass
from decimal import Decimal

from ehson_bot.domain.entities import PendingPayment
from ehson_bot.domain.exceptions import ReferenceCodeGenerationError
from ehson_bot.domain.repositories import PendingPaymentRepository
from ehson_bot.domain.value_objects import Money

# No 0/O, 1/I/L: avoids visual ambiguity when a donor reads the code aloud
# or a Super Admin retypes it.
_CODE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
_CODE_LENGTH = 5
_MAX_GENERATION_ATTEMPTS = 5


def generate_reference_code() -> str:
    suffix = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(_CODE_LENGTH))
    return f"EH-{suffix}"


@dataclass(frozen=True, slots=True)
class SubmitPendingPaymentInput:
    amount: Decimal
    donor_telegram_id: int
    receipt_file_id: str | None = None


class SubmitPendingPaymentUseCase:
    def __init__(self, payments: PendingPaymentRepository) -> None:
        self._payments = payments

    async def execute(self, data: SubmitPendingPaymentInput) -> PendingPayment:
        code = await self._unique_reference_code()
        return await self._payments.add(
            PendingPayment(
                reference_code=code,
                amount=Money(data.amount),
                donor_telegram_id=data.donor_telegram_id,
                receipt_file_id=data.receipt_file_id,
            )
        )

    async def _unique_reference_code(self) -> str:
        for _ in range(_MAX_GENERATION_ATTEMPTS):
            code = generate_reference_code()
            if await self._payments.get_by_reference(code) is None:
                return code
        raise ReferenceCodeGenerationError(
            f"Could not generate a unique reference code in {_MAX_GENERATION_ATTEMPTS} attempts"
        )
