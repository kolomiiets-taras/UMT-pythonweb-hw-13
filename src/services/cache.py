"""Redis-backed cache for the authenticated user.

Caching the current user avoids hitting the database on every authenticated
request. Entries are stored as JSON keyed by ``user:<email>`` and invalidated
whenever the user record changes (avatar, confirmation, password reset).
"""

import json

import redis.asyncio as redis

from src.conf.config import settings
from src.entity.models import Role, User

_pool = redis.ConnectionPool(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD,
    decode_responses=True,
)


def get_redis() -> redis.Redis:
    """Return a Redis client bound to the shared connection pool."""
    return redis.Redis(connection_pool=_pool)


def _key(email: str) -> str:
    return f"user:{email}"


def _serialize(user: User) -> str:
    return json.dumps(
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "password": user.password,
            "avatar": user.avatar,
            "refresh_token": user.refresh_token,
            "confirmed": user.confirmed,
            "role": user.role.value if isinstance(user.role, Role) else user.role,
        }
    )


def _deserialize(raw: str) -> User:
    data = json.loads(raw)
    user = User(
        id=data["id"],
        username=data["username"],
        email=data["email"],
        password=data["password"],
        avatar=data["avatar"],
        refresh_token=data["refresh_token"],
        confirmed=data["confirmed"],
        role=Role(data["role"]),
    )
    return user


async def get_cached_user(email: str) -> User | None:
    """Return the cached :class:`User` for ``email`` or ``None`` on a cache miss."""
    try:
        client = get_redis()
        raw = await client.get(_key(email))
        if raw:
            return _deserialize(raw)
    except Exception:
        # Cache must never break auth — fall back to the database on any error.
        return None
    return None


async def set_cached_user(user: User) -> None:
    """Store ``user`` in the cache with the configured TTL."""
    try:
        client = get_redis()
        await client.set(_key(user.email), _serialize(user), ex=settings.USER_CACHE_TTL)
    except Exception:
        pass


async def invalidate_user(email: str) -> None:
    """Drop the cached entry for ``email`` so the next read reloads from the DB."""
    try:
        client = get_redis()
        await client.delete(_key(email))
    except Exception:
        pass
