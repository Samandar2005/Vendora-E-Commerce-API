from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.all_enums import OrderStatus
from app.models.order import Order, OrderItems
from app.models.product import Product
from app.models.store import Store
from app.models.user import User


@pytest.mark.asyncio
async def test_cart_add_get_remove_clear_and_stock_validation(
    client: AsyncClient,
    seller_headers: dict[str, str],
    buyer_headers: dict[str, str],
    product: Product,
) -> None:
    assert (await client.get("/cart/", headers=buyer_headers)).json() == {"items": [], "grand_total": "0.00"}
    added = await client.post(
        "/cart/items", json={"product_id": str(product.id), "quantity": 2}, headers=buyer_headers
    )
    assert added.status_code == 200
    assert added.json()["items"][0]["quantity"] == 2
    assert added.json()["items"][0]["total_price"] == "399.98"

    too_many = await client.post(
        "/cart/items", json={"product_id": str(product.id), "quantity": 100}, headers=buyer_headers
    )
    assert too_many.status_code == 400
    assert (await client.delete(f"/cart/items/{product.id}", headers=buyer_headers)).status_code == 200
    assert (await client.delete("/cart/", headers=buyer_headers)).status_code == 204
    assert (await client.get("/cart/", headers=buyer_headers)).json()["items"] == []
    assert (await client.post("/cart/items", json={"product_id": str(uuid4()), "quantity": 1}, headers=buyer_headers)).status_code == 404
    assert (await client.post("/cart/items", json={"product_id": str(product.id), "quantity": 1}, headers=seller_headers)).status_code == 200


@pytest.mark.asyncio
async def test_inactive_product_cannot_be_added_to_cart(
    client: AsyncClient,
    db_session: AsyncSession,
    buyer_headers: dict[str, str],
    seller_store: Store,
    category,
) -> None:
    inactive = Product(title="Inactive", price=10, stock=2, is_active=False, store_id=seller_store.id, category_id=category.id)
    db_session.add(inactive)
    await db_session.commit()
    await db_session.refresh(inactive)
    response = await client.post(
        "/cart/items", json={"product_id": str(inactive.id), "quantity": 1}, headers=buyer_headers
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_checkout_decrements_stock_clears_cart_and_cancellation_restores_it(
    client: AsyncClient,
    db_session: AsyncSession,
    buyer_headers: dict[str, str],
    product: Product,
    buyer_user: User,
) -> None:
    await client.post("/cart/items", json={"product_id": str(product.id), "quantity": 3}, headers=buyer_headers)
    checkout = await client.post("/orders/checkout", headers=buyer_headers)
    assert checkout.status_code == 201
    order = checkout.json()
    assert order["status"] == "PENDING"
    assert order["total_amount"] == "599.97"
    await db_session.refresh(product)
    assert product.stock == 7
    assert (await client.get("/cart/", headers=buyer_headers)).json()["items"] == []

    orders = await client.get("/orders/", headers=buyer_headers)
    assert orders.status_code == 200
    assert len(orders.json()) == 1
    cancel = await client.post(f"/orders/{order['id']}/cancel", headers=buyer_headers)
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "CANCELLED"
    await db_session.refresh(product)
    assert product.stock == 10 and product.is_active


@pytest.mark.asyncio
async def test_order_access_is_scoped_to_owner(
    client: AsyncClient,
    db_session: AsyncSession,
    buyer_headers: dict[str, str],
    seller_headers: dict[str, str],
    buyer_user: User,
    seller_user: User,
    product: Product,
) -> None:
    order = Order(user_id=buyer_user.id, total_amount=product.price, status=OrderStatus.PENDING)
    db_session.add(order)
    await db_session.flush()
    db_session.add(OrderItems(order_id=order.id, product_id=product.id, quantity=1, price=product.price))
    await db_session.commit()
    await db_session.refresh(order)
    assert (await client.get(f"/orders/{order.id}", headers=buyer_headers)).status_code == 200
    assert (await client.get(f"/orders/{order.id}", headers=seller_headers)).status_code == 404
    assert (await client.get(f"/orders/{uuid4()}", headers=buyer_headers)).status_code == 404
