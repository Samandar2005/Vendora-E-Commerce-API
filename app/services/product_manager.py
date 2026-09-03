import os
import uuid
from collections.abc import Sequence
from uuid import UUID

import aiofiles
from fastapi import HTTPException, UploadFile, status
from slugify import slugify
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.enums.all_enums import UserRole
from app.models.product import Product, ProductImage
from app.models.store import Store
from app.models.user import User
from app.schemas.product import ProductCreate, ProductFilterParams, ProductUpdate

UPLOAD_DIR = "media/uploads"


class ProductManager:

    @staticmethod
    async def create_product(
        product_data: ProductCreate,
        current_user: User,
        session: AsyncSession,
    ) -> Product:
        """Create a new product (Only store owner or Admin)."""
        store = await session.get(Store, product_data.store_id)
        if not store:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Biriktirilayotgan do'kon topilmadi.",
            )

        if (
            store.seller_id != current_user.id
            and current_user.role != UserRole.ADMIN
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Siz faqat o'zingizning do'koningizga mahsulot qo'sha olasiz.",
            )

        try:
            product_dict = product_data.model_dump()

            # Agar modelda slug bo'lmasa, slugify qismini olib tashlaymiz
            product = Product(**product_dict)

            session.add(product)
            await session.commit()

            return await ProductManager.get_product_by_id(product.id, session)

        except IntegrityError:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bunday nomli mahsulot allaqachon mavjud.",
            ) from None

    @staticmethod
    async def upload_images(
        product_id: UUID,
        files: list[UploadFile],
        current_user: User,
        session: AsyncSession,
    ) -> Product:
        """Upload product images and assign them to product."""
        product = await ProductManager.get_product_by_id(product_id, session)

        # Do'kon egasini tekshirish
        store = await session.get(Store, product.store_id)
        if (
            store
            and store.seller_id != current_user.id
            and current_user.role != UserRole.ADMIN
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Siz faqat o'zingizning mahsulotingizga rasm qo'sha olasiz.",
            )

        os.makedirs(UPLOAD_DIR, exist_ok=True)

        # Agar mahsulotda hali umuman rasm bo'lmasa, birinchi yuklangan rasm asosiy (is_main=True) bo'ladi
        has_main_image = any(img.is_main for img in product.images)

        for index, file in enumerate(files):
            # Fayl kengaytmasini ajratib olish va unikal nom berish
            file_extension = (
                file.filename.split(".")[-1]
                if file.filename and "." in file.filename
                else "jpg"
            )
            filename = f"{uuid.uuid4()}.{file_extension}"
            file_path = os.path.join(UPLOAD_DIR, filename)

            # Asinxron ravishda diskka yozish
            async with aiofiles.open(file_path, "wb") as out_file:
                content = await file.read()
                await out_file.write(content)

            # Baza uchun nisbiy silka yaratish
            image_url = f"/media/uploads/{filename}"

            is_main = False
            if not has_main_image and index == 0:
                is_main = True
                has_main_image = True

            product_image = ProductImage(
                product_id=product.id,
                image_url=image_url,
                is_main=is_main,
            )
            session.add(product_image)

        await session.commit()  # Rasmlarni bazaga saqlash
        return await ProductManager.get_product_by_id(product.id, session)

    @staticmethod
    async def get_all_products(
        filters: ProductFilterParams, session: AsyncSession
    ) -> Sequence[Product]:
        """Fetch all products with dynamic filtering and images."""
        stmt = select(Product).options(
            selectinload(Product.category),
            selectinload(Product.images),
        )

        if filters.store_id:
            stmt = stmt.where(Product.store_id == filters.store_id)
        if filters.category_id:
            stmt = stmt.where(Product.category_id == filters.category_id)
        if filters.is_active is not None:
            stmt = stmt.where(Product.is_active == filters.is_active)
        if filters.min_price is not None:
            stmt = stmt.where(Product.price >= filters.min_price)
        if filters.max_price is not None:
            stmt = stmt.where(Product.price <= filters.max_price)
        if filters.search:
            stmt = stmt.where(Product.title.ilike(f"%{filters.search}%"))

        result = await session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_product_by_id(
        product_id: UUID, session: AsyncSession
    ) -> Product:
        """Fetch single product by ID with category and images loaded."""
        stmt = (
            select(Product)
            .where(Product.id == product_id)
            .options(
                selectinload(Product.category),
                selectinload(Product.images),
            )
        )
        result = await session.execute(stmt)
        product = result.scalar_one_or_none()

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mahsulot topilmadi.",
            )
        return product

    @staticmethod
    async def update_product(
        product_id: UUID,
        product_data: ProductUpdate,
        current_user: User,
        session: AsyncSession,
    ) -> Product:
        """Update product details."""
        product = await ProductManager.get_product_by_id(product_id, session)

        store = await session.get(Store, product.store_id)
        if (
            store
            and store.seller_id != current_user.id
            and current_user.role != UserRole.ADMIN
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Siz faqat o'zingizning mahsulotingizni tahrirlay olasiz.",
            )

        update_data = product_data.model_dump(exclude_unset=True)
        if "title" in update_data and update_data["title"]:
            update_data["slug"] = slugify(update_data["title"])

        for key, value in update_data.items():
            setattr(product, key, value)

        try:
            await session.commit()  # Bazaga saqlash
            return await ProductManager.get_product_by_id(product.id, session)
        except IntegrityError:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bunday nomli mahsulot allaqachon mavjud.",
            ) from None

    @staticmethod
    async def delete_product(
        product_id: UUID, current_user: User, session: AsyncSession
    ) -> None:
        """Delete product."""
        product = await ProductManager.get_product_by_id(product_id, session)

        store = await session.get(Store, product.store_id)
        if (
            store
            and store.seller_id != current_user.id
            and current_user.role != UserRole.ADMIN
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Siz faqat o'zingizning mahsulotingizni o'chira olasiz.",
            )

        await session.delete(product)
        await session.commit()  # O'chirishni bazaga saqlash