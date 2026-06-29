import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "users.db"


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    Получает пользователя из SQLite по email.
    Используется при POST /login.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, email, password_hash, role, is_active
        FROM users
        WHERE email = ?;
    """, (email,))

    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    return dict(row)


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Получает пользователя из SQLite по user_id.
    Используется при проверке JWT-токена для POST /ask.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, email, role, is_active
        FROM users
        WHERE id = ?;
    """, (user_id,))

    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    return dict(row)