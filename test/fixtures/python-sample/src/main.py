"""Main FastAPI application entry point."""

from fastapi import FastAPI
from dotenv import load_dotenv

from src.api.routes import users, health
from src.core.config import settings

load_dotenv()

app = FastAPI(
    title=settings.APP_NAME,
    description="Sample Python API for testing /analyze-codebase",
    version="1.0.0",
)

# Include routers
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(health.router, prefix="/api/health", tags=["health"])


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint returning welcome message."""
    return {"message": "Welcome to the Python Sample API"}


# TODO: Add authentication middleware
# FIXME: CORS configuration is missing


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
