"""User management business logic for Vendora E-Commerce."""

from collections.abc import Sequence
from uuid import UUID  # Standard library UUID import qilindi
from email_validator import EmailNotValidError, validate_email
from fastapi import HTTPException, status
from passlib.context import CryptContext
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthManager
from app.models.user import User, UserRole
from app.schemas.user import UserChangePasswordRequest, UserEditRequest, UserRegisterRequest

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class ErrorMessages:
    """Error message constants."""

    EMAIL_EXISTS = "A user with this email address already exists"
    EMAIL_INVALID = "This email address is not valid"
    AUTH_INVALID = "Invalid email or password"
    USER_INVALID = "User not found"
    CANT_SELF_BAN = "You cannot ban or unban yourself"
    NOT_VERIFIED = "You need to verify your email before logging in"
    EMPTY_FIELDS = "Required fields cannot be empty"
    ALREADY_BANNED_OR_UNBANNED = "User status already matches requested action"


class UserManager:
    """Business logic for User authentication and profile operations."""

    @staticmethod
    async def register(user_data: UserRegisterRequest, session: AsyncSession) -> tuple[str, str]:
        """Register a new user and generate access/refresh tokens."""
        try:
            email_validation = validate_email(user_data.email, check_deliverability=False)
            valid_email = email_validation.email
        except EmailNotValidError as err:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, ErrorMessages.EMAIL_INVALID) from err

        hashed_password = pwd_context.hash(user_data.password)

        new_user = User(
            email=valid_email,
            hashed_password=hashed_password,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            role=UserRole.CUSTOMER,
            is_active=True,
        )

        session.add(new_user)
        try:
            await session.flush()
            await session.refresh(new_user)  # Atributlarni yuklab olish

            token = AuthManager.encode_token(new_user)
            refresh = AuthManager.encode_refresh_token(new_user)

            await session.commit()
        except IntegrityError as err:
            await session.rollback()
            raise HTTPException(status.HTTP_400_BAD_REQUEST, ErrorMessages.EMAIL_EXISTS) from err

        return token, refresh

    @staticmethod
    async def login(user_data: dict[str, str], session: AsyncSession) -> tuple[str, str]:
        """Authenticate user and return tokens."""
        email_validation = validate_email(user_data.email, check_deliverability=False)
        valid_email = email_validation.email
        result = await session.execute(select(User).where(User.email == valid_email))
        user_do = result.scalar_one_or_none()

        if not user_do or not pwd_context.verify(user_data.password, str(user_do.hashed_password)) or not user_do.is_active:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, ErrorMessages.AUTH_INVALID)

        token = AuthManager.encode_token(user_do)
        refresh = AuthManager.encode_refresh_token(user_do)

        return token, refresh

    @staticmethod
    async def delete_user(user_id: UUID, session: AsyncSession) -> None:
        """Delete user by ID."""
        user = await session.get(User, user_id)
        if not user:
            raise HTTPException(status.HTTP_404_NOT_FOUND, ErrorMessages.USER_INVALID)

        await session.execute(delete(User).where(User.id == user_id))
        await session.commit()

    @staticmethod
    async def update_user(user_id: UUID, user_data: UserEditRequest, session: AsyncSession) -> User:
        """Update user profile fields."""
        user = await session.get(User, user_id)
        if not user:
            raise HTTPException(status.HTTP_404_NOT_FOUND, ErrorMessages.USER_INVALID)

        update_dict = user_data.model_dump(exclude_unset=True)
        if "password" in update_dict:
            update_dict["hashed_password"] = pwd_context.hash(update_dict.pop("password"))

        if update_dict:
            await session.execute(update(User).where(User.id == user_id).values(**update_dict))
            await session.commit()
            await session.refresh(user)

        return user

    @staticmethod
    async def change_password(user_id: UUID, user_data: UserChangePasswordRequest, session: AsyncSession) -> None:
        """Change user password."""
        user = await session.get(User, user_id)
        if not user:
            raise HTTPException(status.HTTP_404_NOT_FOUND, ErrorMessages.USER_INVALID)

        hashed_password = pwd_context.hash(user_data.password)
        await session.execute(update(User).where(User.id == user_id).values(hashed_password=hashed_password))
        await session.commit()

    @staticmethod
    async def set_ban_status(user_id: UUID, state: bool, my_id: UUID, session: AsyncSession) -> None:
        """Ban (deactivate) or unban user."""
        if my_id == user_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, ErrorMessages.CANT_SELF_BAN)

        user = await session.get(User, user_id)
        if not user:
            raise HTTPException(status.HTTP_404_NOT_FOUND, ErrorMessages.USER_INVALID)

        is_currently_banned = not user.is_active
        if is_currently_banned == state:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, ErrorMessages.ALREADY_BANNED_OR_UNBANNED)

        await session.execute(update(User).where(User.id == user_id).values(is_active=not state))
        await session.commit()

    @staticmethod
    async def change_role(role: UserRole, user_id: UUID, session: AsyncSession) -> None:
        """Update user role."""
        user = await session.get(User, user_id)
        if not user:
            raise HTTPException(status.HTTP_404_NOT_FOUND, ErrorMessages.USER_INVALID)

        await session.execute(update(User).where(User.id == user_id).values(role=role))
        await session.commit()

    @staticmethod
    async def get_all_users(session: AsyncSession) -> Sequence[User]:
        """Fetch all users."""
        result = await session.execute(select(User))
        return result.scalars().all()

    @staticmethod
    async def get_user_by_id(user_id: UUID, session: AsyncSession) -> User:
        """Fetch single user by ID."""
        user = await session.get(User, user_id)
        if not user:
            raise HTTPException(status.HTTP_404_NOT_FOUND, ErrorMessages.USER_INVALID)
        return user

    @staticmethod
    async def get_user_by_email(email: str, session: AsyncSession) -> User:
        """Fetch single user by Email."""
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status.HTTP_404_NOT_FOUND, ErrorMessages.USER_INVALID)
        return user