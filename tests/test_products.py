from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.all_enums import UserRole
from app.models.product import Product, ProductImage
from app.models.store import Store
from app.models.user import User


@pytest.mark.asyncio
async def test_create_product_success_by_seller(
    client: AsyncClient,
    seller_headers: dict[str, str],
    seller_store: Store,
    category,
) -> None:
    payload = {
        "title": "Seller Created Product",
        "description": "A product created by the seller.",
        "price": "19.99",
        "stock": 12,
        "is_active": True,
        "store_id": str(seller_store.id),
        "category_id": str(category.id),
    }

    response = await client.post("/products/", json=payload, headers=seller_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == payload["title"]
    assert data["store_id"] == str(seller_store.id)
    assert Decimal(str(data["price"])) == Decimal("19.99")


@pytest.mark.asyncio
async def test_create_product_success_by_admin(
    client: AsyncClient,
    admin_headers: dict[str, str],
    seller_store: Store,
    category,
) -> None:
    payload = {
        "title": "Admin Created Product",
        "description": "Created by admin for a seller store.",
        "price": "49.99",
        "stock": 8,
        "is_active": True,
        "store_id": str(seller_store.id),
        "category_id": str(category.id),
    }

    response = await client.post("/products/", json=payload, headers=admin_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == payload["title"]
    assert data["store_id"] == str(seller_store.id)


@pytest.mark.asyncio
async def test_create_product_forbidden_for_other_seller(
    client: AsyncClient,
    seller_headers: dict[str, str],
    other_store: Store,
    category,
) -> None:
    payload = {
        "title": "Forbidden Product",
        "description": "Seller attempts to add to another seller's store.",
        "price": "29.99",
        "stock": 5,
        "is_active": True,
        "store_id": str(other_store.id),
        "category_id": str(category.id),
    }

    response = await client.post("/products/", json=payload, headers=seller_headers)

    assert response.status_code == 403
    assert "o'zingizning do'koningizga" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_product_requires_authentication(
    client: AsyncClient,
    seller_store: Store,
    category,
) -> None:
    payload = {
        "title": "Unauthenticated Product",
        "description": "No token is included.",
        "price": "12.50",
        "stock": 2,
        "is_active": True,
        "store_id": str(seller_store.id),
        "category_id": str(category.id),
    }

    response = await client.post("/products/", json=payload)

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_product_validation_error_for_negative_price(
    client: AsyncClient,
    seller_headers: dict[str, str],
    seller_store: Store,
    category,
) -> None:
    payload = {
        "title": "Invalid Product",
        "description": "This should fail validation.",
        "price": -1,
        "stock": 2,
        "is_active": True,
        "store_id": str(seller_store.id),
        "category_id": str(category.id),
    }

    response = await client.post("/products/", json=payload, headers=seller_headers)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_products_public_access_and_filters(
    client: AsyncClient,
    db_session: AsyncSession,
    seller_store: Store,
    category,
) -> None:
    db_session.add_all(
        [
            Product(
                title="Apple Watch",
                description="Smart watch",
                price=150.00,
                stock=7,
                is_active=True,
                store_id=seller_store.id,
                category_id=category.id,
            ),
            Product(
                title="Orange Charger",
                description="Charged cable",
                price=35.00,
                stock=20,
                is_active=True,
                store_id=seller_store.id,
                category_id=category.id,
            ),
            Product(
                title="Keyboard",
                description="Mechanical keyboard",
                price=80.00,
                stock=4,
                is_active=False,
                store_id=seller_store.id,
                category_id=category.id,
            ),
        ]
    )
    await db_session.commit()

    list_response = await client.get("/products/")
    assert list_response.status_code == 200
    assert len(list_response.json()) >= 3

    filtered_response = await client.get(
        "/products/",
        params={
            "store_id": str(seller_store.id),
            "category_id": str(category.id),
            "min_price": "50",
            "max_price": "200",
            "search": "apple",
            "is_active": True,
        },
    )

    assert filtered_response.status_code == 200
    filtered_data = filtered_response.json()
    assert len(filtered_data) == 1
    assert filtered_data[0]["title"] == "Apple Watch"


@pytest.mark.asyncio
async def test_get_product_by_id_success_and_not_found(
    client: AsyncClient,
    db_session: AsyncSession,
    seller_store: Store,
    category,
) -> None:
    product = Product(
        title="Smartphone",
        description="Android smartphone",
        price=299.99,
        stock=8,
        is_active=True,
        store_id=seller_store.id,
        category_id=category.id,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    response = await client.get(f"/products/{product.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(product.id)
    assert data["title"] == "Smartphone"

    missing_response = await client.get(f"/products/{uuid4()}")
    assert missing_response.status_code == 404


@pytest.mark.asyncio
async def test_update_product_success_by_owner_and_admin(
    client: AsyncClient,
    seller_headers: dict[str, str],
    admin_headers: dict[str, str],
    db_session: AsyncSession,
    seller_store: Store,
    category,
) -> None:
    product = Product(
        title="Original Product",
        description="Before update",
        price=99.99,
        stock=5,
        is_active=True,
        store_id=seller_store.id,
        category_id=category.id,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    owner_response = await client.patch(
        f"/products/{product.id}",
        json={"title": "Updated By Owner", "price": "129.99"},
        headers=seller_headers,
    )
    assert owner_response.status_code == 200
    owner_data = owner_response.json()
    assert owner_data["title"] == "Updated By Owner"
    assert Decimal(str(owner_data["price"])) == Decimal("129.99")

    admin_response = await client.patch(
        f"/products/{product.id}",
        json={"title": "Updated By Admin", "stock": 42},
        headers=admin_headers,
    )
    assert admin_response.status_code == 200
    admin_data = admin_response.json()
    assert admin_data["title"] == "Updated By Admin"
    assert admin_data["stock"] == 42


@pytest.mark.asyncio
async def test_update_product_forbidden_for_unauthorized_seller(
    client: AsyncClient,
    seller_headers: dict[str, str],
    db_session: AsyncSession,
    other_store: Store,
    category,
) -> None:
    product = Product(
        title="Other Seller Product",
        description="Owned by another seller",
        price=89.99,
        stock=4,
        is_active=True,
        store_id=other_store.id,
        category_id=category.id,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    response = await client.patch(
        f"/products/{product.id}",
        json={"price": "99.99"},
        headers=seller_headers,
    )

    assert response.status_code == 403
    assert "tahrirlay" in response.json()["detail"]


@pytest.mark.asyncio
async def test_delete_product_success_by_admin_and_forbidden_for_unauthorized_seller(
    client: AsyncClient,
    admin_headers: dict[str, str],
    seller_headers: dict[str, str],
    db_session: AsyncSession,
    seller_store: Store,
    other_store: Store,
    category,
) -> None:
    owner_product = Product(
        title="Deleteable Product",
        description="This product can be deleted by owner.",
        price=55.00,
        stock=10,
        is_active=True,
        store_id=seller_store.id,
        category_id=category.id,
    )
    db_session.add(owner_product)
    await db_session.commit()
    await db_session.refresh(owner_product)

    admin_response = await client.delete(
        f"/products/{owner_product.id}",
        headers=admin_headers,
    )
    assert admin_response.status_code == 204

    other_product = Product(
        title="Protected Product",
        description="Only owner or admin can delete this.",
        price=65.00,
        stock=15,
        is_active=True,
        store_id=other_store.id,
        category_id=category.id,
    )
    db_session.add(other_product)
    await db_session.commit()
    await db_session.refresh(other_product)

    forbidden_response = await client.delete(
        f"/products/{other_product.id}",
        headers=seller_headers,
    )
    assert forbidden_response.status_code == 403
    assert "o'chira" in forbidden_response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_product_image_sets_first_image_as_main_and_checks_owner(
    client: AsyncClient,
    db_session: AsyncSession,
    seller_headers: dict[str, str],
    buyer_headers: dict[str, str],
    product: Product,
) -> None:
    response = await client.post(
        f"/products/{product.id}/images",
        files={"file": ("product.jpg", b"image-bytes", "image/jpeg")},
        headers=seller_headers,
    )
    assert response.status_code == 200
    image = (await db_session.execute(select(ProductImage).where(ProductImage.product_id == product.id))).scalar_one()
    assert image.is_main is True
    assert (await client.post(
        f"/products/{product.id}/images",
        files={"file": ("product.jpg", b"image-bytes", "image/jpeg")},
        headers=buyer_headers,
    )).status_code == 403
