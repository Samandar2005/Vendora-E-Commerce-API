from uuid import UUID
from typing import TYPE_CHECKING
from sqlalchemy import Enum as SQLEnum, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from decimal import Decimal

from app.models.base import TimeStampedModel
from app.enums.all_enums import OrderStatus

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.payment import Payment
    from app.models.product import Product

class Order(TimeStampedModel):
    __tablename__ = "orders"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    total_amount: Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=2), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(SQLEnum(OrderStatus), nullable=False, default=OrderStatus.PENDING)


    user: Mapped["User"] = relationship("User", back_populates="orders")

    orderItems: Mapped[list["OrderItems"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan"
    )

    payments: Mapped[list["Payment"]] = relationship(
            "Payment",
            back_populates="order",
            cascade="all, delete-orphan"
    )

class OrderItems(TimeStampedModel):
    order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.id"), nullable=False)
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"), nullable=False)

    quantity: Mapped[int] = mapped_column(default=1, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=2), nullable=False)

    order: Mapped["Order"] = relationship(
        back_populates="orderItems"
    )

    product: Mapped["Product"] = relationship(
        back_populates="orderItems"
    )