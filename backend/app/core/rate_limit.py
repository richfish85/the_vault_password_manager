import asyncio
import hashlib
import math
import time
from threading import Lock

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from app.db.redis_client import get_redis_client


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int) -> None:
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.local_counts: dict[str, tuple[int, float]] = {}
        self.lock = Lock()

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method == "OPTIONS" or request.url.path.endswith("/health"):
            return await call_next(request)

        limit_key = self._build_key(request)
        current_count = await asyncio.to_thread(self._increment, limit_key)
        remaining = max(self.requests_per_minute - current_count, 0)
        retry_after = max(1, math.ceil(60 - (time.time() % 60)))

        headers = {
            "X-RateLimit-Limit": str(self.requests_per_minute),
            "X-RateLimit-Remaining": str(remaining),
            "Retry-After": str(retry_after),
        }
        if current_count > self.requests_per_minute:
            return JSONResponse(
                status_code=429,
                headers=headers,
                content={"detail": "Rate limit exceeded. Try again shortly."},
            )

        response = await call_next(request)
        response.headers.update(headers)
        return response

    def _build_key(self, request: Request) -> str:
        forwarded_for = request.headers.get("x-forwarded-for")
        client_id = forwarded_for.split(",")[0].strip() if forwarded_for else (request.client.host if request.client else "anonymous")
        auth_header = request.headers.get("authorization", "")
        auth_fingerprint = hashlib.sha1(auth_header.encode("utf-8")).hexdigest()[:12] if auth_header else "guest"
        current_window = int(time.time() // 60)
        return f"ratelimit:{request.url.path}:{client_id}:{auth_fingerprint}:{current_window}"

    def _increment(self, limit_key: str) -> int:
        redis_client = get_redis_client()
        if redis_client is not None:
            try:
                current_count = int(redis_client.incr(limit_key))
                if current_count == 1:
                    redis_client.expire(limit_key, 60)
                return current_count
            except Exception:
                pass

        now = time.time()
        with self.lock:
            self.local_counts = {
                key: value
                for key, value in self.local_counts.items()
                if value[1] > now
            }
            current_count, expires_at = self.local_counts.get(limit_key, (0, now + 60))
            current_count += 1
            self.local_counts[limit_key] = (current_count, expires_at)
            return current_count
