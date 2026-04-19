from fastapi import APIRouter

from app.api.routes import audit, auth, health, secrets

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(secrets.router, prefix="/secrets", tags=["secrets"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
