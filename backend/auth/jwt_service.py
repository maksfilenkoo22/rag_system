import base64
import hashlib
import hmac
import json
import time
from typing import Dict, Any


SECRET_KEY = "dev_secret_key_change_later"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_SECONDS = 60 * 60


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _base64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_access_token(payload: Dict[str, Any]) -> str:
    """
    Создаёт JWT-токен.
    """
    header = {
        "alg": ALGORITHM,
        "typ": "JWT"
    }

    payload = payload.copy()
    payload["exp"] = int(time.time()) + ACCESS_TOKEN_EXPIRE_SECONDS

    encoded_header = _base64url_encode(
        json.dumps(header, separators=(",", ":")).encode("utf-8")
    )

    encoded_payload = _base64url_encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    )

    signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")

    signature = hmac.new(
        SECRET_KEY.encode("utf-8"),
        signing_input,
        hashlib.sha256
    ).digest()

    encoded_signature = _base64url_encode(signature)

    return f"{encoded_header}.{encoded_payload}.{encoded_signature}"


def verify_access_token(token: str) -> Dict[str, Any] | None:
    """
    Проверяет JWT-токен и возвращает payload.
    Если токен некорректный или истёк — возвращает None.
    """
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".")
    except ValueError:
        return None

    signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")

    expected_signature = hmac.new(
        SECRET_KEY.encode("utf-8"),
        signing_input,
        hashlib.sha256
    ).digest()

    expected_encoded_signature = _base64url_encode(expected_signature)

    if not hmac.compare_digest(expected_encoded_signature, encoded_signature):
        return None

    payload = json.loads(_base64url_decode(encoded_payload))

    if payload.get("exp", 0) < int(time.time()):
        return None

    return payload