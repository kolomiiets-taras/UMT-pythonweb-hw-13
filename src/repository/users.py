"""Database access layer for :class:`~src.entity.models.User`."""

from libgravatar import Gravatar
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.entity.models import User
from src.schemas.users import UserCreate
from src.services import cache


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Return the user with the given ``email`` or ``None``."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, body: UserCreate, hashed_password: str) -> User:
    """Create a new user with a Gravatar avatar and the supplied password hash."""
    avatar = None
    try:
        avatar = Gravatar(body.email).get_image()
    except Exception:
        pass
    user = User(
        username=body.username,
        email=body.email,
        password=hashed_password,
        avatar=avatar,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def confirmed_email(db: AsyncSession, email: str) -> None:
    """Mark the user's email as confirmed and invalidate the cache."""
    user = await get_user_by_email(db, email)
    if user:
        user.confirmed = True
        await db.commit()
        await cache.invalidate_user(email)


async def update_avatar(db: AsyncSession, email: str, url: str) -> User | None:
    """Update the user's avatar URL and invalidate the cache."""
    user = await get_user_by_email(db, email)
    if user:
        user.avatar = url
        await db.commit()
        await db.refresh(user)
        await cache.invalidate_user(email)
    return user


async def update_refresh_token(
    db: AsyncSession, user: User, token: str | None
) -> None:
    """Persist the user's current ``refresh_token`` (or clear it) and refresh cache."""
    user.refresh_token = token
    await db.commit()
    await cache.invalidate_user(user.email)


async def update_password(db: AsyncSession, email: str, hashed_password: str) -> None:
    """Set a new password hash for the user and invalidate the cache."""
    user = await get_user_by_email(db, email)
    if user:
        user.password = hashed_password
        await db.commit()
        await cache.invalidate_user(email)
