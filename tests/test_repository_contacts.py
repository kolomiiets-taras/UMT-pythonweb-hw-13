"""Unit tests for the contacts repository (mocked AsyncSession)."""

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.entity.models import Contact
from src.repository import contacts as repo
from src.schemas.contacts import ContactCreate, ContactUpdate


def _make_db(scalar_result=None, scalars_list=None):
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = scalar_result
    scalars = MagicMock()
    scalars.all.return_value = scalars_list or []
    result.scalars.return_value = scalars
    db.execute.return_value = result
    return db


@pytest.fixture
def body():
    return ContactCreate(
        first_name="Bob",
        last_name="Hill",
        email="bob@x.com",
        phone="+1000000",
        birthday=date(1990, 1, 1),
    )


async def test_get_contacts():
    contacts = [Contact(id=1, user_id=1), Contact(id=2, user_id=1)]
    db = _make_db(scalars_list=contacts)
    result = await repo.get_contacts(db, user_id=1, first_name="b", email="x")
    assert result == contacts
    db.execute.assert_awaited()


async def test_get_contact_found():
    contact = Contact(id=5, user_id=1)
    db = _make_db(scalar_result=contact)
    result = await repo.get_contact(db, user_id=1, contact_id=5)
    assert result is contact


async def test_get_contact_missing():
    db = _make_db(scalar_result=None)
    result = await repo.get_contact(db, user_id=1, contact_id=99)
    assert result is None


async def test_create_contact(body):
    db = _make_db()
    result = await repo.create_contact(db, user_id=1, body=body)
    assert result.first_name == "Bob"
    assert result.user_id == 1
    db.add.assert_called_once()
    db.commit.assert_awaited()
    db.refresh.assert_awaited()


async def test_update_contact_found(body):
    existing = Contact(id=3, user_id=1, first_name="Old", last_name="N",
                       email="o@x.com", phone="1", birthday=date(2000, 1, 1))
    db = _make_db(scalar_result=existing)
    upd = ContactUpdate(**{**body.model_dump(), "first_name": "New"})
    result = await repo.update_contact(db, user_id=1, contact_id=3, body=upd)
    assert result.first_name == "New"
    db.commit.assert_awaited()


async def test_update_contact_missing(body):
    db = _make_db(scalar_result=None)
    result = await repo.update_contact(db, user_id=1, contact_id=3, body=ContactUpdate(**body.model_dump()))
    assert result is None


async def test_delete_contact_found():
    existing = Contact(id=7, user_id=1)
    db = _make_db(scalar_result=existing)
    result = await repo.delete_contact(db, user_id=1, contact_id=7)
    assert result is existing
    db.delete.assert_awaited_once_with(existing)
    db.commit.assert_awaited()


async def test_delete_contact_missing():
    db = _make_db(scalar_result=None)
    result = await repo.delete_contact(db, user_id=1, contact_id=7)
    assert result is None


async def test_upcoming_birthdays():
    soon = Contact(id=1, user_id=1, birthday=date(1990, 1, 1))
    db = _make_db(scalars_list=[soon])
    result = await repo.get_upcoming_birthdays(db, user_id=1, days=7)
    assert result == [soon]
    db.execute.assert_awaited()
