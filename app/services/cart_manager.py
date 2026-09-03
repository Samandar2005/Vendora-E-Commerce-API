import json
from decimal import Decimal
from uuid import UUID
from fastapi import HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.product import Product
from app.schemas.cart import CartItemAdd, CartItemResponse, CartResponse


class CartManager:
    @staticmethod
    def _get_cart_key(user_id: UUID) -> str:
        return f"cart:{user_id}"

    @classmethod
    async def get_cart(cls, redis: Redis, db: AsyncSession, user_id: UUID) -> CartResponse:
        """Foydalanuvchi savatidagi barcha mahsulotlarni va narxlarni hisoblab qaytaradi."""
        cart_key = cls._get_cart_key(user_id)
        raw_cart = await redis.get(cart_key)

        if not raw_cart:
            return CartResponse(items=[], grand_total=Decimal("0.00"))

        cart_data: dict[str, int] = json.loads(raw_cart)  # {"product_id_str": quantity}
        if not cart_data:
            return CartResponse(items=[], grand_total=Decimal("0.00"))

        product_ids = [UUID(pid) for pid in cart_data.keys()]

        # Bazadan mahsulotlarni va ularning birinchi rasmini olamiz
        stmt = (
            select(Product)
            .where(Product.id.in_(product_ids))
            .options(selectinload(Product.images))
        )
        result = await db.execute(stmt)
        products = result.scalars().all()

        items_response: list[CartItemResponse] = []
        grand_total = Decimal("0.00")

        for product in products:
            qty = cart_data.get(str(product.id), 0)
            if qty <= 0:
                continue

            main_image = next((img.image_url for img in product.images if img.is_main), None)
            if not main_image and product.images:
                main_image = product.images[0].image_url

            item_total = product.price * qty
            grand_total += item_total

            items_response.append(
                CartItemResponse(
                    product_id=product.id,
                    title=product.title,
                    price=product.price,
                    image_url=main_image,
                    quantity=qty,
                    total_price=item_total,
                )
            )

        return CartResponse(items=items_response, grand_total=grand_total)

    @classmethod
    async def add_item(
        cls, redis: Redis, db: AsyncSession, user_id: UUID, item_data: CartItemAdd
    ) -> CartResponse:
        """Savatga mahsulot qo'shadi yoki miqdorini oshiradi."""
        # Product va stock mavjudligini tekshiramiz
        stmt = select(Product).where(Product.id == item_data.product_id)
        result = await db.execute(stmt)
        product = result.scalar_one_or_none()

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Mahsulot topilmadi."
            )

        cart_key = cls._get_cart_key(user_id)
        raw_cart = await redis.get(cart_key)
        cart_data: dict[str, int] = json.loads(raw_cart) if raw_cart else {}

        current_qty = cart_data.get(str(item_data.product_id), 0)
        new_qty = current_qty + item_data.quantity

        if product.stock < new_qty:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Omborda yetarli mahsulot yo'q. Mavjud: {product.stock} ta",
            )

        cart_data[str(item_data.product_id)] = new_qty

        # Redis'da saqlash (masalan 14 kun TTL bilan)
        await redis.set(cart_key, json.dumps(cart_data), ex=14 * 86400)

        return await cls.get_cart(redis, db, user_id)

    @classmethod
    async def remove_item(
        cls, redis: Redis, db: AsyncSession, user_id: UUID, product_id: UUID
    ) -> CartResponse:
        """Savatdan mahsulotni o'chiradi."""
        cart_key = cls._get_cart_key(user_id)
        raw_cart = await redis.get(cart_key)

        if raw_cart:
            cart_data: dict[str, int] = json.loads(raw_cart)
            cart_data.pop(str(product_id), None)
            await redis.set(cart_key, json.dumps(cart_data), ex=14 * 86400)

        return await cls.get_cart(redis, db, user_id)

    @classmethod
    async def clear_cart(cls, redis: Redis, user_id: UUID) -> None:
        """Savatni tozalash (Checkout'dan so'ng chaqiriladi)."""
        cart_key = cls._get_cart_key(user_id)
        await redis.delete(cart_key)