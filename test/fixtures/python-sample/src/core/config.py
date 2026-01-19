"""Application configuration module."""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    APP_NAME: str = "Python Sample API"
    DEBUG: bool = False
    EXTERNAL_API_URL: str = "https://api.example.com"
    DATABASE_URL: str = "sqlite:///./app.db"

    class Config:
        env_file = ".env"


settings = Settings()
