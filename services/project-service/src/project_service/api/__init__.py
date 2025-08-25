from fastapi import APIRouter

# Import all route modules
from . import episodes, health, projects

# Create main API router
api_router = APIRouter()

# Include all routers with their prefixes
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(episodes.router, prefix="/episodes", tags=["episodes"])

__all__ = ["api_router"]
