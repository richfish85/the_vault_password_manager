from fastapi import APIRouter, Depends

from app.db.redis_client import ping_redis
from app.db.session import fetch_value, get_db
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("", response_model=HealthResponse)
def health_check(db=Depends(get_db)) -> HealthResponse:
    db_status = "up"
    redis_status = "up"

    try:
        fetch_value(db, "SELECT 1")
    except Exception:
        db_status = "down"

    if not ping_redis():
        redis_status = "down"

    status_value = "ok" if db_status == "up" and redis_status == "up" else "degraded"
    return HealthResponse(
        status=status_value,
        services={
            "database": db_status,
            "redis": redis_status,
        },
    )
