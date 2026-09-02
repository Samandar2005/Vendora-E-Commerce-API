"""Example data for Schemas."""

from datetime import datetime

from uuid import UUID
from app.enums.all_enums import UserRole

class ExapleUser:
    """Example user data for schemas."""

    email: str = "admin@vendora.com"
    password: str = "admin1234"
    first_name: str = "John"
    last_name: str = "Doe"
    role = UserRole.ADMIN

    is_active: bool = True

class ExampleCategory:
    """Example category data for schemas."""

    name: str = "Electronics"
    slug: str = "electronics"
    description: str = "All kinds of electronic devices and gadgets."
    parent_id: UUID | None = None
    created_at: datetime = datetime.now()

class ExampleProduct:
    """Example product data for schemas."""

    store_id: UUID | None = None
    category_id: UUID | None = None

    title: str = "Smartphone"
    description: str = "A high-end smartphone with the latest features."
    price: float = 699.99
    stock: int = 50
    is_active: bool = True
    
    created_at: datetime = datetime.now()

class ExampleStore:
    """Example store data for schemas."""

    seller_id: UUID | None = None

    name: str = "Example Store"
    slug: str = "example-store"
    description: str = "An example store for demonstration purposes."

    created_at: datetime = datetime.now()

class ExamplePayment:
    pass