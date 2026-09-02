from typing import Any
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_database
from app.api.deps import (
    allow_admin,
    allow_seller_or_admin,
    get_current_user,
    oauth2_schema,
)
from app.models.user import User
from app.schemas.category import (
    CategoryCreate,
    CategoryDetailResponse,
    CategoryResponse,
    CategoryUpdate,
)
from app.services.category_manager import CategoryManager

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("/", response_model=list[CategoryDetailResponse])
async def get_categories(
    session: AsyncSession = Depends(get_database),
) -> Any:
    """Barcha asosiy kategoriyalarni sub-kategoriyalari bilan olish."""
    return await CategoryManager.get_all_categories(session)


@router.get("/{category_id}", response_model=CategoryDetailResponse)
async def get_category(
    category_id: UUID, session: AsyncSession = Depends(get_database)
) -> Any:
    """ID bo'yicha bitta kategoriyani olish."""
    return await CategoryManager.get_category_by_id(category_id, session)


@router.post(
    "/",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_category(
    category_data: CategoryCreate,
    session: AsyncSession = Depends(get_database),
    current_user: User = Depends(allow_admin),  # Faqat adminlar
) -> Any:
    """Yangi kategoriya yaratish (Faqat Admin)."""
    return await CategoryManager.create_category(category_data, session)


@router.patch("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: UUID,
    category_data: CategoryUpdate,
    session: AsyncSession = Depends(get_database),
    current_user: User = Depends(allow_admin),
) -> Any:
    """Kategoriyani tahrirlash (Faqat Admin)."""
    return await CategoryManager.update_category(
        category_id, category_data, session
    )


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: UUID,
    session: AsyncSession = Depends(get_database),
    current_user: User = Depends(allow_admin),
) -> None:
    """Kategoriyani o'chirish (Faqat Admin)."""
    await CategoryManager.delete_category(category_id, session)

