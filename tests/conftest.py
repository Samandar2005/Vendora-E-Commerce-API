from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_database
from app.core.security import AuthManager
from app.enums.all_enums import UserRole
from app.main import app
from app.models.base import Base
from app.models.order import Order, OrderItems
from app.models.payment import Payment
from app.models.product import Category, Product
from app.models.store import Store
from app.models.user import User


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh in-memory SQLite database for each test."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async API client backed by the in-memory test database."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_database] = override_get_db

    try:
        async with AsyncClient(app=app, base_url="http://test") as async_client:
            yield async_client
    except TypeError:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as async_client:
            yield async_client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    user = User(
        email="admin@example.com",
        first_name="Admin",
        last_name="User",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def seller_user(db_session: AsyncSession) -> User:
    user = User(
        email="seller@example.com",
        first_name="Seller",
        last_name="User",
        role=UserRole.SELLER,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def buyer_user(db_session: AsyncSession) -> User:
    user = User(
        email="buyer@example.com",
        first_name="Buyer",
        last_name="User",
        role=UserRole.CUSTOMER,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def admin_headers(admin_user: User) -> dict[str, str]:
    token = AuthManager.encode_token(admin_user)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def seller_headers(seller_user: User) -> dict[str, str]:
    token = AuthManager.encode_token(seller_user)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def buyer_headers(buyer_user: User) -> dict[str, str]:
    token = AuthManager.encode_token(buyer_user)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def category(db_session: AsyncSession) -> Category:
    item = Category(name="Electronics", slug="electronics", description="Electronic items")
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    return item


@pytest_asyncio.fixture
async def seller_store(db_session: AsyncSession, seller_user: User) -> Store:
    store = Store(name="Seller Store", slug="seller-store", description="Seller main store", seller_id=seller_user.id)
    db_session.add(store)
    await db_session.commit()
    await db_session.refresh(store)
    return store


@pytest_asyncio.fixture
async def other_seller_user(db_session: AsyncSession) -> User:
    user = User(
        email="other-seller@example.com",
        first_name="Other",
        last_name="Seller",
        role=UserRole.SELLER,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def other_store(db_session: AsyncSession, other_seller_user: User) -> Store:
    store = Store(name="Other Store", slug="other-store", description="Another seller store", seller_id=other_seller_user.id)
    db_session.add(store)
    await db_session.commit()
    await db_session.refresh(store)
    return store


@pytest_asyncio.fixture
async def product(db_session: AsyncSession, seller_store: Store, category: Category) -> Product:
    item = Product(
        title="Apple Laptop",
        description="Laptop for everyday use",
        price=199.99,
        stock=10,
        is_active=True,
        store_id=seller_store.id,
        category_id=category.id,
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    return item
