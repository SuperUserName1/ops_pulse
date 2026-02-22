from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from starlette import status

from app.core.rate_limit import (
    RateLimiter,
    get_rate_limiter_dep,
    rate_limit_dependency,
)
from app.core.security import (
    CurrentOrgDep,
    CurrentUserDep,
    get_auth_service_dep,
    require_role,
)
from app.schemas.auth import (
    CurrentUserResponse,
    LoginRequest,
    RefreshRequest,
    TokenPairResponse,
    UsersListResponse,
)
from app.schemas.common import StandardListFilters, StatusFilterLiteral
from app.services.auth import AuthenticatedUser, AuthService

router = APIRouter(prefix="/auth")

AuthServiceDep = Annotated[AuthService, Depends(get_auth_service_dep)]
RateLimiterDep = Annotated[RateLimiter, Depends(get_rate_limiter_dep)]

_LOGIN_EXAMPLE = {
    "token_type": "bearer",
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "access_expires_in": 900,
    "refresh_expires_in": 604800,
    "user": {
        "id": "usr-admin-1",
        "org_id": "org-acme",
        "username": "admin",
        "full_name": "Admin User",
        "role": "admin",
        "status": "active",
        "created_at": "2025-01-10T12:00:00Z",
    },
}


@router.post(
    "/login",
    response_model=TokenPairResponse,
    tags=["auth"],
    summary="Login with username and password",
    description=(
        "Authenticates an active user and returns JWT access/refresh tokens. "
        "Refresh tokens use rotation on `/v1/auth/refresh`."
    ),
    responses={
        200: {
            "description": "Login successful",
            "content": {"application/json": {"example": _LOGIN_EXAMPLE}},
        },
        401: {"description": "Invalid credentials"},
        429: {"description": "Rate limited"},
        503: {"description": "Rate limit backend unavailable"},
    },
)
async def login(
    payload: LoginRequest,
    auth_service: AuthServiceDep,
    _: Annotated[None, Depends(rate_limit_dependency("auth_login", fail_closed=True))],
) -> TokenPairResponse:
    user = auth_service.authenticate(payload.username, payload.password)
    return auth_service.issue_token_pair(user)


@router.post(
    "/refresh",
    response_model=TokenPairResponse,
    tags=["auth"],
    summary="Refresh token pair with rotation",
    description="Rotates the provided refresh token and returns a new access/refresh pair.",
)
async def refresh(
    request: Request,
    payload: RefreshRequest,
    auth_service: AuthServiceDep,
    limiter: RateLimiterDep,
) -> TokenPairResponse:
    user_id = auth_service.peek_refresh_subject(payload.refresh_token)
    await limiter.enforce(
        request=request,
        scope="auth_refresh",
        user_id=user_id,
        fail_closed=True,
    )
    return auth_service.rotate_refresh_token(payload.refresh_token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["auth"],
    summary="Logout current user",
    description="Revokes all active refresh tokens for the current user.",
)
async def logout(
    user: CurrentUserDep,
    auth_service: AuthServiceDep,
    _: Annotated[
        None,
        Depends(
            rate_limit_dependency(
                "auth_logout",
                fail_closed=True,
                include_user_id_from_request=True,
            )
        ),
    ],
) -> Response:
    auth_service.revoke_user_refresh_tokens(user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/me",
    response_model=CurrentUserResponse,
    tags=["auth"],
    summary="Get current user context",
)
async def get_me(user: CurrentUserDep, auth_service: AuthServiceDep) -> CurrentUserResponse:
    user_record = auth_service.get_user_for_org(user_id=user.id, org_id=user.org_id)
    return CurrentUserResponse(user=auth_service.to_public_user(user_record))


@router.get(
    "/users/{user_id}",
    response_model=CurrentUserResponse,
    tags=["users"],
    summary="Get user by id within current organization",
)
async def get_user_by_id(
    user_id: str,
    _admin: Annotated[AuthenticatedUser, Depends(require_role("admin"))],
    org_id: CurrentOrgDep,
    auth_service: AuthServiceDep,
) -> CurrentUserResponse:
    user = auth_service.get_user_for_org(user_id=user_id, org_id=org_id)
    return CurrentUserResponse(user=auth_service.to_public_user(user))


@router.get(
    "/users",
    response_model=UsersListResponse,
    tags=["users"],
    summary="List users with standard pagination and filters",
    description=(
        "Admin-only endpoint using the standard list contract: "
        "`items`, `total`, `limit`, `offset` plus filters "
        "`search`, `status`, `created_from`, `created_to`."
    ),
)
async def list_users(
    _admin: Annotated[AuthenticatedUser, Depends(require_role("admin"))],
    org_id: CurrentOrgDep,
    auth_service: AuthServiceDep,
    __: Annotated[
        None,
        Depends(
            rate_limit_dependency(
                "auth_users",
                fail_closed=True,
                include_user_id_from_request=True,
            )
        ),
    ],
    limit: int = Query(default=20, ge=1, le=100, description="Page size"),
    offset: int = Query(default=0, ge=0, description="Offset from start"),
    search: str | None = Query(default=None, min_length=1, max_length=100),
    status_filter: StatusFilterLiteral | None = Query(default=None, alias="status"),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
) -> UsersListResponse:
    filters = StandardListFilters(
        search=search,
        status=status_filter,
        created_from=created_from,
        created_to=created_to,
    )
    items, total = auth_service.list_users(
        org_id=org_id,
        filters=filters,
        limit=limit,
        offset=offset,
    )
    return UsersListResponse(items=items, total=total, limit=limit, offset=offset)
