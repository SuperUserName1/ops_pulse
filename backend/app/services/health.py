from datetime import UTC, datetime

from app.core.settings import Settings
from app.schemas.health import HealthResponse


def build_health_response(*, request_id: str, settings: Settings) -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.api_version,
        environment=settings.app_env,
        request_id=request_id,
        timestamp=datetime.now(UTC),
    )
