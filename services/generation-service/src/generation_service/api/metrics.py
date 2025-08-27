"""
Metrics and observability endpoints for Generation Service
Provides Prometheus-compatible metrics and system observability data.
"""

import time
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Response, status
from pydantic import BaseModel

from generation_service.services.job_manager import get_job_manager

router = APIRouter()

# In-memory metrics storage (for production, use proper metrics collector)
_metrics = {
    "requests_total": 0,
    "requests_duration_sum": 0.0,
    "active_jobs_count": 0,
    "completed_jobs_count": 0,
    "failed_jobs_count": 0,
    "sse_connections_active": 0,
    "start_time": time.time(),
}


class MetricsResponse(BaseModel):
    """Metrics response model"""

    service: str
    timestamp: datetime
    uptime_seconds: float
    metrics: Dict[str, Any]


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
    job_manager = get_job_manager()

    # Update job metrics
    job_stats = job_manager.get_job_stats()
    _metrics.update(
        {
            "active_jobs_count": job_stats.get("queued", 0)
            + job_stats.get("streaming", 0),
            "completed_jobs_count": job_stats.get("completed", 0),
            "failed_jobs_count": job_stats.get("failed", 0),
            "sse_connections_active": job_stats.get("active_connections", 0),
        }
    )

    uptime = current_time - _metrics["start_time"]

    # Generate Prometheus format
    metrics_text = f"""# HELP generation_service_uptime_seconds Total uptime of the service
# TYPE generation_service_uptime_seconds counter
generation_service_uptime_seconds {uptime:.2f}

# HELP generation_service_requests_total Total number of requests processed
# TYPE generation_service_requests_total counter
generation_service_requests_total {_metrics["requests_total"]}

# HELP generation_service_requests_duration_seconds Total time spent processing requests
# TYPE generation_service_requests_duration_seconds counter
generation_service_requests_duration_seconds {_metrics["requests_duration_sum"]:.3f}

# HELP generation_service_jobs_active Number of currently active jobs
# TYPE generation_service_jobs_active gauge
generation_service_jobs_active {_metrics["active_jobs_count"]}

# HELP generation_service_jobs_completed_total Total number of completed jobs
# TYPE generation_service_jobs_completed_total counter
generation_service_jobs_completed_total {_metrics["completed_jobs_count"]}

# HELP generation_service_jobs_failed_total Total number of failed jobs
# TYPE generation_service_jobs_failed_total counter
generation_service_jobs_failed_total {_metrics["failed_jobs_count"]}

# HELP generation_service_sse_connections_active Number of active SSE connections
# TYPE generation_service_sse_connections_active gauge
generation_service_sse_connections_active {_metrics["sse_connections_active"]}

# HELP generation_service_build_info Build information
# TYPE generation_service_build_info gauge
generation_service_build_info{{version="3.0.0",service="generation-service"}} 1
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
    job_manager = get_job_manager()

    # Update job metrics
    job_stats = job_manager.get_job_stats()
    _metrics.update(
        {
            "active_jobs_count": job_stats.get("queued", 0)
            + job_stats.get("streaming", 0),
            "completed_jobs_count": job_stats.get("completed", 0),
            "failed_jobs_count": job_stats.get("failed", 0),
            "sse_connections_active": job_stats.get("active_connections", 0),
        }
    )

    uptime = current_time - _metrics["start_time"]

    return MetricsResponse(
        service="generation-service",
        timestamp=datetime.now(timezone.utc),
        uptime_seconds=uptime,
        metrics={
            "uptime_seconds": uptime,
            "requests_total": _metrics["requests_total"],
            "requests_duration_seconds": _metrics["requests_duration_sum"],
            "jobs_active": _metrics["active_jobs_count"],
            "jobs_completed_total": _metrics["completed_jobs_count"],
            "jobs_failed_total": _metrics["failed_jobs_count"],
            "sse_connections_active": _metrics["sse_connections_active"],
            "build_info": {
                "version": "3.0.0",
                "service": "generation-service",
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
    job_manager = get_job_manager()

    # Basic readiness checks
    checks = {
        "job_manager": job_manager is not None,
        "service_healthy": True,  # Add more sophisticated checks here
    }

    all_ready = all(checks.values())

    return {
        "status": "ready" if all_ready else "not_ready",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "service": "generation-service",
        "version": "3.0.0",
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
        "service": "generation-service",
        "version": "3.0.0",
    }


def increment_request_counter(duration: float = 0.0):
    """Increment request metrics (call this from middleware)"""
    _metrics["requests_total"] += 1
    _metrics["requests_duration_sum"] += duration
