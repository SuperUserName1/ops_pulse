from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import Settings, get_settings
from app.db.session import get_async_session


async def get_request_id(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None)
    return str(request_id) if request_id else "unknown"


async def get_app_settings() -> Settings:
    return get_settings()


SettingsDep = Annotated[Settings, Depends(get_app_settings)]
DbSessionDep = Annotated[AsyncSession, Depends(get_async_session)]
RequestIdDep = Annotated[str, Depends(get_request_id)]
