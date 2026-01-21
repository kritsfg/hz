
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Iterable, List, Optional, Sequence, Tuple

from config import settings


@contextmanager
def get_connection():
    database_path = settings.database_path
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                full_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                city TEXT NOT NULL,
                age INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                last_activity_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                value REAL NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_activities_user_category ON activities (user_id, category, created_at)
            """
        )


def add_user(user_id: int, full_name: str, phone: str, city: str, age: int) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO users (user_id, full_name, phone, city, age, status)
            VALUES (?, ?, ?, ?, ?, 'pending')
            ON CONFLICT(user_id) DO UPDATE SET
                full_name = excluded.full_name,
                phone = excluded.phone,
                city = excluded.city,
                age = excluded.age,
                status = 'pending'
            """,
            (user_id, full_name, phone, city, age),
        )


def get_user(user_id: int) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        cursor = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return cursor.fetchone()


def set_user_status(user_id: int, status: str) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE users SET status = ? WHERE user_id = ?", (status, user_id))


def add_activity(user_id: int, category: str, value: float) -> None:
    now = datetime.utcnow().isoformat()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO activities (user_id, category, value, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, category, value, now),
        )
        conn.execute(
            "UPDATE users SET last_activity_at = ? WHERE user_id = ?",
            (now, user_id),
        )


def list_pending_users() -> List[sqlite3.Row]:
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT * FROM users WHERE status = 'pending' ORDER BY created_at ASC"
        )
        return cursor.fetchall()


def list_users_by_status(statuses: Sequence[str]) -> List[sqlite3.Row]:
    placeholders = ",".join(["?"] * len(statuses))
    query = f"SELECT * FROM users WHERE status IN ({placeholders}) ORDER BY created_at DESC"
    with get_connection() as conn:
        cursor = conn.execute(query, tuple(statuses))
        return cursor.fetchall()


def get_leaderboard(category: str, since: Optional[datetime]) -> List[sqlite3.Row]:
    with get_connection() as conn:
        if since:
            cursor = conn.execute(
                """
                SELECT u.full_name, u.city, SUM(a.value) as total
                FROM activities a
                JOIN users u ON u.user_id = a.user_id
                WHERE a.category = ? AND a.created_at >= ? AND u.status = 'approved'
                GROUP BY a.user_id
                ORDER BY total DESC
                LIMIT 10
                """,
                (category, since.isoformat()),
            )
        else:
            cursor = conn.execute(
                """
                SELECT u.full_name, u.city, SUM(a.value) as total
                FROM activities a
                JOIN users u ON u.user_id = a.user_id
                WHERE a.category = ? AND u.status = 'approved'
                GROUP BY a.user_id
                ORDER BY total DESC
                LIMIT 10
                """,
                (category,),
            )
        return cursor.fetchall()


def get_personal_stats(user_id: int, category: str, since: Optional[datetime]) -> float:
    with get_connection() as conn:
        if since:
            cursor = conn.execute(
                """
                SELECT SUM(value) as total
                FROM activities
                WHERE user_id = ? AND category = ? AND created_at >= ?
                """,
                (user_id, category, since.isoformat()),
            )
        else:
            cursor = conn.execute(
                """
                SELECT SUM(value) as total
                FROM activities
                WHERE user_id = ? AND category = ?
                """,
                (user_id, category),
            )
        row = cursor.fetchone()
        return float(row["total"]) if row and row["total"] is not None else 0.0


def get_personal_all_stats(user_id: int) -> List[Tuple[str, str, float]]:
    categories = [
        "pushups",
        "squats",
        "pullups",
        "running",
        "reading",
    ]
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    week = today - timedelta(days=7)
    month = today - timedelta(days=30)

    stats: List[Tuple[str, str, float]] = []
    for period_key, period_name, since in (
        ("day", "За 1 день", today),
        ("week", "За неделю", week),
        ("month", "За месяц", month),
    ):
        for category in categories:
            total = get_personal_stats(user_id, category, since)
            stats.append((category, period_key, total))
    return stats


def format_period(period: str) -> Optional[datetime]:
    now = datetime.utcnow()
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if period == "day":
        return start_of_day
    if period == "week":
        return start_of_day - timedelta(days=7)
    if period == "month":
        return start_of_day - timedelta(days=30)
    if period == "year":
        return start_of_day - timedelta(days=365)
    if period == "all":
        return None
    return None


def get_profile(user_id: int) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        cursor = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return cursor.fetchone()


def get_registered_users(statuses: Sequence[str]) -> Iterable[int]:
    placeholders = ",".join(["?"] * len(statuses))
    query = f"SELECT user_id FROM users WHERE status IN ({placeholders})"
    with get_connection() as conn:
        cursor = conn.execute(query, tuple(statuses))
        for row in cursor.fetchall():
            yield row["user_id"]