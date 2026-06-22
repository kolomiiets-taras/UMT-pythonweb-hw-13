import cloudinary
import cloudinary.uploader
from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.conf.config import settings
from src.database.db import get_db
from src.entity.models import User
from src.repository import users as users_repo
from src.schemas.users import UserResponse
from src.services.auth import auth_service
from src.services.limiter import limiter

router = APIRouter(prefix="/users", tags=["users"])

cloudinary.config(
    cloud_name=settings.CLD_NAME,
    api_key=settings.CLD_API_KEY,
    api_secret=settings.CLD_API_SECRET,
    secure=True,
)


@router.get("/me", response_model=UserResponse)
@limiter.limit("10/minute")
async def read_me(
    request: Request,
    current_user: User = Depends(auth_service.get_current_user),
):
    """Return the authenticated user. Rate limited to 10 requests/minute."""
    return current_user


@router.patch("/avatar", response_model=UserResponse)
async def update_avatar(
    file: UploadFile = File(),
    current_user: User = Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    public_id = f"contacts_api/{current_user.email}"
    result = cloudinary.uploader.upload(file.file, public_id=public_id, overwrite=True)
    src_url = cloudinary.CloudinaryImage(public_id).build_url(
        width=250, height=250, crop="fill", version=result.get("version")
    )
    user = await users_repo.update_avatar(db, current_user.email, src_url)
    return user
