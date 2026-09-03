from decimal import Decimal
from uuid import UUID
from fastapi import HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.enums.all_enums import OrderStatus
from app.models.order import Order, OrderItems
from app.models.product import Product
from app.services.cart_manager import CartManager


class OrderManager:
    @classmethod
    async def create_order_from_cart(
        cls, db: AsyncSession, redis: Redis, user_id: UUID
    ) -> Order:
        """Redis savatidagi mahsulotlardan yangi Order yaratadi va stock'ni kamaytiradi."""
        # 1. Savatni Redis'dan olamiz
        cart = await CartManager.get_cart(redis, db, user_id)
        if not cart.items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Savatingiz bo'sh. Buyurtma berish uchun mahsulot qo'shing.",
            )

        product_ids = [item.product_id for item in cart.items]

        # 2. Bazadan mahsulotlarni bloklab olamiz (Race condition'ning oldini olish uchun)
        stmt = select(Product).where(Product.id.in_(product_ids)).with_for_update()
        result = await db.execute(stmt)
        products_db = {p.id: p for p in result.scalars().all()}

        # 3. Stock yetarliligini tekshiramiz va OrderItems ro'yxatini tayyorlaymiz
        order_items: list[OrderItems] = []
        total_amount = Decimal("0.00")

        for cart_item in cart.items:
            product = products_db.get(cart_item.product_id)

            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Mahsulot topilmadi: {cart_item.title}",
                )

            # Faqat faol mahsulotlarni sotib olish mumkin
            if not product.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"'{product.title}' mahsuloti hozirda sotuvda mavjud emas.",
                )

            if product.stock < cart_item.quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"'{product.title}' mahsulotidan omborda yetarli emas. Mavjud: {product.stock} ta",
                )

            # Ombordagi stock'ni kamaytiramiz
            product.stock -= cart_item.quantity

            # Agar stock 0 ga tushib qolsa, is_active'ni False qilamiz
            if product.stock == 0:
                product.is_active = False

            # Real bazadagi narx bo'yicha hisoblaymiz
            item_price = product.price
            total_amount += item_price * cart_item.quantity

            order_items.append(
                OrderItems(
                    product_id=product.id,
                    quantity=cart_item.quantity,
                    price=item_price,
                )
            )

        # 4. Order'ni saqlaymiz
        new_order = Order(
            user_id=user_id,
            total_amount=total_amount,
            status=OrderStatus.PENDING,
            orderItems=order_items,
        )

        db.add(new_order)
        await db.commit()

        # 5. AsyncIO xatoligini (MissingGreenlet) oldini olish uchun Order'ni OrderItems bilan qayta yuklaymiz
        stmt_order = (
            select(Order)
            .where(Order.id == new_order.id)
            .options(selectinload(Order.orderItems))
        )
        created_order_res = await db.execute(stmt_order)
        created_order = created_order_res.scalar_one()

        # 6. Buyurtma yaratilgach, Redis'dagi savatni tozalaymiz
        await CartManager.clear_cart(redis, user_id)

        return created_order

    @classmethod
    async def get_user_orders(cls, db: AsyncSession, user_id: UUID) -> list[Order]:
        """Foydalanuvchining barcha buyurtmalarini qaytaradi."""
        stmt = (
            select(Order)
            .where(Order.user_id == user_id)
            .options(selectinload(Order.orderItems))
            .order_by(Order.created_at.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @classmethod
    async def get_order_by_id(
        cls, db: AsyncSession, order_id: UUID, user_id: UUID
    ) -> Order:
        """Bitta buyurtma tafsilotlarini beradi."""
        stmt = (
            select(Order)
            .where(Order.id == order_id, Order.user_id == user_id)
            .options(selectinload(Order.orderItems))
        )
        result = await db.execute(stmt)
        order = result.scalar_one_or_none()

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Buyurtma topilmadi.",
            )
        return order

    @classmethod
    async def cancel_order(
        cls, db: AsyncSession, order_id: UUID, user_id: UUID
    ) -> Order:
        """Buyurtmani bekor qilish va omborga mahsulot sonini qaytarish."""
        stmt = (
            select(Order)
            .where(Order.id == order_id, Order.user_id == user_id)
            .options(selectinload(Order.orderItems))
            .with_for_update()
        )
        result = await db.execute(stmt)
        order = result.scalar_one_or_none()

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Buyurtma topilmadi.",
            )

        if order.status != OrderStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Faqat kutilayotgan (PENDING) holatdagi buyurtmalarni bekor qilish mumkin.",
            )

        # Statusni CANCELLED ga o'zgartiramiz
        order.status = OrderStatus.CANCELLED

        # Ombordagi stock'ni qaytaramiz
        for item in order.orderItems:
            product_stmt = (
                select(Product)
                .where(Product.id == item.product_id)
                .with_for_update()
            )
            prod_res = await db.execute(product_stmt)
            product = prod_res.scalar_one_or_none()
            if product:
                product.stock += item.quantity
                # Gar stock yana 0 dan oshsa, is_active'ni qayta True qilamiz
                if product.stock > 0:
                    product.is_active = True

        await db.commit()

        # Qayta yuklab javob beramiz
        stmt_order = (
            select(Order)
            .where(Order.id == order.id)
            .options(selectinload(Order.orderItems))
        )
        cancelled_order_res = await db.execute(stmt_order)
        return cancelled_order_res.scalar_one()