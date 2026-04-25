"""
Pydantic schemas for authentication.
"""

from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """Request to register a new user."""

    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    password: str = Field(..., min_length=8, max_length=100)
    full_name: Optional[str] = None


class UserResponse(BaseModel):
    """User data response (excludes password)."""

    id: str
    username: str
    email: Optional[str]
    full_name: Optional[str]
    disabled: bool

    class Config:
        from_attributes = True


class Token(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Data encoded in JWT payload."""

    username: Optional[str] = None
