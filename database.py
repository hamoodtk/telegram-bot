from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from bot.config import TIMEZONE
from bot.utils.constants import (
    ACHIEVEMENTS,
    POINTS,
    QURAN_PAGE_PER_KHATMA,
)
from bot.utils.formatters import level_from_points
from bot.utils.parsers import normalize_recurrence


TZ = ZoneInfo(TIMEZONE)


def _row_to_dict(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row is not None else None


class Database:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def now(self) -> datetime:
        return datetime.now(TZ)

    def today(self) -> str:
        return self.now().date().isoformat()

    def initialize(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                PRAGMA journal_mode=WAL;

                CREATE TABLE IF NOT EXISTS users (
                    telegram_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    joined_at TEXT NOT NULL,
                    last_seen_at TEXT,
                    total_points INTEGER NOT NULL DEFAULT 0,
                    current_streak INTEGER NOT NULL DEFAULT 0,
                    best_streak INTEGER NOT NULL DEFAULT 0,
                    last_active_date TEXT,
                    level_name TEXT NOT NULL DEFAULT 'مبتدئ',
                    prayer_total INTEGER NOT NULL DEFAULT 0,
                    quran_pages_total INTEGER NOT NULL DEFAULT 0,
                    quran_khatmas_total INTEGER NOT NULL DEFAULT 0,
                    exercise_total INTEGER NOT NULL DEFAULT 0,
                    water_cups_total INTEGER NOT NULL DEFAULT 0,
                    tasks_done_total INTEGER NOT NULL DEFAULT 0,
                    morning_adhkar_total INTEGER NOT NULL DEFAULT 0,
                    evening_adhkar_total INTEGER NOT NULL DEFAULT 0,
                    weight_last REAL,
                    weight_last_at TEXT
                );

                CREATE TABLE IF NOT EXISTS point_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    points INTEGER NOT NULL,
                    payload TEXT,
                    event_date TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS daily_stats (
                    telegram_id INTEGER NOT NULL,
                    stat_date TEXT NOT NULL,
                    prayers_done INTEGER NOT NULL DEFAULT 0,
                    quran_pages INTEGER NOT NULL DEFAULT 0,
                    quran_khatmas INTEGER NOT NULL DEFAULT 0,
                    morning_adhkar INTEGER NOT NULL DEFAULT 0,
                    evening_adhkar INTEGER NOT NULL DEFAULT 0,
                    exercises INTEGER NOT NULL DEFAULT 0,
                    water_cups INTEGER NOT NULL DEFAULT 0,
                    tasks_done INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (telegram_id, stat_date)
                );

                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    due_date TEXT,
                    recurrence TEXT NOT NULL DEFAULT 'once',
                    remind_time TEXT,
                    points INTEGER NOT NULL DEFAULT 25,
                    is_completed INTEGER NOT NULL DEFAULT 0,
                    last_completed_date TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS goals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    target_value INTEGER NOT NULL,
                    current_value INTEGER NOT NULL DEFAULT 0,
                    shared INTEGER NOT NULL DEFAULT 0,
                    is_completed INTEGER NOT NULL DEFAULT 0,
                    created_by INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS weight_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL,
                    weight REAL NOT NULL,
                    note TEXT,
                    measured_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS exercise_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL,
                    description TEXT NOT NULL,
                    minutes INTEGER,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS water_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL,
                    cups INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS quran_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL,
                    pages INTEGER NOT NULL,
                    note TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS achievements (
                    telegram_id INTEGER NOT NULL,
                    code TEXT NOT NULL,
                    title TEXT NOT NULL,
                    emoji TEXT NOT NULL,
                    achieved_at TEXT NOT NULL,
                    PRIMARY KEY (telegram_id, code)
                );
                """
            )

    def register_user(self, user) -> None:
        now = self.now().isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO users (
                    telegram_id, username, first_name, last_name, joined_at, last_seen_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(telegram_id) DO UPDATE SET
                    username=excluded.username,
                    first_name=excluded.first_name,
                    last_name=excluded.last_name,
                    last_seen_at=excluded.last_seen_at
                """,
                (
                    user.id,
                    getattr(user, "username", None),
                    getattr(user, "first_name", None),
                    getattr(user, "last_name", None),
                    now,
                    now,
                ),
            )

    def _ensure_daily_row(self, conn: sqlite3.Connection, user_id: int, stat_date: str) -> None:
        conn.execute(
            """
            INSERT OR IGNORE INTO daily_stats (telegram_id, stat_date)
            VALUES (?, ?)
            """,
            (user_id, stat_date),
        )

    def _get_user(self, conn: sqlite3.Connection, user_id: int) -> dict | None:
        row = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (user_id,)).fetchone()
        return _row_to_dict(row)

    def _update_user(self, conn: sqlite3.Connection, user_id: int, **updates) -> None:
        if not updates:
            return
        columns = ", ".join(f"{column} = ?" for column in updates)
        values = list(updates.values()) + [user_id]
        conn.execute(f"UPDATE users SET {columns} WHERE telegram_id = ?", values)

    def _record_points(
        self,
        conn: sqlite3.Connection,
        user_id: int,
        event_type: str,
        source: str,
        points: int,
        payload: dict | None = None,
        stat_date: str | None = None,
    ) -> None:
        stat_date = stat_date or self.today()
        now = self.now().isoformat()
        conn.execute(
            """
            INSERT INTO point_events (
                telegram_id, event_type, source, points, payload, event_date, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, event_type, source, points, json.dumps(payload or {}, ensure_ascii=False), stat_date, now),
        )
        conn.execute(
            """
            UPDATE users
            SET total_points = total_points + ?,
                last_seen_at = ?
            WHERE telegram_id = ?
            """,
            (points, now, user_id),
        )

    def _update_streak(self, conn: sqlite3.Connection, user_id: int, active_date: str) -> None:
        user = self._get_user(conn, user_id)
        if not user:
            return

        last_active_date = user.get("last_active_date")
        current_streak = int(user.get("current_streak") or 0)
        active_day = date.fromisoformat(active_date)

        if last_active_date == active_date:
            next_streak = current_streak
        elif last_active_date:
            previous_day = active_day - timedelta(days=1)
            if last_active_date == previous_day.isoformat():
                next_streak = current_streak + 1
            else:
                next_streak = 1
        else:
            next_streak = 1

        best_streak = max(int(user.get("best_streak") or 0), next_streak)
        level_name = level_from_points(int(user.get("total_points") or 0))["name"]
        conn.execute(
            """
            UPDATE users
            SET current_streak = ?,
                best_streak = ?,
                last_active_date = ?,
                level_name = ?
            WHERE telegram_id = ?
            """,
            (next_streak, best_streak, active_date, level_name, user_id),
        )

    def _evaluate_achievements(self, conn: sqlite3.Connection, user_id: int) -> list[dict]:
        user = self._get_user(conn, user_id)
        if not user:
            return []

        unlocked: list[dict] = []
        checks = [
            ("first_exercise", int(user.get("exercise_total") or 0) >= 1),
            ("first_khatma", int(user.get("quran_khatmas_total") or 0) >= 1),
            ("streak_7", int(user.get("current_streak") or 0) >= 7),
            ("streak_30", int(user.get("current_streak") or 0) >= 30),
            ("points_1000", int(user.get("total_points") or 0) >= 1000),
            ("points_5000", int(user.get("total_points") or 0) >= 5000),
        ]

        now = self.now().isoformat()
        for code, condition in checks:
            if not condition:
                continue
            achievement = ACHIEVEMENTS[code]
            existing = conn.execute(
                "SELECT 1 FROM achievements WHERE telegram_id = ? AND code = ?",
                (user_id, code),
            ).fetchone()
            if existing:
                continue
            conn.execute(
                """
                INSERT INTO achievements (telegram_id, code, title, emoji, achieved_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, code, achievement["title"], achievement["emoji"], now),
            )
            unlocked.append(achievement)
        return unlocked

    def _daily_summary_from_conn(
        self,
        conn: sqlite3.Connection,
        user_id: int,
        stat_date: str,
    ) -> dict:
        stat_row = conn.execute(
            """
            SELECT * FROM daily_stats
            WHERE telegram_id = ? AND stat_date = ?
            """,
            (user_id, stat_date),
        ).fetchone()
        point_row = conn.execute(
            """
            SELECT COALESCE(SUM(points), 0) AS points
            FROM point_events
            WHERE telegram_id = ? AND event_date = ?
            """,
            (user_id, stat_date),
        ).fetchone()
        user = self._get_user(conn, user_id) or {}
        stats = _row_to_dict(stat_row) or {
            "prayers_done": 0,
            "quran_pages": 0,
            "quran_khatmas": 0,
            "morning_adhkar": 0,
            "evening_adhkar": 0,
            "exercises": 0,
            "water_cups": 0,
            "tasks_done": 0,
        }
        active = sum(
            int(stats[key])
            for key in [
                "prayers_done",
                "quran_pages",
                "quran_khatmas",
                "morning_adhkar",
                "evening_adhkar",
                "exercises",
                "water_cups",
                "tasks_done",
            ]
        )
        return {
            **stats,
            "points": int(point_row["points"]) if point_row else 0,
            "effective_streak": int(user.get("current_streak") or 0) if active else 0,
        }

    def _apply_activity(
        self,
        user_id: int,
        *,
        event_type: str,
        source: str,
        points: int,
        stat_fields: dict[str, int] | None = None,
        counter_updates: dict[str, int | float] | None = None,
        payload: dict | None = None,
        stat_date: str | None = None,
    ) -> dict:
        stat_date = stat_date or self.today()
        stat_fields = stat_fields or {}
        counter_updates = counter_updates or {}

        with self._connect() as conn:
            self._ensure_daily_row(conn, user_id, stat_date)
            for field, value in stat_fields.items():
                conn.execute(
                    f"""
                    UPDATE daily_stats
                    SET {field} = {field} + ?
                    WHERE telegram_id = ? AND stat_date = ?
                    """,
                    (value, user_id, stat_date),
                )

            if counter_updates:
                assignments = ", ".join(f"{field} = {field} + ?" for field in counter_updates)
                conn.execute(
                    f"""
                    UPDATE users
                    SET {assignments}
                    WHERE telegram_id = ?
                    """,
                    (*counter_updates.values(), user_id),
                )

            self._record_points(conn, user_id, event_type, source, points, payload=payload, stat_date=stat_date)
            self._update_streak(conn, user_id, stat_date)
            level_name = level_from_points(self._get_user(conn, user_id)["total_points"])["name"]
            conn.execute("UPDATE users SET level_name = ? WHERE telegram_id = ?", (level_name, user_id))
            unlocked = self._evaluate_achievements(conn, user_id)
            user = self._get_user(conn, user_id)
            return {
                "points": points,
                "user": user,
                "achievements": unlocked,
                "daily": self._daily_summary_from_conn(conn, user_id, stat_date),
            }

    def record_prayer(self, user_id: int, prayer_name: str) -> dict:
        return self._apply_activity(
            user_id,
            event_type="prayer",
            source=f"صلاة {prayer_name}",
            points=POINTS["prayer"],
            stat_fields={"prayers_done": 1},
            counter_updates={"prayer_total": 1},
            payload={"prayer": prayer_name},
        )

    def record_adhkar(self, user_id: int, period: str) -> dict:
        field = "morning_adhkar" if period == "morning" else "evening_adhkar"
        total_field = "morning_adhkar_total" if period == "morning" else "evening_adhkar_total"
        points_key = "morning_adhkar" if period == "morning" else "evening_adhkar"
        source = "أذكار الصباح" if period == "morning" else "أذكار المساء"
        return self._apply_activity(
            user_id,
            event_type=f"{period}_adhkar",
            source=source,
            points=POINTS[points_key],
            stat_fields={field: 1},
            counter_updates={total_field: 1},
        )

    def record_quran_pages(self, user_id: int, pages: int, note: str | None = None) -> dict:
        with self._connect() as conn:
            user = self._get_user(conn, user_id)
            if not user:
                return {"points": 0, "user": None, "achievements": [], "daily": {}}

            stat_date = self.today()
            self._ensure_daily_row(conn, user_id, stat_date)
            conn.execute(
                """
                INSERT INTO quran_logs (telegram_id, pages, note, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, pages, note, self.now().isoformat()),
            )
            conn.execute(
                """
                UPDATE daily_stats
                SET quran_pages = quran_pages + ?
                WHERE telegram_id = ? AND stat_date = ?
                """,
                (pages, user_id, stat_date),
            )

            old_pages = int(user.get("quran_pages_total") or 0)
            old_khatmas = int(user.get("quran_khatmas_total") or 0)
            new_pages = old_pages + pages
            new_khatmas = new_pages // QURAN_PAGE_PER_KHATMA
            bonus_khatmas = max(0, new_khatmas - old_khatmas)
            points = pages * POINTS["quran_page"] + bonus_khatmas * POINTS["quran_khatma"]

            conn.execute(
                """
                UPDATE users
                SET quran_pages_total = ?,
                    quran_khatmas_total = quran_khatmas_total + ?
                WHERE telegram_id = ?
                """,
                (new_pages, bonus_khatmas, user_id),
            )

            if bonus_khatmas:
                conn.execute(
                    """
                    UPDATE daily_stats
                    SET quran_khatmas = quran_khatmas + ?
                    WHERE telegram_id = ? AND stat_date = ?
                    """,
                    (bonus_khatmas, user_id, stat_date),
                )

            self._record_points(
                conn,
                user_id,
                "quran",
                "قراءة القرآن",
                points,
                payload={"pages": pages, "khatmas": bonus_khatmas},
                stat_date=stat_date,
            )
            self._update_streak(conn, user_id, stat_date)
            level_name = level_from_points(self._get_user(conn, user_id)["total_points"])["name"]
            conn.execute("UPDATE users SET level_name = ? WHERE telegram_id = ?", (level_name, user_id))
            unlocked = self._evaluate_achievements(conn, user_id)
            user = self._get_user(conn, user_id)
            return {
                "points": points,
                "pages": pages,
                "bonus_khatmas": bonus_khatmas,
                "user": user,
                "achievements": unlocked,
                "daily": self._daily_summary_from_conn(conn, user_id, stat_date),
            }

    def record_exercise(self, user_id: int, description: str, minutes: int | None = None) -> dict:
        with self._connect() as conn:
            now = self.now().isoformat()
            conn.execute(
                """
                INSERT INTO exercise_logs (telegram_id, description, minutes, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, description, minutes, now),
            )
        return self._apply_activity(
            user_id,
            event_type="exercise",
            source="تسجيل تمرين",
            points=POINTS["exercise"],
            stat_fields={"exercises": 1},
            counter_updates={"exercise_total": 1},
            payload={"description": description, "minutes": minutes},
        )

    def record_weight(self, user_id: int, weight: float, note: str | None = None) -> dict:
        now = self.now().isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO weight_logs (telegram_id, weight, note, measured_at)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, weight, note, now),
            )
            conn.execute(
                """
                UPDATE users
                SET weight_last = ?, weight_last_at = ?
                WHERE telegram_id = ?
                """,
                (weight, now, user_id),
            )
        return {"weight": weight, "measured_at": now}

    def record_water(self, user_id: int, cups: int) -> dict:
        with self._connect() as conn:
            now = self.now().isoformat()
            conn.execute(
                """
                INSERT INTO water_logs (telegram_id, cups, created_at)
                VALUES (?, ?, ?)
                """,
                (user_id, cups, now),
            )
        return self._apply_activity(
            user_id,
            event_type="water",
            source="شرب الماء",
            points=cups * POINTS["water_cup"],
            stat_fields={"water_cups": cups},
            counter_updates={"water_cups_total": cups},
            payload={"cups": cups},
        )

    def add_note(self, user_id: int, title: str, content: str) -> dict:
        now = self.now().isoformat()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO notes (telegram_id, title, content, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, title, content, now, now),
            )
            return {"id": cursor.lastrowid, "telegram_id": user_id, "title": title, "content": content, "updated_at": now}

    def list_notes(self, user_id: int) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM notes
                WHERE telegram_id = ?
                ORDER BY updated_at DESC, id DESC
                """,
                (user_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_note(self, user_id: int, note_id: int) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM notes WHERE telegram_id = ? AND id = ?",
                (user_id, note_id),
            ).fetchone()
            return _row_to_dict(row)

    def update_note(self, user_id: int, note_id: int, title: str, content: str) -> dict | None:
        now = self.now().isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE notes
                SET title = ?, content = ?, updated_at = ?
                WHERE telegram_id = ? AND id = ?
                """,
                (title, content, now, user_id, note_id),
            )
            return {"id": note_id, "telegram_id": user_id, "title": title, "content": content, "updated_at": now}

    def delete_note(self, user_id: int, note_id: int) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM notes WHERE telegram_id = ? AND id = ?",
                (user_id, note_id),
            )
            return cursor.rowcount > 0

    def add_task(
        self,
        user_id: int,
        title: str,
        due_date: str | None,
        recurrence: str,
        points: int,
        remind_time: str | None,
    ) -> dict:
        now = self.now().isoformat()
        recurrence = normalize_recurrence(recurrence)
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO tasks (
                    telegram_id, title, due_date, recurrence, remind_time, points, is_completed,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)
                """,
                (user_id, title, due_date, recurrence, remind_time, points, now, now),
            )
            return {
                "id": cursor.lastrowid,
                "telegram_id": user_id,
                "title": title,
                "due_date": due_date,
                "recurrence": recurrence,
                "remind_time": remind_time,
                "points": points,
                "is_completed": 0,
                "last_completed_date": None,
                "created_at": now,
                "updated_at": now,
            }

    def list_tasks(self, user_id: int, include_completed: bool = True) -> list[dict]:
        query = "SELECT * FROM tasks WHERE telegram_id = ?"
        params: list = [user_id]
        if not include_completed:
            query += " AND is_completed = 0"
        query += " ORDER BY COALESCE(due_date, '2999-12-31') ASC, id DESC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def get_task(self, user_id: int, task_id: int) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM tasks WHERE telegram_id = ? AND id = ?",
                (user_id, task_id),
            ).fetchone()
            return _row_to_dict(row)

    def update_task(
        self,
        user_id: int,
        task_id: int,
        title: str,
        due_date: str | None,
        recurrence: str,
        points: int,
        remind_time: str | None,
    ) -> dict | None:
        now = self.now().isoformat()
        recurrence = normalize_recurrence(recurrence)
        original = self.get_task(user_id, task_id) or {}
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE tasks
                SET title = ?, due_date = ?, recurrence = ?, points = ?, remind_time = ?, updated_at = ?
                WHERE telegram_id = ? AND id = ?
                """,
                (title, due_date, recurrence, points, remind_time, now, user_id, task_id),
            )
            return {
                "id": task_id,
                "telegram_id": user_id,
                "title": title,
                "due_date": due_date,
                "recurrence": recurrence,
                "remind_time": remind_time,
                "points": points,
                "is_completed": int(original.get("is_completed") or 0),
                "last_completed_date": original.get("last_completed_date"),
                "created_at": original.get("created_at"),
                "updated_at": now,
            }

    def delete_task(self, user_id: int, task_id: int) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM tasks WHERE telegram_id = ? AND id = ?",
                (user_id, task_id),
            )
            return cursor.rowcount > 0

    def complete_task(self, user_id: int, task_id: int) -> dict:
        task = self.get_task(user_id, task_id)
        if not task:
            return {"ok": False, "reason": "not_found"}
        if int(task["is_completed"] or 0) == 1:
            return {"ok": False, "reason": "already_completed"}

        now = self.now().isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE tasks
                SET is_completed = 1,
                    last_completed_date = ?,
                    updated_at = ?
                WHERE telegram_id = ? AND id = ?
                """,
                (self.today(), now, user_id, task_id),
            )

        result = self._apply_activity(
            user_id,
            event_type="task",
            source=f"إكمال مهمة: {task['title']}",
            points=int(task["points"] or POINTS["task"]),
            stat_fields={"tasks_done": 1},
            counter_updates={"tasks_done_total": 1},
            payload={"task_id": task_id, "title": task["title"]},
        )
        task["is_completed"] = 1
        task["last_completed_date"] = self.today()
        task["updated_at"] = now
        result["task"] = task
        return result

    def reset_recurring_tasks(self, reference_date: str | None = None) -> int:
        reference = date.fromisoformat(reference_date or self.today())
        count = 0
        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE tasks SET is_completed = 0 WHERE recurrence = 'daily'",
            )
            count += cursor.rowcount or 0
            if reference.weekday() == 0:
                cursor = conn.execute(
                    "UPDATE tasks SET is_completed = 0 WHERE recurrence = 'weekly'",
                )
                count += cursor.rowcount or 0
        return count

    def due_tasks(self, user_id: int, current_date: str | None = None) -> list[dict]:
        today = current_date or self.today()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM tasks
                WHERE telegram_id = ?
                  AND (
                    (recurrence = 'once' AND is_completed = 0 AND (due_date IS NULL OR due_date <= ?))
                    OR (recurrence IN ('daily', 'weekly') AND is_completed = 0)
                  )
                ORDER BY CASE WHEN due_date IS NULL THEN 1 ELSE 0 END, due_date ASC, id DESC
                """,
                (user_id, today),
            ).fetchall()
            return [dict(row) for row in rows]

    def add_goal(
        self,
        user_id: int,
        title: str,
        description: str,
        target_value: int,
        shared: bool,
    ) -> dict:
        now = self.now().isoformat()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO goals (
                    telegram_id, title, description, target_value, current_value, shared,
                    is_completed, created_by, created_at, updated_at
                ) VALUES (?, ?, ?, ?, 0, ?, 0, ?, ?, ?)
                """,
                (user_id, title, description, target_value, 1 if shared else 0, user_id, now, now),
            )
            return {
                "id": cursor.lastrowid,
                "telegram_id": user_id,
                "title": title,
                "description": description,
                "target_value": target_value,
                "current_value": 0,
                "shared": 1 if shared else 0,
                "is_completed": 0,
                "created_by": user_id,
                "created_at": now,
                "updated_at": now,
            }

    def list_goals(self, user_id: int) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM goals
                WHERE telegram_id = ? OR shared = 1
                ORDER BY shared DESC, updated_at DESC, id DESC
                """,
                (user_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_goal(self, user_id: int, goal_id: int) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM goals
                WHERE id = ? AND (telegram_id = ? OR shared = 1)
                """,
                (goal_id, user_id),
            ).fetchone()
            return _row_to_dict(row)

    def update_goal(
        self,
        user_id: int,
        goal_id: int,
        title: str,
        description: str,
        target_value: int,
    ) -> dict | None:
        now = self.now().isoformat()
        original = self.get_goal(user_id, goal_id) or {}
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE goals
                SET title = ?, description = ?, target_value = ?, updated_at = ?
                WHERE id = ? AND (telegram_id = ? OR shared = 1)
                """,
                (title, description, target_value, now, goal_id, user_id),
            )
            return {
                "id": goal_id,
                "telegram_id": original.get("telegram_id", user_id),
                "title": title,
                "description": description,
                "target_value": target_value,
                "current_value": int(original.get("current_value") or 0),
                "shared": int(original.get("shared") or 0),
                "is_completed": int(original.get("is_completed") or 0),
                "created_by": int(original.get("created_by") or user_id),
                "created_at": original.get("created_at"),
                "updated_at": now,
            }

    def update_goal_progress(self, user_id: int, goal_id: int, increment: int) -> dict:
        goal = self.get_goal(user_id, goal_id)
        if not goal:
            return {"ok": False, "reason": "not_found"}

        current_value = int(goal["current_value"] or 0) + increment
        target_value = int(goal["target_value"] or 0)
        completed = 1 if current_value >= target_value else 0
        now = self.now().isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE goals
                SET current_value = ?, is_completed = ?, updated_at = ?
                WHERE id = ?
                """,
                (min(current_value, target_value), completed, now, goal_id),
            )
        goal["current_value"] = min(current_value, target_value)
        goal["is_completed"] = completed
        goal["updated_at"] = now
        return {"ok": True, "goal": goal, "completed": bool(completed)}

    def delete_goal(self, user_id: int, goal_id: int) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM goals WHERE id = ? AND (telegram_id = ? OR shared = 1)",
                (goal_id, user_id),
            )
            return cursor.rowcount > 0

    def add_weight(self, user_id: int, weight: float, note: str | None = None) -> dict:
        return self.record_weight(user_id, weight, note)

    def weight_history(self, user_id: int, limit: int = 10) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM weight_logs
                WHERE telegram_id = ?
                ORDER BY measured_at DESC, id DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
            return [dict(row) for row in reversed(rows)]

    def recent_exercises(self, user_id: int, limit: int = 10) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM exercise_logs
                WHERE telegram_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
            return [dict(row) for row in rows]

    def recent_quran(self, user_id: int, limit: int = 10) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM quran_logs
                WHERE telegram_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
            return [dict(row) for row in rows]

    def recent_water(self, user_id: int, limit: int = 10) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM water_logs
                WHERE telegram_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_daily_summary(self, user_id: int, stat_date: str | None = None) -> dict:
        stat_date = stat_date or self.today()
        with self._connect() as conn:
            return self._daily_summary_from_conn(conn, user_id, stat_date)

    def get_user_profile(self, user_id: int) -> dict | None:
        with self._connect() as conn:
            user = self._get_user(conn, user_id)
            if not user:
                return None

            today_summary = self._daily_summary_from_conn(conn, user_id, self.today())
            level = level_from_points(int(user.get("total_points") or 0))
            last_weight_row = conn.execute(
                """
                SELECT weight, measured_at
                FROM weight_logs
                WHERE telegram_id = ?
                ORDER BY measured_at DESC, id DESC
                LIMIT 1
                """,
                (user_id,),
            ).fetchone()

            profile = {
                "telegram_id": user["telegram_id"],
                "display_name": " ".join(
                    piece for piece in [user.get("first_name"), user.get("last_name")] if piece
                )
                or (f"@{user['username']}" if user.get("username") else str(user_id)),
                "total_points": int(user.get("total_points") or 0),
                "level_name": level["name"],
                "current_streak": int(user.get("current_streak") or 0),
                "effective_streak": int(today_summary["effective_streak"]),
                "best_streak": int(user.get("best_streak") or 0),
                "today_activity": sum(
                    int(today_summary[key])
                    for key in [
                        "prayers_done",
                        "quran_pages",
                        "quran_khatmas",
                        "morning_adhkar",
                        "evening_adhkar",
                        "exercises",
                        "water_cups",
                        "tasks_done",
                    ]
                ),
                "today_points": int(today_summary["points"]),
                "prayer_total": int(user.get("prayer_total") or 0),
                "quran_pages_total": int(user.get("quran_pages_total") or 0),
                "quran_khatmas_total": int(user.get("quran_khatmas_total") or 0),
                "exercise_total": int(user.get("exercise_total") or 0),
                "water_cups_total": int(user.get("water_cups_total") or 0),
                "tasks_done_total": int(user.get("tasks_done_total") or 0),
                "morning_adhkar_total": int(user.get("morning_adhkar_total") or 0),
                "evening_adhkar_total": int(user.get("evening_adhkar_total") or 0),
                "last_weight": float(last_weight_row["weight"]) if last_weight_row else user.get("weight_last"),
                "last_weight_at": last_weight_row["measured_at"] if last_weight_row else user.get("weight_last_at"),
            }
            profile["level"] = level
            return profile

    def get_weekly_summary(self, user_id: int, end_date: str | None = None) -> dict:
        end = date.fromisoformat(end_date or self.today())
        start = end - timedelta(days=6)
        start_iso = start.isoformat()
        end_iso = end.isoformat()

        with self._connect() as conn:
            points_row = conn.execute(
                """
                SELECT COALESCE(SUM(points), 0) AS points
                FROM point_events
                WHERE telegram_id = ? AND event_date BETWEEN ? AND ?
                """,
                (user_id, start_iso, end_iso),
            ).fetchone()
            stats_row = conn.execute(
                """
                SELECT
                    COALESCE(SUM(prayers_done), 0) AS prayers_done,
                    COALESCE(SUM(quran_pages), 0) AS quran_pages,
                    COALESCE(SUM(quran_khatmas), 0) AS quran_khatmas,
                    COALESCE(SUM(morning_adhkar), 0) AS morning_adhkar,
                    COALESCE(SUM(evening_adhkar), 0) AS evening_adhkar,
                    COALESCE(SUM(exercises), 0) AS exercises,
                    COALESCE(SUM(water_cups), 0) AS water_cups,
                    COALESCE(SUM(tasks_done), 0) AS tasks_done
                FROM daily_stats
                WHERE telegram_id = ? AND stat_date BETWEEN ? AND ?
                """,
                (user_id, start_iso, end_iso),
            ).fetchone()
            active_days_row = conn.execute(
                """
                SELECT COUNT(*) AS active_days
                FROM daily_stats
                WHERE telegram_id = ?
                  AND stat_date BETWEEN ? AND ?
                  AND (
                    prayers_done > 0 OR quran_pages > 0 OR quran_khatmas > 0 OR
                    morning_adhkar > 0 OR evening_adhkar > 0 OR exercises > 0 OR
                    water_cups > 0 OR tasks_done > 0
                  )
                """,
                (user_id, start_iso, end_iso),
            ).fetchone()
            user = self._get_user(conn, user_id) or {}

        active_days = int(active_days_row["active_days"]) if active_days_row else 0
        return {
            "points": int(points_row["points"]) if points_row else 0,
            "prayers_done": int(stats_row["prayers_done"]) if stats_row else 0,
            "quran_pages": int(stats_row["quran_pages"]) if stats_row else 0,
            "quran_khatmas": int(stats_row["quran_khatmas"]) if stats_row else 0,
            "morning_adhkar": int(stats_row["morning_adhkar"]) if stats_row else 0,
            "evening_adhkar": int(stats_row["evening_adhkar"]) if stats_row else 0,
            "exercises": int(stats_row["exercises"]) if stats_row else 0,
            "water_cups": int(stats_row["water_cups"]) if stats_row else 0,
            "tasks_done": int(stats_row["tasks_done"]) if stats_row else 0,
            "active_days": active_days,
            "adherence": int(round((active_days / 7) * 100)),
            "effective_streak": int(user.get("current_streak") or 0),
            "level_name": level_from_points(int(user.get("total_points") or 0))["name"],
        }

    def get_leaderboard(self, period: str) -> list[dict]:
        today = date.fromisoformat(self.today())
        if period == "week":
            start = (today - timedelta(days=6)).isoformat()
            end = today.isoformat()
        elif period == "month":
            start = today.replace(day=1).isoformat()
            end = today.isoformat()
        else:
            start = "0001-01-01"
            end = today.isoformat()

        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT u.telegram_id, u.username, u.first_name, u.last_name,
                       COALESCE(SUM(p.points), 0) AS points
                FROM users u
                LEFT JOIN point_events p
                    ON p.telegram_id = u.telegram_id
                   AND p.event_date BETWEEN ? AND ?
                GROUP BY u.telegram_id
                ORDER BY points DESC, u.total_points DESC, u.telegram_id ASC
                """,
                (start, end),
            ).fetchall()

        result = []
        for row in rows:
            display_name = " ".join(
                piece for piece in [row["first_name"], row["last_name"]] if piece
            ) or (f"@{row['username']}" if row["username"] else str(row["telegram_id"]))
            result.append(
                {
                    "telegram_id": row["telegram_id"],
                    "display_name": display_name,
                    "points": int(row["points"] or 0),
                }
            )
        return result

    def get_today_task_summary(self, user_id: int) -> list[dict]:
        return self.due_tasks(user_id)

    def reset_inactive_streaks(self, current_date: str | None = None) -> int:
        today = current_date or self.today()
        with self._connect() as conn:
            rows = conn.execute("SELECT telegram_id FROM users").fetchall()
            updated = 0
            for row in rows:
                user_id = int(row["telegram_id"])
                daily = self._daily_summary_from_conn(conn, user_id, today)
                active = sum(
                    int(daily[key])
                    for key in [
                        "prayers_done",
                        "quran_pages",
                        "quran_khatmas",
                        "morning_adhkar",
                        "evening_adhkar",
                        "exercises",
                        "water_cups",
                        "tasks_done",
                    ]
                )
                if active == 0:
                    conn.execute(
                        "UPDATE users SET current_streak = 0 WHERE telegram_id = ?",
                        (user_id,),
                    )
                    updated += 1
            return updated

    def get_due_task_groups(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute("SELECT telegram_id FROM users ORDER BY telegram_id ASC").fetchall()
        groups = []
        for row in rows:
            user_id = int(row["telegram_id"])
            tasks = self.due_tasks(user_id)
            if tasks:
                groups.append({"user_id": user_id, "tasks": tasks})
        return groups
