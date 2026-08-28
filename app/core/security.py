import datetime
from uuid import UUID
import jwt
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import get_settings
from app.models.user import User
from app.schemas.auth import TokenRefreshRequest

settings = get_settings()


class ResponseMessages:
    """Auth xatoliklari uchun xabarlar matni."""
    CANT_GENERATE_JWT = "JWT token yaratishda xatolik yuz berdi"
    CANT_GENERATE_REFRESH = "Refresh token yaratishda xatolik yuz berdi"
    INVALID_TOKEN = "Yaroqsiz yoki noto'g'ri token"
    EXPIRED_TOKEN = "Tokenning amal qilish muddati tugagan"
    USER_NOT_FOUND = "Foydalanuvchi topilmadi"
    USER_INACTIVE = "Foydalanuvchi hisobi faol emas"


class AuthManager:
    """JWT Tokenlar bilan ishlash menejeri."""

    # @staticmethod
    # def encode_token(user: User) -> str:
    #     """Access Token yaratish (15-30 daqiqa)."""
    #     # DEBUG: Asl xatoni ko'rish uchun try...except'ni vaqtincha olib turamiz
    #     role_value = user.role.value if hasattr(user.role, "value") else str(user.role)

    #     now = datetime.datetime.now(tz=datetime.timezone.utc)
    #     expire = now + datetime.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    #     payload = {
    #         "sub": str(user.id),
    #         "role": role_value,
    #         "exp": int(expire.timestamp()),
    #         "typ": "access",
    #     }
    #     return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


    @staticmethod
    def encode_token(user: User) -> str:
        """Access Token yaratish (15-30 daqiqa)."""
        try:
            role_value = user.role.value if hasattr(user.role, "value") else str(user.role)

            now = datetime.datetime.now(tz=datetime.timezone.utc)
            expire = now + datetime.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            
            payload = {
                "sub": str(user.id),
                "role": role_value,
                "exp": int(expire.timestamp()),
                "typ": "access",
            }
            return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        except (jwt.PyJWTError, AttributeError, Exception) as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail=ResponseMessages.CANT_GENERATE_JWT
            ) from exc

    @staticmethod
    def encode_refresh_token(user: User) -> str:
        """Refresh Token yaratish (30 kun)."""
        try:
            now = datetime.datetime.now(tz=datetime.timezone.utc)
            expire = now + datetime.timedelta(days=30)

            payload = {
                "sub": str(user.id),
                "exp": int(expire.timestamp()),
                "typ": "refresh",
            }
            return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        except (jwt.PyJWTError, AttributeError, Exception) as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail=ResponseMessages.CANT_GENERATE_REFRESH
            ) from exc

    @staticmethod
    async def refresh(refresh_data: TokenRefreshRequest, session: AsyncSession) -> dict:
        """Refresh token orqali yangi Access va Refresh token berish."""
        try:
            payload = jwt.decode(refresh_data.refresh_token, settings.SECRET_KEY, algorithms=["HS256"])

            if payload.get("typ") != "refresh":
                raise HTTPException(status.HTTP_401_UNAUTHORIZED, ResponseMessages.INVALID_TOKEN)

            user_id = UUID(payload["sub"])
            
            # Bazadan foydalanuvchini olish
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()

            if not user:
                raise HTTPException(status.HTTP_404_NOT_FOUND, ResponseMessages.USER_NOT_FOUND)

            if not user.is_active:
                raise HTTPException(status.HTTP_401_UNAUTHORIZED, ResponseMessages.USER_INACTIVE)

            # Yangi juftlik hosil qilish
            new_access_token = AuthManager.encode_token(user)
            new_refresh_token = AuthManager.encode_refresh_token(user)

            return {
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,
                "token_type": "bearer"
            }

        except jwt.ExpiredSignatureError as exc:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, ResponseMessages.EXPIRED_TOKEN) from exc
        except jwt.InvalidTokenError as exc:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, ResponseMessages.INVALID_TOKEN) from exc