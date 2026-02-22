import pytest

pytestmark = pytest.mark.anyio


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _admin_access_token(client) -> str:
    response = await client.post(
        "/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


async def test_users_list_uses_standard_pagination_contract(client) -> None:
    token = await _admin_access_token(client)
    response = await client.get("/v1/auth/users", headers=_auth_header(token))
    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == {"items", "total", "limit", "offset"}
    assert isinstance(payload["items"], list)
    assert payload["total"] >= len(payload["items"])


async def test_users_list_paginates_with_limit_and_offset(client) -> None:
    token = await _admin_access_token(client)
    page_1 = await client.get(
        "/v1/auth/users",
        headers=_auth_header(token),
        params={"limit": 2, "offset": 0},
    )
    page_2 = await client.get(
        "/v1/auth/users",
        headers=_auth_header(token),
        params={"limit": 2, "offset": 2},
    )
    assert page_1.status_code == 200
    assert page_2.status_code == 200
    payload_1 = page_1.json()
    payload_2 = page_2.json()
    assert payload_1["limit"] == 2
    assert payload_2["offset"] == 2
    assert payload_1["items"][0]["id"] != payload_2["items"][0]["id"]


async def test_users_list_filters_by_search(client) -> None:
    token = await _admin_access_token(client)
    response = await client.get(
        "/v1/auth/users",
        headers=_auth_header(token),
        params={"search": "agent"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert [item["username"] for item in payload["items"]] == ["agent", "agent2"]


async def test_users_list_filters_by_status(client) -> None:
    token = await _admin_access_token(client)
    response = await client.get(
        "/v1/auth/users",
        headers=_auth_header(token),
        params={"status": "disabled"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["status"] == "disabled"


async def test_users_list_filters_by_created_range(client) -> None:
    token = await _admin_access_token(client)
    response = await client.get(
        "/v1/auth/users",
        headers=_auth_header(token),
        params={
            "created_from": "2025-01-20T00:00:00Z",
            "created_to": "2025-02-02T00:00:00Z",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    usernames = [item["username"] for item in payload["items"]]
    assert usernames == ["viewer", "agent2"]


async def test_users_list_rejects_invalid_created_range(client) -> None:
    token = await _admin_access_token(client)
    response = await client.get(
        "/v1/auth/users",
        headers=_auth_header(token),
        params={
            "created_from": "2025-03-01T00:00:00Z",
            "created_to": "2025-02-01T00:00:00Z",
        },
    )
    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "invalid_filters"
