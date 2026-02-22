from __future__ import annotations

import importlib
from collections.abc import Callable
from dataclasses import dataclass
from time import time
from typing import Annotated, Any, Protocol, cast

from fastapi import Depends, Request
from starlette import status

from app.core.errors import AppException
from app.core.settings import Settings, get_settings

try:
    redis_asyncio_module: Any | None = importlib.import_module("redis.asyncio")
except Exception:  # pragma: no cover - import failure only matters at runtime
    redis_asyncio_module = None


class RedisRateLimitClient(Protocol):
    async def incr(self, name: str) -> int: ...
    async def expire(self, name: str, time: int) -> bool: ...


class RateLimitStoreUnavailable(Exception):
    pass


@dataclass(frozen=True, slots=True)
class RateLimitWindow:
    name: str
    seconds: int
    limit: int


class RedisRateLimitStore:
    def __init__(
        self,
        client: RedisRateLimitClient,
        *,
        key_prefix: str = "ops_pulse:rl",
    ) -> None:
        self.client = client
        self.key_prefix = key_prefix

    async def consume(self, *, scope: str, identity: str, window: RateLimitWindow) -> int:
        bucket = int(time()) // window.seconds
        key = f"{self.key_prefix}:{scope}:{window.name}:{bucket}:{identity}"
        try:
            count = await self.client.incr(key)
            if count == 1:
                await self.client.expire(key, window.seconds + 1)
        except Exception as exc:  # pragma: no cover - concrete backend errors vary
            raise RateLimitStoreUnavailable("Rate limit backend unavailable.") from exc
        return count


class RateLimiter:
    def __init__(
        self,
        *,
        enabled: bool,
        store: RedisRateLimitStore | None,
        per_second: int,
        per_minute: int,
    ) -> None:
        self.enabled = enabled
        self.store = store
        self.windows = (
            RateLimitWindow(name="1s", seconds=1, limit=per_second),
            RateLimitWindow(name="1m", seconds=60, limit=per_minute),
        )

    async def enforce(
        self,
        *,
        request: Request,
        scope: str,
        user_id: str | None = None,
        fail_closed: bool = True,
    ) -> None:
        if not self.enabled:
            return

        if self.store is None:
            if fail_closed:
                raise AppException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    code="rate_limit_backend_unavailable",
                    message="Rate limit backend is unavailable.",
                )
            return

        client_host = request.client.host if request.client is not None else "unknown"
        identities = [f"ip:{client_host}"]
        if user_id:
            identities.append(f"user:{user_id}")

        try:
            for identity in identities:
                for window in self.windows:
                    count = await self.store.consume(
                        scope=scope,
                        identity=identity,
                        window=window,
                    )
                    if count > window.limit:
                        raise AppException(
                            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            code="rate_limited",
                            message=(
                                "Rate limit exceeded "
                                f"({window.limit} requests/{window.seconds}s) for {scope}."
                            ),
                        )
        except RateLimitStoreUnavailable as exc:
            if fail_closed:
                raise AppException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    code="rate_limit_backend_unavailable",
                    message="Rate limit backend is unavailable.",
                ) from exc


_RATE_LIMITER: RateLimiter | None = None
_REDIS_CLIENT: RedisRateLimitClient | None = None


def _build_redis_client(settings: Settings) -> RedisRateLimitClient | None:
    if not settings.rate_limit_enabled:
        return None
    if not settings.rate_limit_redis_url:
        return None
    if redis_asyncio_module is None:
        return None
    return cast(
        RedisRateLimitClient,
        redis_asyncio_module.from_url(settings.rate_limit_redis_url, decode_responses=True),
    )


def get_rate_limiter() -> RateLimiter:
    global _RATE_LIMITER, _REDIS_CLIENT
    if _RATE_LIMITER is None:
        settings = get_settings()
        _REDIS_CLIENT = _build_redis_client(settings)
        store = (
            RedisRateLimitStore(_REDIS_CLIENT)
            if _REDIS_CLIENT is not None and settings.rate_limit_enabled
            else None
        )
        _RATE_LIMITER = RateLimiter(
            enabled=settings.rate_limit_enabled,
            store=store,
            per_second=settings.rate_limit_per_second,
            per_minute=settings.rate_limit_per_minute,
        )
    return _RATE_LIMITER


def reset_rate_limit_singletons() -> None:
    global _RATE_LIMITER, _REDIS_CLIENT
    _RATE_LIMITER = None
    _REDIS_CLIENT = None


async def get_rate_limiter_dep() -> RateLimiter:
    return get_rate_limiter()


def rate_limit_dependency(
    scope: str,
    *,
    fail_closed: bool = True,
    include_user_id_from_request: bool = False,
) -> Callable[..., object]:
    async def dependency(
        request: Request,
        limiter: Annotated[RateLimiter, Depends(get_rate_limiter_dep)],
    ) -> None:
        request_user_id = getattr(request.state, "user_id", None)
        user_id = (
            str(request_user_id)
            if include_user_id_from_request and request_user_id
            else None
        )
        await limiter.enforce(
            request=request,
            scope=scope,
            user_id=user_id,
            fail_closed=fail_closed,
        )

    return dependency
