from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.exceptions import DomainException
from backend.app.core.security import get_password_hash, verify_password
from backend.app.models.identity import User, UserRole
from backend.app.schemas.identity import UserCreate


class AuthService:
    @staticmethod
    async def authenticate_user(
        db: AsyncSession, email: str, password: str
    ) -> Optional[User]:
        stmt = select(User).where(User.email == email, User.is_active == True)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    @staticmethod
    async def create_user(db: AsyncSession, user_in: UserCreate) -> User:
        # Check if email exists
        stmt = select(User).where(User.email == user_in.email)
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            raise DomainException(f"User with email '{user_in.email}' already exists.", code="DUPLICATE_EMAIL")

        hashed_pw = get_password_hash(user_in.password)
        db_user = User(
            organization_id=user_in.organization_id,
            email=user_in.email,
            hashed_password=hashed_pw,
            full_name=user_in.full_name,
            role=user_in.role
        )
        db.add(db_user)
        await db.flush()
        return db_user
