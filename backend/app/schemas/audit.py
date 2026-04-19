from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AuditEventResponse(BaseModel):
    id: str
    action: str
    target_type: str
    target_id: str | None
    ip_address: str | None
    details: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime
    actor_email: str | None = None

    class Config:
        orm_mode = True
