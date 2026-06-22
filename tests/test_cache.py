"""Unit tests for the Redis user cache (serialize/deserialize + fake client)."""

from unittest.mock import AsyncMock

import pytest

from src.entity.models import Role, User
from src.services import cache


def _user():
    return User(
        id=1, username="al", email="al@x.com", password="hash",
        avatar="a.png", refresh_token="r", confirmed=True, role=Role.admin,
    )


def test_serialize_roundtrip():
    raw = cache._serialize(_user())
    user = cache._deserialize(raw)
    assert user.email == "al@x.com"
    assert user.role == Role.admin
    assert user.confirmed is True


async def test_get_cached_user_hit(monkeypatch):
    fake = AsyncMock()
    fake.get.return_value = cache._serialize(_user())
    monkeypatch.setattr(cache, "get_redis", lambda: fake)
    user = await cache.get_cached_user("al@x.com")
    assert user is not None
    assert user.email == "al@x.com"


async def test_get_cached_user_miss(monkeypatch):
    fake = AsyncMock()
    fake.get.return_value = None
    monkeypatch.setattr(cache, "get_redis", lambda: fake)
    assert await cache.get_cached_user("nope@x.com") is None


async def test_set_and_invalidate(monkeypatch):
    fake = AsyncMock()
    monkeypatch.setattr(cache, "get_redis", lambda: fake)
    await cache.set_cached_user(_user())
    fake.set.assert_awaited()
    await cache.invalidate_user("al@x.com")
    fake.delete.assert_awaited()
