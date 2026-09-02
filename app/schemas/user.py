from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, EmailStr
from typing import Optional
from app.schemas.example import ExapleUser
from app.enums.all_enums import UserRole

class UserBase(BaseModel):
    """Base schema for User model representation."""

    email: EmailStr = Field(examples=[ExapleUser.email], description="User email address")

    model_config = ConfigDict(from_attributes=True)


class UserRegisterRequest(UserBase):
    """Request schema for user registration."""

    password: str = Field(examples=[ExapleUser.password], min_length=8, description="User password (min 8 characters)")
    first_name: Optional[str] = Field(examples=[ExapleUser.first_name], max_length=50)
    last_name: Optional[str] = Field(examples=[ExapleUser.last_name], max_length=50)


class UserLoginRequest(UserBase):
    """Request schema for user authentication."""

    password: str = Field(examples=[ExapleUser.password], description="User password")


class UserEditRequest(BaseModel):
    """Request schema for updating user profile (PATCH style)."""

    email: Optional[EmailStr] = Field(None, examples=[ExapleUser.email])
    password: Optional[str] = Field(None, examples=[ExapleUser.password], min_length=8)
    first_name: Optional[str] = Field(None, examples=[ExapleUser.first_name], min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, examples=[ExapleUser.last_name], min_length=1, max_length=50)


class UserChangePasswordRequest(BaseModel):
    """Request schema for updating account password."""

    password: str = Field(examples=[ExapleUser.password], min_length=8, description="New password")


class MyUserResponse(UserBase):
    """Public response profile for current authenticated user."""

    id: UUID  # int o'rniga UUID
    first_name: Optional[str] = Field(None, examples=[ExapleUser.first_name])  # None bo'lish imkoniyati berildi
    last_name: Optional[str] = Field(None, examples=[ExapleUser.last_name])
    is_active: bool = Field(None, examples=[ExapleUser.is_active])


class UserResponse(MyUserResponse):
    """Detailed response schema for admin user listings."""

    role: UserRole
    is_active: bool


class UserCreate(UserRegisterRequest):
    """Request schema for creating a new user (Admin only)."""

    role: UserRole = Field(examples=[ExapleUser.role], description="Role of the user being created")
    is_active: bool = Field(default=True, examples=[ExapleUser.is_active], description="Indicates if the user account is active")