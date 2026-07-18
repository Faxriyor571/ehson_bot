"""Unit tests for the random anonymous-name generator."""
from __future__ import annotations

from ehson_bot.interfaces.telegram.handlers.anonymous_name import (
    _RANDOM_NAME_ROOTS,
    generate_random_anonymous_name,
)


def test_generated_name_is_a_known_root_plus_a_three_digit_suffix() -> None:
    name = generate_random_anonymous_name()

    matching_roots = [root for root in _RANDOM_NAME_ROOTS if name.startswith(root)]
    assert len(matching_roots) == 1

    suffix = name.removeprefix(matching_roots[0])
    assert suffix.isdigit()
    assert 100 <= int(suffix) <= 999


def test_generated_names_are_not_all_identical() -> None:
    names = {generate_random_anonymous_name() for _ in range(30)}

    assert len(names) > 1
