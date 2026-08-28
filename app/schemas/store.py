from enum import Enum
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.user import UserResponse


class StoreCreate(BaseModel):
    name: str
    slug: str
    description: str | None = None


class StoreResponse(BaseModel):
    id: UUID
    seller_id: UUID
    name: str
    slug: str
    description: str | None = None

    created_at: datetime

    seller: UserResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class StoreEditRequest(BaseModel):
    name: str | None = None
    slug: str | None = None
    description: str | None = None

