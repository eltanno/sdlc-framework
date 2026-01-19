"""Health check routes module."""

from datetime import datetime
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def health_check() -> dict:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/ready")
async def readiness_check() -> dict:
    """Readiness check endpoint."""
    # TODO: Check database connection
    return {"ready": True}
