"""Application configuration loaded from environment variables (``.env``)."""
from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    bot_token: str
    timezone: str = Field(default="Asia/Tashkent")

    # Kept as a raw comma-separated string: pydantic-settings tries to
    # JSON-decode "list"-typed env values before any validator runs, which
    # breaks on a plain "111,222" string. Parse it ourselves via the property
    # below instead.
    #
    # Bootstrap only: these Telegram IDs are (re-)promoted to SUPER_ADMIN on
    # every startup. Once a Super Admin exists, day-to-day role management
    # happens in the bot itself ("Manage Treasurers"), not by editing this.
    super_admin_ids: str = Field(default="")

    postgres_user: str = Field(default="ehson_user")
    postgres_password: str = Field(default="ehson_password")
    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432)
    postgres_db: str = Field(default="ehson_db")

    # Optional: a Telegram group chat to post an anonymous "new donation
    # received" announcement to (step 9 of the manual payment flow). Posting
    # is skipped silently if unset -- get the numeric id by adding the bot
    # to the group and checking an update's chat.id (group ids are negative).
    public_group_chat_id: int | None = Field(default=None)

    @property
    def super_admin_id_list(self) -> list[int]:
        return [
            int(part.strip()) for part in self.super_admin_ids.split(",") if part.strip()
        ]

    @property
    def database_url(self) -> str:
        """Async SQLAlchemy URL using the asyncpg driver."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
