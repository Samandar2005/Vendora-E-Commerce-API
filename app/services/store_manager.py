"""Define the Store manager."""

import os
import uuid
from collections.abc import Sequence
from uuid import UUID

import aiofiles
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.store import Store
from app.models.user import User
from app.schemas.store import StoreCreate, StoreEditRequest
from app.schemas.user import UserRole

UPLOAD_DIR = "media/uploads"


class StoreManager:
    """Class to Manage the Store."""

    @staticmethod
    async def create_store(
        store_data: StoreCreate, current_user: User, session: AsyncSession
    ) -> Store:
        """Create new store."""
        try:
            store_dict = store_data.model_dump()
            store = Store(**store_dict, seller_id=current_user.id)

            session.add(store)
            await session.commit()

            stmt = (
                select(Store)
                .where(Store.id == store.id)
                .options(selectinload(Store.seller))
            )
            result = await session.execute(stmt)
            return result.scalar_one()

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

        await session.commit()
        return await StoreManager.get_store_by_id(store_id, session)

    @staticmethod
    async def delete_store(store_id: UUID, session: AsyncSession) -> None:
        """Delete store with id."""
        store = await StoreManager.get_store_by_id(store_id, session)
        await session.delete(store)
        await session.commit()

    @staticmethod
    async def upload_logo(
        store_id: UUID,
        file: UploadFile,
        current_user: User,
        session: AsyncSession,
    ) -> Store:
        """Upload store logo."""
        store = await StoreManager.get_store_by_id(store_id, session)

        if store.seller_id != current_user.id and current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only upload logo for your own store.",
            )

        os.makedirs(UPLOAD_DIR, exist_ok=True)
        file_ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "jpg"
        filename = f"logo_{uuid.uuid4()}.{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, filename)

        async with aiofiles.open(file_path, "wb") as out_file:
            content = await file.read()
            await out_file.write(content)

        store.logo_url = f"/media/uploads/{filename}"
        await session.commit()
        return await StoreManager.get_store_by_id(store_id, session)

    @staticmethod
    async def upload_banner(
        store_id: UUID,
        file: UploadFile,
        current_user: User,
        session: AsyncSession,
    ) -> Store:
        """Upload store banner."""
        store = await StoreManager.get_store_by_id(store_id, session)

        if store.seller_id != current_user.id and current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only upload banner for your own store.",
            )

        os.makedirs(UPLOAD_DIR, exist_ok=True)
        file_ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "jpg"
        filename = f"banner_{uuid.uuid4()}.{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, filename)

        async with aiofiles.open(file_path, "wb") as out_file:
            content = await file.read()
            await out_file.write(content)

        store.banner_url = f"/media/uploads/{filename}"
        await session.commit()
        return await StoreManager.get_store_by_id(store_id, session)