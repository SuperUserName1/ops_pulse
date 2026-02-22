from __future__ import annotations

from collections import defaultdict

import pytest
from starlette.requests import Request

import app.core.rate_limit as rate_limit_module
from app.core.rate_limit import (
    RateLimiter,
    RateLimitStoreUnavailable,
    RateLimitWindow,
    RedisRateLimitStore,
)

pytestmark = pytest.mark.anyio


class FakeRedisClient:
    def __init__(self) -> None:
        self.counts: dict[str, int] = defaultdict(int)
        self.expire_calls: list[tuple[str, int]] = []

    async def incr(self, name: str) -> int:
        self.counts[name] += 1
        return self.counts[name]

    async def expire(self, name: str, time: int) -> bool:
        self.expire_calls.append((name, time))
        return True


class FailingRedisClient:
    async def incr(self, name: str) -> int:
        raise RuntimeError(f"boom: {name}")

    async def expire(self, name: str, time: int) -> bool:
        raise RuntimeError(f"boom: {name}:{time}")


def _request() -> Request:
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/test",
        "raw_path": b"/test",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
    }
    request = Request(scope)
    request.state.user_id = "usr-admin-1"
    return request


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _admin_access_token(client) -> str:
    response = await client.post(
        "/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


async def test_redis_store_consume_uses_mocked_redis_client() -> None:
    fake_client = FakeRedisClient()
    store = RedisRateLimitStore(fake_client, key_prefix="test")
    window = RateLimitWindow(name="1s", seconds=1, limit=5)

    count_1 = await store.consume(scope="auth_login", identity="ip:127.0.0.1", window=window)
    count_2 = await store.consume(scope="auth_login", identity="ip:127.0.0.1", window=window)

    assert count_1 == 1
    assert count_2 == 2
    assert len(fake_client.expire_calls) == 1
    assert fake_client.expire_calls[0][1] == 2


async def test_redis_store_wraps_backend_error() -> None:
    store = RedisRateLimitStore(FailingRedisClient())
    window = RateLimitWindow(name="1s", seconds=1, limit=1)

    with pytest.raises(RateLimitStoreUnavailable):
        await store.consume(scope="auth_login", identity="ip:127.0.0.1", window=window)


async def test_rate_limiter_uses_ip_and_user_id_with_mocked_redis_client() -> None:
    fake_client = FakeRedisClient()
    limiter = RateLimiter(
        enabled=True,
        store=RedisRateLimitStore(fake_client, key_prefix="rl"),
        per_second=10,
        per_minute=30,
    )

    await limiter.enforce(request=_request(), scope="auth_users", user_id="usr-admin-1")

    keys = list(fake_client.counts.keys())
    assert any(":ip:127.0.0.1" in key for key in keys)
    assert any(":user:usr-admin-1" in key for key in keys)


async def test_login_returns_503_when_rate_limit_backend_is_unavailable(
    client,
    monkeypatch,
) -> None:
    unavailable_limiter = RateLimiter(enabled=True, store=None, per_second=5, per_minute=30)
    monkeypatch.setattr(rate_limit_module, "get_rate_limiter", lambda: unavailable_limiter)

    response = await client.post(
        "/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "rate_limit_backend_unavailable"


async def test_public_health_returns_503_when_rate_limit_backend_is_unavailable(
    client,
    monkeypatch,
) -> None:
    unavailable_limiter = RateLimiter(enabled=True, store=None, per_second=5, per_minute=30)
    monkeypatch.setattr(rate_limit_module, "get_rate_limiter", lambda: unavailable_limiter)

    response = await client.get("/v1/health")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "rate_limit_backend_unavailable"


async def test_protected_endpoint_rate_limit_receives_user_id(client, monkeypatch) -> None:
    captured: list[str | None] = []

    class CaptureLimiter:
        async def enforce(
            self,
            *,
            request,
            scope: str,
            user_id: str | None = None,
            fail_closed: bool = True,
        ) -> None:
            captured.append(user_id)
            assert scope == "auth_users"
            assert fail_closed is True
            assert getattr(request.state, "user_id", None) == "usr-admin-1"

    token = await _admin_access_token(client)
    monkeypatch.setattr(rate_limit_module, "get_rate_limiter", lambda: CaptureLimiter())
    response = await client.get("/v1/auth/users", headers=_auth_header(token))
    assert response.status_code == 200, response.text
    assert captured and captured[-1] == "usr-admin-1"
