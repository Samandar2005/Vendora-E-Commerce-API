from uuid import UUID
from typing import TYPE_CHECKING
from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from slugify import slugify

from app.models.base import TimeStampedModel

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.product import Product

class Store(TimeStampedModel):
    __tablename__ = "stores"

    seller_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    description: Mapped[Text | None] = mapped_column(Text, nullable=True)

    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    banner_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    seller: Mapped["User"] = relationship("User", back_populates="store")
    

    products: Mapped[list["Product"]] = relationship(
        back_populates="store", 
        cascade="all, delete-orphan"
    )

    @validates("name")
    def generate_slug(self, key: str, name: str) -> str:
        """Name o'zgarganda slug'ni avtomatik yaratadi."""
        if name:
            self.slug = slugify(name)
        return name
