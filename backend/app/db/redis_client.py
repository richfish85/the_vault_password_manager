from functools import lru_cache

from redis import Redis

from app.core.config import get_settings

settings = get_settings()


@lru_cache
def get_redis_client() -> Redis | None:
    try:
        return Redis.from_url(settings.redis_url, decode_responses=True)
    except Exception:
        return None


def ping_redis() -> bool:
    redis_client = get_redis_client()
    if redis_client is None:
        return False

    try:
        return bool(redis_client.ping())
    except Exception:
        return False
