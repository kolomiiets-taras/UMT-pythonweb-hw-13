"""Authentication & authorization service.

Handles password hashing, JWT creation/decoding (access, refresh, email and
password-reset tokens), the ``get_current_user`` dependency (with Redis cache)
and role-based access control.
"""

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from src.conf.config import settings
from src.database.db import get_db
from src.entity.models import Role, User
from src.repository import users as users_repo
from src.services import cache


class Auth:
    """Bundles all auth-related helpers behind a single instance."""

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
    SECRET = settings.JWT_SECRET
    ALGORITHM = settings.JWT_ALGORITHM

    def verify_password(self, plain: str, hashed: str) -> bool:
        """Return ``True`` if ``plain`` matches the bcrypt ``hashed`` value."""
        return self.pwd_context.verify(plain, hashed)

    def get_password_hash(self, password: str) -> str:
        """Return a bcrypt hash for ``password``."""
        return self.pwd_context.hash(password)

    def _create_token(self, data: dict, expires_delta: timedelta, scope: str) -> str:
        to_encode = data.copy()
        now = datetime.now(timezone.utc)
        to_encode.update({"iat": now, "exp": now + expires_delta, "scope": scope})
        return jwt.encode(to_encode, self.SECRET, algorithm=self.ALGORITHM)

    def create_access_token(self, data: dict, expires_minutes: int | None = None) -> str:
        """Create a short-lived ``access_token`` JWT."""
        delta = timedelta(minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        return self._create_token(data, delta, "access_token")

    def create_refresh_token(self, data: dict, expires_days: int | None = None) -> str:
        """Create a long-lived ``refresh_token`` JWT."""
        delta = timedelta(days=expires_days or settings.REFRESH_TOKEN_EXPIRE_DAYS)
        return self._create_token(data, delta, "refresh_token")

    def create_email_token(self, data: dict) -> str:
        """Create an email-verification token."""
        return self._create_token(
            data, timedelta(hours=settings.EMAIL_TOKEN_EXPIRE_HOURS), "email_token"
        )

    def create_reset_token(self, data: dict) -> str:
        """Create a password-reset token."""
        return self._create_token(
            data, timedelta(hours=settings.RESET_TOKEN_EXPIRE_HOURS), "reset_token"
        )

    def _decode(self, token: str, expected_scope: str) -> str:
        try:
            payload = jwt.decode(token, self.SECRET, algorithms=[self.ALGORITHM])
            if payload.get("scope") != expected_scope:
                raise HTTPException(
                    status.HTTP_401_UNAUTHORIZED, detail="Invalid token scope"
                )
            email = payload.get("sub")
            if email is None:
                raise HTTPException(
                    status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
                )
            return email
        except jwt.ExpiredSignatureError:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Token expired")
        except jwt.PyJWTError:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials"
            )

    def get_email_from_token(self, token: str) -> str:
        """Return the subject email from a valid email-verification token."""
        return self._decode(token, "email_token")

    def get_email_from_reset_token(self, token: str) -> str:
        """Return the subject email from a valid password-reset token."""
        return self._decode(token, "reset_token")

    def decode_refresh_token(self, token: str) -> str:
        """Return the subject email from a valid ``refresh_token``."""
        return self._decode(token, "refresh_token")

    async def get_current_user(
        self,
        token: str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        """Resolve the authenticated user from a bearer ``access_token``.

        Checks the Redis cache first; on a miss, loads the user from the
        database and caches it. Raises ``401`` if the token is invalid or the
        user no longer exists.
        """
        credentials_exc = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        email = self._decode(token, "access_token")

        user = await cache.get_cached_user(email)
        if user is not None:
            return user

        user = await users_repo.get_user_by_email(db, email)
        if user is None:
            raise credentials_exc
        await cache.set_cached_user(user)
        return user


auth_service = Auth()


class RoleAccess:
    """Dependency that allows the request only for the listed roles."""

    def __init__(self, allowed_roles: list[Role]):
        self.allowed_roles = allowed_roles

    async def __call__(
        self, current_user: User = Depends(auth_service.get_current_user)
    ) -> User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, detail="Operation forbidden for your role"
            )
        return current_user


require_admin = RoleAccess([Role.admin])
