import pytest

pytestmark = pytest.mark.anyio


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _login(client, username: str, password: str) -> dict[str, object]:
    response = await client.post(
        "/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()


async def test_tasks_crud_flow_for_admin_and_agent(db_client) -> None:
    admin_tokens = await _login(db_client, "admin", "admin123")
    agent_tokens = await _login(db_client, "agent", "agent123")

    create_response = await db_client.post(
        "/v1/tasks",
        headers=_auth_header(agent_tokens["access_token"]),
        json={
            "title": "Investigate delayed shipment",
            "description": "Call warehouse",
            "status": "open",
            "assignee_user_id": "usr-agent-1",
        },
    )
    assert create_response.status_code == 201, create_response.text
    task = create_response.json()["task"]
    task_id = task["id"]
    assert task["org_id"] == "org-acme"
    assert task["assignee_user_id"] == "usr-agent-1"

    list_response = await db_client.get(
        "/v1/tasks",
        headers=_auth_header(admin_tokens["access_token"]),
        params={"status": "open"},
    )
    assert list_response.status_code == 200, list_response.text
    list_payload = list_response.json()
    assert list_payload["total"] == 1
    assert list_payload["items"][0]["id"] == task_id

    patch_response = await db_client.patch(
        f"/v1/tasks/{task_id}",
        headers=_auth_header(agent_tokens["access_token"]),
        json={"status": "in_progress", "description": "Warehouse contacted"},
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["task"]["status"] == "in_progress"

    get_response = await db_client.get(
        f"/v1/tasks/{task_id}",
        headers=_auth_header(admin_tokens["access_token"]),
    )
    assert get_response.status_code == 200
    assert get_response.json()["task"]["description"] == "Warehouse contacted"

    delete_response = await db_client.delete(
        f"/v1/tasks/{task_id}",
        headers=_auth_header(admin_tokens["access_token"]),
    )
    assert delete_response.status_code == 204

    missing_response = await db_client.get(
        f"/v1/tasks/{task_id}",
        headers=_auth_header(admin_tokens["access_token"]),
    )
    assert missing_response.status_code == 404


async def test_viewer_cannot_create_task(db_client) -> None:
    viewer_tokens = await _login(db_client, "viewer", "viewer123")
    response = await db_client.post(
        "/v1/tasks",
        headers=_auth_header(viewer_tokens["access_token"]),
        json={"title": "Should fail"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


async def test_task_assignee_must_belong_to_current_org(db_client) -> None:
    admin_tokens = await _login(db_client, "admin", "admin123")
    response = await db_client.post(
        "/v1/tasks",
        headers=_auth_header(admin_tokens["access_token"]),
        json={
            "title": "Invalid assignee",
            "assignee_user_id": "usr-viewer-2",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_assignee"


async def test_task_access_is_tenant_scoped(db_client) -> None:
    beta_agent_tokens = await _login(db_client, "ops-bot", "agent123")
    acme_admin_tokens = await _login(db_client, "admin", "admin123")

    create_response = await db_client.post(
        "/v1/tasks",
        headers=_auth_header(beta_agent_tokens["access_token"]),
        json={"title": "Beta task"},
    )
    assert create_response.status_code == 201, create_response.text
    beta_task_id = create_response.json()["task"]["id"]

    get_response = await db_client.get(
        f"/v1/tasks/{beta_task_id}",
        headers=_auth_header(acme_admin_tokens["access_token"]),
    )
    assert get_response.status_code == 404
    assert get_response.json()["error"]["code"] == "not_found"


async def test_dashboard_summary_aggregates_current_org_tasks(db_client) -> None:
    admin_tokens = await _login(db_client, "admin", "admin123")

    for payload in (
        {"title": "T1", "status": "open"},
        {"title": "T2", "status": "blocked"},
        {"title": "T3", "status": "done"},
    ):
        response = await db_client.post(
            "/v1/tasks",
            headers=_auth_header(admin_tokens["access_token"]),
            json=payload,
        )
        assert response.status_code == 201, response.text

    summary_response = await db_client.get(
        "/v1/dashboard/summary",
        headers=_auth_header(admin_tokens["access_token"]),
    )
    assert summary_response.status_code == 200, summary_response.text
    payload = summary_response.json()
    assert payload["org_id"] == "org-acme"
    assert payload["total_tasks"] == 3
    assert payload["counts"]["open"] == 1
    assert payload["counts"]["blocked"] == 1
    assert payload["counts"]["done"] == 1
    assert len(payload["recent_tasks"]) == 3
