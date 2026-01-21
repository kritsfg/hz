from dataclasses import dataclass
import os
from typing import List
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()


@dataclass
class Settings:
    bot_token: str
    admin_ids: List[int]
    admin_phones: List[str]
    database_path: str = "data/bot.db"

    @classmethod
    def from_env(cls) -> "Settings":
        token = os.getenv("BOT_TOKEN")
        admin_raw = os.getenv("ADMIN_IDS")
        admin_ids = [int(value) for value in admin_raw.split(",") if value.strip()]
        admin_phones_raw = os.getenv("ADMIN_PHONES")
        admin_phones = [value.strip() for value in admin_phones_raw.split(",") if value.strip()]
        database_path = os.getenv("DATABASE_PATH", cls.database_path)
        return cls(
            bot_token=token,
            admin_ids=admin_ids,
            admin_phones=admin_phones,
            database_path=database_path,
        )



settings = Settings.from_env()
