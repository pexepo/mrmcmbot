import sqlite3
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

DB_PATH = Path(__file__).parent / "bot_data.db"


def init_db():
    """Инициализация базы данных."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Таблица пользователей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_banned INTEGER DEFAULT 0,
            total_submissions INTEGER DEFAULT 0
        )
    """)

    # Таблица логов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_type TEXT,
            user_id INTEGER,
            message TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    """)

    # Таблица медиа
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS media_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            kind TEXT,
            media_type TEXT,
            file_id TEXT,
            caption TEXT,
            social_link TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    """)

    conn.commit()
    conn.close()


def add_or_update_user(
    user_id: int,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
):
    """Добавить или обновить пользователя."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO users (user_id, username, first_name, last_name, last_activity)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id) DO UPDATE SET
            username = excluded.username,
            first_name = excluded.first_name,
            last_name = excluded.last_name,
            last_activity = CURRENT_TIMESTAMP
    """,
        (user_id, username, first_name, last_name),
    )

    conn.commit()
    conn.close()


def increment_user_submissions(user_id: int):
    """Увеличить счетчик отправок пользователя."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE users SET total_submissions = total_submissions + 1
        WHERE user_id = ?
    """,
        (user_id,),
    )

    conn.commit()
    conn.close()


def add_log(log_type: str, message: str, user_id: int | None = None):
    """Добавить лог."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO logs (log_type, user_id, message)
        VALUES (?, ?, ?)
    """,
        (log_type, user_id, message),
    )

    conn.commit()
    conn.close()


def add_media_submission(
    user_id: int,
    kind: str,
    media_type: str,
    file_id: str,
    caption: str | None = None,
    social_link: str | None = None,
):
    """Добавить медиа отправку."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO media_submissions (user_id, kind, media_type, file_id, caption, social_link)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
        (user_id, kind, media_type, file_id, caption, social_link),
    )

    conn.commit()
    conn.close()


def get_all_users() -> List[Dict]:
    """Получить всех пользователей."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT user_id, username, first_name, last_name, first_seen, 
               last_activity, is_banned, total_submissions
        FROM users
        ORDER BY last_activity DESC
    """)

    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return users


def get_active_users(hours: int = 24) -> List[Dict]:
    """Получить активных пользователей за последние N часов."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT user_id, username, first_name, last_name, last_activity, total_submissions
        FROM users
        WHERE datetime(last_activity) >= datetime('now', '-' || ? || ' hours')
        ORDER BY last_activity DESC
    """,
        (hours,),
    )

    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return users


def get_logs(log_type: str | None = None, limit: int = 100) -> List[Dict]:
    """Получить логи."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if log_type:
        cursor.execute(
            """
            SELECT l.*, u.username, u.first_name
            FROM logs l
            LEFT JOIN users u ON l.user_id = u.user_id
            WHERE l.log_type = ?
            ORDER BY l.timestamp DESC
            LIMIT ?
        """,
            (log_type, limit),
        )
    else:
        cursor.execute(
            """
            SELECT l.*, u.username, u.first_name
            FROM logs l
            LEFT JOIN users u ON l.user_id = u.user_id
            ORDER BY l.timestamp DESC
            LIMIT ?
        """,
            (limit,),
        )

    logs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return logs


def get_media_submissions(limit: int = 50) -> List[Dict]:
    """Получить медиа отправки."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT m.*, u.username, u.first_name
        FROM media_submissions m
        LEFT JOIN users u ON m.user_id = u.user_id
        ORDER BY m.timestamp DESC
        LIMIT ?
    """,
        (limit,),
    )

    media = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return media


def get_stats() -> Dict:
    """Получить статистику."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Всего пользователей
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    # Активных за 24 часа
    cursor.execute("""
        SELECT COUNT(*) FROM users
        WHERE datetime(last_activity) >= datetime('now', '-24 hours')
    """)
    active_24h = cursor.fetchone()[0]

    # Всего отправок
    cursor.execute("SELECT SUM(total_submissions) FROM users")
    total_submissions = cursor.fetchone()[0] or 0

    # Забаненных
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_banned = 1")
    banned_users = cursor.fetchone()[0]

    conn.close()

    return {
        "total_users": total_users,
        "active_24h": active_24h,
        "total_submissions": total_submissions,
        "banned_users": banned_users,
    }


# Инициализация при импорте
init_db()
