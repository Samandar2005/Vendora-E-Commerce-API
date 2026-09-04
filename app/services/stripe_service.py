from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
import stripe

from app.core.config import get_settings
from app.enums.all_enums import OrderStatus, PaymentProvider, PaymentStatus
from app.models.order import Order
from app.models.payment import Payment
from app.tasks.email_tasks import (
    send_payment_success_email_task,
    send_refund_success_email_task,
)

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

        # 2. Line items tayyorlaymiz (Stripe summalarini tsentlarda qabul qiladi)
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

    @classmethod
    async def handle_webhook(
        cls, db: AsyncSession, payload: bytes, sig_header: str
    ) -> None:
        """Stripe Webhook eventlarini xavfsiz va idempotent qayta ishlash."""
        try:
            event = stripe.Webhook.construct_event(
                payload=payload,
                sig_header=sig_header,
                secret=get_settings().STRIPE_WEBHOOK_SECRET,
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Yaroqsiz payload")
        except stripe.error.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Signatura tasdiqlanmadi")

        event_dict = event.to_dict()
        event_type = event_dict.get("type")

        if event_type == "checkout.session.completed":
            session = event_dict.get("data", {}).get("object", {})
            metadata = session.get("metadata") or {}
            session_id = session.get("id")
            payment_intent_id = session.get("payment_intent")

            if not session_id:
                return

            # 1. DB dan Session ID bo'yicha to'lovni qidiramiz
            stmt_pay = select(Payment).where(Payment.transaction_id == session_id)
            res_pay = await db.execute(stmt_pay)
            payment = res_pay.scalar_one_or_none()

            # Idempotent tekshiruv
            if payment and payment.status == PaymentStatus.SUCCESS:
                print(f"⚠️ Event {session_id} allaqachon qayta ishlangan (Idempotent bypass).")
                return

            order_id_str = metadata.get("order_id")
            if not order_id_str:
                return

            try:
                order_id = UUID(order_id_str)
            except (ValueError, TypeError):
                return

            try:
                # 2. Order va unga bog'langan User-ni birga yuklab olish (joinedload)
                stmt_order = (
                    select(Order)
                    .options(joinedload(Order.user))
                    .where(Order.id == order_id)
                )
                res_order = await db.execute(stmt_order)
                order = res_order.scalar_one_or_none()

                status_changed = False

                if order and order.status != OrderStatus.PAID:
                    order.status = OrderStatus.PAID
                    status_changed = True

                if payment:
                    payment.status = PaymentStatus.SUCCESS
                    if payment_intent_id:
                        payment.transaction_id = payment_intent_id

                await db.commit()
                print(f"✅ Order {order_id} va Payment muvaffaqiyatli yangilandi.")

                # 3. Emailni avval bazadagi User-dan, agar bo'lmasa Stripe Session-dan olamiz
                if status_changed and order and payment:
                    user_email = None

                    # Bazadagi foydalanuvchi emaili
                    if order.user and getattr(order.user, "email", None):
                        user_email = order.user.email
                    else:
                        # Fallback: Stripe Checkout-da kiritilgan email
                        user_email = session.get("customer_details", {}).get("email")

                    if user_email:
                        send_payment_success_email_task.delay(
                            user_email=user_email,
                            order_id=str(order.id),
                            amount=str(payment.amount),
                            currency=payment.currency,
                        )
                        print(f"📧 Celery email task yuborildi: {user_email}")

            except Exception as ex:
                await db.rollback()
                print(f"❌ Webhook DB Xatolik: {ex}")
                raise HTTPException(status_code=500, detail=str(ex))

    @classmethod
    async def refund_payment(
        cls,
        db: AsyncSession,
        payment_id: UUID,
        reason: Optional[str] = "Customer request",
    ) -> Payment:
        """To'lovni Stripe va Baza orqali bekor qilish va pulni qaytarish."""
        stmt = select(Payment).where(Payment.id == payment_id)
        result = await db.execute(stmt)
        payment = result.scalar_one_or_none()

        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="To'lov topilmadi.",
            )

        if payment.status != PaymentStatus.SUCCESS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Faqat muvaffaqiyatli (SUCCESS) to'lovlarni qaytarish mumkin.",
            )

        try:
            # Stripe API orqali Refund yaratish (PaymentIntent ID ishlatiladi)
            stripe_refund = stripe.Refund.create(
                payment_intent=payment.transaction_id,
                reason="requested_by_customer",
            )

            payment.status = PaymentStatus.REFUNDED
            payment.refund_id = stripe_refund.id
            payment.refund_reason = reason

            # Order va uning User relatsiyasini birga yuklaymiz (joinedload)
            stmt_order = (
                select(Order)
                .options(joinedload(Order.user))
                .where(Order.id == payment.order_id)
            )
            res_order = await db.execute(stmt_order)
            order = res_order.scalar_one_or_none()

            if order:
                order.status = OrderStatus.CANCELLED

            await db.commit()

            # Emailni xavfsiz tekshirib olish
            user_email = None
            if order and order.user and getattr(order.user, "email", None):
                user_email = order.user.email
            elif payment:
                user_email = getattr(payment, "customer_email", None)

            if user_email and order:
                send_refund_success_email_task.delay(
                    user_email=user_email,
                    order_id=str(order.id),
                    amount=str(payment.amount),
                    currency=payment.currency,
                )
                print(f"📧 Refund email task yuborildi: {user_email}")

            await db.refresh(payment)
            return payment

        except stripe.error.StripeError as e:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stripe Refund xatoligi: {str(e)}",
            )
        except Exception as e:
            await db.rollback()
            print(f"❌ Refund jarayonida kutilmagan xatolik: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Refund xatoligi: {str(e)}",
            )

