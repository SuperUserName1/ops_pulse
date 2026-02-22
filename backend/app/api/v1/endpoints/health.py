from fastapi import APIRouter

from app.core.deps import RequestIdDep, SettingsDep
from app.schemas.health import HealthResponse
from app.services.health import build_health_response

router = APIRouter()

_HEALTH_EXAMPLE = {
    "status": "ok",
    "service": "Ops Pulse API",
    "version": "0.1.0",
    "environment": "local",
    "request_id": "req-example-123",
    "timestamp": "2026-02-22T12:00:00Z",
}


@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["health"],
    summary="Health check",
    description=(
        "Returns service liveness metadata and the propagated `X-Request-ID` for tracing."
    ),
    responses={
        200: {
            "description": "Service is healthy",
            "content": {"application/json": {"example": _HEALTH_EXAMPLE}},
        }
    },
)
async def get_health(request_id: RequestIdDep, settings: SettingsDep) -> HealthResponse:
    return build_health_response(request_id=request_id, settings=settings)
