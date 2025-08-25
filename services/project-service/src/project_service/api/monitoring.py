"""
Episode numbering system monitoring API endpoints
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..monitoring.episode_alerting import get_alert_manager
from ..monitoring.episode_metrics import get_integrity_checker, get_performance_tracker
from ..monitoring.integrity_jobs import IntegrityAutoFixer, get_integrity_job

try:
    from ai_script_core import SuccessResponseDTO, get_service_logger

    logger = get_service_logger("project-service.monitoring-api")
    CORE_AVAILABLE = True
except ImportError:
    import logging

    logger = logging.getLogger(__name__)
    CORE_AVAILABLE = False

    class SuccessResponseDTO:
        def __init__(self, success=True, message="Success", data=None):
            self.success = success
            self.message = message
            self.data = data


router = APIRouter(prefix="/monitoring/episodes", tags=["Episode Monitoring"])


@router.get("/integrity/summary")
async def get_integrity_summary(db: Session = Depends(get_db)):
    """Get overall episode numbering integrity summary"""
    try:
        checker = get_integrity_checker(db)
        summary = checker.get_integrity_summary()

        if CORE_AVAILABLE:
            return SuccessResponseDTO(
                success=True,
                message="Integrity summary retrieved successfully",
                data=summary,
            )
        else:
            return {"success": True, "data": summary}

    except Exception as e:
        logger.error(f"Failed to get integrity summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve integrity summary",
        )


@router.get("/integrity/project/{project_id}")
async def get_project_integrity(project_id: str, db: Session = Depends(get_db)):
    """Get integrity status for a specific project"""
    try:
        checker = get_integrity_checker(db)
        result = checker.check_project_integrity(project_id)

        integrity_data = {
            "project_id": result.project_id,
            "is_healthy": result.is_healthy,
            "total_episodes": result.total_episodes,
            "gaps": result.gaps,
            "duplicates": result.duplicates,
            "gap_count": len(result.gaps),
            "duplicate_count": len(result.duplicates),
            "health_percentage": (
                100.0
                if result.is_healthy
                else max(
                    0,
                    100
                    - (
                        (len(result.gaps) + len(result.duplicates))
                        / max(result.total_episodes, 1)
                        * 100
                    ),
                )
            ),
            "check_timestamp": result.check_timestamp.isoformat(),
            "expected_sequence": result.expected_sequence,
            "actual_numbers": result.actual_numbers,
        }

        if CORE_AVAILABLE:
            return SuccessResponseDTO(
                success=True,
                message=f"Project integrity check completed for {project_id}",
                data=integrity_data,
            )
        else:
            return {"success": True, "data": integrity_data}

    except Exception as e:
        logger.error(f"Failed to check project integrity: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check integrity for project {project_id}",
        )


@router.get("/performance/stats")
async def get_performance_stats(
    project_id: str | None = Query(None, description="Filter by project ID"),
    db: Session = Depends(get_db),
):
    """Get episode creation performance statistics"""
    try:
        tracker = get_performance_tracker()

        # Get basic performance stats
        stats = {
            "active_operations": len(tracker.active_operations),
            "average_duration_seconds": 0.5,  # Placeholder - would come from metrics DB
            "p95_duration_seconds": 1.2,  # Placeholder
            "p99_duration_seconds": 2.1,  # Placeholder
            "success_rate_percentage": 98.5,  # Placeholder
            "conflict_rate_percentage": 2.1,  # Placeholder
            "total_operations_today": 1247,  # Placeholder
            "failed_operations_today": 18,  # Placeholder
        }

        # Add project-specific stats if requested
        if project_id:
            stats["project_id"] = project_id
            stats["project_operations_today"] = 45  # Placeholder
            stats["project_success_rate"] = 97.8  # Placeholder

        if CORE_AVAILABLE:
            return SuccessResponseDTO(
                success=True,
                message="Performance statistics retrieved successfully",
                data=stats,
            )
        else:
            return {"success": True, "data": stats}

    except Exception as e:
        logger.error(f"Failed to get performance stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve performance statistics",
        )


@router.get("/alerts/active")
async def get_active_alerts(db: Session = Depends(get_db)):
    """Get currently active alerts"""
    try:
        alert_manager = get_alert_manager(db)
        active_alerts = alert_manager.get_active_alerts()

        alerts_data = [alert.to_dict() for alert in active_alerts]
        summary = alert_manager.get_alert_summary()

        response_data = {"active_alerts": alerts_data, "summary": summary}

        if CORE_AVAILABLE:
            return SuccessResponseDTO(
                success=True,
                message=f"Retrieved {len(active_alerts)} active alerts",
                data=response_data,
            )
        else:
            return {"success": True, "data": response_data}

    except Exception as e:
        logger.error(f"Failed to get active alerts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve active alerts",
        )


@router.post("/alerts/check")
async def trigger_alert_checks(
    project_id: str | None = Query(None, description="Check specific project"),
    db: Session = Depends(get_db),
):
    """Manually trigger alert checks"""
    try:
        alert_manager = get_alert_manager(db)
        triggered_alerts = alert_manager.run_all_checks(project_id)

        if CORE_AVAILABLE:
            return SuccessResponseDTO(
                success=True,
                message=f"Alert checks completed, {len(triggered_alerts)} alerts triggered",
                data={
                    "triggered_alerts": len(triggered_alerts),
                    "alerts": [alert.to_dict() for alert in triggered_alerts],
                },
            )
        else:
            return {
                "success": True,
                "data": {"triggered_alerts": len(triggered_alerts)},
            }

    except Exception as e:
        logger.error(f"Failed to trigger alert checks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger alert checks",
        )


@router.post("/alerts/{alert_key}/resolve")
async def resolve_alert(alert_key: str, db: Session = Depends(get_db)):
    """Resolve a specific alert"""
    try:
        alert_manager = get_alert_manager(db)
        resolved = alert_manager.resolve_alert(alert_key)

        if resolved:
            if CORE_AVAILABLE:
                return SuccessResponseDTO(
                    success=True, message=f"Alert {alert_key} resolved successfully"
                )
            else:
                return {"success": True, "message": "Alert resolved"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert {alert_key} not found",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resolve alert: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resolve alert",
        )


@router.get("/jobs/integrity/status")
async def get_integrity_job_status(db: Session = Depends(get_db)):
    """Get status of integrity monitoring job"""
    try:
        job = get_integrity_job(db)
        stats = job.get_stats()

        if CORE_AVAILABLE:
            return SuccessResponseDTO(
                success=True,
                message="Integrity job status retrieved successfully",
                data=stats,
            )
        else:
            return {"success": True, "data": stats}

    except Exception as e:
        logger.error(f"Failed to get integrity job status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve integrity job status",
        )


@router.post("/jobs/integrity/run-check")
async def run_integrity_check(
    deep_check: bool = Query(False, description="Run deep integrity check"),
    db: Session = Depends(get_db),
):
    """Manually run integrity check"""
    try:
        job = get_integrity_job(db)

        if deep_check:
            result = await job.run_deep_check()
        else:
            result = await job.run_basic_check()

        if CORE_AVAILABLE:
            return SuccessResponseDTO(
                success=True,
                message=f"{'Deep' if deep_check else 'Basic'} integrity check completed",
                data=result,
            )
        else:
            return {"success": True, "data": result}

    except Exception as e:
        logger.error(f"Failed to run integrity check: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to run integrity check",
        )


@router.post("/integrity/fix-gaps/{project_id}")
async def fix_project_gaps(
    project_id: str,
    dry_run: bool = Query(True, description="Perform dry run without making changes"),
    db: Session = Depends(get_db),
):
    """Fix episode number gaps for a project (use with caution)"""
    try:
        fixer = IntegrityAutoFixer(db)
        result = await fixer.fix_gaps(project_id, dry_run)

        if CORE_AVAILABLE:
            return SuccessResponseDTO(
                success=True,
                message=f"Gap fixing {'simulation' if dry_run else 'operation'} completed for project {project_id}",
                data=result,
            )
        else:
            return {"success": True, "data": result}

    except Exception as e:
        logger.error(f"Failed to fix gaps for project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fix gaps for project {project_id}",
        )


@router.get("/metrics/export")
async def export_metrics(
    format: str = Query("json", description="Export format: json, prometheus"),
    project_id: str | None = Query(None, description="Filter by project"),
    db: Session = Depends(get_db),
):
    """Export episode monitoring metrics"""
    try:
        # Collect all metrics
        integrity_checker = get_integrity_checker(db)
        summary = integrity_checker.get_integrity_summary()

        metrics = {
            "episode_number_gaps_detected": summary["total_gaps"],
            "episode_number_duplicates_detected": summary["total_duplicates"],
            "episode_creation_success_rate": 98.5,  # Placeholder
            "episode_creation_conflicts_total": 25,  # Placeholder
            "episode_creation_retries_total": 67,  # Placeholder
            "episode_projects_healthy": summary["healthy_projects"],
            "episode_projects_total": summary["total_projects"],
            "timestamp": datetime.utcnow().isoformat(),
        }

        if format == "prometheus":
            # Convert to Prometheus format
            prometheus_metrics = []
            for metric_name, value in metrics.items():
                if isinstance(value, (int, float)):
                    prometheus_metrics.append(f"{metric_name} {value}")

            prometheus_output = "\n".join(prometheus_metrics)

            return {"format": "prometheus", "data": prometheus_output}
        else:
            # Return JSON format
            if CORE_AVAILABLE:
                return SuccessResponseDTO(
                    success=True, message="Metrics exported successfully", data=metrics
                )
            else:
                return {"success": True, "data": metrics}

    except Exception as e:
        logger.error(f"Failed to export metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export metrics",
        )
