import hashlib
import hmac


def verify_password(plain_password: str, stored_password_hash: str) -> bool:
    """
    Проверяет введённый пароль по сохранённому хешу.

    Формат хеша:
    pbkdf2_sha256$iterations$salt$hash
    """
    try:
        algorithm, iterations, salt, password_hash = stored_password_hash.split("$")
    except ValueError:
        return False

    if algorithm != "pbkdf2_sha256":
        return False

    new_hash = hashlib.pbkdf2_hmac(
        "sha256",
        plain_password.encode("utf-8"),
        salt.encode("utf-8"),
        int(iterations)
    ).hex()

    return hmac.compare_digest(new_hash, password_hash)