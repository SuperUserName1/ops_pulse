from datetime import UTC, datetime, timedelta

import pytest

from app.services.auth import AuthService

pytestmark = pytest.mark.anyio


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _login(client, username: str = "admin", password: str = "admin123") -> dict[str, object]:
    response = await client.post(
        "/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()


async def test_login_success_returns_access_and_refresh(client) -> None:
    payload = await _login(client)
    assert payload["token_type"] == "bearer"
    assert payload["access_token"]
    assert payload["refresh_token"]
    assert payload["access_expires_in"] == 900
    assert payload["refresh_expires_in"] == 604800
    assert payload["user"]["role"] == "admin"
    assert payload["user"]["org_id"] == "org-acme"


async def test_login_invalid_password_returns_401(client) -> None:
    response = await client.post(
        "/v1/auth/login",
        json={"username": "admin", "password": "wrong"},
    )
    assert response.status_code == 401
    payload = response.json()
    assert payload["error"]["code"] == "invalid_credentials"


async def test_login_disabled_user_returns_401(client) -> None:
    response = await client.post(
        "/v1/auth/login",
        json={"username": "agent2", "password": "agent123"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


async def test_me_requires_authorization(client) -> None:
    response = await client.get("/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


async def test_me_returns_current_user(client) -> None:
    tokens = await _login(client, "viewer", "viewer123")
    response = await client.get("/v1/auth/me", headers=_auth_header(tokens["access_token"]))
    assert response.status_code == 200
    payload = response.json()
    assert payload["user"]["username"] == "viewer"
    assert payload["user"]["role"] == "viewer"
    assert payload["user"]["org_id"] == "org-acme"


async def test_admin_endpoint_forbidden_for_viewer(client) -> None:
    tokens = await _login(client, "viewer", "viewer123")
    response = await client.get("/v1/auth/users", headers=_auth_header(tokens["access_token"]))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


async def test_admin_endpoint_access_for_admin(client) -> None:
    tokens = await _login(client, "admin", "admin123")
    response = await client.get("/v1/auth/users", headers=_auth_header(tokens["access_token"]))
    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == {"items", "total", "limit", "offset"}
    assert payload["total"] == 4
    assert {item["org_id"] for item in payload["items"]} == {"org-acme"}


async def test_admin_can_get_user_in_same_org(client) -> None:
    tokens = await _login(client, "admin", "admin123")
    response = await client.get(
        "/v1/auth/users/usr-viewer-1",
        headers=_auth_header(tokens["access_token"]),
    )
    assert response.status_code == 200
    assert response.json()["user"]["org_id"] == "org-acme"


async def test_admin_cannot_access_user_from_other_org(client) -> None:
    tokens = await _login(client, "admin", "admin123")
    response = await client.get(
        "/v1/auth/users/usr-viewer-2",
        headers=_auth_header(tokens["access_token"]),
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


async def test_refresh_success_rotates_refresh_token(client) -> None:
    tokens = await _login(client, "agent", "agent123")
    refresh_response = await client.post(
        "/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refresh_response.status_code == 200
    new_tokens = refresh_response.json()
    assert new_tokens["refresh_token"] != tokens["refresh_token"]
    assert new_tokens["access_token"] != tokens["access_token"]


async def test_refresh_rotation_rejects_reuse_of_old_refresh_token(client) -> None:
    tokens = await _login(client, "agent", "agent123")
    first_refresh = await client.post(
        "/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert first_refresh.status_code == 200

    reuse_response = await client.post(
        "/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert reuse_response.status_code == 401
    assert reuse_response.json()["error"]["code"] == "invalid_refresh_token"


async def test_refresh_rejects_access_token(client) -> None:
    tokens = await _login(client)
    response = await client.post(
        "/v1/auth/refresh",
        json={"refresh_token": tokens["access_token"]},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"


async def test_expired_access_token_is_rejected(client, auth_service: AuthService) -> None:
    user = auth_service.get_user_by_username("admin")
    assert user is not None
    expired_access, _ = auth_service.create_access_token(
        user,
        expires_in=timedelta(seconds=-1),
        now=datetime.now(UTC),
    )
    response = await client.get("/v1/auth/me", headers=_auth_header(expired_access))
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "token_expired"


async def test_expired_refresh_token_is_rejected(client, auth_service: AuthService) -> None:
    user = auth_service.get_user_by_username("admin")
    assert user is not None
    expired_refresh, _ = auth_service.create_refresh_token(
        user,
        expires_in=timedelta(seconds=-1),
        now=datetime.now(UTC),
    )
    response = await client.post(
        "/v1/auth/refresh",
        json={"refresh_token": expired_refresh},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "token_expired"


async def test_logout_revokes_refresh_tokens(client) -> None:
    tokens = await _login(client, "admin", "admin123")
    logout_response = await client.post(
        "/v1/auth/logout",
        headers=_auth_header(tokens["access_token"]),
    )
    assert logout_response.status_code == 204

    refresh_response = await client.post(
        "/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refresh_response.status_code == 401
    assert refresh_response.json()["error"]["code"] == "invalid_refresh_token"
