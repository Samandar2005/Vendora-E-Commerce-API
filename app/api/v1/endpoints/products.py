from typing import Any
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import allow_seller_or_admin, get_current_user, oauth2_schema
from app.core.database import get_database
from app.models.user import User
from app.schemas.product import (
    ProductCreate,
    ProductFilterParams,
    ProductResponse,
    ProductUpdate,
)
from app.services.product_manager import ProductManager

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("/", response_model=list[ProductResponse])
async def get_products(
    filters: ProductFilterParams = Depends(),
    session: AsyncSession = Depends(get_database),
) -> Any:
    """Barcha mahsulotlarni filtrlash va qidiruv imkoniyati bilan olish (Ochiq API)."""
    return await ProductManager.get_all_products(filters, session)


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: UUID, session: AsyncSession = Depends(get_database)
) -> Any:
    """ID bo'yicha bitta mahsulotni olish (Ochiq API)."""
    return await ProductManager.get_product_by_id(product_id, session)


@router.post(
    "/",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(oauth2_schema), Depends(allow_seller_or_admin)],
)
async def create_product(
    product_data: ProductCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_database),
) -> Any:
    """Yangi mahsulot yaratish (Faqat Sotuvchi va Admin)."""
    return await ProductManager.create_product(
        product_data, current_user, session
    )


@router.patch(
    "/{product_id}",
    response_model=ProductResponse,
    dependencies=[Depends(oauth2_schema), Depends(allow_seller_or_admin)],
)
async def update_product(
    product_id: UUID,
    product_data: ProductUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_database),
) -> Any:
    """Mahsulotni tahrirlash (Faqat Sotuvchi va Admin)."""
    return await ProductManager.update_product(
        product_id, product_data, current_user, session
    )


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(oauth2_schema), Depends(allow_seller_or_admin)],
)
async def delete_product(
    product_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_database),
) -> None:
    """Mahsulotni o'chirish (Faqat Sotuvchi va Admin)."""
    await ProductManager.delete_product(product_id, current_user, session)