"""Unit tests for the users repository (mocked AsyncSession)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.entity.models import Role, User
from src.repository import users as repo
from src.schemas.users import UserCreate


def _make_db(scalar_result=None):
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = scalar_result
    db.execute.return_value = result
    return db


async def test_get_user_by_email_found():
    u = User(id=1, email="a@x.com")
    db = _make_db(scalar_result=u)
    assert await repo.get_user_by_email(db, "a@x.com") is u


async def test_get_user_by_email_missing():
    db = _make_db(scalar_result=None)
    assert await repo.get_user_by_email(db, "a@x.com") is None


async def test_create_user(monkeypatch):
    class _G:
        def __init__(self, *a):
            pass

        def get_image(self):
            return "http://avatar/x.png"

    monkeypatch.setattr(repo, "Gravatar", _G)
    db = _make_db()
    body = UserCreate(username="al", email="al@x.com", password="secret123")
    user = await repo.create_user(db, body, "hashed")
    assert user.email == "al@x.com"
    assert user.password == "hashed"
    assert user.avatar == "http://avatar/x.png"
    db.add.assert_called_once()
    db.commit.assert_awaited()


async def test_confirmed_email(monkeypatch):
    u = User(id=1, email="a@x.com", confirmed=False)
    db = _make_db(scalar_result=u)
    monkeypatch.setattr(repo.cache, "invalidate_user", AsyncMock())
    await repo.confirmed_email(db, "a@x.com")
    assert u.confirmed is True
    db.commit.assert_awaited()


async def test_update_avatar(monkeypatch):
    u = User(id=1, email="a@x.com")
    db = _make_db(scalar_result=u)
    monkeypatch.setattr(repo.cache, "invalidate_user", AsyncMock())
    result = await repo.update_avatar(db, "a@x.com", "http://new/av.png")
    assert result.avatar == "http://new/av.png"


async def test_update_refresh_token(monkeypatch):
    u = User(id=1, email="a@x.com")
    db = _make_db()
    monkeypatch.setattr(repo.cache, "invalidate_user", AsyncMock())
    await repo.update_refresh_token(db, u, "tok")
    assert u.refresh_token == "tok"
    db.commit.assert_awaited()


async def test_update_password(monkeypatch):
    u = User(id=1, email="a@x.com", password="old")
    db = _make_db(scalar_result=u)
    monkeypatch.setattr(repo.cache, "invalidate_user", AsyncMock())
    await repo.update_password(db, "a@x.com", "newhash")
    assert u.password == "newhash"
