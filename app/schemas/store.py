from enum import Enum
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.user import UserResponse
from app.schemas.example import ExampleStore


class StoreCreate(BaseModel):
    name: str = Field(examples=[ExampleStore.name])
    description: str | None = Field(examples=[ExampleStore.description], default=None)


class StoreResponse(BaseModel):
    id: UUID
    seller_id: UUID
    name: str = Field(examples=[ExampleStore.name])
    slug: str = Field(examples=[ExampleStore.slug])
    description: str | None = Field(examples=[ExampleStore.description], default=None)

    created_at: datetime

    seller: UserResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class StoreEditRequest(BaseModel):
    name: str | None = Field(examples=[ExampleStore.name], default=None)
    description: str | None = Field(examples=[ExampleStore.description], default=None)

