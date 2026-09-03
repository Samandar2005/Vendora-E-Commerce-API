from uuid import UUID
from fastapi import APIRouter, Depends, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_redis, oauth2_schema
from app.core.database import get_database
from app.models.user import User
from app.schemas.cart import CartItemAdd, CartResponse
from app.services.cart_manager import CartManager

router = APIRouter(tags=["Cart"], prefix="/cart")


@router.get("/", dependencies=[Depends(oauth2_schema)], response_model=CartResponse)
async def get_cart(
    current_user: User = Depends(get_current_user),
    redis: Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_database),
):
    """Foydalanuvchining joriy savatini ko'rish."""
    return await CartManager.get_cart(redis=redis, db=db, user_id=current_user.id)


@router.post("/items", dependencies=[Depends(oauth2_schema)], response_model=CartResponse)
async def add_item_to_cart(
    item_data: CartItemAdd,
    current_user: User = Depends(get_current_user),
    redis: Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_database),
):
    """Savatga mahsulot qo'shish."""
    return await CartManager.add_item(
        redis=redis, db=db, user_id=current_user.id, item_data=item_data
    )


@router.delete(
    "/items/{product_id}",
    dependencies=[Depends(oauth2_schema)],
    response_model=CartResponse,
)
async def remove_item_from_cart(
    product_id: UUID,
    current_user: User = Depends(get_current_user),
    redis: Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_database),
):
    """Savatdan bitta mahsulotni o'chirish."""
    return await CartManager.remove_item(
        redis=redis, db=db, user_id=current_user.id, product_id=product_id
    )


@router.delete("/", dependencies=[Depends(oauth2_schema)], status_code=status.HTTP_204_NO_CONTENT)
async def clear_cart(
    current_user: User = Depends(get_current_user),
    redis: Redis = Depends(get_redis),
):
    """Savatni to'liq tozalash."""
    await CartManager.clear_cart(redis=redis, user_id=current_user.id)
    