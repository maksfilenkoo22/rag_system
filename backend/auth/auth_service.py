from typing import Dict, Any

from backend.database.users_repository import get_user_by_email, get_user_by_id
from backend.auth.password_service import verify_password
from backend.auth.jwt_service import create_access_token, verify_access_token


def authenticate_user(email: str, password: str) -> Dict[str, Any]:
    """
    Проверяет email и пароль пользователя.
    Если всё корректно — возвращает JWT-токен.
    Используется для POST /login.
    """
    user = get_user_by_email(email)

    if user is None:
        return {
            "success": False,
            "error": "Invalid email or password"
        }

    if not user["is_active"]:
        return {
            "success": False,
            "error": "User is inactive"
        }

    password_is_valid = verify_password(
        plain_password=password,
        stored_password_hash=user["password_hash"]
    )

    if not password_is_valid:
        return {
            "success": False,
            "error": "Invalid email or password"
        }

    token = create_access_token({
        "user_id": user["id"],
        "email": user["email"],
        "role": user["role"]
    })

    return {
        "success": True,
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "role": user["role"]
        }
    }


def check_access_by_token(token: str) -> Dict[str, Any]:
    """
    Проверяет JWT-токен.
    Используется перед обработкой POST /ask.
    """
    payload = verify_access_token(token)

    if payload is None:
        return {
            "access_status": "denied",
            "error": "Invalid or expired token"
        }

    user_id = payload.get("user_id")

    if user_id is None:
        return {
            "access_status": "denied",
            "error": "Token does not contain user_id"
        }

    user = get_user_by_id(user_id)

    if user is None:
        return {
            "access_status": "denied",
            "error": "User not found"
        }

    if not user["is_active"]:
        return {
            "access_status": "denied",
            "error": "User is inactive"
        }

    return {
        "access_status": "allowed",
        "user_id": user["id"],
        "email": user["email"],
        "role": user["role"]
    }