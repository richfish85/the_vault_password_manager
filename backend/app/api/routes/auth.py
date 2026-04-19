from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials

from app.api.deps import bearer_scheme, get_current_user, get_token_payload
from app.core.security import TokenPayload, create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.schemas.auth import (
    LoginRequest,
    LogoutResponse,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.audit_service import record_audit_event
from app.services.auth_service import blacklist_token, count_users, create_user, get_user_by_email
from app.services.request_context import get_client_ip

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(
    payload: RegisterRequest,
    request: Request,
    db=Depends(get_db),
) -> UserResponse:
    existing_user = get_user_by_email(db, payload.email)
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that email already exists.",
        )

    is_first_user = count_users(db) == 0
    role = "admin" if is_first_user else "member"
    user = create_user(
        db,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=role,
    )
    record_audit_event(
        db,
        actor_id=user["id"],
        action="auth.register",
        target_type="user",
        target_id=user["id"],
        ip_address=get_client_ip(request),
        details={"role": role},
    )
    db.commit()
    return UserResponse.parse_obj(user)


@router.post("/login", response_model=TokenResponse)
def login_user(
    payload: LoginRequest,
    request: Request,
    db=Depends(get_db),
) -> TokenResponse:
    user = get_user_by_email(db, payload.email)
    if user is None or not verify_password(payload.password, user["password_hash"]):
        record_audit_event(
            db,
            actor_id=user["id"] if user else None,
            action="auth.login_failed",
            target_type="user",
            target_id=user["id"] if user else None,
            ip_address=get_client_ip(request),
            details={"email": payload.email},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )

    token, expires_at = create_access_token(subject=user["id"], role=user["role"])
    record_audit_event(
        db,
        actor_id=user["id"],
        action="auth.login",
        target_type="user",
        target_id=user["id"],
        ip_address=get_client_ip(request),
    )
    db.commit()

    expires_in = max(int((expires_at - datetime.now(UTC)).total_seconds()), 1)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in,
        user=UserResponse.parse_obj(user),
    )


@router.post("/logout", response_model=LogoutResponse)
def logout_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    token_payload: TokenPayload = Depends(get_token_payload),
    current_user: dict[str, Any] = Depends(get_current_user),
    db=Depends(get_db),
) -> LogoutResponse:
    expires_in = max(token_payload.exp - int(datetime.now(UTC).timestamp()), 1)
    if credentials is not None:
        blacklist_token(token_payload.jti, expires_in)
    record_audit_event(
        db,
        actor_id=current_user["id"],
        action="auth.logout",
        target_type="user",
        target_id=current_user["id"],
        ip_address=get_client_ip(request),
        details={"scheme": credentials.scheme if credentials else "unknown"},
    )
    db.commit()
    return LogoutResponse(message="Session revoked.")


@router.get("/me", response_model=UserResponse)
def read_current_user(current_user: dict[str, Any] = Depends(get_current_user)) -> UserResponse:
    return UserResponse.parse_obj(current_user)
