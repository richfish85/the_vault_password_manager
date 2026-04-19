import base64
import hashlib
import hmac
import os
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import uuid4

import jwt
from fastapi import HTTPException, status
from jwt import InvalidTokenError
from pydantic import BaseModel, ValidationError

from app.core.config import get_settings

settings = get_settings()


class TokenPayload(BaseModel):
    sub: str
    role: str
    token_type: Literal["access"]
    jti: str
    exp: int


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    iterations = 390000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return "$".join(
        [
            str(iterations),
            base64.urlsafe_b64encode(salt).decode("utf-8"),
            base64.urlsafe_b64encode(digest).decode("utf-8"),
        ]
    )


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        iterations_raw, salt_raw, digest_raw = encoded_hash.split("$")
        iterations = int(iterations_raw)
        salt = base64.urlsafe_b64decode(salt_raw.encode("utf-8"))
        expected_digest = base64.urlsafe_b64decode(digest_raw.encode("utf-8"))
    except (TypeError, ValueError):
        return False

    actual_digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(actual_digest, expected_digest)


def create_access_token(*, subject: str, role: str) -> tuple[str, datetime]:
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": subject,
        "role": role,
        "token_type": "access",
        "jti": str(uuid4()),
        "iat": int(datetime.now(UTC).timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    encoded = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded, expires_at


def decode_token(token: str) -> TokenPayload:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return TokenPayload.parse_obj(payload)
    except (InvalidTokenError, ValidationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        ) from exc
