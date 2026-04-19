import json
from collections.abc import Generator, Sequence
from typing import Any
from urllib.parse import unquote, urlparse

import pg8000.dbapi

from app.core.config import get_settings

settings = get_settings()

CREATE_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id VARCHAR(36) PRIMARY KEY,
        email VARCHAR(255) UNIQUE NOT NULL,
        password_hash VARCHAR(512) NOT NULL,
        role VARCHAR(32) NOT NULL DEFAULT 'member',
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_users_email ON users (email)",
    """
    CREATE TABLE IF NOT EXISTS secrets (
        id VARCHAR(36) PRIMARY KEY,
        owner_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        name VARCHAR(120) NOT NULL,
        environment VARCHAR(32) NOT NULL DEFAULT 'production',
        description TEXT NULL,
        tags TEXT NOT NULL DEFAULT '[]',
        ciphertext TEXT NOT NULL,
        nonce VARCHAR(128) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_secrets_owner_id ON secrets (owner_id)",
    """
    CREATE TABLE IF NOT EXISTS audit_events (
        id VARCHAR(36) PRIMARY KEY,
        actor_id VARCHAR(36) NULL REFERENCES users(id) ON DELETE SET NULL,
        action VARCHAR(80) NOT NULL,
        target_type VARCHAR(40) NOT NULL,
        target_id VARCHAR(36) NULL,
        ip_address VARCHAR(64) NULL,
        details TEXT NOT NULL DEFAULT '{}',
        occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_audit_events_actor_id ON audit_events (actor_id)",
    "CREATE INDEX IF NOT EXISTS idx_audit_events_action ON audit_events (action)",
]


def _connection_kwargs() -> dict[str, Any]:
    parsed = urlparse(settings.database_url)
    if parsed.scheme not in {"postgresql", "postgresql+pg8000"}:
        raise RuntimeError("DATABASE_URL must use the postgresql+pg8000 scheme.")

    return {
        "user": unquote(parsed.username or ""),
        "password": unquote(parsed.password or ""),
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 5432,
        "database": parsed.path.removeprefix("/") or "thevault",
    }


def connect():
    return pg8000.dbapi.connect(**_connection_kwargs())


def init_db() -> None:
    connection = connect()
    try:
        cursor = connection.cursor()
        for statement in CREATE_STATEMENTS:
            cursor.execute(statement)
        connection.commit()
    finally:
        connection.close()


def get_db() -> Generator[Any, None, None]:
    connection = connect()
    try:
        yield connection
    finally:
        connection.close()


def execute(connection, query: str, params: Sequence[Any] | None = None):
    cursor = connection.cursor()
    cursor.execute(query, tuple(params or ()))
    return cursor


def fetch_one(connection, query: str, params: Sequence[Any] | None = None) -> dict[str, Any] | None:
    cursor = execute(connection, query, params)
    row = cursor.fetchone()
    if row is None:
        return None
    return _row_to_dict(cursor, row)


def fetch_all(connection, query: str, params: Sequence[Any] | None = None) -> list[dict[str, Any]]:
    cursor = execute(connection, query, params)
    rows = cursor.fetchall()
    return [_row_to_dict(cursor, row) for row in rows]


def fetch_value(connection, query: str, params: Sequence[Any] | None = None) -> Any:
    cursor = execute(connection, query, params)
    row = cursor.fetchone()
    if row is None:
        return None
    return row[0]


def deserialize_json(value: str | None, default: Any) -> Any:
    if not value:
        return default
    return json.loads(value)


def serialize_json(value: Any) -> str:
    return json.dumps(value if value is not None else {}, separators=(",", ":"))


def _row_to_dict(cursor, row: Sequence[Any]) -> dict[str, Any]:
    columns = [column[0] for column in cursor.description]
    return dict(zip(columns, row, strict=False))
