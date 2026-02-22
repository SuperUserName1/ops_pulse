from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import OffsetPaginationMeta

RoleLiteral = Literal["admin", "agent", "viewer"]
UserStatusLiteral = Literal["active", "disabled"]


class UserPublic(BaseModel):
    id: str = Field(..., examples=["usr-admin-1"])
    org_id: str = Field(..., examples=["org-acme"])
    username: str = Field(..., examples=["admin"])
    full_name: str = Field(..., examples=["Admin User"])
    role: RoleLiteral = Field(..., examples=["admin"])
    status: UserStatusLiteral = Field(..., examples=["active"])
    created_at: datetime = Field(..., description="User creation timestamp (UTC)")


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64, examples=["admin"])
    password: str = Field(..., min_length=1, max_length=128, examples=["admin123"])


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=16, description="Refresh JWT")


class TokenPairResponse(BaseModel):
    token_type: Literal["bearer"] = Field(default="bearer")
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    access_expires_in: int = Field(..., ge=1, description="Access token TTL in seconds")
    refresh_expires_in: int = Field(..., ge=1, description="Refresh token TTL in seconds")
    user: UserPublic


class CurrentUserResponse(BaseModel):
    user: UserPublic


class UsersListResponse(OffsetPaginationMeta):
    items: list[UserPublic]
