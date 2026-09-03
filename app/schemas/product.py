from decimal import Decimal
from typing import List
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.category import CategoryResponse
from app.schemas.example import ExampleProduct


class ProductImageResponse(BaseModel):
    id: UUID
    product_id: UUID
    image_url: str
    is_main: bool

    model_config = ConfigDict(from_attributes=True)


class ProductBase(BaseModel):
    title: str = Field(
        json_schema_extra={"example": ExampleProduct.title},
        min_length=2,
        max_length=255,
    )
    description: str | None = Field(
        json_schema_extra={"example": ExampleProduct.description}, default=None
    )
    price: Decimal = Field(
        json_schema_extra={"example": ExampleProduct.price},
        gt=0,
        decimal_places=2,
    )
    stock: int = Field(
        json_schema_extra={"example": ExampleProduct.stock}, default=0, ge=0
    )
    is_active: bool = Field(
        json_schema_extra={"example": ExampleProduct.is_active}, default=True
    )


class ProductCreate(ProductBase):
    store_id: UUID
    category_id: UUID | None = None


class ProductUpdate(BaseModel):
    title: str | None = Field(
        json_schema_extra={"example": ExampleProduct.title},
        default=None,
        min_length=2,
        max_length=255,
    )
    description: str | None = Field(
        json_schema_extra={"example": ExampleProduct.description}, default=None
    )
    price: Decimal | None = Field(
        json_schema_extra={"example": ExampleProduct.price},
        default=None,
        gt=0,
        decimal_places=2,
    )
    stock: int | None = Field(
        json_schema_extra={"example": ExampleProduct.stock},
        default=None,
        ge=0,
    )
    is_active: bool | None = Field(
        json_schema_extra={"example": ExampleProduct.is_active}, default=None
    )
    category_id: UUID | None = Field(
        json_schema_extra={"example": ExampleProduct.category_id}, default=None
    )


class ProductFilterParams(BaseModel):
    store_id: UUID | None = None
    category_id: UUID | None = None
    min_price: Decimal | None = None
    max_price: Decimal | None = None
    search: str | None = None
    is_active: bool | None = None


class ProductResponse(ProductBase):
    id: UUID
    store_id: UUID
    category_id: UUID | None = None
    category: CategoryResponse | None = None
    
    # Mahsulot rasmlari ro'yxati qo'shildi
    images: List[ProductImageResponse] = []

    model_config = ConfigDict(from_attributes=True)