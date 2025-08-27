"""
Metrics and observability endpoints for Project Service
Provides Prometheus-compatible metrics and system observability data.
"""

import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Response, status
from pydantic import BaseModel

from ..database import get_db

router = APIRouter()

# In-memory metrics storage (for production, use proper metrics collector)
_metrics = {
    "requests_total": 0,
    "requests_duration_sum": 0.0,
    "projects_total": 0,
    "episodes_total": 0,
    "start_time": time.time(),
}


class MetricsResponse(BaseModel):
    """Metrics response model"""

    service: str
    timestamp: datetime
    uptime_seconds: float
    metrics: dict[str, Any]


@router.get(
    "/metrics",
    status_code=status.HTTP_200_OK,
    summary="Prometheus Metrics",
    description="Get Prometheus-compatible metrics",
    response_class=Response,
)
async def metrics():
    """Prometheus-compatible metrics endpoint"""
    current_time = time.time()
    uptime = current_time - _metrics["start_time"]

    # Get database counts (basic implementation)
    try:
        db = next(get_db())
        from sqlalchemy import text

        # Count projects
        projects_result = db.execute(text("SELECT COUNT(*) FROM projects")).fetchone()
        projects_count = projects_result[0] if projects_result else 0

        # Count episodes
        episodes_result = db.execute(text("SELECT COUNT(*) FROM episodes")).fetchone()
        episodes_count = episodes_result[0] if episodes_result else 0

        _metrics["projects_total"] = projects_count
        _metrics["episodes_total"] = episodes_count

    except Exception:
        # If DB query fails, use last known values
        pass

    # Generate Prometheus format
    metrics_text = f"""# HELP project_service_uptime_seconds Total uptime of the service
# TYPE project_service_uptime_seconds counter
project_service_uptime_seconds {uptime:.2f}

# HELP project_service_requests_total Total number of requests processed
# TYPE project_service_requests_total counter
project_service_requests_total {_metrics["requests_total"]}

# HELP project_service_requests_duration_seconds Total time spent processing requests
# TYPE project_service_requests_duration_seconds counter
project_service_requests_duration_seconds {_metrics["requests_duration_sum"]:.3f}

# HELP project_service_projects_total Total number of projects in database
# TYPE project_service_projects_total gauge
project_service_projects_total {_metrics["projects_total"]}

# HELP project_service_episodes_total Total number of episodes in database
# TYPE project_service_episodes_total gauge
project_service_episodes_total {_metrics["episodes_total"]}

# HELP project_service_build_info Build information
# TYPE project_service_build_info gauge
project_service_build_info{{version="1.0.0",service="project-service"}} 1
"""

    return Response(content=metrics_text, media_type="text/plain")


@router.get(
    "/metrics/json",
    response_model=MetricsResponse,
    status_code=status.HTTP_200_OK,
    summary="JSON Metrics",
    description="Get metrics in JSON format",
)
async def metrics_json():
    """JSON format metrics endpoint"""
    current_time = time.time()
    uptime = current_time - _metrics["start_time"]

    # Get database counts
    try:
        db = next(get_db())
        from sqlalchemy import text

        projects_result = db.execute(text("SELECT COUNT(*) FROM projects")).fetchone()
        projects_count = projects_result[0] if projects_result else 0

        episodes_result = db.execute(text("SELECT COUNT(*) FROM episodes")).fetchone()
        episodes_count = episodes_result[0] if episodes_result else 0

        _metrics["projects_total"] = projects_count
        _metrics["episodes_total"] = episodes_count

    except Exception:
        pass

    return MetricsResponse(
        service="project-service",
        timestamp=datetime.now(timezone.utc),
        uptime_seconds=uptime,
        metrics={
            "uptime_seconds": uptime,
            "requests_total": _metrics["requests_total"],
            "requests_duration_seconds": _metrics["requests_duration_sum"],
            "projects_total": _metrics["projects_total"],
            "episodes_total": _metrics["episodes_total"],
            "build_info": {
                "version": "1.0.0",
                "service": "project-service",
            },
        },
    )


@router.get(
    "/readyz",
    status_code=status.HTTP_200_OK,
    summary="Readiness Check",
    description="Check if service is ready to accept requests",
)
async def readiness_check():
    """Kubernetes-style readiness check"""
    checks = {
        "database": False,
        "service_healthy": True,
    }

    # Check database connectivity
    try:
        db = next(get_db())
        from sqlalchemy import text

        db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        checks["database"] = False

    all_ready = all(checks.values())

    return {
        "status": "ready" if all_ready else "not_ready",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "service": "project-service",
        "version": "1.0.0",
    }


@router.get(
    "/livez",
    status_code=status.HTTP_200_OK,
    summary="Liveness Check",
    description="Check if service is alive and should not be restarted",
)
async def liveness_check():
    """Kubernetes-style liveness check"""
    return {
        "status": "alive",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "project-service",
        "version": "1.0.0",
    }


def increment_request_counter(duration: float = 0.0):
    """Increment request metrics (call this from middleware)"""
    _metrics["requests_total"] += 1
    _metrics["requests_duration_sum"] += duration
