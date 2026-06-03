from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, verify_refresh_token
from app.core.exceptions import UnauthorizedError, ConflictError, NotFoundError
from app.modules.identity.models import User, UserRole
from app.modules.identity.schemas import UserCreate, Token


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def register_user(self, user_data: UserCreate, role: UserRole = UserRole.CUSTOMER) -> User:
        existing = await self.db.execute(select(User).where(User.email == user_data.email))
        if existing.scalar_one_or_none():
            raise ConflictError(f"User with email {user_data.email} already exists")

        hashed_password = hash_password(user_data.password)
        user = User(
            email=user_data.email,
            password_hash=hashed_password,
            role=role,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def authenticate(self, email: str, password: str) -> Token:
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.password_hash):
            raise UnauthorizedError("Invalid email or password")

        if not user.is_active:
            raise UnauthorizedError("User account is inactive")

        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role.value}
        )
        refresh_token = create_refresh_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role.value}
        )

        return Token(access_token=access_token, refresh_token=refresh_token)

    async def refresh_access_token(self, refresh_token: str) -> Token:
        payload = verify_refresh_token(refresh_token)
        if not payload:
            raise UnauthorizedError("Invalid or expired refresh token")

        user_id_str = payload.get("sub")
        try:
            user_id = int(user_id_str)
        except (ValueError, TypeError):
            raise UnauthorizedError("Invalid or expired refresh token")
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            raise UnauthorizedError("User not found or inactive")

        new_access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role.value}
        )
        new_refresh_token = create_refresh_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role.value}
        )

        return Token(access_token=new_access_token, refresh_token=new_refresh_token)

    async def get_user_by_id(self, user_id: int) -> User:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise NotFoundError("User", str(user_id))

        return user