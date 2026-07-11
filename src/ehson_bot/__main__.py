"""Entry point: ``python -m ehson_bot``."""
from __future__ import annotations

import asyncio
import logging

from ehson_bot.interfaces.telegram.bot import run

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

if __name__ == "__main__":
    asyncio.run(run())
