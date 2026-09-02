import asyncio
from uuid import uuid4

import jwt
import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.core.security import AuthManager
from app.enums.all_enums import UserRole
from app.models.user import User
from app.schemas.auth import TokenRefreshRequest
from app.schemas.user import UserLoginRequest, UserRegisterRequest
from app.services.user import UserManager, pwd_context


class FakeSession:
    def __init__(self, user=None):
        self.user = user
        self.added = []

    async def execute(self, statement):
        return FakeResult(self.user)

    async def flush(self):
        return None

    async def refresh(self, obj):
        return None

    async def commit(self):
        return None

    async def rollback(self):
        return None

    def add(self, obj):
        self.added.append(obj)


class FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value

    def scalars(self):
        return self

    def all(self):
        if self._value is None:
            return []
        if isinstance(self._value, list):
            return self._value
        return [self._value]


def make_user(email="alice@example.com", password="Secret@123", role=UserRole.CUSTOMER, is_active=True):
    return User(
        id=uuid4(),
        email=email,
        hashed_password=password,
        first_name="Alice",
        last_name="Smith",
        role=role,
        is_active=is_active,
    )


def test_auth_manager_generates_access_and_refresh_tokens():
    user = make_user()

    access_token = AuthManager.encode_token(user)
    refresh_token = AuthManager.encode_refresh_token(user)

    access_payload = jwt.decode(access_token, "default_secret", algorithms=["HS256"])
    refresh_payload = jwt.decode(refresh_token, "default_secret", algorithms=["HS256"])

    assert access_payload["typ"] == "access"
    assert refresh_payload["typ"] == "refresh"
    assert access_payload["sub"] == str(user.id)

    session = FakeSession(user=user)
    response = asyncio.run(
        AuthManager.refresh(TokenRefreshRequest(refresh=refresh_token), session)
    )

    assert response["token_type"] == "bearer"
    assert response["access_token"]
    assert response["refresh_token"]


def test_auth_manager_rejects_refresh_when_wrong_token_type():
    user = make_user()
    access_token = AuthManager.encode_token(user)

    with pytest.raises(HTTPException):
        asyncio.run(
            AuthManager.refresh(TokenRefreshRequest(refresh=access_token), FakeSession(user=user))
        )


def test_user_manager_login_returns_tokens_for_valid_user():
    plain_password = "Secret@123"
    user = make_user(password=plain_password)
    user.hashed_password = pwd_context.hash(plain_password)

    session = FakeSession(user=user)
    login_data = UserLoginRequest(email="alice@example.com", password=plain_password)

    access_token, refresh_token = asyncio.run(UserManager.login(login_data, session))

    assert access_token
    assert refresh_token


def test_user_manager_login_rejects_invalid_password():
    plain_password = "Secret@123"
    user = make_user(password=plain_password)
    user.hashed_password = pwd_context.hash(plain_password)
    session = FakeSession(user=user)

    with pytest.raises(HTTPException):
        asyncio.run(
            UserManager.login(
                UserLoginRequest(email="alice@example.com", password="WrongPass123"),
                session,
            )
        )


def test_user_manager_register_raises_duplicate_email_error():
    class DuplicateEmailSession(FakeSession):
        async def flush(self):
            raise IntegrityError("duplicate email", {}, None)

    register_data = UserRegisterRequest(
        email="alice@example.com",
        password="Secret@123",
        first_name="Alice",
        last_name="Smith",
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(UserManager.register(register_data, DuplicateEmailSession()))

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "A user with this email address already exists"
