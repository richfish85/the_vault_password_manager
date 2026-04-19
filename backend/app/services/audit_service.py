from typing import Any
from uuid import uuid4

from app.db.session import fetch_all, fetch_one, serialize_json, deserialize_json


def record_audit_event(
    db,
    *,
    action: str,
    target_type: str,
    actor_id: str | None = None,
    target_id: str | None = None,
    ip_address: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    event = fetch_one(
        db,
        """
        INSERT INTO audit_events (id, actor_id, action, target_type, target_id, ip_address, details)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id, actor_id, action, target_type, target_id, ip_address, details, occurred_at
        """,
        (
            str(uuid4()),
            actor_id,
            action,
            target_type,
            target_id,
            ip_address,
            serialize_json(details or {}),
        ),
    )
    if event is None:
        raise RuntimeError("Failed to persist audit event.")
    event["details"] = deserialize_json(event.get("details"), {})
    return event


def list_audit_events(db, *, actor_id: str | None, include_all: bool, limit: int) -> list[dict[str, Any]]:
    if include_all:
        rows = fetch_all(
            db,
            """
            SELECT
                audit_events.id,
                audit_events.action,
                audit_events.target_type,
                audit_events.target_id,
                audit_events.ip_address,
                audit_events.details,
                audit_events.occurred_at,
                users.email AS actor_email
            FROM audit_events
            LEFT JOIN users ON users.id = audit_events.actor_id
            ORDER BY audit_events.occurred_at DESC
            LIMIT %s
            """,
            (limit,),
        )
    else:
        rows = fetch_all(
            db,
            """
            SELECT
                audit_events.id,
                audit_events.action,
                audit_events.target_type,
                audit_events.target_id,
                audit_events.ip_address,
                audit_events.details,
                audit_events.occurred_at,
                users.email AS actor_email
            FROM audit_events
            LEFT JOIN users ON users.id = audit_events.actor_id
            WHERE audit_events.actor_id = %s
            ORDER BY audit_events.occurred_at DESC
            LIMIT %s
            """,
            (actor_id, limit),
        )

    for row in rows:
        row["details"] = deserialize_json(row.get("details"), {})
    return rows
