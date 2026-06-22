"""Authentication routes: signup, login, token refresh, email verification,
and password reset."""

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    status,
)
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.db import get_db
from src.repository import users as users_repo
from src.schemas.users import (
    RequestEmail,
    ResetPasswordRequest,
    Token,
    UserCreate,
    UserResponse,
)
from src.services.auth import auth_service
from src.services.email import send_reset_password_email, send_verification_email

router = APIRouter(prefix="/auth", tags=["auth"])
bearer = HTTPBearer()


@router.post(
    "/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def signup(
    body: UserCreate,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user. Returns ``409`` if the email already exists."""
    existing = await users_repo.get_user_by_email(db, body.email)
    if existing:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="Account with this email already exists"
        )
    hashed = auth_service.get_password_hash(body.password)
    user = await users_repo.create_user(db, body, hashed)
    background_tasks.add_task(
        send_verification_email,
        user.email,
        user.username,
        str(request.base_url).rstrip("/"),
    )
    return user


@router.post("/login", response_model=Token)
async def login(
    body: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Authenticate by email + password and issue an access/refresh token pair."""
    user = await users_repo.get_user_by_email(db, body.username)
    if user is None or not auth_service.verify_password(body.password, user.password):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )
    if not user.confirmed:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Email not confirmed")
    access_token = auth_service.create_access_token({"sub": user.email})
    refresh_token = auth_service.create_refresh_token({"sub": user.email})
    await users_repo.update_refresh_token(db, user, refresh_token)
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.get("/refresh_token", response_model=Token)
async def refresh_token(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: AsyncSession = Depends(get_db),
):
    """Exchange a valid ``refresh_token`` (Bearer) for a fresh token pair."""
    token = credentials.credentials
    email = auth_service.decode_refresh_token(token)
    user = await users_repo.get_user_by_email(db, email)
    if user is None or user.refresh_token != token:
        if user:
            await users_repo.update_refresh_token(db, user, None)
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )
    access_token = auth_service.create_access_token({"sub": email})
    new_refresh = auth_service.create_refresh_token({"sub": email})
    await users_repo.update_refresh_token(db, user, new_refresh)
    return Token(access_token=access_token, refresh_token=new_refresh)


@router.get("/confirmed_email/{token}")
async def confirmed_email(token: str, db: AsyncSession = Depends(get_db)):
    """Confirm a user's email from the verification token."""
    email = auth_service.get_email_from_token(token)
    user = await users_repo.get_user_by_email(db, email)
    if user is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Verification error")
    if user.confirmed:
        return {"message": "Your email is already confirmed"}
    await users_repo.confirmed_email(db, email)
    return {"message": "Email confirmed"}


@router.post("/request_email")
async def request_email(
    body: RequestEmail,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Resend the email-verification message."""
    user = await users_repo.get_user_by_email(db, body.email)
    if user and user.confirmed:
        return {"message": "Your email is already confirmed"}
    if user:
        background_tasks.add_task(
            send_verification_email,
            user.email,
            user.username,
            str(request.base_url).rstrip("/"),
        )
    return {"message": "Check your email for confirmation"}


@router.post("/forgot_password")
async def forgot_password(
    body: RequestEmail,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Start the password-reset flow by emailing a reset token.

    Always returns the same response to avoid leaking which emails are registered.
    """
    user = await users_repo.get_user_by_email(db, body.email)
    if user:
        background_tasks.add_task(
            send_reset_password_email,
            user.email,
            user.username,
            str(request.base_url).rstrip("/"),
        )
    return {"message": "If the email exists, a reset link has been sent"}


@router.post("/reset_password")
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Complete the password reset using the token and a new password."""
    email = auth_service.get_email_from_reset_token(body.token)
    user = await users_repo.get_user_by_email(db, email)
    if user is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Reset error")
    hashed = auth_service.get_password_hash(body.new_password)
    await users_repo.update_password(db, email, hashed)
    return {"message": "Password updated"}
