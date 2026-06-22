from datetime import date, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.entity.models import Contact
from src.schemas.contacts import ContactCreate, ContactUpdate


async def get_contacts(
    db: AsyncSession,
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    first_name: str | None = None,
    last_name: str | None = None,
    email: str | None = None,
) -> list[Contact]:
    stmt = select(Contact).where(Contact.user_id == user_id)
    if first_name:
        stmt = stmt.where(Contact.first_name.ilike(f"%{first_name}%"))
    if last_name:
        stmt = stmt.where(Contact.last_name.ilike(f"%{last_name}%"))
    if email:
        stmt = stmt.where(Contact.email.ilike(f"%{email}%"))
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_contact(db: AsyncSession, user_id: int, contact_id: int) -> Contact | None:
    result = await db.execute(
        select(Contact).where(
            Contact.id == contact_id, Contact.user_id == user_id
        )
    )
    return result.scalar_one_or_none()


async def create_contact(
    db: AsyncSession, user_id: int, body: ContactCreate
) -> Contact:
    contact = Contact(**body.model_dump(), user_id=user_id)
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    return contact


async def update_contact(
    db: AsyncSession, user_id: int, contact_id: int, body: ContactUpdate
) -> Contact | None:
    contact = await get_contact(db, user_id, contact_id)
    if contact is None:
        return None
    for field, value in body.model_dump().items():
        setattr(contact, field, value)
    await db.commit()
    await db.refresh(contact)
    return contact


async def delete_contact(
    db: AsyncSession, user_id: int, contact_id: int
) -> Contact | None:
    contact = await get_contact(db, user_id, contact_id)
    if contact is None:
        return None
    await db.delete(contact)
    await db.commit()
    return contact


async def get_upcoming_birthdays(
    db: AsyncSession, user_id: int, days: int = 7
) -> list[Contact]:
    """Return user's contacts whose birthday (month/day) falls in the next `days` days."""
    today = date.today()
    upcoming = [today + timedelta(days=offset) for offset in range(days + 1)]
    # Match on (month, day) so it works across year boundaries regardless of birth year.
    md_pairs = {(d.month, d.day) for d in upcoming}
    conditions = [
        (func.extract("month", Contact.birthday) == m)
        & (func.extract("day", Contact.birthday) == d)
        for m, d in md_pairs
    ]
    stmt = select(Contact).where(Contact.user_id == user_id, or_(*conditions))
    result = await db.execute(stmt)
    return list(result.scalars().all())
