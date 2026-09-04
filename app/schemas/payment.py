from enum import Enum
from typing import Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field
from app.enums.all_enums import PaymentProvider, PaymentStatus

class PaymentCreate(BaseModel):
    order_id: UUID
    provider: PaymentProvider
    amount: Decimal = Field(..., gt=0, decimal_places=2)


class PaymentResponse(BaseModel):
    id: UUID
    order_id: UUID
    user_id: UUID
    provider: PaymentProvider
    status: PaymentStatus
    amount: Decimal
    currency: str
    transaction_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CreateCheckoutSessionRequest(BaseModel):
    order_id: UUID

class CheckoutSessionResponse(BaseModel):
    checkout_url: str
    session_id: str


class RefundPaymentRequest(BaseModel):
    payment_id: UUID
    reason: Optional[str] = "Mijoz so'rovi bo'yicha qaytarildi"

