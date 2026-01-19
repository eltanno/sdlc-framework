"""User service module."""

from datetime import datetime
import httpx

from src.models.user import User, UserCreate
from src.core.config import settings


# HACK: Using in-memory store instead of database
_users: list[User] = [
    User(id="1", name="John Doe", email="john@example.com", created_at=datetime.now()),
    User(id="2", name="Jane Smith", email="jane@example.com", created_at=datetime.now()),
]


class UserService:
    """Service class for user operations."""

    def __init__(self) -> None:
        """Initialize user service."""
        self.api_base_url = settings.EXTERNAL_API_URL

    async def get_all_users(self) -> list[User]:
        """Get all users."""
        return _users

    async def get_user_by_id(self, user_id: str) -> User | None:
        """Get a user by ID."""
        for user in _users:
            if user.id == user_id:
                return user
        return None

    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        new_user = User(
            id=str(len(_users) + 1),
            name=user_data.name,
            email=user_data.email,
            created_at=datetime.now(),
        )
        _users.append(new_user)
        return new_user

    async def fetch_external_user_data(self, user_id: str) -> dict:
        """Fetch user data from external API."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.api_base_url}/users/{user_id}")
            response.raise_for_status()
            return response.json()
