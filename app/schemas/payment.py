from enum import Enum
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class PaymentProvider(str, Enum):
    STRIPE = "STRIPE"
    MOCK = "MOCK"


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class PaymentCreate(BaseModel):
    order_id: UUID
    provider: PaymentProvider
    amount: Decimal = Field(..., gt=0, decimal_places=2)


class PaymentResponse(BaseModel):
    id: UUID
    order_id: UUID
    provider: PaymentProvider
    status: PaymentStatus
    amount: Decimal
    currency: str
    transaction_id: str | None = None
    error_message: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)