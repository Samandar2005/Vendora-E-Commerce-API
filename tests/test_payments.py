from types import SimpleNamespace
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.all_enums import OrderStatus, PaymentProvider, PaymentStatus
from app.models.order import Order, OrderItems
from app.models.payment import Payment
from app.models.product import Product
from app.models.user import User


async def make_order(db_session: AsyncSession, user: User, product: Product) -> Order:
    order = Order(user_id=user.id, total_amount=product.price, status=OrderStatus.PENDING)
    db_session.add(order)
    await db_session.flush()
    db_session.add(OrderItems(order_id=order.id, product_id=product.id, quantity=1, price=product.price))
    await db_session.commit()
    await db_session.refresh(order)
    return order


@pytest.mark.asyncio
async def test_create_checkout_session_and_payment_lists(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    buyer_headers: dict[str, str],
    buyer_user: User,
    product: Product,
) -> None:
    order = await make_order(db_session, buyer_user, product)
    fake_session = SimpleNamespace(id="cs_test_123", url="https://checkout.test/session")
    monkeypatch.setattr("app.services.stripe_service.stripe.checkout.Session.create", lambda **kwargs: fake_session)

    created = await client.post("/payments/create-checkout-session", json={"order_id": str(order.id)}, headers=buyer_headers)
    assert created.status_code == 200
    assert created.json() == {"checkout_url": fake_session.url, "session_id": fake_session.id}
    payments = await client.get("/payments/my-payments", headers=buyer_headers)
    assert payments.status_code == 200
    assert payments.json()[0]["transaction_id"] == "cs_test_123"

    assert (await client.post("/payments/create-checkout-session", json={"order_id": str(uuid4())}, headers=buyer_headers)).status_code == 404


@pytest.mark.asyncio
async def test_payment_visibility_and_admin_filtering(
    client: AsyncClient,
    db_session: AsyncSession,
    buyer_headers: dict[str, str],
    seller_headers: dict[str, str],
    admin_headers: dict[str, str],
    buyer_user: User,
    seller_user: User,
    product: Product,
) -> None:
    buyer_order = await make_order(db_session, buyer_user, product)
    seller_order = await make_order(db_session, seller_user, product)
    own = Payment(order_id=buyer_order.id, user_id=buyer_user.id, provider=PaymentProvider.MOCK, status=PaymentStatus.SUCCESS, amount=product.price, currency="USD")
    other = Payment(order_id=seller_order.id, user_id=seller_user.id, provider=PaymentProvider.MOCK, status=PaymentStatus.FAILED, amount=product.price, currency="USD")
    db_session.add_all([own, other])
    await db_session.commit()
    await db_session.refresh(own)
    await db_session.refresh(other)

    assert (await client.get(f"/payments/{own.id}", headers=buyer_headers)).status_code == 200
    assert (await client.get(f"/payments/{other.id}", headers=buyer_headers)).status_code == 404
    assert (await client.get("/payments/all", headers=seller_headers)).status_code == 403
    all_payments = await client.get("/payments/all", params={"status_filter": "FAILED"}, headers=admin_headers)
    assert all_payments.status_code == 200
    assert len(all_payments.json()) == 1
    assert (await client.get("/payments/my-payments?limit=0", headers=buyer_headers)).status_code == 422


@pytest.mark.asyncio
async def test_refund_updates_payment_order_and_queues_email(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    admin_headers: dict[str, str],
    admin_user: User,
    product: Product,
) -> None:
    order = await make_order(db_session, admin_user, product)
    payment = Payment(order_id=order.id, user_id=admin_user.id, provider=PaymentProvider.STRIPE, status=PaymentStatus.SUCCESS, amount=product.price, currency="USD", transaction_id="pi_123")
    db_session.add(payment)
    await db_session.commit()
    await db_session.refresh(payment)
    monkeypatch.setattr("app.services.stripe_service.stripe.Refund.create", lambda **kwargs: SimpleNamespace(id="re_123"))
    email = SimpleNamespace(delay=lambda **kwargs: None)
    monkeypatch.setattr("app.services.stripe_service.send_refund_success_email_task", email)

    response = await client.post("/payments/refund", json={"payment_id": str(payment.id), "reason": "Changed mind"}, headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "REFUNDED"
    await db_session.refresh(order)
    assert order.status == OrderStatus.CANCELLED
    assert (await client.post("/payments/refund", json={"payment_id": str(uuid4())}, headers=admin_headers)).status_code == 404


@pytest.mark.asyncio
async def test_webhook_requires_signature_and_is_idempotent(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    buyer_user: User,
    product: Product,
) -> None:
    order = await make_order(db_session, buyer_user, product)
    payment = Payment(order_id=order.id, user_id=buyer_user.id, provider=PaymentProvider.STRIPE, status=PaymentStatus.PENDING, amount=product.price, currency="USD", transaction_id="cs_123")
    db_session.add(payment)
    await db_session.commit()

    assert (await client.post("/payments/webhook", content=b"{}" )).status_code == 400
    event = SimpleNamespace(to_dict=lambda: {"type": "checkout.session.completed", "data": {"object": {"id": "cs_123", "payment_intent": "pi_123", "metadata": {"order_id": str(order.id)}}}})
    monkeypatch.setattr("app.services.stripe_service.stripe.Webhook.construct_event", lambda **kwargs: event)
    monkeypatch.setattr("app.services.stripe_service.send_payment_success_email_task", SimpleNamespace(delay=lambda **kwargs: None))

    response = await client.post("/payments/webhook", content=b"payload", headers={"Stripe-Signature": "valid"})
    assert response.status_code == 200
    await db_session.refresh(payment)
    await db_session.refresh(order)
    assert payment.status == PaymentStatus.SUCCESS and order.status == OrderStatus.PAID
    assert (await client.post("/payments/webhook", content=b"payload", headers={"Stripe-Signature": "valid"})).status_code == 200
