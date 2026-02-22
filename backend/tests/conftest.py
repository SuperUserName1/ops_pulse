import os
from collections.abc import AsyncIterator

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.core.rate_limit import reset_rate_limit_singletons
from app.core.settings import get_settings
from app.db.base import Base
from app.db.session import get_async_session
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
async def db_client() -> AsyncIterator[httpx.AsyncClient]:
    database_url = os.getenv("OPS_PULSE_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("OPS_PULSE_TEST_DATABASE_URL is required for db_client fixture.")
    if "ops_pulse_test" not in database_url:
        raise RuntimeError("db_client fixture requires a dedicated test database URL.")

    engine = create_async_engine(database_url, future=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_async_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_async_session] = override_get_async_session
    transport = httpx.ASGITransport(app=app)

    try:
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as async_client:
            yield async_client
    finally:
        app.dependency_overrides.pop(get_async_session, None)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()


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
