"""User models module."""

from datetime import datetime
from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    """Base user model with common fields."""
    name: str
    email: EmailStr


class UserCreate(UserBase):
    """Model for creating a new user."""
    pass


class User(UserBase):
    """Full user model with all fields."""
    id: str
    created_at: datetime

    class Config:
        from_attributes = True
