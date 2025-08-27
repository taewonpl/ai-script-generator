"""
Generation Job Manager for SSE-based script generation
"""

import asyncio
import json
import logging
import threading
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

import redis

from ..models.sse_models import (
    GenerationJob,
    GenerationJobRequest,
    GenerationJobStatus,
    SSEEvent,
)

logger = logging.getLogger(__name__)


class JobManager:
    """Manages generation jobs and SSE events with Redis persistence"""

    def __init__(self, redis_url: Optional[str] = None) -> None:
        self.jobs: dict[str, GenerationJob] = {}
        self.active_connections: dict[str, int] = {}  # jobId -> connection count
        self.event_history: dict[str, list[str]] = {}  # jobId -> [event_id, ...]
        self.lock = threading.Lock()
        self.connection_timeout = 60  # seconds
        self.cleanup_interval = 300  # 5 minutes

        # Redis setup for distributed environment
        self.redis_client: redis.Optional[Redis] = None
        self._setup_redis(redis_url)

        # Start background tasks
        self._start_cleanup_task()

    def _setup_redis(self, redis_url: Optional[str]) -> None:
        """Setup Redis connection for distributed job storage"""
        try:
            if redis_url:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                # Test connection
                self.redis_client.ping()
                logger.info(f"Connected to Redis: {redis_url}")
            else:
                # Try default local Redis
                self.redis_client = redis.Redis(
                    host="localhost", port=6379, decode_responses=True
                )
                self.redis_client.ping()
                logger.info("Connected to local Redis")
        except Exception as e:
            logger.warning(
                f"Redis connection failed: {e}. Running in memory-only mode."
            )
            self.redis_client = None

    def _persist_job(self, job: GenerationJob) -> None:
        """Persist job to Redis if available"""
        if self.redis_client:
            try:
                key = f"job:{job.jobId}"
                job_data = job.model_dump(mode="json")
                self.redis_client.setex(
                    key, 3600, json.dumps(job_data)
                )  # 1 hour expiry
                logger.debug(f"Persisted job {job.jobId} to Redis")
            except Exception as e:
                logger.warning(f"Failed to persist job {job.jobId}: {e}")

    def _load_job_from_redis(self, job_id: str) -> Optional[GenerationJob]:
        """Load job from Redis if available"""
        if self.redis_client:
            try:
                key = f"job:{job_id}"
                job_data = self.redis_client.get(key)
                if job_data:
                    data = json.loads(job_data)
                    return GenerationJob(**data)
            except Exception as e:
                logger.warning(f"Failed to load job {job_id} from Redis: {e}")
        return None

    def _get_event_history(self, job_id: str) -> list[str]:
        """Get event history for Last-Event-ID support"""
        if self.redis_client:
            try:
                key = f"events:{job_id}"
                return self.redis_client.lrange(key, 0, -1)
            except Exception as e:
                logger.warning(f"Failed to get event history for {job_id}: {e}")

        return self.event_history.get(job_id, [])

    def _store_event_id(self, job_id: str, event_id: str) -> None:
        """Store event ID for Last-Event-ID support"""
        if self.redis_client:
            try:
                key = f"events:{job_id}"
                # Keep last 100 events
                self.redis_client.lpush(key, event_id)
                self.redis_client.ltrim(key, 0, 99)
                self.redis_client.expire(key, 3600)  # 1 hour expiry
            except Exception as e:
                logger.warning(f"Failed to store event ID for {job_id}: {e}")
        else:
            # Fallback to in-memory
            if job_id not in self.event_history:
                self.event_history[job_id] = []
            self.event_history[job_id].append(event_id)
            # Keep last 100 events
            self.event_history[job_id] = self.event_history[job_id][-100:]

    def _start_cleanup_task(self) -> None:
        """Start background task for cleanup"""
        asyncio.create_task(self._cleanup_task())

    async def _cleanup_task(self) -> None:
        """Clean up finished jobs periodically"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)

                cutoff_time = datetime.now(timezone.utc) - timedelta(
                    hours=1
                )  # Keep for 1 hour

                with self.lock:
                    jobs_to_remove = []
                    for job_id, job in self.jobs.items():
                        if (
                            job.is_finished()
                            and job.completedAt
                            and job.completedAt < cutoff_time
                            and self.active_connections.get(job_id, 0) == 0
                        ):
                            jobs_to_remove.append(job_id)

                    for job_id in jobs_to_remove:
                        logger.info(f"Cleaning up finished job: {job_id}")
                        self.jobs.pop(job_id, None)
                        self.active_connections.pop(job_id, None)

            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")

    def create_job(self, request: GenerationJobRequest) -> GenerationJob:
        """Create a new generation job"""
        job_id = f"job_{uuid4().hex[:16]}"

        # Generate title if not provided
        title = request.title
        if not title:
            title = f"Script Generation - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        job = GenerationJob(
            jobId=job_id,
            projectId=request.projectId,
            episodeNumber=request.episodeNumber,
            title=title,
            description=request.description,
            scriptType=request.scriptType,
            promptSnapshot=request.description,
            estimatedDuration=self._estimate_duration(request),
        )

        with self.lock:
            self.jobs[job_id] = job
            self.active_connections[job_id] = 0

        logger.info(f"Created generation job: {job_id}")
        return job

    def get_job(self, job_id: str) -> Optional[GenerationJob]:
        """Get job by ID, checking Redis if not in memory"""
        # Check in-memory first
        job = self.jobs.get(job_id)
        if job:
            return job

        # Check Redis if not in memory (distributed environment)
        job = self._load_job_from_redis(job_id)
        if job:
            # Cache in memory for performance
            with self.lock:
                self.jobs[job_id] = job
                if job_id not in self.active_connections:
                    self.active_connections[job_id] = 0

        return job

    def update_job_progress(
        self, job_id: str, progress: int, step: str, content: str = ""
    ) -> bool:
        """Update job progress"""
        job = self.get_job(job_id)
        if not job:
            return False

        job.update_progress(progress, step, content)

        # Store event ID for Last-Event-ID support
        if job.lastEventId:
            self._store_event_id(job_id, job.lastEventId)

        # Persist to Redis
        self._persist_job(job)

        logger.debug(f"Updated job {job_id}: {progress}% - {step}")
        return True

    def complete_job(
        self, job_id: str, final_content: str, tokens: int = 0, model_used: str = None
    ) -> bool:
        """Mark job as completed"""
        job = self.get_job(job_id)
        if not job:
            return False

        job.complete(final_content, tokens, model_used)
        logger.info(f"Completed job {job_id}")
        return True

    def fail_job(self, job_id: str, error_code: str, error_message: str) -> bool:
        """Mark job as failed"""
        job = self.get_job(job_id)
        if not job:
            return False

        job.fail(error_code, error_message)
        logger.error(f"Failed job {job_id}: {error_code} - {error_message}")
        return True

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job (idempotent)"""
        job = self.get_job(job_id)
        if not job:
            return False  # Job doesn't exist

        if job.is_finished():
            return True  # Already finished (idempotent)

        job.cancel()
        logger.info(f"Canceled job {job_id}")
        return True

    def start_job_streaming(self, job_id: str) -> bool:
        """Start job streaming"""
        job = self.get_job(job_id)
        if not job or job.status != GenerationJobStatus.QUEUED:
            return False

        job.status = GenerationJobStatus.STREAMING
        job.startedAt = datetime.now(timezone.utc)
        logger.info(f"Started streaming job {job_id}")
        return True

    def add_connection(self, job_id: str) -> None:
        """Add SSE connection for a job"""
        with self.lock:
            self.active_connections[job_id] = self.active_connections.get(job_id, 0) + 1
        logger.debug(
            f"Added connection for job {job_id}, total: {self.active_connections[job_id]}"
        )

    def remove_connection(self, job_id: str) -> None:
        """Remove SSE connection for a job"""
        with self.lock:
            if job_id in self.active_connections:
                self.active_connections[job_id] = max(
                    0, self.active_connections[job_id] - 1
                )
        logger.debug(
            f"Removed connection for job {job_id}, remaining: {self.active_connections.get(job_id, 0)}"
        )

    def get_active_jobs(self) -> list[GenerationJob]:
        """Get all active jobs"""
        return [job for job in self.jobs.values() if job.is_active()]

    def get_job_stats(self) -> dict[str, int]:
        """Get job statistics"""
        stats = {
            "total_jobs": len(self.jobs),
            "queued": 0,
            "streaming": 0,
            "completed": 0,
            "failed": 0,
            "canceled": 0,
            "active_connections": sum(self.active_connections.values()),
        }

        for job in self.jobs.values():
            stats[job.status.value] += 1

        return stats

    async def generate_sse_events(
        self, job_id: str, last_event_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Generate SSE events for a job"""
        job = self.get_job(job_id)
        if not job:
            # Send error event for non-existent job
            error_event = SSEEvent.create_error(
                job_id=job_id,
                error_code="JOB_NOT_FOUND",
                error_message="Job not found",
                retryable=False,
            )
            yield error_event.format_sse()
            return

        # Add connection
        self.add_connection(job_id)

        try:
            # Handle Last-Event-ID reconnection
            if last_event_id:
                # Check if we need to replay missed events
                event_history = self._get_event_history(job_id)
                try:
                    last_index = event_history.index(last_event_id)
                    # Send events after the last received event
                    missed_events = event_history[:last_index]
                    for missed_event_id in reversed(
                        missed_events
                    ):  # Redis LRANGE returns in reverse
                        # For simplicity, just send current state
                        # In production, you'd store event data too
                        logger.info(
                            f"Replaying missed event {missed_event_id} for job {job_id}"
                        )
                except (ValueError, IndexError):
                    logger.warning(
                        f"Could not find last event ID {last_event_id} for job {job_id}"
                    )

            # Send initial progress event with event ID
            job.eventSequence += 1
            job.lastEventId = f"{job.jobId}_{job.eventSequence}"
            self._store_event_id(job_id, job.lastEventId)
            yield job.to_progress_event().format_sse(job.lastEventId)

            last_progress = job.progress
            last_content = job.currentContent

            while not job.is_finished():
                # Send progress update if changed
                if job.progress != last_progress:
                    job.eventSequence += 1
                    progress_event_id = f"{job.jobId}_{job.eventSequence}"
                    job.lastEventId = progress_event_id
                    self._store_event_id(job_id, progress_event_id)

                    yield job.to_progress_event().format_sse(progress_event_id)
                    last_progress = job.progress

                # Send preview update if content changed
                if job.currentContent != last_content and job.currentContent.strip():
                    job.eventSequence += 1
                    preview_event_id = f"{job.jobId}_{job.eventSequence}"
                    job.lastEventId = preview_event_id
                    self._store_event_id(job_id, preview_event_id)

                    yield job.to_preview_event().format_sse(preview_event_id)
                    last_content = job.currentContent

                # Wait before checking again
                await asyncio.sleep(0.5)

            # Send final event based on job status with event ID
            job.eventSequence += 1
            final_event_id = f"{job.jobId}_{job.eventSequence}"
            job.lastEventId = final_event_id
            self._store_event_id(job_id, final_event_id)

            if job.status == GenerationJobStatus.COMPLETED:
                yield job.to_completed_event().format_sse(final_event_id)
            elif job.status == GenerationJobStatus.FAILED:
                yield job.to_failed_event().format_sse(final_event_id)
            elif job.status == GenerationJobStatus.CANCELED:
                cancel_event = SSEEvent.create_error(
                    job_id=job_id,
                    error_code="JOB_CANCELED",
                    error_message="Job was canceled",
                    retryable=False,
                )
                yield cancel_event.format_sse(final_event_id)

        except Exception as e:
            logger.error(f"Error generating SSE events for job {job_id}: {e}")
            error_event = SSEEvent.create_error(
                job_id=job_id,
                error_code="SSE_ERROR",
                error_message=f"SSE stream error: {e!s}",
                retryable=True,
            )
            yield error_event.format_sse()
        finally:
            # Remove connection
            self.remove_connection(job_id)

    def _estimate_duration(self, request: GenerationJobRequest) -> int:
        """Estimate generation duration in seconds"""
        base_time = 60  # 1 minute base

        # Adjust based on content length
        content_factor = len(request.description) / 100
        length_factor = (request.lengthTarget or 1000) / 1000

        estimated = base_time + (content_factor * 10) + (length_factor * 30)
        return max(30, min(300, int(estimated)))  # Between 30s and 5 minutes


# Global job manager instance
_job_manager: Optional[JobManager] = None


def get_job_manager() -> JobManager:
    """Get or create job manager instance"""
    global _job_manager
    if _job_manager is None:
        _job_manager = JobManager()
    return _job_manager
