from functools import lru_cache

from pydantic import BaseSettings


class Settings(BaseSettings):
    app_name: str = "TheVault API"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    frontend_origin: str = "http://localhost:3000"
    database_url: str = "postgresql+pg8000://postgres:postgres@localhost:5432/thevault"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret_key: str = "unsafe-dev-jwt-secret-change-me"
    encryption_key: str = "unsafe-dev-encryption-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    rate_limit_per_minute: int = 120
    audit_log_limit: int = 100
    token_blacklist_prefix: str = "thevault:blacklist"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origin.split(",") if origin.strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
