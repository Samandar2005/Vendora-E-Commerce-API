from uuid import UUID
from typing import TYPE_CHECKING
from sqlalchemy import String, Enum as SQLEnum, Boolean
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimeStampedModel
from app.enums.all_enums import UserRole

if TYPE_CHECKING:
    from app.models.store import Store
    from app.models.order import Order
    from app.models.payment import Payment

class User(TimeStampedModel):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)

    first_name: Mapped[Optional[str]] = mapped_column(nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(nullable=True)

    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), nullable=False, default=UserRole.CUSTOMER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    store: Mapped["Store | None"] = relationship(
        "Store",
        back_populates="seller", 
        uselist=False, 
        cascade="all, delete-orphan"
    )

    orders: Mapped[list["Order"]] = relationship(
        "Order",
        back_populates="user", 
        cascade="all, delete-orphan"
    )

    payments: Mapped[list["Payment"]] = relationship(
        "Payment",
        back_populates="user", 
        cascade="all, delete-orphan"
    )