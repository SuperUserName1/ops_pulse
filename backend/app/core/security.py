import secrets
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette import status

from app.core.errors import AppException
from app.core.settings import Settings, get_settings

bearer_scheme = HTTPBearer(auto_error=False)


def validate_bearer_token(
    credentials: HTTPAuthorizationCredentials | None,
    expected_token: str | None,
) -> None:
    if not expected_token:
        return

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="unauthorized",
            message="Missing bearer token.",
        )

    if not secrets.compare_digest(credentials.credentials, expected_token):
        raise AppException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="unauthorized",
            message="Invalid bearer token.",
        )


def require_api_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    validate_bearer_token(credentials=credentials, expected_token=settings.api_token)
