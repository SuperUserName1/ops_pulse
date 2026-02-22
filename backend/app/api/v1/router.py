from fastapi import APIRouter

from app.api.v1.endpoints import auth, dashboard, health, tasks

api_v1_router = APIRouter()
api_v1_router.include_router(auth.router)
api_v1_router.include_router(dashboard.router)
api_v1_router.include_router(tasks.router)
api_v1_router.include_router(health.router)
