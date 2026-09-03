from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field

from app.enums.all_enums import OrderStatus


class OrderItemResponse(BaseModel):
    id: UUID
    product_id: UUID
    quantity: int
    price: Decimal

    model_config = {"from_attributes": True}


class OrderResponse(BaseModel):
    id: UUID
    user_id: UUID
    total_amount: Decimal
    status: OrderStatus
    created_at: datetime
    orderItems: list[OrderItemResponse] = []

    model_config = {"from_attributes": True}


class OrderListResponse(BaseModel):
    items: list[OrderResponse]
    total: int