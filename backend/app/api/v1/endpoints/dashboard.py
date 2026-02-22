from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.deps import DbSessionDep
from app.core.rate_limit import rate_limit_dependency
from app.core.security import CurrentOrgDep, CurrentUserDep, get_auth_service_dep
from app.schemas.dashboard import DashboardSummaryResponse
from app.services.auth import AuthService
from app.services.demo_directory import ensure_demo_directory_seeded
from app.services.tasks import build_dashboard_summary

router = APIRouter(prefix="/dashboard")

AuthServiceDep = Annotated[AuthService, Depends(get_auth_service_dep)]


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    tags=["dashboard"],
    summary="Get tenant dashboard summary",
)
async def get_dashboard_summary(
    user: CurrentUserDep,
    org_id: CurrentOrgDep,
    session: DbSessionDep,
    auth_service: AuthServiceDep,
    _: Annotated[
        None,
        Depends(
            rate_limit_dependency(
                "dashboard_summary",
                fail_closed=True,
                include_user_id_from_request=True,
            )
        ),
    ],
) -> DashboardSummaryResponse:
    del user
    await ensure_demo_directory_seeded(session, auth_service)
    return await build_dashboard_summary(session, org_id=org_id)
