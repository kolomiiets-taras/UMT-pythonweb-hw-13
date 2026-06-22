from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    status,
)
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.db import get_db
from src.repository import users as users_repo
from src.schemas.users import RequestEmail, Token, UserCreate, UserResponse
from src.services.auth import auth_service
from src.services.email import send_verification_email

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def signup(
    body: UserCreate,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    existing = await users_repo.get_user_by_email(db, body.email)
    if existing:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="Account with this email already exists"
        )
    hashed = auth_service.get_password_hash(body.password)
    user = await users_repo.create_user(db, body, hashed)
    background_tasks.add_task(
        send_verification_email, user.email, user.username, str(request.base_url).rstrip("/")
    )
    return user


@router.post("/login", response_model=Token)
async def login(
    body: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    # OAuth2 form uses `username`; we authenticate by email supplied there.
    user = await users_repo.get_user_by_email(db, body.username)
    if user is None or not auth_service.verify_password(body.password, user.password):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )
    if not user.confirmed:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="Email not confirmed"
        )
    access_token = auth_service.create_access_token({"sub": user.email})
    return Token(access_token=access_token, token_type="bearer")


@router.get("/confirmed_email/{token}")
async def confirmed_email(token: str, db: AsyncSession = Depends(get_db)):
    email = auth_service.get_email_from_token(token)
    user = await users_repo.get_user_by_email(db, email)
    if user is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Verification error"
        )
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
