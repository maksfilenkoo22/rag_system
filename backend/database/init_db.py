import sqlite3
import hashlib
import secrets
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "users.db"


def hash_password(password: str) -> str:
    """
    Создаёт хеш пароля через PBKDF2-SHA256.
    В БД хранится не пароль, а строка вида:
    pbkdf2_sha256$iterations$salt$hash
    """
    iterations = 100_000
    salt = secrets.token_hex(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations
    ).hex()

    return f"pbkdf2_sha256${iterations}${salt}${password_hash}"


def create_database() -> None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1
    );
    """)

    test_users = [
        {
            "email": "student@test.local",
            "password": "student123",
            "role": "student",
            "is_active": 1
        },
        {
            "email": "teacher@test.local",
            "password": "teacher123",
            "role": "teacher",
            "is_active": 1
        },
        {
            "email": "inactive@test.local",
            "password": "inactive123",
            "role": "student",
            "is_active": 0
        }
    ]

    for user in test_users:
        password_hash = hash_password(user["password"])

        cursor.execute("""
        INSERT OR IGNORE INTO users (
            email,
            password_hash,
            role,
            is_active
        )
        VALUES (?, ?, ?, ?);
        """, (
            user["email"],
            password_hash,
            user["role"],
            user["is_active"]
        ))

    conn.commit()

    cursor.execute("SELECT id, email, role, is_active FROM users;")
    rows = cursor.fetchall()

    print(f"База данных создана: {DB_PATH}")
    print("Пользователи в базе:")

    for row in rows:
        print(row)

    conn.close()


if __name__ == "__main__":
    create_database()