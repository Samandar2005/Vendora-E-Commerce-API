"""Define the Store manager."""

from collections.abc import Sequence
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.store import Store
from app.models.user import User
from app.schemas.store import StoreCreate, StoreEditRequest


class StoreManager:
    """Class to Manage the Store."""

    @staticmethod
    async def create_store(
        store_data: StoreCreate, current_user: User, session: AsyncSession
    ) -> Store:
        """Create new store."""
        try:
            # Pydantic modelni lug'atga o'girib, seller_id bilan birga SQLAlchemy modeliga beramiz
            store_dict = store_data.model_dump()
            store = Store(**store_dict, seller_id=current_user.id)

            session.add(store)
            await session.flush()
            await session.refresh(store)  # Yaratilgan store ma'lumotlarini yuklash

            return store

        except Exception as err:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Something went wrong. Why: {err}",
            ) from err

    @staticmethod
    async def get_all_stores(session: AsyncSession) -> Sequence[Store]:
        """Fetch all stores."""
        stmt = select(Store).options(selectinload(Store.seller))
        result = await session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_store_by_id(store_id: UUID, session: AsyncSession) -> Store:
        """Return one store by ID."""
        stmt = (
            select(Store)
            .where(Store.id == store_id)
            .options(selectinload(Store.seller))
        )
        result = await session.execute(stmt)
        store = result.scalar_one_or_none()
        if not store:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Store Not Found {store_id}",
            )
        return store

    @staticmethod
    async def update_store(
        store_id: UUID, store_data: StoreEditRequest, session: AsyncSession
    ) -> Store:
        """Update Store with id."""
        store = await StoreManager.get_store_by_id(store_id, session)

        update_data = store_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(store, key, value)

        await session.flush()
        await session.refresh(store)
        return store

    @staticmethod
    async def delete_store(store_id: UUID, session: AsyncSession) -> None:
        """Delete store with id."""
        store = await StoreManager.get_store_by_id(store_id, session)
        await session.delete(store)
        await session.flush()