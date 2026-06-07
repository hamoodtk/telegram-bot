from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Iterable


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def parse_user_ids(value: str) -> tuple[int, ...]:
    if not value:
        return tuple()

    user_ids = []
    for part in value.replace(";", ",").split(","):
        cleaned = part.strip()
        if not cleaned:
            continue
        if cleaned.isdigit():
            user_ids.append(int(cleaned))
    return tuple(dict.fromkeys(user_ids))


def split_pipe_text(text: str, minimum_parts: int = 1) -> list[str]:
    parts = [part.strip() for part in text.split("|")]
    while len(parts) < minimum_parts:
        parts.append("")
    return parts


def parse_int(value: str, default: int | None = None, minimum: int | None = None) -> int | None:
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError):
        return default

    if minimum is not None and number < minimum:
        return default
    return number


def parse_float(value: str, default: float | None = None, minimum: float | None = None) -> float | None:
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return default

    if minimum is not None and number < minimum:
        return default
    return number


def parse_date(value: str) -> str | None:
    cleaned = str(value).strip()
    if cleaned in {"", "-", "لا"}:
        return None
    try:
        datetime.strptime(cleaned, "%Y-%m-%d")
    except ValueError:
        return None
    return cleaned


def parse_time(value: str) -> str | None:
    cleaned = str(value).strip()
    if cleaned in {"", "-", "لا"}:
        return None
    try:
        datetime.strptime(cleaned, "%H:%M")
    except ValueError:
        return None
    return cleaned


def normalize_recurrence(value: str) -> str:
    cleaned = str(value).strip().lower()
    mapping = {
        "مرة": "once",
        "مرة واحدة": "once",
        "once": "once",
        "يومية": "daily",
        "يوميا": "daily",
        "daily": "daily",
        "أسبوعية": "weekly",
        "اسبوعية": "weekly",
        "weekly": "weekly",
    }
    return mapping.get(cleaned, "once")


def format_iso_date(value: str | None) -> str:
    if not value:
        return "غير محدد"
    return value


def clamp_text(value: str, length: int = 40) -> str:
    cleaned = " ".join(str(value).split())
    if len(cleaned) <= length:
        return cleaned
    return cleaned[: length - 1] + "…"

