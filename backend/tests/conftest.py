from collections.abc import AsyncIterator

import httpx
import pytest

from app.core.rate_limit import reset_rate_limit_singletons
from app.core.settings import get_settings
from app.main import app
from app.services.auth import get_auth_service, reset_auth_service_state


@pytest.fixture(autouse=True)
def reset_app_singletons(request: pytest.FixtureRequest) -> None:
    if str(request.node.path).endswith("test_migrations.py"):
        return
    get_settings.cache_clear()
    reset_rate_limit_singletons()
    reset_auth_service_state()


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client


@pytest.fixture
def auth_service():
    return get_auth_service()


async def login_and_get_tokens(
    client: httpx.AsyncClient,
    *,
    username: str,
    password: str,
) -> dict[str, object]:
    response = await client.post(
        "/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()
