from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.audit import AuditEventResponse
from app.services.audit_service import list_audit_events as fetch_audit_events

router = APIRouter()
settings = get_settings()


@router.get("", response_model=list[AuditEventResponse])
def list_audit_events(
    current_user: dict[str, Any] = Depends(get_current_user),
    db=Depends(get_db),
) -> list[AuditEventResponse]:
    events = fetch_audit_events(
        db,
        actor_id=current_user["id"],
        include_all=current_user["role"] == "admin",
        limit=settings.audit_log_limit,
    )
    return [AuditEventResponse(**event) for event in events]
