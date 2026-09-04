from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_database as get_db
from app.api.deps import get_current_user
from app.models.user import User
from uuid import UUID
from app.schemas.payment import CreateCheckoutSessionRequest, CheckoutSessionResponse, PaymentResponse, RefundPaymentRequest
from app.services.stripe_service import StripeService
from fastapi import APIRouter, Depends, Query, HTTPException, status, Request, Header
from app.enums.all_enums import PaymentStatus, UserRole 
import stripe
from typing import List, Optional


router = APIRouter(prefix="/payments", tags=["Payments"])
STRIPE_WEBHOOK_SECRET="whsec_3340d300eea2d432a94662f78ac575432442b84ae6eca80887b61a1b367aca59"

@router.post("/create-checkout-session", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    payload: CreateCheckoutSessionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Stripe Checkout to'lov sessiyasini yaratish va URL olish."""
    return await StripeService.create_checkout_session(
        db=db, order_id=payload.order_id, user_id=current_user.id
    )

@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
    db: AsyncSession = Depends(get_db), # DB async session qo'shildi
):
    if not stripe_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stripe-Signature header missing",
        )

    payload = await request.body()

    # Barcha DB o'zgarishlari va event mantiqlari StripeService ichida bajariladi
    await StripeService.handle_webhook(
        db=db, payload=payload, sig_header=stripe_signature
    )

    return {"status": "success"}

@router.get("/my-payments", response_model=List[PaymentResponse])
async def get_my_payments(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Foydalanuvchiga tegishli barcha to'lovlar ro'yxatini olish."""
    return await StripeService.get_user_payments(
        db=db, user_id=current_user.id, limit=limit, offset=offset
    )


# 2. Barcha to'lovlarni ko'rish (Adminlar uchun)
@router.get("/all", response_model=List[PaymentResponse])
async def get_all_payments(
    status_filter: Optional[PaymentStatus] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Barcha to'lovlarni ko'rish (Faqat ADMIN va SUPERUSER uchun)."""
    # Admin huquqini tekshirish
    if current_user.role not in [UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ushbu ma'lumotlarni ko'rish uchun huquqingiz yetarli emas.",
        )
    return await StripeService.get_all_payments(
        db=db, status_filter=status_filter, limit=limit, offset=offset
    )


# 3. Muayyan to'lov ID'si bo'yicha ma'lumot olish
@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment_detail(
    payment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """To'lov haqida batafsil ma'lumot olish."""
    # Agar admin bo'lmasa, faqat o'ziga tegishli to'lovni ko'ra oladi
    user_id = None if current_user.role in [UserRole.ADMIN] else current_user.id
    return await StripeService.get_payment_by_id(
        db=db, payment_id=payment_id, user_id=user_id
    )


@router.post("/refund", response_model=PaymentResponse)
async def refund_payment(
    payload: RefundPaymentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Muvaffaqiyatli to'lovni bekor qilish va pulni qaytarish (Faqat Adminlar uchun)."""
    if current_user.role not in [UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ushbu amalni bajarish uchun admin huquqi talab etiladi.",
        )

    return await StripeService.refund_payment(
        db=db, payment_id=payload.payment_id, reason=payload.reason
    )