import asyncio
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.enums.all_enums import UserRole
from app.models.product import Category, Product
from app.models.store import Store
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.schemas.product import ProductCreate, ProductUpdate
from app.schemas.store import StoreCreate, StoreEditRequest
from app.services.category_manager import CategoryManager
from app.services.product_manager import ProductManager
from app.services.store_manager import StoreManager
from app.services.user import UserManager


class FakeResult:
    def __init__(self, value=None):
        self._value = value

    def scalar_one_or_none(self):
        return self._value

    def scalars(self):
        return self

    def all(self):
        if self._value is None:
            return []
        if isinstance(self._value, list):
            return self._value
        return [self._value]


class BaseFakeSession:
    def __init__(self):
        self.added = []
        self.deleted = None

    async def flush(self):
        return None

    async def refresh(self, obj):
        return None

    async def delete(self, obj):
        self.deleted = obj

    def add(self, obj):
        self.added.append(obj)

    async def get(self, model, obj_id):
        return None

    async def execute(self, statement):
        return FakeResult(None)


class FakeCategorySession(BaseFakeSession):
    def __init__(self, category=None):
        super().__init__()
        self.category = category

    async def execute(self, statement):
        return FakeResult(self.category)


class FakeStoreSession(BaseFakeSession):
    def __init__(self, store=None):
        super().__init__()
        self.store = store

    async def get(self, model, obj_id):
        if self.store and self.store.id == obj_id:
            return self.store
        return None

    async def execute(self, statement):
        return FakeResult(self.store)


class FakeProductSession(BaseFakeSession):
    def __init__(self, store=None, product=None):
        super().__init__()
        self.store = store
        self.product = product

    async def get(self, model, obj_id):
        if model is Store and self.store and self.store.id == obj_id:
            return self.store
        return None

    async def execute(self, statement):
        return FakeResult(self.product)

    def add(self, obj):
        self.added.append(obj)
        if isinstance(obj, Product):
            self.product = obj


def make_user(role=UserRole.SELLER):
    return User(
        id=uuid4(),
        email=f"{uuid4()}@example.com",
        hashed_password="hashed",
        first_name="Seller",
        last_name="User",
        role=role,
        is_active=True,
    )


def test_store_manager_creates_store_with_slug_and_owner_id():
    current_user = make_user()
    session = BaseFakeSession()

    created_store = asyncio.run(
        StoreManager.create_store(
            StoreCreate(name="Azad Store", description="Electronics store"),
            current_user,
            session,
        )
    )

    assert created_store.name == "Azad Store"
    assert created_store.slug == "azad-store"
    assert created_store.seller_id == current_user.id
    assert session.added


def test_category_manager_auto_generates_slug_and_updates_name():
    category = Category(
        id=uuid4(),
        name="Office Supplies",
        slug="office-supplies",
        description="Stationery and stationery accessories",
    )
    session = FakeCategorySession(category=category)

    created = asyncio.run(
        CategoryManager.create_category(
            CategoryCreate(name="Home Decor", description="Decor items"),
            session,
        )
    )
    assert created.slug == "home-decor"

    updated = asyncio.run(
        CategoryManager.update_category(
            category.id,
            CategoryUpdate(name="Office Essentials", description="Updated description"),
            session,
        )
    )
    assert updated.slug == "office-essentials"
    assert updated.description == "Updated description"


def test_product_manager_only_allows_owner_or_admin_to_create_product():
    current_user = make_user(role=UserRole.SELLER)
    store = Store(
        id=uuid4(),
        name="Byte Mart",
        slug="byte-mart",
        seller_id=current_user.id,
    )
    session = FakeProductSession(store=store)
    product_data = ProductCreate(
        title="Gaming Laptop",
        description="Laptop for developers",
        price=Decimal("1299.99"),
        stock=8,
        store_id=store.id,
        category_id=None,
        is_active=True,
    )

    created_product = asyncio.run(
        ProductManager.create_product(product_data, current_user, session)
    )
    assert created_product.title == "Gaming Laptop"
    assert created_product.store_id == store.id

    different_user = make_user(role=UserRole.CUSTOMER)
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(ProductManager.create_product(product_data, different_user, session))

    assert exc_info.value.status_code == 403


def test_product_manager_rejects_updates_for_non_owner():
    seller = make_user(role=UserRole.SELLER)
    store = Store(id=uuid4(), name="Alpha Shop", slug="alpha-shop", seller_id=seller.id)
    product = Product(
        id=uuid4(),
        store_id=store.id,
        title="Mouse",
        description="Wireless mouse",
        price=Decimal("25.00"),
        stock=10,
        is_active=True,
    )
    session = FakeProductSession(store=store, product=product)

    another_user = make_user(role=UserRole.CUSTOMER)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            ProductManager.update_product(
                product.id,
                ProductUpdate(title="Updated Mouse"),
                another_user,
                session,
            )
        )

    assert exc_info.value.status_code == 403


def test_user_manager_prevents_self_ban_action():
    current_user = make_user(role=UserRole.ADMIN)
    session = BaseFakeSession()

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(UserManager.set_ban_status(current_user.id, True, current_user.id, session))

    assert exc_info.value.status_code == 400


def test_store_and_product_lookup_failures_return_404():
    session = BaseFakeSession()

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(StoreManager.get_store_by_id(uuid4(), session))
    assert exc_info.value.status_code == 404

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(ProductManager.get_product_by_id(uuid4(), session))
    assert exc_info.value.status_code == 404

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(CategoryManager.get_category_by_id(uuid4(), session))
    assert exc_info.value.status_code == 404
