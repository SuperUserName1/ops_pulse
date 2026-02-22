from fastapi import FastAPI

from app.api.v1.router import api_v1_router
from app.core.errors import register_exception_handlers
from app.core.middleware import RequestIdMiddleware
from app.core.settings import get_settings

OPENAPI_TAGS = [
    {
        "name": "health",
        "description": "Liveness/readiness checks and basic service metadata.",
    },
    {
        "name": "auth",
        "description": "Authentication, token refresh rotation, and role-aware user context.",
    },
    {
        "name": "users",
        "description": "User directory endpoints with standard pagination and filters.",
    },
    {
        "name": "tasks",
        "description": (
            "Tenant-scoped task CRUD endpoints with pagination, filters, and assignee support."
        ),
    },
    {
        "name": "dashboard",
        "description": "Aggregated tenant metrics for the ops dashboard UI.",
    },
]


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.api_version,
        description=(
            "Ops Pulse API.\n\n"
            "Includes request-id propagation, unified error responses, and a typed API layout."
        ),
        openapi_tags=OPENAPI_TAGS,
    )

    app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(app)
    app.include_router(api_v1_router, prefix="/v1")

    return app


app = create_app()
