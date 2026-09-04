from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Category
from app.models.store import Store


@pytest.mark.asyncio
async def test_category_public_tree_and_admin_crud(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
    seller_headers: dict[str, str],
) -> None:
    assert (await client.get("/categories/")).status_code == 200
    assert (await client.post("/categories/", json={"name": "Phones", "description": "Mobile"}, headers=seller_headers)).status_code == 403

    created = await client.post("/categories/", json={"name": "Phones", "description": "Mobile"}, headers=admin_headers)
    assert created.status_code == 201
    category = created.json()
    assert category["slug"] == "phones"
    assert (await client.post("/categories/", json={"name": "Phones"}, headers=admin_headers)).status_code == 400

    child = await client.post("/categories/", json={"name": "Android", "parent_id": category["id"]}, headers=admin_headers)
    assert child.status_code == 201
    tree = await client.get("/categories/")
    root = next(item for item in tree.json() if item["id"] == category["id"])
    assert any(item["name"] == "Android" for item in root["subcategories"])

    updated = await client.patch(f"/categories/{category['id']}", json={"name": "Smart Phones"}, headers=admin_headers)
    assert updated.status_code == 200
    assert updated.json()["slug"] == "smart-phones"
    assert (await client.get(f"/categories/{uuid4()}")).status_code == 404
    assert (await client.delete(f"/categories/{category['id']}", headers=admin_headers)).status_code == 204


@pytest.mark.asyncio
async def test_store_crud_permissions_and_uploads(
    client: AsyncClient,
    seller_headers: dict[str, str],
    admin_headers: dict[str, str],
    seller_store: Store,
    other_store: Store,
) -> None:
    created = await client.post("/stores/", json={"name": "Fresh Store", "description": "New"}, headers=seller_headers)
    assert created.status_code == 201
    assert created.json()["slug"] == "fresh-store"
    store_id = created.json()["id"]

    assert (await client.get("/stores/", headers=admin_headers)).status_code == 200
    assert (await client.get("/stores/", headers=seller_headers)).status_code == 403
    assert (await client.get(f"/stores/{store_id}", headers=seller_headers)).status_code == 200
    assert (await client.put(f"/stores/{store_id}", json={"description": "Updated"}, headers=seller_headers)).status_code == 200

    forbidden_update = await client.put(
        f"/stores/{other_store.id}", json={"description": "No"}, headers=seller_headers
    )
    assert forbidden_update.status_code == 403
    forbidden_delete = await client.delete(f"/stores/{other_store.id}", headers=seller_headers)
    assert forbidden_delete.status_code == 403

    upload = await client.post(
        f"/stores/{seller_store.id}/logo",
        files={"file": ("logo.jpg", b"image-bytes", "image/jpeg")},
        headers=seller_headers,
    )
    assert upload.status_code == 200
    assert upload.json()["logo_url"].startswith("/media/uploads/logo_")
    banner = await client.post(
        f"/stores/{seller_store.id}/banner",
        files={"file": ("banner.png", b"image-bytes", "image/png")},
        headers=admin_headers,
    )
    assert banner.status_code == 200
    assert (await client.get(f"/stores/{uuid4()}", headers=admin_headers)).status_code == 404
