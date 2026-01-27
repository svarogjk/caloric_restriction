"""
Authentication service for user management and JWT tokens.

Handles password hashing with Argon2 and JWT token creation/validation.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.database import User
from app.schemas.auth import UserCreate
from app.config.settings import settings

# Use Argon2 - recommended password hashing
password_hash = PasswordHash.recommended()


class AuthService:
    """Service for authentication operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return password_hash.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Hash a password using Argon2."""
        return password_hash.hash(password)

    def create_access_token(
        self,
        data: dict,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """Create a JWT access token."""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + (
            expires_delta or timedelta(minutes=settings.jwt_expire_minutes)
        )
        to_encode.update({"exp": expire})
        return jwt.encode(
            to_encode,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Fetch user by username."""
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Fetch user by email."""
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def authenticate_user(
        self,
        username: str,
        password: str,
    ) -> Optional[User]:
        """Authenticate user with username and password."""
        user = await self.get_user_by_username(username)
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        return user

    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user with hashed password."""
        user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=self.get_password_hash(user_data.password),
            full_name=user_data.full_name,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user
