import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import List, Dict, Optional

# Получаем URL базы данных из переменной окружения
DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection():
    """Получить подключение к базе данных."""
    return psycopg2.connect(DATABASE_URL)


def init_db():
    """Инициализация базы данных."""
    conn = get_connection()
    cursor = conn.cursor()

    # Таблица пользователей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
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
            id SERIAL PRIMARY KEY,
            log_type TEXT,
            user_id BIGINT,
            message TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
        )
    """)

    # Таблица медиа
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS media_submissions (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
            kind TEXT,
            media_type TEXT,
            file_id TEXT,
            caption TEXT,
            social_link TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
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
    conn = get_connection()
    cursor = conn.cursor()

    # Проверяем, существует ли пользователь
    cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
    is_new_user = cursor.fetchone() is None

    cursor.execute(
        """
        INSERT INTO users (user_id, username, first_name, last_name, last_activity)
        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id) DO UPDATE SET
            username = EXCLUDED.username,
            first_name = EXCLUDED.first_name,
            last_name = EXCLUDED.last_name,
            last_activity = CURRENT_TIMESTAMP
    """,
        (user_id, username, first_name, last_name),
    )

    # Логируем нового пользователя
    if is_new_user:
        user_display = f"@{username}" if username else f"{first_name or 'Unknown'}"
        cursor.execute(
            """
            INSERT INTO logs (log_type, user_id, message)
            VALUES (%s, %s, %s)
        """,
            ("new_user", user_id, f"Новый пользователь: {user_display}"),
        )

    conn.commit()
    conn.close()


def increment_user_submissions(user_id: int):
    """Увеличить счетчик отправок пользователя."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE users SET total_submissions = total_submissions + 1
        WHERE user_id = %s
    """,
        (user_id,),
    )

    conn.commit()
    conn.close()


def add_log(log_type: str, message: str, user_id: int | None = None):
    """Добавить лог."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO logs (log_type, user_id, message)
        VALUES (%s, %s, %s)
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
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO media_submissions (user_id, kind, media_type, file_id, caption, social_link)
        VALUES (%s, %s, %s, %s, %s, %s)
    """,
        (user_id, kind, media_type, file_id, caption, social_link),
    )

    conn.commit()
    conn.close()


def get_all_users() -> List[Dict]:
    """Получить всех пользователей."""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

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
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute(
        """
        SELECT user_id, username, first_name, last_name, last_activity, total_submissions
        FROM users
        WHERE last_activity >= NOW() - INTERVAL '%s hours'
        ORDER BY last_activity DESC
    """,
        (hours,),
    )

    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return users


def get_logs(log_type: str | None = None, limit: int = 100) -> List[Dict]:
    """Получить логи."""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    if log_type:
        cursor.execute(
            """
            SELECT l.*, u.username, u.first_name
            FROM logs l
            LEFT JOIN users u ON l.user_id = u.user_id
            WHERE l.log_type = %s
            ORDER BY l.timestamp DESC
            LIMIT %s
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
            LIMIT %s
        """,
            (limit,),
        )

    logs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return logs


def get_media_submissions(limit: int = 50) -> List[Dict]:
    """Получить медиа отправки."""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute(
        """
        SELECT m.*, u.username, u.first_name
        FROM media_submissions m
        LEFT JOIN users u ON m.user_id = u.user_id
        ORDER BY m.timestamp DESC
        LIMIT %s
    """,
        (limit,),
    )

    media = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return media


def get_stats() -> Dict:
    """Получить статистику."""
    conn = get_connection()
    cursor = conn.cursor()

    # Всего пользователей
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    # Активных за 24 часа
    cursor.execute("""
        SELECT COUNT(*) FROM users
        WHERE last_activity >= NOW() - INTERVAL '24 hours'
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


# Инициализация при импорте (только если DATABASE_URL установлен)
if DATABASE_URL:
    try:
        init_db()
        print("✅ PostgreSQL база данных инициализирована")
    except Exception as e:
        print(f"❌ Ошибка инициализации базы данных: {e}")
else:
    print("⚠️ DATABASE_URL не установлен, используется SQLite")
    # Fallback на старый database.py если нужно
