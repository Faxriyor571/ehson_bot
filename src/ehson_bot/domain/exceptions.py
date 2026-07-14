"""Domain-level errors. Raised by entities/value objects, caught by adapters."""
from __future__ import annotations


class DomainError(Exception):
    """Base class for all business-rule violations."""


class InvalidDonationAmount(DomainError):
    """A donation amount failed a business rule (e.g. not positive)."""


class DonationNotFound(DomainError):
    """A donation referenced by id does not exist in the ledger."""


class InvalidExpenseDescription(DomainError):
    """An expense was recorded without a (required) description."""


class ExpenseNotFound(DomainError):
    """An expense referenced by id does not exist in the ledger."""


class ReferenceCodeGenerationError(DomainError):
    """Could not find an unused reference code within the retry budget --
    astronomically unlikely at this app's scale; signals something is
    actually wrong (e.g. a broken random source) rather than bad luck.
    """
