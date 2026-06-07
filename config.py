from __future__ import annotations

import os
from pathlib import Path

from bot.utils.parsers import load_env_file, parse_user_ids


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

load_env_file(PROJECT_ROOT / ".env")
load_env_file(BASE_DIR / ".env")


def _read_env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


BOT_TOKEN = _read_env("8838423698:AAESWUq2jGJzluHPhgq8sZIzdx2Z8G1x-wE")
USER_IDS = parse_user_ids(_read_env("8560368305"))
TIMEZONE = _read_env("TIMEZONE", "Asia/Beirut")

DATABASE_PATH = Path(_read_env("DATABASE_PATH", str(BASE_DIR / "data" / "bot.sqlite3")))
if not DATABASE_PATH.is_absolute():
    DATABASE_PATH = (PROJECT_ROOT / DATABASE_PATH).resolve()
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

PRAYER_TIMES = {
    "الفجر": _read_env("PRAYER_FAJR", "05:00"),
    "الظهر": _read_env("PRAYER_DHUHR", "12:15"),
    "العصر": _read_env("PRAYER_ASR", "15:45"),
    "المغرب": _read_env("PRAYER_MAGHRIB", "18:10"),
    "العشاء": _read_env("PRAYER_ISHA", "19:45"),
}

MORNING_ADHKAR_TIME = _read_env("MORNING_ADHKAR_TIME", "06:30")
EVENING_ADHKAR_TIME = _read_env("EVENING_ADHKAR_TIME", "18:30")
KAHF_REMINDER_TIME = _read_env("KAHF_REMINDER_TIME", "08:00")
FASTING_REMINDER_TIME = _read_env("FASTING_REMINDER_TIME", "19:30")
EXERCISE_REMINDER_TIME = _read_env("EXERCISE_REMINDER_TIME", "20:00")
DAILY_REPORT_TIME = _read_env("DAILY_REPORT_TIME", "22:00")
WEEKLY_REPORT_TIME = _read_env("WEEKLY_REPORT_TIME", "22:10")
MIDNIGHT_MAINTENANCE_TIME = _read_env("MIDNIGHT_MAINTENANCE_TIME", "00:05")

_water_hours = tuple(
    int(part)
    for part in _read_env("WATER_REMINDER_HOURS", "9,11,13,15,17,19,21").split(",")
    if part.strip().isdigit()
)
WATER_REMINDER_HOURS = _water_hours or (9, 11, 13, 15, 17, 19, 21)

DEFAULT_QURAN_PAGE_TARGET = int(_read_env("QURAN_PAGE_TARGET", "604"))

