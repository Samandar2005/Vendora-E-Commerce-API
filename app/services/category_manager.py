from collections.abc import Sequence
from uuid import UUID
from fastapi import HTTPException, status
from slugify import slugify
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.product import Category
from app.schemas.category import CategoryCreate, CategoryUpdate


class CategoryManager:

    @staticmethod
    async def create_category(
        category_data: CategoryCreate, session: AsyncSession
    ) -> Category:
        """Create new category with slug."""
        try:
            cat_dict = category_data.model_dump()
            cat_dict["slug"] = slugify(category_data.name)

            category = Category(**cat_dict)
            session.add(category)

            await session.flush()
            await session.refresh(category)
            return category

        except IntegrityError:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bunday nomli kategoriya allaqachon mavjud.",
            ) from None

    @staticmethod
    async def get_all_categories(session: AsyncSession) -> Sequence[Category]:
        """Fetch root categories with subcategories."""
        stmt = (
            select(Category)
            .where(Category.parent_id.is_(None))
            .options(selectinload(Category.subcategories))
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_category_by_id(
        category_id: UUID, session: AsyncSession
    ) -> Category:
        """Fetch single category with subcategories."""
        stmt = (
            select(Category)
            .where(Category.id == category_id)
            .options(selectinload(Category.subcategories))
        )
        result = await session.execute(stmt)
        category = result.scalar_one_or_none()

        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Kategoriya topilmadi.",
            )
        return category

    @staticmethod
    async def update_category(
        category_id: UUID,
        category_data: CategoryUpdate,
        session: AsyncSession,
    ) -> Category:
        """Update category attributes."""
        category = await CategoryManager.get_category_by_id(
            category_id, session
        )
        update_data = category_data.model_dump(exclude_unset=True)

        if "name" in update_data:
            update_data["slug"] = slugify(update_data["name"])

        for key, value in update_data.items():
            setattr(category, key, value)

        try:
            await session.flush()
            await session.refresh(category)
            return category
        except IntegrityError:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bunday nomli kategoriya allaqachon mavjud.",
            ) from None

    @staticmethod
    async def delete_category(category_id: UUID, session: AsyncSession) -> None:
        """Delete category."""
        category = await CategoryManager.get_category_by_id(
            category_id, session
        )
        await session.delete(category)
        await session.flush()

