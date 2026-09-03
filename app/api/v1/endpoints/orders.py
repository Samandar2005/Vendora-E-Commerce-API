from uuid import UUID
from fastapi import APIRouter, Depends, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_redis, oauth2_schema
from app.core.database import get_database
from app.models.user import User
from app.schemas.order import OrderResponse
from app.services.order_manager import OrderManager

router = APIRouter(tags=["Orders"], prefix="/orders")


@router.post(
    "/checkout",
    dependencies=[Depends(oauth2_schema)],
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def checkout(
    current_user: User = Depends(get_current_user),
    redis: Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_database),
):
    """Savatdagi mahsulotlardan yangi buyurtma rasmiylashtirish (Checkout)."""
    return await OrderManager.create_order_from_cart(
        db=db, redis=redis, user_id=current_user.id
    )


@router.get(
    "/",
    dependencies=[Depends(oauth2_schema)],
    response_model=list[OrderResponse],
)
async def get_my_orders(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
):
    """Foydalanuvchining barcha buyurtmalari ro'yxati."""
    return await OrderManager.get_user_orders(db=db, user_id=current_user.id)


@router.get(
    "/{order_id}",
    dependencies=[Depends(oauth2_schema)],
    response_model=OrderResponse,
)
async def get_order_details(
    order_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
):
    """Aynan bitta buyurtma haqida to'liq ma'lumot."""
    return await OrderManager.get_order_by_id(
        db=db, order_id=order_id, user_id=current_user.id
    )


@router.post(
    "/{order_id}/cancel",
    dependencies=[Depends(oauth2_schema)],
    response_model=OrderResponse,
)
async def cancel_order(
    order_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
):
    """Kutilayotgan buyurtmani bekor qilish (ombor zakaslari qaytariladi)."""
    return await OrderManager.cancel_order(
        db=db, order_id=order_id, user_id=current_user.id
    )
