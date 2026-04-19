from datetime import datetime

from pydantic import BaseModel, Field, validator


def _normalize_tags(tags: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        cleaned = tag.strip().lower()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            normalized.append(cleaned)
    return normalized


class SecretCreate(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    value: str = Field(min_length=1, max_length=8192)
    environment: str = Field(default="production", min_length=2, max_length=32)
    description: str | None = Field(default=None, max_length=1000)
    tags: list[str] = Field(default_factory=list)

    @validator("tags")
    def normalize_tags(cls, value: list[str]) -> list[str]:
        return _normalize_tags(value)


class SecretUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=120)
    value: str | None = Field(default=None, min_length=1, max_length=8192)
    environment: str | None = Field(default=None, min_length=2, max_length=32)
    description: str | None = Field(default=None, max_length=1000)
    tags: list[str] | None = None

    @validator("tags")
    def normalize_tags(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return _normalize_tags(value)


class SecretSummary(BaseModel):
    id: str
    name: str
    environment: str
    description: str | None
    tags: list[str]
    owner_email: str
    updated_at: datetime

    class Config:
        orm_mode = True


class SecretDetail(SecretSummary):
    value: str
