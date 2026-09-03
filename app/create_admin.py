import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from passlib.context import CryptContext

from app.core.database import async_engine
from app.models.user import User, UserRole
from app.core.database import Base

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def create_admin_user() -> None:
    # 1. Bazada jadvallar mavjud bo'lmasa, avtomati yaratish
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 2. Admin foydalanuvchini izlash va yaratish
    async with AsyncSession(async_engine) as session:
        email = "admin@vendora.com"
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user:
            user.role = UserRole.ADMIN
            await session.commit()
            print(f"[+] '{email}' foydalanuvchisi mavjud edi, roli ADMIN ga o'zgartirildi!")
            return

        hashed_password = pwd_context.hash("admin1234")
        admin_user = User(
            email=email,
            hashed_password=hashed_password,
            first_name="Admin",
            last_name="System",
            role=UserRole.ADMIN,
            is_active=True,
        )
        session.add(admin_user)
        await session.commit()
        print(f"[+] Admin muvaffaqiyatli yaratildi!\nEmail: {email}\nParol: admin1234")


if __name__ == "__main__":
    asyncio.run(create_admin_user())