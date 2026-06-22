"""Pydantic schemas for users and auth tokens."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from src.entity.models import Role


class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)


class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    avatar: str | None
    confirmed: bool
    role: Role
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class RequestEmail(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=6, max_length=72)
