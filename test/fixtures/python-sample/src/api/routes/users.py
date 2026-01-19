"""User routes module."""

from fastapi import APIRouter, HTTPException

from src.services.user_service import UserService
from src.models.user import User, UserCreate

router = APIRouter()
user_service = UserService()


@router.get("/", response_model=list[User])
async def get_all_users() -> list[User]:
    """Get all users."""
    return await user_service.get_all_users()


@router.get("/{user_id}", response_model=User)
async def get_user(user_id: str) -> User:
    """Get a specific user by ID."""
    user = await user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/", response_model=User, status_code=201)
async def create_user(user_data: UserCreate) -> User:
    """Create a new user."""
    return await user_service.create_user(user_data)
