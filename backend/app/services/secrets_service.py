from typing import Any
from uuid import uuid4

from app.core.encryption import decrypt_value, encrypt_value
from app.db.session import deserialize_json, execute, fetch_all, fetch_one, serialize_json
from app.schemas.secret import SecretCreate, SecretDetail, SecretSummary, SecretUpdate


def list_secrets(db, *, current_user: dict[str, Any]) -> list[dict[str, Any]]:
    if current_user["role"] == "admin":
        rows = fetch_all(
            db,
            """
            SELECT
                secrets.id,
                secrets.owner_id,
                secrets.name,
                secrets.environment,
                secrets.description,
                secrets.tags,
                secrets.ciphertext,
                secrets.nonce,
                secrets.created_at,
                secrets.updated_at,
                users.email AS owner_email
            FROM secrets
            JOIN users ON users.id = secrets.owner_id
            ORDER BY secrets.updated_at DESC
            """
        )
    else:
        rows = fetch_all(
            db,
            """
            SELECT
                secrets.id,
                secrets.owner_id,
                secrets.name,
                secrets.environment,
                secrets.description,
                secrets.tags,
                secrets.ciphertext,
                secrets.nonce,
                secrets.created_at,
                secrets.updated_at,
                users.email AS owner_email
            FROM secrets
            JOIN users ON users.id = secrets.owner_id
            WHERE secrets.owner_id = %s
            ORDER BY secrets.updated_at DESC
            """,
            (current_user["id"],),
        )

    return [_inflate_secret(row) for row in rows]


def get_secret_for_user(db, *, secret_id: str, current_user: dict[str, Any]) -> dict[str, Any] | None:
    if current_user["role"] == "admin":
        row = fetch_one(
            db,
            """
            SELECT
                secrets.id,
                secrets.owner_id,
                secrets.name,
                secrets.environment,
                secrets.description,
                secrets.tags,
                secrets.ciphertext,
                secrets.nonce,
                secrets.created_at,
                secrets.updated_at,
                users.email AS owner_email
            FROM secrets
            JOIN users ON users.id = secrets.owner_id
            WHERE secrets.id = %s
            """,
            (secret_id,),
        )
    else:
        row = fetch_one(
            db,
            """
            SELECT
                secrets.id,
                secrets.owner_id,
                secrets.name,
                secrets.environment,
                secrets.description,
                secrets.tags,
                secrets.ciphertext,
                secrets.nonce,
                secrets.created_at,
                secrets.updated_at,
                users.email AS owner_email
            FROM secrets
            JOIN users ON users.id = secrets.owner_id
            WHERE secrets.id = %s AND secrets.owner_id = %s
            """,
            (secret_id, current_user["id"]),
        )

    return _inflate_secret(row) if row else None


def create_secret(db, *, owner: dict[str, Any], payload: SecretCreate) -> dict[str, Any]:
    ciphertext, nonce = encrypt_value(payload.value)
    row = fetch_one(
        db,
        """
        INSERT INTO secrets (id, owner_id, name, environment, description, tags, ciphertext, nonce)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id, owner_id, name, environment, description, tags, ciphertext, nonce, created_at, updated_at
        """,
        (
            str(uuid4()),
            owner["id"],
            payload.name.strip(),
            payload.environment.strip().lower(),
            payload.description.strip() if payload.description else None,
            serialize_json(payload.tags),
            ciphertext,
            nonce,
        ),
    )
    if row is None:
        raise RuntimeError("Failed to persist secret.")
    row["owner_email"] = owner["email"]
    return _inflate_secret(row)


def update_secret(db, *, secret_id: str, payload: SecretUpdate) -> dict[str, Any] | None:
    current = fetch_one(
        db,
        """
        SELECT id, owner_id, name, environment, description, tags, ciphertext, nonce, created_at, updated_at
        FROM secrets
        WHERE id = %s
        """,
        (secret_id,),
    )
    if current is None:
        return None

    updated_name = payload.name.strip() if payload.name is not None else current["name"]
    updated_environment = payload.environment.strip().lower() if payload.environment is not None else current["environment"]
    updated_description = (
        payload.description.strip() or None if payload.description is not None else current["description"]
    )
    updated_tags = payload.tags if payload.tags is not None else deserialize_json(current.get("tags"), [])

    ciphertext = current["ciphertext"]
    nonce = current["nonce"]
    if payload.value is not None:
        ciphertext, nonce = encrypt_value(payload.value)

    execute(
        db,
        """
        UPDATE secrets
        SET name = %s,
            environment = %s,
            description = %s,
            tags = %s,
            ciphertext = %s,
            nonce = %s,
            updated_at = NOW()
        WHERE id = %s
        """,
        (
            updated_name,
            updated_environment,
            updated_description,
            serialize_json(updated_tags),
            ciphertext,
            nonce,
            secret_id,
        ),
    )
    owner = fetch_one(db, "SELECT email FROM users WHERE id = %s", (current["owner_id"],))
    refreshed = fetch_one(
        db,
        """
        SELECT id, owner_id, name, environment, description, tags, ciphertext, nonce, created_at, updated_at
        FROM secrets
        WHERE id = %s
        """,
        (secret_id,),
    )
    if refreshed is None:
        return None
    refreshed["owner_email"] = owner["email"] if owner else ""
    return _inflate_secret(refreshed)


def delete_secret(db, *, secret_id: str) -> None:
    execute(db, "DELETE FROM secrets WHERE id = %s", (secret_id,))


def secret_to_summary(secret: dict[str, Any]) -> SecretSummary:
    return SecretSummary(
        id=secret["id"],
        name=secret["name"],
        environment=secret["environment"],
        description=secret.get("description"),
        tags=secret["tags"],
        owner_email=secret["owner_email"],
        updated_at=secret["updated_at"],
    )


def secret_to_detail(secret: dict[str, Any]) -> SecretDetail:
    summary = secret_to_summary(secret)
    return SecretDetail(
        **summary.dict(),
        value=decrypt_value(secret["ciphertext"], secret["nonce"]),
    )


def _inflate_secret(secret: dict[str, Any]) -> dict[str, Any]:
    secret["tags"] = deserialize_json(secret.get("tags"), [])
    return secret
