from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, ForeignKey, Numeric, String, Text

from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimeStampedModel

if TYPE_CHECKING:
    from app.models.order import OrderItems
    from app.models.store import Store


class Category(TimeStampedModel):
    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    slug: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), nullable=True
    )
    parent: Mapped["Category | None"] = relationship(
        "Category", remote_side="Category.id", back_populates="subcategories"
    )
    subcategories: Mapped[list["Category"]] = relationship(
        "Category", back_populates="parent", cascade="all, delete-orphan"
    )

    products: Mapped[list["Product"]] = relationship(
        back_populates="category"  # Kategoriya o'chsa mahsulotlar o'chib ketmasligi uchun delete-orphan o'chirildi
    )


class Product(TimeStampedModel):
    __tablename__ = "products" 

    store_id: Mapped[UUID] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    category_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )

    title: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2), nullable=False
    )
    stock: Mapped[int] = mapped_column(default=0)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    images: Mapped[list["ProductImage"]] = relationship(
        "ProductImage",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductImage.is_main.desc()",
    )

    store: Mapped["Store"] = relationship(back_populates="products")
    category: Mapped["Category | None"] = relationship(
        "Category", back_populates="products"
    )
    orderItems: Mapped[list["OrderItems"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )


class ProductImage(TimeStampedModel):
    __tablename__ = "product_images"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    is_main: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    product: Mapped["Product"] = relationship("Product", back_populates="images")