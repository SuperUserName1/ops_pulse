from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError
from starlette import status

from app.core.errors import AppException
from app.core.settings import Settings, get_settings
from app.schemas.auth import (
    RoleLiteral,
    TokenPairResponse,
    UserPublic,
    UserStatusLiteral,
)
from app.schemas.common import StandardListFilters


@dataclass(frozen=True, slots=True)
class UserRecord:
    id: str
    org_id: str
    username: str
    full_name: str
    role: RoleLiteral
    status: UserStatusLiteral
    created_at: datetime
    password_salt: str
    password_hash: str


@dataclass(slots=True)
class RefreshTokenState:
    jti: str
    user_id: str
    expires_at: datetime
    revoked: bool = False
    rotated_to_jti: str | None = None


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    id: str
    org_id: str
    username: str
    full_name: str
    role: RoleLiteral
    status: UserStatusLiteral

    def to_public(self, created_at: datetime) -> UserPublic:
        return UserPublic(
            id=self.id,
            org_id=self.org_id,
            username=self.username,
            full_name=self.full_name,
            role=self.role,
            status=self.status,
            created_at=created_at,
        )


def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000,
    ).hex()


class AuthService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._users_by_username = self._build_users()
        self._users_by_id = {user.id: user for user in self._users_by_username.values()}
        self._refresh_states: dict[str, RefreshTokenState] = {}

    def reset_state(self) -> None:
        self._refresh_states.clear()

    def _build_users(self) -> dict[str, UserRecord]:
        raw_users: list[
            tuple[
                str,
                str,
                str,
                str,
                RoleLiteral,
                UserStatusLiteral,
                str,
                str,
            ]
        ] = [
            (
                "usr-admin-1",
                "org-acme",
                "admin",
                "Admin User",
                "admin",
                "active",
                "2025-01-10T12:00:00Z",
                "admin123",
            ),
            (
                "usr-agent-1",
                "org-acme",
                "agent",
                "Agent One",
                "agent",
                "active",
                "2025-01-15T12:00:00Z",
                "agent123",
            ),
            (
                "usr-viewer-1",
                "org-acme",
                "viewer",
                "Viewer One",
                "viewer",
                "active",
                "2025-01-20T12:00:00Z",
                "viewer123",
            ),
            (
                "usr-agent-2",
                "org-acme",
                "agent2",
                "Agent Two",
                "agent",
                "disabled",
                "2025-01-25T12:00:00Z",
                "agent123",
            ),
            (
                "usr-viewer-2",
                "org-beta",
                "auditor",
                "Audit Viewer",
                "viewer",
                "active",
                "2025-02-01T08:30:00Z",
                "viewer123",
            ),
            (
                "usr-agent-3",
                "org-beta",
                "ops-bot",
                "Ops Bot",
                "agent",
                "active",
                "2025-02-05T09:45:00Z",
                "agent123",
            ),
        ]
        users: dict[str, UserRecord] = {}
        for (
            user_id,
            org_id,
            username,
            full_name,
            role,
            user_status,
            created_at_raw,
            password,
        ) in raw_users:
            salt = f"salt-{username}"
            users[username] = UserRecord(
                id=user_id,
                org_id=org_id,
                username=username,
                full_name=full_name,
                role=role,
                status=user_status,
                created_at=datetime.fromisoformat(created_at_raw.replace("Z", "+00:00")),
                password_salt=salt,
                password_hash=_hash_password(password, salt),
            )
        return users

    def get_user_by_username(self, username: str) -> UserRecord | None:
        return self._users_by_username.get(username)

    def get_user_by_id(self, user_id: str) -> UserRecord | None:
        return self._users_by_id.get(user_id)

    def _validate_password(self, user: UserRecord, password: str) -> bool:
        candidate_hash = _hash_password(password, user.password_salt)
        return secrets.compare_digest(candidate_hash, user.password_hash)

    def authenticate(self, username: str, password: str) -> UserRecord:
        user = self.get_user_by_username(username)
        if user is None or user.status != "active" or not self._validate_password(user, password):
            raise AppException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                code="invalid_credentials",
                message="Invalid username or password.",
            )
        return user

    def list_users(
        self,
        *,
        org_id: str,
        filters: StandardListFilters,
        limit: int,
        offset: int,
    ) -> tuple[list[UserPublic], int]:
        if (
            filters.created_from
            and filters.created_to
            and filters.created_from > filters.created_to
        ):
            raise AppException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                code="invalid_filters",
                message="`created_from` must be less than or equal to `created_to`.",
            )

        users = [user for user in self._users_by_username.values() if user.org_id == org_id]

        if filters.search:
            needle = filters.search.casefold()
            users = [
                user
                for user in users
                if needle in user.username.casefold() or needle in user.full_name.casefold()
            ]

        if filters.status:
            users = [user for user in users if user.status == filters.status]

        if filters.created_from:
            users = [user for user in users if user.created_at >= filters.created_from]

        if filters.created_to:
            users = [user for user in users if user.created_at <= filters.created_to]

        users.sort(key=lambda user: user.created_at)
        total = len(users)
        page = users[offset : offset + limit]

        return [self.to_public_user(user) for user in page], total

    def to_public_user(self, user: UserRecord) -> UserPublic:
        return UserPublic(
            id=user.id,
            org_id=user.org_id,
            username=user.username,
            full_name=user.full_name,
            role=user.role,
            status=user.status,
            created_at=user.created_at,
        )

    def get_user_for_org(self, *, user_id: str, org_id: str) -> UserRecord:
        user = self.get_user_by_id(user_id)
        if user is None or user.org_id != org_id:
            raise AppException(
                status_code=status.HTTP_404_NOT_FOUND,
                code="not_found",
                message="User not found.",
            )
        return user

    def _access_ttl(self) -> timedelta:
        return timedelta(minutes=self.settings.jwt_access_ttl_minutes)

    def _refresh_ttl(self) -> timedelta:
        return timedelta(days=self.settings.jwt_refresh_ttl_days)

    def _encode_token(
        self,
        *,
        user: UserRecord,
        token_type: str,
        jti: str,
        expires_at: datetime,
        secret: str,
        now: datetime,
    ) -> str:
        payload: dict[str, Any] = {
            "sub": user.id,
            "org_id": user.org_id,
            "username": user.username,
            "role": user.role,
            "status": user.status,
            "token_type": token_type,
            "jti": jti,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
        }
        return str(
            jwt.encode(
                payload,
                secret,
                algorithm=self.settings.jwt_algorithm,
            )
        )

    def create_access_token(
        self,
        user: UserRecord,
        *,
        expires_in: timedelta | None = None,
        now: datetime | None = None,
    ) -> tuple[str, int]:
        issued_at = now or datetime.now(UTC)
        ttl = expires_in or self._access_ttl()
        jti = str(uuid4())
        expires_at = issued_at + ttl
        token = self._encode_token(
            user=user,
            token_type="access",
            jti=jti,
            expires_at=expires_at,
            secret=self.settings.jwt_access_secret,
            now=issued_at,
        )
        return token, int(ttl.total_seconds())

    def create_refresh_token(
        self,
        user: UserRecord,
        *,
        expires_in: timedelta | None = None,
        now: datetime | None = None,
    ) -> tuple[str, int]:
        issued_at = now or datetime.now(UTC)
        ttl = expires_in or self._refresh_ttl()
        jti = str(uuid4())
        expires_at = issued_at + ttl
        token = self._encode_token(
            user=user,
            token_type="refresh",
            jti=jti,
            expires_at=expires_at,
            secret=self.settings.jwt_refresh_secret,
            now=issued_at,
        )
        self._refresh_states[jti] = RefreshTokenState(
            jti=jti,
            user_id=user.id,
            expires_at=expires_at,
        )
        return token, int(ttl.total_seconds())

    def issue_token_pair(self, user: UserRecord) -> TokenPairResponse:
        access_token, access_ttl = self.create_access_token(user)
        refresh_token, refresh_ttl = self.create_refresh_token(user)
        return TokenPairResponse(
            token_type="bearer",
            access_token=access_token,
            refresh_token=refresh_token,
            access_expires_in=access_ttl,
            refresh_expires_in=refresh_ttl,
            user=self.to_public_user(user),
        )

    def _decode_token(
        self,
        *,
        token: str,
        expected_type: str,
        secret: str,
    ) -> dict[str, Any]:
        try:
            payload = jwt.decode(
                token,
                secret,
                algorithms=[self.settings.jwt_algorithm],
                options={"require": ["sub", "org_id", "jti", "exp", "token_type"]},
            )
        except ExpiredSignatureError as exc:
            raise AppException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                code="token_expired",
                message="Token has expired.",
            ) from exc
        except InvalidTokenError as exc:
            raise AppException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                code="invalid_token",
                message="Invalid token.",
            ) from exc

        if payload.get("token_type") != expected_type:
            raise AppException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                code="invalid_token_type",
                message=f"Expected {expected_type} token.",
            )
        return payload

    def decode_access_token(self, token: str) -> AuthenticatedUser:
        payload = self._decode_token(
            token=token,
            expected_type="access",
            secret=self.settings.jwt_access_secret,
        )
        user_id = str(payload["sub"])
        token_org_id = str(payload["org_id"])
        user = self.get_user_by_id(user_id)
        if user is None or user.org_id != token_org_id:
            raise AppException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                code="user_not_found",
                message="User not found for token subject.",
            )
        return AuthenticatedUser(
            id=user.id,
            org_id=token_org_id,
            username=user.username,
            full_name=user.full_name,
            role=user.role,
            status=user.status,
        )

    def peek_refresh_subject(self, token: str) -> str | None:
        try:
            payload = self._decode_token(
                token=token,
                expected_type="refresh",
                secret=self.settings.jwt_refresh_secret,
            )
        except AppException:
            return None
        return str(payload.get("sub"))

    def rotate_refresh_token(self, refresh_token: str) -> TokenPairResponse:
        payload = self._decode_token(
            token=refresh_token,
            expected_type="refresh",
            secret=self.settings.jwt_refresh_secret,
        )
        jti = str(payload["jti"])
        user_id = str(payload["sub"])
        state = self._refresh_states.get(jti)
        if (
            state is None
            or state.user_id != user_id
            or state.revoked
            or state.rotated_to_jti
        ):
            raise AppException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                code="invalid_refresh_token",
                message="Refresh token is invalid, revoked, or already rotated.",
            )

        user = self.get_user_by_id(user_id)
        if user is None:
            raise AppException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                code="user_not_found",
                message="User not found for refresh token subject.",
            )

        new_pair = self.issue_token_pair(user)
        new_payload = self._decode_token(
            token=new_pair.refresh_token,
            expected_type="refresh",
            secret=self.settings.jwt_refresh_secret,
        )
        state.revoked = True
        state.rotated_to_jti = str(new_payload["jti"])
        return new_pair

    def revoke_user_refresh_tokens(self, user_id: str) -> int:
        revoked_count = 0
        for state in self._refresh_states.values():
            if state.user_id == user_id and not state.revoked:
                state.revoked = True
                revoked_count += 1
        return revoked_count


_AUTH_SERVICE: AuthService | None = None


def get_auth_service() -> AuthService:
    global _AUTH_SERVICE
    if _AUTH_SERVICE is None:
        _AUTH_SERVICE = AuthService(get_settings())
    return _AUTH_SERVICE


def reset_auth_service_state() -> None:
    service = get_auth_service()
    service.reset_state()
