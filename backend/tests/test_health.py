import httpx
import pytest

from app.main import app


@pytest.mark.anyio
async def test_health_endpoint_returns_expected_payload() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/v1/health", headers={"X-Request-ID": "req-test-1"})

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "req-test-1"

    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "Ops Pulse API"
    assert payload["version"] == "0.1.0"
    assert payload["environment"] == "local"
    assert payload["request_id"] == "req-test-1"
    assert "timestamp" in payload


@pytest.mark.anyio
async def test_not_found_returns_unified_error_schema() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/v1/does-not-exist")

    assert response.status_code == 404
    assert "x-request-id" in response.headers

    payload = response.json()
    assert "request_id" in payload
    assert payload["error"]["code"] == "not_found"
    assert payload["error"]["message"]
