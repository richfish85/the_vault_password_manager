from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas.secret import SecretCreate, SecretDetail, SecretSummary, SecretUpdate
from app.services.audit_service import record_audit_event
from app.services.request_context import get_client_ip
from app.services.secrets_service import (
    create_secret,
    delete_secret,
    get_secret_for_user,
    list_secrets as fetch_secrets,
    secret_to_detail,
    secret_to_summary,
    update_secret,
)

router = APIRouter()


@router.get("", response_model=list[SecretSummary])
def list_secrets(
    current_user: dict[str, Any] = Depends(get_current_user),
    db=Depends(get_db),
) -> list[SecretSummary]:
    secrets = fetch_secrets(db, current_user=current_user)
    return [secret_to_summary(secret) for secret in secrets]


@router.post("", response_model=SecretSummary, status_code=status.HTTP_201_CREATED)
def create_secret_entry(
    payload: SecretCreate,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),
    db=Depends(get_db),
) -> SecretSummary:
    secret = create_secret(db, owner=current_user, payload=payload)
    record_audit_event(
        db,
        actor_id=current_user["id"],
        action="secret.create",
        target_type="secret",
        target_id=secret["id"],
        ip_address=get_client_ip(request),
        details={"environment": secret["environment"]},
    )
    db.commit()
    return secret_to_summary(secret)


@router.get("/{secret_id}", response_model=SecretDetail)
def read_secret_entry(
    secret_id: str,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),
    db=Depends(get_db),
) -> SecretDetail:
    secret = get_secret_for_user(db, secret_id=secret_id, current_user=current_user)
    if secret is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Secret not found.")

    record_audit_event(
        db,
        actor_id=current_user["id"],
        action="secret.read",
        target_type="secret",
        target_id=secret["id"],
        ip_address=get_client_ip(request),
    )
    db.commit()
    return secret_to_detail(secret)


@router.patch("/{secret_id}", response_model=SecretSummary)
def update_secret_entry(
    secret_id: str,
    payload: SecretUpdate,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),
    db=Depends(get_db),
) -> SecretSummary:
    secret = get_secret_for_user(db, secret_id=secret_id, current_user=current_user)
    if secret is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Secret not found.")

    updated_secret = update_secret(db, secret_id=secret_id, payload=payload)
    if updated_secret is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Secret not found.")

    record_audit_event(
        db,
        actor_id=current_user["id"],
        action="secret.update",
        target_type="secret",
        target_id=updated_secret["id"],
        ip_address=get_client_ip(request),
        details={"environment": updated_secret["environment"]},
    )
    db.commit()
    return secret_to_summary(updated_secret)


@router.delete("/{secret_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_secret_entry(
    secret_id: str,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),
    db=Depends(get_db),
) -> Response:
    secret = get_secret_for_user(db, secret_id=secret_id, current_user=current_user)
    if secret is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Secret not found.")

    record_audit_event(
        db,
        actor_id=current_user["id"],
        action="secret.delete",
        target_type="secret",
        target_id=secret["id"],
        ip_address=get_client_ip(request),
        details={"name": secret["name"]},
    )
    delete_secret(db, secret_id=secret_id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
