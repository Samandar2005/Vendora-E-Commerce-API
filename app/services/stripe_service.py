import stripe
from decimal import Decimal
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional

from app.core.config import get_settings
from app.models.order import Order
from app.models.payment import Payment
from app.enums.all_enums import OrderStatus, PaymentStatus, PaymentProvider

# Stripe API Key
stripe.api_key = get_settings().STRIPE_SECRET_KEY


class StripeService:
    @classmethod
    async def create_checkout_session(
        cls, db: AsyncSession, order_id: UUID, user_id: UUID
    ) -> dict:
        """Stripe Checkout Session yaratadi va to'lov URL manzilini qaytaradi."""
        # 1. Order va uning item'larini olamiz
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

        if order.status != OrderStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ushbu buyurtma uchun to'lov qilib bo'lmaydi yoki allaqachon to'langan.",
            )

        # 2. Line items tayyorlaymiz (Stripe summalami tsentlarda qabul qiladi)
        line_items = []
        for item in order.orderItems:
            unit_amount_cents = int(item.price * 100)
            line_items.append(
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": f"Product ID: {item.product_id}",
                        },
                        "unit_amount": unit_amount_cents,
                    },
                    "quantity": item.quantity,
                }
            )

        try:
            # 3. Stripe Checkout Session yaratamiz
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=line_items,
                mode="payment",
                success_url="https://example.com/payment-success?session_id={CHECKOUT_SESSION_ID}",
                cancel_url="https://example.com/payment-cancelled",
                metadata={
                    "order_id": str(order.id),
                    "user_id": str(user_id),
                },
            )

            # 4. DB'da Payment yozuvini yaratamiz
            payment = Payment(
                order_id=order.id,
                user_id=user_id,
                provider=PaymentProvider.STRIPE,
                status=PaymentStatus.PENDING,
                amount=order.total_amount,
                currency="USD",
                transaction_id=checkout_session.id,
            )
            db.add(payment)
            await db.commit()

            return {
                "checkout_url": checkout_session.url,
                "session_id": checkout_session.id,
            }

        except stripe.error.StripeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stripe xatoligi: {str(e)}",
            )


    @classmethod
    async def handle_webhook(
        cls, db: AsyncSession, payload: bytes, sig_header: str
    ) -> None:
        """Stripe Webhook eventlarini xavfsiz qayta ishlash."""
        try:
            event = stripe.Webhook.construct_event(
                payload=payload,
                sig_header=sig_header,
                secret=get_settings().STRIPE_WEBHOOK_SECRET,
            )
        except ValueError as e:
            print(f"❌ Webhook Payload Error: {e}")
            raise HTTPException(status_code=400, detail="Yaroqsiz payload")
        except stripe.error.SignatureVerificationError as e:
            print(f"❌ Webhook Signature Error: {e}")
            raise HTTPException(status_code=400, detail="Signatura tasdiqlanmadi")

        # Event va session obyektlarini qulay ishlash uchun dict'ga o'g'iramiz
        event_dict = event.to_dict()
        event_type = event_dict.get("type")

        if event_type == "checkout.session.completed":
            session = event_dict.get("data", {}).get("object", {})
            metadata = session.get("metadata") or {}
            
            order_id_str = metadata.get("order_id")
            session_id = session.get("id")

            print(f"🔍 Event: {event_type} | Session ID: {session_id} | Order ID: {order_id_str}")

            if not order_id_str:
                print("⚠️ Metadata ichidan order_id topilmadi (Stripe CLI trigger bo'lishi mumkin).")
                return

            try:
                order_id = UUID(order_id_str)
            except (ValueError, TypeError) as e:
                print(f"❌ UUID parsing xatosi: {e}")
                return

            try:
                # 1. Order statusini PAID qilish
                stmt_order = select(Order).where(Order.id == order_id)
                res_order = await db.execute(stmt_order)
                order = res_order.scalar_one_or_none()

                if order:
                    order.status = OrderStatus.PAID
                    print(f"✅ Order {order_id} statusi PAID ga o'zgartirildi.")

                # 2. Payment statusini SUCCESS qilish
                if session_id:
                    stmt_pay = select(Payment).where(Payment.transaction_id == session_id)
                    res_pay = await db.execute(stmt_pay)
                    payment = res_pay.scalar_one_or_none()

                    if payment:
                        payment.status = PaymentStatus.SUCCESS
                        print(f"✅ Payment {payment.id} statusi SUCCESS ga o'zgartirildi.")

                await db.commit()
            except Exception as ex:
                await db.rollback()
                print(f"❌ DB Xatolik: {ex}")
                raise HTTPException(status_code=500, detail=str(ex))


    @classmethod
    async def get_user_payments(
        cls, db: AsyncSession, user_id: UUID, limit: int = 20, offset: int = 0
    ) -> List[Payment]:
        """Foydalanuvchining o'z to'lovlari ro'yxatini qaytaradi."""
        stmt = (
            select(Payment)
            .where(Payment.user_id == user_id)
            .order_by(Payment.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    @classmethod
    async def get_all_payments(
        cls,
        db: AsyncSession,
        status_filter: Optional[PaymentStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Payment]:
        """Adminlar uchun barcha to'lovlarni ko'rish va status bo'yicha filterlash."""
        stmt = select(Payment).order_by(Payment.created_at.desc())
        
        if status_filter:
            stmt = stmt.where(Payment.status == status_filter)
            
        stmt = stmt.limit(limit).offset(offset)
        result = await db.execute(stmt)
        return result.scalars().all()

    @classmethod
    async def get_payment_by_id(
        cls, db: AsyncSession, payment_id: UUID, user_id: Optional[UUID] = None
    ) -> Payment:
        """To'lov haqida batafsil ma'lumot olish."""
        stmt = select(Payment).where(Payment.id == payment_id)
        if user_id:
            stmt = stmt.where(Payment.user_id == user_id)

        result = await db.execute(stmt)
        payment = result.scalar_one_or_none()

        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="To'lov topilmadi.",
            )
        return payment