"""
API endpoints for retry queue management and progress monitoring
"""

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, status

from ..services.retry_queue import get_retry_queue
from ..services.save_processors import (
    enqueue_generation_save,
)

try:
    from ai_script_core import ErrorResponseDTO, SuccessResponseDTO, get_service_logger

    logger = get_service_logger("generation-service.retry-endpoints")
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


router = APIRouter(prefix="/api/v1/retry", tags=["Retry Management"])


@router.get("/queue/stats")
async def get_queue_stats() -> dict[str, Any]:
    """Get retry queue statistics"""
    try:
        queue = get_retry_queue()
        stats = await queue.get_queue_stats()

        if CORE_AVAILABLE:
            return SuccessResponseDTO(
                success=True,
                message="Queue statistics retrieved successfully",
                data=stats,
            )
        else:
            return {"success": True, "data": stats}

    except Exception as e:
        logger.error(f"Failed to get queue stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve queue statistics",
        )


@router.get("/job/{job_id}/status")
async def get_job_status(job_id: str) -> dict[str, Any]:
    """Get status of a specific retry job"""
    try:
        queue = get_retry_queue()
        job = await queue.get_job_status(job_id)

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found"
            )

        job_dict = job.to_dict()

        if CORE_AVAILABLE:
            return SuccessResponseDTO(
                success=True, message="Job status retrieved successfully", data=job_dict
            )
        else:
            return {"success": True, "data": job_dict}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve job status",
        )


@router.get("/generation/{generation_id}/retry-progress")
async def get_generation_retry_progress(
    generation_id: str,
) -> dict[str, Any]:
    """Get retry progress for a generation"""
    try:
        # This would need to be implemented to track generation-specific retry jobs
        # For now, return a placeholder response

        retry_progress = {
            "jobId": f"retry_gen_{generation_id}",
            "generationId": generation_id,
            "currentAttempt": 2,
            "maxAttempts": 5,
            "attempts": [
                {
                    "attempt": 1,
                    "timestamp": "2024-01-01T10:00:00Z",
                    "status": "failed",
                    "error": "Network timeout",
                    "nextRetryAt": "2024-01-01T10:01:00Z",
                },
                {
                    "attempt": 2,
                    "timestamp": "2024-01-01T10:01:00Z",
                    "status": "processing",
                },
            ],
            "status": "processing",
            "createdAt": "2024-01-01T09:59:00Z",
            "lastError": "Network timeout",
        }

        if CORE_AVAILABLE:
            return SuccessResponseDTO(
                success=True,
                message="Retry progress retrieved successfully",
                data=retry_progress,
            )
        else:
            return {"success": True, "data": retry_progress}

    except Exception as e:
        logger.error(f"Failed to get retry progress: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve retry progress",
        )


@router.post("/generation/{generation_id}/manual-save")
async def manual_save_generation(
    generation_id: str, save_data: Optional[dict[str, Any]] = None
) -> dict[str, Any]:
    """Manually trigger save for a generation"""
    try:
        # Extract save data from request or fetch from cache
        if not save_data:
            # This would typically fetch generation data from cache/database
            save_data = {
                "generation_id": generation_id,
                "project_id": "example_project",
                "episode_id": "example_episode",
                "generation_data": {
                    "content": "Generated script content",
                    "title": "Generated Title",
                    "metadata": {"model": "gpt-4", "timestamp": "2024-01-01T10:00:00Z"},
                },
            }

        # Enqueue save job with immediate processing
        job_id = await enqueue_generation_save(
            generation_id=generation_id,
            project_id=save_data["project_id"],
            episode_id=save_data["episode_id"],
            generation_data=save_data["generation_data"],
            delay_seconds=0,  # Process immediately
        )

        logger.info(
            f"Manual save job enqueued: {job_id} for generation {generation_id}"
        )

        if CORE_AVAILABLE:
            return SuccessResponseDTO(
                success=True,
                message="Manual save job enqueued successfully",
                data={"job_id": job_id},
            )
        else:
            return {"success": True, "data": {"job_id": job_id}}

    except Exception as e:
        logger.error(f"Failed to enqueue manual save: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enqueue manual save job",
        )


@router.post("/cleanup/old-jobs")
async def cleanup_old_jobs(
    older_than_hours: int = 24,
) -> dict[str, Any]:
    """Clean up old retry jobs"""
    try:
        queue = get_retry_queue()
        cleaned_count = await queue.cleanup_old_jobs(older_than_hours)

        logger.info(f"Cleaned up {cleaned_count} old jobs")

        if CORE_AVAILABLE:
            return SuccessResponseDTO(
                success=True,
                message=f"Cleaned up {cleaned_count} old jobs",
                data={"cleaned_count": cleaned_count},
            )
        else:
            return {"success": True, "data": {"cleaned_count": cleaned_count}}

    except Exception as e:
        logger.error(f"Failed to cleanup old jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cleanup old jobs",
        )
