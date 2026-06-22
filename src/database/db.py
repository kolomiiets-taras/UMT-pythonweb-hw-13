"""Async database engine, session manager and the ``get_db`` dependency."""

import contextlib

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.conf.config import settings


class DatabaseSessionManager:
    """Manages the async engine and session lifecycle."""

    def __init__(self, url: str):
        self._engine = create_async_engine(url)
        self._session_maker = async_sessionmaker(
            bind=self._engine,
            autoflush=False,
            expire_on_commit=False,
            class_=AsyncSession,
        )

    @contextlib.asynccontextmanager
    async def session(self):
        session = self._session_maker()
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


sessionmanager = DatabaseSessionManager(settings.DB_URL)


async def get_db():
    """FastAPI dependency that yields an async DB session."""
    async with sessionmanager.session() as session:
        yield session
