from libgravatar import Gravatar
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.entity.models import User
from src.schemas.users import UserCreate


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, body: UserCreate, hashed_password: str) -> User:
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
    user = await get_user_by_email(db, email)
    if user:
        user.confirmed = True
        await db.commit()


async def update_avatar(db: AsyncSession, email: str, url: str) -> User | None:
    user = await get_user_by_email(db, email)
    if user:
        user.avatar = url
        await db.commit()
        await db.refresh(user)
    return user
