from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.user import UserChangePasswordRequest, UserEditRequest, UserRegisterRequest, UserLoginRequest

from app.core.database import get_database
from app.core.security import AuthManager
from app.schemas.auth import TokenResponse, TokenRefreshRequest
from app.api.deps import get_current_user
from app.models.user import User
from app.services.user import UserManager

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_data: TokenRefreshRequest, 
    session: AsyncSession = Depends(get_database)
):
    return await AuthManager.refresh(refresh_data, session)

@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegisterRequest,
    session: AsyncSession = Depends(get_database)
):
    # UserManager tuple qaytaradi: (token, refresh)
    access_token, refresh_token = await UserManager.register(user_data, session)

    # Kalit nomlarini access_token va refresh_token deb o'zgartiramiz
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/login/", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(user_data: UserLoginRequest, session: AsyncSession = Depends(get_database)):
    access_token, refresh_token = await UserManager.login(user_data, session)

    return {
            "access_token": access_token,
            "refresh_token": refresh_token,
        }

