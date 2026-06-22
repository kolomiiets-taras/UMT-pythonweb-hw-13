"""Shared pytest fixtures: in-memory DB, ASGI client, and stubbed externals."""

import asyncio

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from main import app
from src.database.db import get_db
from src.entity.models import Base, Role, User
from src.services import cache
from src.services.auth import auth_service

TEST_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    TEST_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool
)
TestSession = async_sessionmaker(
    bind=engine, autoflush=False, expire_on_commit=False, class_=AsyncSession
)


@pytest_asyncio.fixture(autouse=True)
async def _create_schema():
    # Recreate the schema per test so the shared in-memory DB stays isolated.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest.fixture(autouse=True)
def _stub_externals(monkeypatch):
    """Neutralize Redis, email sending and Gravatar network calls in tests.

    Redis is replaced with a fake client that always misses, so the real cache
    code runs (and is covered) without a running Redis server.
    """
    from unittest.mock import AsyncMock

    fake_redis = AsyncMock()
    fake_redis.get.return_value = None
    monkeypatch.setattr(cache, "get_redis", lambda: fake_redis)

    async def _none(*a, **k):
        return None

    import src.repository.users as users_repo

    class _FakeGravatar:
        def __init__(self, *a, **k):
            pass

        def get_image(self):
            return "http://avatar.example/img.png"

    monkeypatch.setattr(users_repo, "Gravatar", _FakeGravatar)

    import src.routes.auth as auth_routes
    monkeypatch.setattr(auth_routes, "send_verification_email", _none)
    monkeypatch.setattr(auth_routes, "send_reset_password_email", _none)


@pytest_asyncio.fixture
async def db_session():
    async with TestSession() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session):
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def user(db_session) -> User:
    u = User(
        username="alice",
        email="alice@example.com",
        password=auth_service.get_password_hash("secret123"),
        confirmed=True,
        role=Role.user,
    )
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


@pytest_asyncio.fixture
async def admin(db_session) -> User:
    u = User(
        username="boss",
        email="boss@example.com",
        password=auth_service.get_password_hash("secret123"),
        confirmed=True,
        role=Role.admin,
    )
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


@pytest.fixture
def token(user) -> str:
    return auth_service.create_access_token({"sub": user.email})


@pytest.fixture
def admin_token(admin) -> str:
    return auth_service.create_access_token({"sub": admin.email})


@pytest.fixture
def auth_headers(token) -> dict:
    return {"Authorization": f"Bearer {token}"}
