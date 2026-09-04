from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthManager
from app.enums.all_enums import UserRole
from app.models.user import User
from app.services.user import pwd_context


@pytest.mark.asyncio
async def test_register_login_refresh_and_me(client: AsyncClient, db_session: AsyncSession) -> None:
    register = await client.post(
        "/auth/register",
        json={"email": "NewUser@Example.com", "password": "password123", "first_name": "New"},
    )
    assert register.status_code == 201
    tokens = register.json()
    assert tokens["token_type"] == "bearer"
    assert tokens["access_token"] and tokens["refresh_token"]

    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == "NewUser@example.com"

    login = await client.post("/auth/login/", json={"email": "NewUser@example.com", "password": "password123"})
    assert login.status_code == 200
    refreshed = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"]

    user = (await db_session.execute(select(User).where(User.email == "NewUser@example.com"))).scalar_one()
    assert user.role == UserRole.CUSTOMER
    assert pwd_context.verify("password123", user.hashed_password)


@pytest.mark.asyncio
async def test_auth_rejects_duplicate_invalid_and_inactive_users(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    payload = {"email": "duplicate@example.com", "password": "password123"}
    assert (await client.post("/auth/register", json=payload)).status_code == 201
    assert (await client.post("/auth/register", json=payload)).status_code == 400
    assert (await client.post("/auth/login/", json={"email": payload["email"], "password": "wrongpass"})).status_code == 400
    assert (await client.post("/auth/refresh", json={"refresh_token": "bad-token"})).status_code == 401

    inactive = User(email="inactive@example.com", hashed_password=pwd_context.hash("password123"), is_active=False)
    db_session.add(inactive)
    await db_session.commit()
    response = await client.post("/auth/login/", json={"email": inactive.email, "password": "password123"})
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_auth_rejects_missing_malformed_and_expired_tokens(client: AsyncClient) -> None:
    assert (await client.get("/auth/me")).status_code == 401
    assert (await client.get("/auth/me", headers={"Authorization": "Bearer invalid"})).status_code == 401


@pytest.mark.asyncio
async def test_admin_user_management_and_profile_permissions(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user: User,
    admin_headers: dict[str, str],
    buyer_user: User,
    buyer_headers: dict[str, str],
) -> None:
    assert (await client.get("/users/", headers=admin_headers)).status_code == 200
    assert (await client.get("/users/", headers=buyer_headers)).status_code == 403
    assert (await client.get("/users/me", headers=buyer_headers)).json()["id"] == str(buyer_user.id)

    edit = await client.put(f"/users/{buyer_user.id}", json={"first_name": "Changed"}, headers=buyer_headers)
    assert edit.status_code == 200
    assert edit.json()["first_name"] == "Changed"

    assert (await client.post(f"/users/{buyer_user.id}/make-seller", headers=admin_headers)).status_code == 204
    assert (await client.post(f"/users/{buyer_user.id}/make-admin", headers=admin_headers)).status_code == 204
    await db_session.refresh(buyer_user)
    assert buyer_user.role == UserRole.ADMIN

    changed = await client.post(
        f"/users/{buyer_user.id}/password", json={"password": "newpassword"}, headers=admin_headers
    )
    assert changed.status_code == 204
    await db_session.refresh(buyer_user)
    assert pwd_context.verify("newpassword", buyer_user.hashed_password)


@pytest.mark.asyncio
async def test_user_self_or_admin_rules_and_ban_lifecycle(
    client: AsyncClient,
    admin_user: User,
    admin_headers: dict[str, str],
    buyer_user: User,
    buyer_headers: dict[str, str],
    seller_user: User,
    seller_headers: dict[str, str],
) -> None:
    assert (await client.put(f"/users/{seller_user.id}", json={"first_name": "x"}, headers=buyer_headers)).status_code == 403
    assert (await client.post(f"/users/{seller_user.id}/password", json={"password": "newpassword"}, headers=buyer_headers)).status_code == 403
    assert (await client.post(f"/users/{seller_user.id}/ban", headers=admin_headers)).status_code == 204
    assert (await client.post(f"/users/{seller_user.id}/ban", headers=admin_headers)).status_code == 400
    assert (await client.post(f"/users/{seller_user.id}/unban", headers=admin_headers)).status_code == 204
    assert (await client.post(f"/users/{seller_user.id}/unban", headers=admin_headers)).status_code == 400
    assert (await client.post(f"/users/{buyer_user.id}/ban", headers=buyer_headers)).status_code == 403
    assert (await client.post(f"/users/{admin_user.id}/ban", headers=admin_headers)).status_code == 400


@pytest.mark.asyncio
async def test_admin_can_delete_user_and_missing_user_is_404(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    missing = await client.delete(f"/users/{uuid4()}", headers=admin_headers)
    assert missing.status_code == 404
