"""Routes for Store control."""

from collections.abc import Sequence
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    allow_admin,
    allow_seller_or_admin,
    get_current_user,
    oauth2_schema,
)
from app.core.database import get_database
from app.models.store import Store
from app.models.user import User
from app.schemas.store import StoreCreate, StoreEditRequest, StoreResponse
from app.services.store_manager import StoreManager

router = APIRouter(tags=["Stores"], prefix="/stores")


@router.get(
    "/",
    dependencies=[Depends(oauth2_schema), Depends(allow_admin)],
    response_model=list[StoreResponse],
)
async def get_stores(
    db: AsyncSession = Depends(get_database),
) -> Sequence[Store]:
    """Get all stores."""
    return await StoreManager.get_all_stores(db)


@router.get(
    "/{store_id}",
    dependencies=[Depends(oauth2_schema), Depends(allow_seller_or_admin)],
    response_model=StoreResponse,
)
async def get_store_by_id(
    store_id: UUID, db: AsyncSession = Depends(get_database)
) -> Store:
    """Get store by id."""
    return await StoreManager.get_store_by_id(store_id, db)


@router.post(
    "/",
    dependencies=[Depends(oauth2_schema), Depends(allow_seller_or_admin)],
    response_model=StoreResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_store(
    store_data: StoreCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
) -> Store:
    """Create a store."""
    return await StoreManager.create_store(store_data, current_user, db)


@router.put(
    "/{store_id}",
    dependencies=[Depends(oauth2_schema), Depends(allow_seller_or_admin)],
    status_code=status.HTTP_200_OK,
    response_model=StoreResponse,
)
async def update_store(
    store_id: UUID,
    store_data: StoreEditRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
) -> Store:
    """Update a store."""
    return await StoreManager.update_store(
        store_id=store_id, store_data=store_data, current_user=current_user, session=db
    )


@router.delete(
    "/{store_id}",
    dependencies=[Depends(oauth2_schema), Depends(allow_seller_or_admin)],
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_store(
    store_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
) -> None:
    """Delete Store with id."""
    await StoreManager.delete_store(store_id=store_id, current_user=current_user, session=db)


@router.post(
    "/{store_id}/logo",
    dependencies=[Depends(oauth2_schema), Depends(allow_seller_or_admin)],
    response_model=StoreResponse,
    status_code=status.HTTP_200_OK,
)
async def upload_store_logo(
    store_id: UUID,
    file: UploadFile = File(description="Store logo image"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
) -> Store:
    """Upload store logo image."""
    return await StoreManager.upload_logo(
        store_id=store_id, file=file, current_user=current_user, session=db
    )


@router.post(
    "/{store_id}/banner",
    dependencies=[Depends(oauth2_schema), Depends(allow_seller_or_admin)],
    response_model=StoreResponse,
    status_code=status.HTTP_200_OK,
)
async def upload_store_banner(
    store_id: UUID,
    file: UploadFile = File(description="Store banner image"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
) -> Store:
    """Upload store banner image."""
    return await StoreManager.upload_banner(
        store_id=store_id, file=file, current_user=current_user, session=db
    )