import secrets
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request
from starlette import status

from app.core.errors import AppException
from app.core.settings import Settings, get_settings
from app.schemas.auth import RoleLiteral
from app.services.auth import (
    AuthenticatedUser,
    AuthService,
    get_auth_service,
)


def validate_bearer_token(
    token: str | None,
    expected_token: str | None,
) -> None:
    if not expected_token:
        return

    if not token:
        raise AppException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="unauthorized",
            message="Missing bearer token.",
        )

    if not secrets.compare_digest(token, expected_token):
        raise AppException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="unauthorized",
            message="Invalid bearer token.",
        )


async def get_settings_dep() -> Settings:
    return get_settings()


async def get_auth_service_dep() -> AuthService:
    return get_auth_service()


async def get_bearer_token(request: Request) -> str:
    authorization = request.headers.get("Authorization")
    if not authorization:
        raise AppException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="unauthorized",
            message="Missing Authorization header.",
        )

    scheme, _, value = authorization.partition(" ")
    if scheme.lower() != "bearer" or not value:
        raise AppException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="unauthorized",
            message="Invalid Authorization header format.",
        )
    return value.strip()


async def require_api_token(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings_dep)],
) -> None:
    authorization = request.headers.get("Authorization")
    scheme, _, value = (authorization or "").partition(" ")
    token = value.strip() if scheme.lower() == "bearer" and value else None
    validate_bearer_token(token=token, expected_token=settings.api_token)


async def current_user(
    request: Request,
    token: Annotated[str, Depends(get_bearer_token)],
    auth_service: Annotated[AuthService, Depends(get_auth_service_dep)],
) -> AuthenticatedUser:
    user = auth_service.decode_access_token(token)
    request.state.user_id = user.id
    request.state.org_id = user.org_id
    request.state.user_role = user.role
    return user


CurrentUserDep = Annotated[AuthenticatedUser, Depends(current_user)]


async def current_org(user: CurrentUserDep) -> str:
    return user.org_id


CurrentOrgDep = Annotated[str, Depends(current_org)]


def require_role(*allowed_roles: RoleLiteral) -> Callable[..., object]:
    async def dependency(user: CurrentUserDep) -> AuthenticatedUser:
        if user.role not in allowed_roles:
            raise AppException(
                status_code=status.HTTP_403_FORBIDDEN,
                code="forbidden",
                message="Insufficient role for this operation.",
            )
        return user

    return dependency
