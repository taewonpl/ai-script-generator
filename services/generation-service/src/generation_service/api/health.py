"""
Health check endpoints for Generation Service
"""

import os
from datetime import datetime
from typing import Any

from fastapi import APIRouter, status
from pydantic import BaseModel

from generation_service.config_loader import settings

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model"""

    service: str
    version: str
    status: str
    timestamp: datetime
    port: int


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health Check",
    description="Check if the Generation Service is running and healthy",
)
async def health_check():
    """Basic health check endpoint"""
    return HealthResponse(
        service="Generation Service",
        version="3.0.0",
        status="healthy",
        timestamp=datetime.now(),
        port=getattr(settings, "port", 8000),
    )


@router.get(
    "/health/detailed",
    status_code=status.HTTP_200_OK,
    summary="Detailed Health Check",
    description="Detailed health check with service dependencies",
)
async def detailed_health_check():
    """Detailed health check with dependency status"""

    health_status = {
        "service": "Generation Service",
        "version": "3.0.0",
        "status": "healthy",
        "timestamp": datetime.now(),
        "dependencies": {},
        "config": {
            "port": getattr(settings, "port", 8000),
            "debug": getattr(settings, "debug", False),
            "max_script_length": getattr(settings, "max_script_length", 10000),
            "default_model": getattr(settings, "default_model", "gpt-4"),
        },
        "ai_providers": {},
        "storage": {},
    }

    # Check database connectivity
    health_status["dependencies"]["database"] = await _check_database_health()

    # Check external services
    health_status["dependencies"][
        "project_service"
    ] = await _check_project_service_health()

    # Check AI provider availability
    health_status["ai_providers"] = await _check_ai_providers_health()

    # Check storage systems
    health_status["storage"] = await _check_storage_health()

    # Determine overall status
    overall_healthy = _determine_overall_health(health_status)
    health_status["status"] = "healthy" if overall_healthy else "degraded"

    return health_status


async def _check_database_health() -> dict[str, Any]:
    """Check database connectivity"""
    try:
        database_url = getattr(settings, "database_url", None)
        if not database_url:
            return {
                "status": "not_configured",
                "message": "Database URL not configured",
            }

        # Basic connectivity check
        # TODO: Implement actual database connection test
        return {"status": "healthy", "url_configured": bool(database_url)}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def _check_project_service_health() -> dict[str, Any]:
    """Check project service connectivity"""
    try:
        import httpx

        project_service_url = getattr(
            settings, "project_service_url", "http://localhost:8001"
        )

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{project_service_url}/api/v1/health")
            if response.status_code == 200:
                return {"status": "healthy", "url": project_service_url}
            else:
                return {
                    "status": "unhealthy",
                    "url": project_service_url,
                    "http_status": response.status_code,
                }

    except Exception as e:
        return {
            "status": "unreachable",
            "error": str(e),
            "url": getattr(settings, "project_service_url", "http://localhost:8001"),
        }


async def _check_ai_providers_health() -> dict[str, Any]:
    """Check AI provider configurations and availability"""
    providers_status = {}

    # Check OpenAI
    openai_key = getattr(settings, "openai_api_key", None)
    if openai_key:
        providers_status["openai"] = {
            "configured": True,
            "api_key_present": bool(openai_key),
            "api_key_masked": _mask_api_key(openai_key),
        }
    else:
        providers_status["openai"] = {"configured": False}

    # Check Anthropic
    anthropic_key = getattr(settings, "anthropic_api_key", None)
    if anthropic_key:
        providers_status["anthropic"] = {
            "configured": True,
            "api_key_present": bool(anthropic_key),
            "api_key_masked": _mask_api_key(anthropic_key),
        }
    else:
        providers_status["anthropic"] = {"configured": False}

    return providers_status


async def _check_storage_health() -> dict[str, Any]:
    """Check storage systems health"""
    storage_status = {}

    # Check Redis (cache)
    redis_url = getattr(settings, "redis_url", None)
    if redis_url:
        storage_status["redis"] = await _check_redis_health(redis_url)
    else:
        storage_status["redis"] = {"status": "not_configured"}

    # Check ChromaDB path
    data_path = "/app/data/chroma"  # Standard path from unified data structure
    storage_status["chroma"] = await _check_chroma_health(data_path)

    # Check file system permissions
    storage_status["filesystem"] = _check_filesystem_health()

    return storage_status


async def _check_redis_health(redis_url: str) -> dict[str, Any]:
    """Check Redis connectivity"""
    try:
        import redis.asyncio as redis

        client = redis.from_url(redis_url, decode_responses=True, socket_timeout=3)
        pong = await client.ping()
        await client.close()

        return {"status": "healthy", "ping_successful": pong}
    except ImportError:
        return {"status": "dependency_missing", "error": "redis package not installed"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def _check_chroma_health(chroma_path: str) -> dict[str, Any]:
    """Check ChromaDB availability"""
    try:
        # Check if path exists and is writable
        path_exists = os.path.exists(chroma_path)
        path_writable = (
            os.access(chroma_path, os.W_OK)
            if path_exists
            else os.access(os.path.dirname(chroma_path), os.W_OK)
        )

        status = {
            "path": chroma_path,
            "path_exists": path_exists,
            "path_writable": path_writable,
        }

        if path_exists and path_writable:
            status["status"] = "healthy"
        elif not path_exists:
            status["status"] = "path_missing"
        else:
            status["status"] = "permission_denied"

        return status
    except Exception as e:
        return {"status": "error", "error": str(e), "path": chroma_path}


def _check_filesystem_health() -> dict[str, Any]:
    """Check filesystem permissions for data directories"""
    data_paths = [
        "/app/data",
        "/app/data/chroma",
        "/app/data/vectors",
        "/app/data/logs",
        "/app/data/cache",
    ]

    fs_status = {"paths": {}}
    all_healthy = True

    for path in data_paths:
        try:
            exists = os.path.exists(path)
            readable = os.access(path, os.R_OK) if exists else False
            writable = os.access(path, os.W_OK) if exists else False

            fs_status["paths"][path] = {
                "exists": exists,
                "readable": readable,
                "writable": writable,
                "status": (
                    "healthy" if (exists and readable and writable) else "unhealthy"
                ),
            }

            if not (exists and readable and writable):
                all_healthy = False

        except Exception as e:
            fs_status["paths"][path] = {"status": "error", "error": str(e)}
            all_healthy = False

    fs_status["overall_status"] = "healthy" if all_healthy else "degraded"
    return fs_status


def _mask_api_key(api_key: str) -> str:
    """Mask API key for safe logging"""
    if not api_key or len(api_key) < 8:
        return "***"
    return f"{api_key[:4]}...{api_key[-4:]}"


def _determine_overall_health(health_status: dict[str, Any]) -> bool:
    """Determine overall health based on component status"""
    # Critical components that must be healthy
    critical_checks = [
        health_status.get("storage", {}).get("filesystem", {}).get("overall_status")
        == "healthy"
    ]

    # At least one AI provider should be configured
    ai_providers = health_status.get("ai_providers", {})
    has_ai_provider = any(
        provider.get("configured", False) for provider in ai_providers.values()
    )

    return all(critical_checks) and has_ai_provider
