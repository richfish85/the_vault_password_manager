from typing import Any
from uuid import uuid4

from app.core.config import get_settings
from app.db.redis_client import get_redis_client
from app.db.session import fetch_one, fetch_value

settings = get_settings()


def get_user_by_email(db, email: str) -> dict[str, Any] | None:
    return fetch_one(
        db,
        """
        SELECT id, email, password_hash, role, is_active, created_at, updated_at
        FROM users
        WHERE email = %s
        """,
        (email,),
    )


def get_user_by_id(db, user_id: str) -> dict[str, Any] | None:
    return fetch_one(
        db,
        """
        SELECT id, email, password_hash, role, is_active, created_at, updated_at
        FROM users
        WHERE id = %s
        """,
        (user_id,),
    )


def count_users(db) -> int:
    return int(fetch_value(db, "SELECT COUNT(*) FROM users") or 0)


def create_user(db, *, email: str, password_hash: str, role: str) -> dict[str, Any]:
    return fetch_one(
        db,
        """
        INSERT INTO users (id, email, password_hash, role, is_active)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id, email, role, is_active, created_at, updated_at
        """,
        (str(uuid4()), email, password_hash, role, True),
    )


def blacklist_token(jti: str, expires_in: int) -> None:
    if expires_in <= 0:
        return

    redis_client = get_redis_client()
    if redis_client is None:
        return

    try:
        redis_client.setex(f"{settings.token_blacklist_prefix}:{jti}", expires_in, "1")
    except Exception:
        return


def is_token_blacklisted(jti: str) -> bool:
    redis_client = get_redis_client()
    if redis_client is None:
        return False

    try:
        return bool(redis_client.exists(f"{settings.token_blacklist_prefix}:{jti}"))
    except Exception:
        return False
