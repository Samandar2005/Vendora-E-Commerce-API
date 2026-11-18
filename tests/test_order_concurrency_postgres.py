import asyncio
import os
from collections.abc import AsyncIterator
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.schema import CreateSchema, DropSchema

from app.enums.all_enums import UserRole
from app.models.base import Base
from app.models.order import Order
from app.models.product import Product
from app.models.store import Store
from app.models.user import User
from app.schemas.cart import CartItemAdd
from app.services.cart_manager import CartManager
from app.services.order_manager import OrderManager


@pytest_asyncio.fixture
async def postgres_sessions() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    url = os.getenv("VENDORA_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set VENDORA_TEST_DATABASE_URL to run PostgreSQL integration tests")

    schema = f"vendora_test_{uuid4().hex}"
    engine = create_async_engine(url, connect_args={"server_settings": {"search_path": schema}})
    try:
        async with engine.begin() as connection:
            await connection.execute(CreateSchema(schema))
            await connection.run_sync(Base.metadata.create_all)
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        try:
            async with engine.begin() as connection:
                await connection.execute(DropSchema(schema, cascade=True, if_exists=True))
        finally:
            await engine.dispose()


@pytest.mark.asyncio
async def test_two_buyers_can_reserve_the_last_item_only_once(postgres_sessions, fake_redis):
    async with postgres_sessions() as setup:
        seller = User(email="seller@example.com", role=UserRole.SELLER)
        first_buyer = User(email="buyer1@example.com", role=UserRole.CUSTOMER)
        second_buyer = User(email="buyer2@example.com", role=UserRole.CUSTOMER)
        product = Product(
            title="Last item",
            price=Decimal("49.00"),
            stock=1,
            store=Store(name="Test Store", seller=seller),
        )
        setup.add_all([first_buyer, second_buyer, product])
        await setup.commit()

        product_id = product.id
        buyer_ids = (first_buyer.id, second_buyer.id)
        for buyer_id in buyer_ids:
            await CartManager.add_item(
                fake_redis, setup, buyer_id, CartItemAdd(product_id=product_id, quantity=1)
            )

    async with (
        postgres_sessions() as first_session,
        postgres_sessions() as second_session,
        postgres_sessions() as gate,
    ):
        buyers = (first_session, second_session)
        # Har ikki sessiyada qulflashdan oldin o‘qilgan qiymatni xotirada saqlaymiz.
        cached_products = [await session.get(Product, product_id) for session in buyers]
        assert all(item.stock == 1 for item in cached_products)

        buyer_pids = [await session.scalar(select(func.pg_backend_pid())) for session in buyers]
        await gate.execute(select(Product.id).where(Product.id == product_id).with_for_update())

        tasks = [
            asyncio.create_task(OrderManager.create_order_from_cart(session, fake_redis, buyer_id))
            for session, buyer_id in zip(buyers, buyer_ids, strict=True)
        ]
        try:
            all_waiting = select(
                *[func.cardinality(func.pg_blocking_pids(pid)) > 0 for pid in buyer_pids]
            )
            # Ikkala xaridor ham qulfda kutayotganini PostgreSQL orqali tekshiramiz.
            async with asyncio.timeout(10):
                while not all((await gate.execute(all_waiting)).one()):
                    await asyncio.sleep(0.02)
            await gate.rollback()
            outcomes = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True), timeout=10
            )
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    successful_orders = [outcome for outcome in outcomes if isinstance(outcome, Order)]
    errors = [outcome for outcome in outcomes if isinstance(outcome, HTTPException)]
    assert len(successful_orders) == 1, outcomes
    assert len(errors) == 1 and errors[0].status_code == 400, outcomes
    assert successful_orders[0].total_amount == Decimal("49.00")

    async with postgres_sessions() as verify:
        persisted = await verify.get(Product, product_id)
        assert persisted.stock == 0
        assert not persisted.is_active
        assert await verify.scalar(select(func.count()).select_from(Order)) == 1
