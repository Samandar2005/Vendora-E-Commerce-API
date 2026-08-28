"""Routes for user profile management and admin actions."""

from collections.abc import Sequence
from typing import Optional, Union
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_database, allow_admin
from app.services.user import UserManager
from app.models.user import User, UserRole
from app.schemas.user import (
    MyUserResponse,
    UserChangePasswordRequest,
    UserEditRequest,
    UserResponse,
)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/",
    dependencies=[Depends(allow_admin)],
    response_model=Union[UserResponse, list[UserResponse]],
)
async def get_users(
    user_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_database),
) -> Union[Sequence[User], User]:
    """Get all users or a specific user by ID (Admin only)."""
    if user_id:
        return await UserManager.get_user_by_id(user_id, db)
    return await UserManager.get_all_users(db)


@router.get(
    "/me",
    response_model=MyUserResponse,
    name="get_my_user_data",
)
async def get_my_user(current_user: User = Depends(get_current_user)) -> User:
    """Get authenticated user profile."""
    return current_user


@router.post(
    "/{user_id}/make-admin",
    dependencies=[Depends(allow_admin)],
    status_code=status.HTTP_204_NO_CONTENT,
)
async def make_admin(user_id: UUID, db: AsyncSession = Depends(get_database)) -> None:
    """Promote user to ADMIN role (Admin only)."""
    await UserManager.change_role(UserRole.ADMIN, user_id, db)

@router.post(
    "/{user_id}/make-seller",
    dependencies=[Depends(allow_admin)],
    status_code=status.HTTP_204_NO_CONTENT,
)
async def make_seller(user_id: UUID, db: AsyncSession = Depends(get_database)) -> None:
    """Promote user to SELLER role (Admin only)."""
    await UserManager.change_role(UserRole.SELLER, user_id, db)

@router.post(
    "/{user_id}/password",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def change_password(
    user_id: UUID,
    user_data: UserChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
) -> None:
    """Change user password. Self or Admin only."""
    if current_user.id != user_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not authorized")
    await UserManager.change_password(user_id, user_data, db)


@router.post(
    "/{user_id}/ban",
    dependencies=[Depends(allow_admin)],
    status_code=status.HTTP_204_NO_CONTENT,
)
async def ban_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
) -> None:
    """Ban user account (Admin only)."""
    await UserManager.set_ban_status(user_id, True, current_user.id, db)


@router.post(
    "/{user_id}/unban",
    dependencies=[Depends(allow_admin)],
    status_code=status.HTTP_204_NO_CONTENT,
)
async def unban_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
) -> None:
    """Unban user account (Admin only)."""
    await UserManager.set_ban_status(user_id, False, current_user.id, db)


@router.put(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    response_model=MyUserResponse,
)
async def edit_user(
    user_id: UUID,
    user_data: UserEditRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
) -> User:
    """Update user details."""
    if current_user.id != user_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not authorized")
    return await UserManager.update_user(user_id, user_data, db)


@router.delete(
    "/{user_id}",
    dependencies=[Depends(allow_admin)],
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_user(user_id: UUID, db: AsyncSession = Depends(get_database)) -> None:
    """Delete user (Admin only)."""
    await UserManager.delete_user(user_id, db)