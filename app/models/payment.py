from uuid import UUID
from typing import TYPE_CHECKING
from sqlalchemy import String, Enum as SQLEnum, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from decimal import Decimal

from app.models.base import TimeStampedModel
from app.schemas.payment import PaymentProvider, PaymentStatus

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.order import Order

class Payment(TimeStampedModel):
    __tablename__ = "payments"

    order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.id"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    provider: Mapped[PaymentProvider] = mapped_column(
        SQLEnum(PaymentProvider), 
        nullable=False, 
        default=PaymentProvider.MOCK
    )
    status: Mapped[PaymentStatus] = mapped_column(
        SQLEnum(PaymentStatus), 
        nullable=False, 
        default=PaymentStatus.PENDING
    )
    
    amount: Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD")

    transaction_id: Mapped[str | None] = mapped_column(
        String(255), 
        unique=True, 
        index=True, 
        nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(String(255), nullable=True)


    user: Mapped["User"] = relationship("User", back_populates="payments")

    order: Mapped["Order"] = relationship("Order", back_populates="payments")
