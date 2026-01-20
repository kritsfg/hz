from dataclasses import dataclass
import os
from typing import List


@dataclass
class Settings:
    bot_token: str
    admin_ids: List[int]
    admin_phones: List[str]
    database_path: str = "data/bot.db"

    @classmethod
    def from_env(cls) -> "Settings":
        token = os.getenv("BOT_TOKEN", "8344847527:AAFJdbJKZi5JpgHAjBPPyDqVgyQTunsJSgE")
        admin_raw = os.getenv("ADMIN_IDS", "7625438712")
        admin_ids = [int(value) for value in admin_raw.split(",") if value.strip()]
        admin_phones_raw = os.getenv("ADMIN_PHONES", "89640062042")
        admin_phones = [value.strip() for value in admin_phones_raw.split(",") if value.strip()]
        database_path = os.getenv("DATABASE_PATH", cls.database_path)
        return cls(
            bot_token=token,
            admin_ids=admin_ids,
            admin_phones=admin_phones,
            database_path=database_path,
        )


settings = Settings.from_env()