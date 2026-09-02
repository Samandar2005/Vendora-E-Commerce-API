from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.example import ExampleCategory

class CategoryBase(BaseModel):
    name: str = Field(examples=[ExampleCategory.name], min_length=2, max_length=255)
    description: str | None = Field(examples=[ExampleCategory.description], default=None)
    parent_id: UUID | None = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: str | None = Field(examples=[ExampleCategory.name], default=None, min_length=2, max_length=255)
    description: str | None = Field(examples=[ExampleCategory.description], default=None)
    parent_id: UUID | None = None


class CategoryResponse(CategoryBase):
    id: UUID
    slug: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CategoryDetailResponse(CategoryResponse):
    subcategories: list[CategoryResponse] = []

