from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from src.conf.config import settings
from src.database.db import get_db
from src.entity.models import User
from src.repository import users as users_repo


class Auth:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
    SECRET = settings.JWT_SECRET
    ALGORITHM = settings.JWT_ALGORITHM

    def verify_password(self, plain: str, hashed: str) -> bool:
        return self.pwd_context.verify(plain, hashed)

    def get_password_hash(self, password: str) -> str:
        return self.pwd_context.hash(password)

    def create_access_token(self, data: dict, expires_minutes: int | None = None) -> str:
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        to_encode.update({"iat": datetime.now(timezone.utc), "exp": expire, "scope": "access_token"})
        return jwt.encode(to_encode, self.SECRET, algorithm=self.ALGORITHM)

    def create_email_token(self, data: dict) -> str:
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(
            hours=settings.EMAIL_TOKEN_EXPIRE_HOURS
        )
        to_encode.update({"iat": datetime.now(timezone.utc), "exp": expire, "scope": "email_token"})
        return jwt.encode(to_encode, self.SECRET, algorithm=self.ALGORITHM)

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
        return self._decode(token, "email_token")

    async def get_current_user(
        self,
        token: str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        credentials_exc = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        email = self._decode(token, "access_token")
        user = await users_repo.get_user_by_email(db, email)
        if user is None:
            raise credentials_exc
        return user


auth_service = Auth()
