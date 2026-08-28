from uuid import UUID
from typing import Optional
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import get_database
from app.models.user import User, UserRole
from app.core.security import ResponseMessages

settings = get_settings()


class CustomHTTPBearer(HTTPBearer):
    """Bearer tokenni o'qish va tekshirish uchun Custom HTTPBearer class."""

    async def __call__(self, request: Request, db: AsyncSession = Depends(get_database)) -> User:
        res: Optional[HTTPAuthorizationCredentials] = await super().__call__(request)

        if not res:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ResponseMessages.INVALID_TOKEN,
            )

        try:
            payload = jwt.decode(res.credentials, settings.SECRET_KEY, algorithms=["HS256"])
            
            # Faqat access token qabul qilinadi
            if payload.get("typ") != "access":
                raise HTTPException(status.HTTP_401_UNAUTHORIZED, ResponseMessages.INVALID_TOKEN)

            user_id = UUID(payload["sub"])
            
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()

            if not user:
                raise HTTPException(status.HTTP_404_NOT_FOUND, ResponseMessages.USER_NOT_FOUND)
            
            if not user.is_active:
                raise HTTPException(status.HTTP_401_UNAUTHORIZED, ResponseMessages.USER_INACTIVE)

            # Context request'ga foydalanuvchini biriktirish
            request.state.user = user
            return user

        except jwt.ExpiredSignatureError as exc:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, ResponseMessages.EXPIRED_TOKEN) from exc
        except jwt.InvalidTokenError as exc:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, ResponseMessages.INVALID_TOKEN) from exc


oauth2_schema = CustomHTTPBearer()


async def get_current_user(user: User = Depends(oauth2_schema)) -> User:
    """Tizimga kirgan joriy foydalanuvchini qaytaradi."""
    return user


# ROLLAR BO'YICHA RUXSAT TEKSHIRUVCHILARI (RBAC)

class RoleChecker:
    """Foydalanuvchi rolingiz mosligini tekshirish uchun dependency."""
    
    def __init__(self, allowed_roles: list[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Ushbu amalni bajarish uchun sizda yetarli ruxsat yo'q"
            )
        return current_user


# Tayyor Ruxsatlar:
allow_admin = RoleChecker([UserRole.ADMIN])
allow_seller = RoleChecker([UserRole.SELLER, UserRole.ADMIN])
allow_seller_or_admin = RoleChecker([UserRole.SELLER, UserRole.ADMIN])
allow_customer = RoleChecker([UserRole.CUSTOMER, UserRole.SELLER, UserRole.ADMIN])