"""Unit test for the shared HTML-escaping helper.

The bot defaults to ``ParseMode.HTML``, so any free text interpolated into a
message (display names, expense descriptions, donation notes) must be
escaped or it can break delivery — or worse, inject markup.
"""
from __future__ import annotations

from ehson_bot.interfaces.telegram.common import esc


def test_esc_escapes_html_special_characters() -> None:
    assert esc("Elektr & suv <asosiy>") == "Elektr &amp; suv &lt;asosiy&gt;"


def test_esc_leaves_quotes_untouched() -> None:
    """Telegram's HTML subset doesn't require quotes to be escaped."""
    assert esc('u aytdi: "rahmat"') == 'u aytdi: "rahmat"'
