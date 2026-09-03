from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field


class CartItemAdd(BaseModel):
    product_id: UUID
    quantity: int = Field(default=1, gt=0)


class CartItemUpdate(BaseModel):
    quantity: int = Field(gt=0)


class CartItemResponse(BaseModel):
    product_id: UUID
    title: str
    price: Decimal
    image_url: str | None = None
    quantity: int
    total_price: Decimal


class CartResponse(BaseModel):
    items: list[CartItemResponse] = []
    grand_total: Decimal = Decimal("0.00")