from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.v1.endpoints import auth as auth_endpoint
from app.api.v1.endpoints import products as products_endpoint
from app.api.v1.endpoints import stores as stores_endpoint
from app.enums.all_enums import UserRole
from app.main import app
from app.models.product import Category, Product
from app.models.user import User


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def make_user(email="seller@example.com", role=UserRole.SELLER):
    return User(
        id=uuid4(),
        email=email,
        hashed_password="hashed",
        first_name="Test",
        last_name="Seller",
        role=role,
        is_active=True,
    )


def test_register_endpoint_returns_tokens(client, monkeypatch):
    async def fake_register(user_data, session):
        assert user_data.email == "newuser@example.com"
        return "access-token", "refresh-token"

    monkeypatch.setattr(auth_endpoint.UserManager, "register", staticmethod(fake_register))
    app.dependency_overrides[auth_endpoint.get_database] = lambda: None

    response = client.post(
        "/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "StrongPass123",
            "first_name": "New",
            "last_name": "User",
        },
    )

    assert response.status_code == 201
    assert response.json()["access_token"] == "access-token"
    assert response.json()["refresh_token"] == "refresh-token"
    assert response.json()["token_type"] == "bearer"


def test_login_endpoint_rejects_invalid_credentials(client, monkeypatch):
    async def fake_login(user_data, session):
        raise HTTPException(400, detail="Invalid email or password")

    monkeypatch.setattr(auth_endpoint.UserManager, "login", staticmethod(fake_login))
    app.dependency_overrides[auth_endpoint.get_database] = lambda: None

    response = client.post(
        "/auth/login/",
        json={"email": "bad@example.com", "password": "wrongpass"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid email or password"


def test_products_endpoint_returns_filtered_products(client, monkeypatch):
    product = Product(
        id=uuid4(),
        store_id=uuid4(),
        category_id=None,
        title="Laptop Pro",
        description="Thin and fast laptop",
        price=Decimal("1999.99"),
        stock=10,
        is_active=True,
        category=None,
    )

    async def fake_get_all_products(filters, session):
        assert filters.search == "laptop"
        return [product]

    monkeypatch.setattr(products_endpoint.ProductManager, "get_all_products", staticmethod(fake_get_all_products))
    app.dependency_overrides[products_endpoint.get_database] = lambda: None

    response = client.get("/products/?search=laptop")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["title"] == "Laptop Pro"
    assert payload[0]["price"] == "1999.99"


def test_store_creation_endpoint_accepts_seller_auth(client, monkeypatch):
    current_user = make_user(email="seller@example.com", role=UserRole.SELLER)

    async def fake_create_store(store_data, user, session):
        assert user.email == current_user.email
        return type(
            "StoreStub",
            (),
            {
                "id": uuid4(),
                "seller_id": user.id,
                "name": store_data.name,
                "slug": "test-store",
                "description": store_data.description,
                "created_at": datetime.now(timezone.utc),
                "seller": user,
            },
        )()

    monkeypatch.setattr(stores_endpoint.StoreManager, "create_store", staticmethod(fake_create_store))
    app.dependency_overrides[stores_endpoint.get_database] = lambda: None
    app.dependency_overrides[stores_endpoint.get_current_user] = lambda: current_user
    app.dependency_overrides[stores_endpoint.oauth2_schema] = lambda: current_user
    app.dependency_overrides[stores_endpoint.allow_seller_or_admin] = lambda: current_user

    response = client.post(
        "/stores/",
        json={"name": "Test Store", "description": "A valid seller-created store"},
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Test Store"
    assert response.json()["slug"] == "test-store"
