from uuid import UUID
from typing import TYPE_CHECKING
from sqlalchemy import String, Boolean, Text, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from decimal import Decimal

from app.models.base import TimeStampedModel

if TYPE_CHECKING:
    from app.models.store import Store
    from app.models.order import OrderItems

class Product(TimeStampedModel):
    __tablename__ = "products"

    store_id: Mapped[UUID] = mapped_column(ForeignKey("stores.id"), nullable=False)

    title: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    description: Mapped[Text | None] = mapped_column(Text, nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=2), nullable=False)
    stock: Mapped[int] = mapped_column(default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    store: Mapped["Store"] = relationship(
        back_populates="products"
    )

    orderItems: Mapped[list["OrderItems"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan"
    )
