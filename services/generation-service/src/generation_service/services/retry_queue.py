"""
Background retry queue system for storage failure recovery
"""

import asyncio
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

import redis
from redis.exceptions import RedisError

try:
    from ai_script_core import get_service_logger

    logger = get_service_logger("generation-service.retry-queue")
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Background job status"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD = "dead"  # Moved to dead letter queue


class JobType(str, Enum):
    """Types of background jobs"""

    SAVE_GENERATION = "save_generation"
    SAVE_EPISODE = "save_episode"
    SAVE_PROJECT = "save_project"
    CLEANUP_CACHE = "cleanup_cache"


@dataclass
class RetryJob:
    """Background retry job definition"""

    id: str
    job_type: JobType
    payload: dict[str, Any]
    created_at: datetime
    scheduled_at: datetime
    attempt: int
    max_attempts: int
    status: JobStatus
    last_error: Optional[str] = None
    last_attempt_at: Optional[datetime] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for Redis storage"""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        data["created_at"] = self.created_at.isoformat()
        data["scheduled_at"] = self.scheduled_at.isoformat()
        if self.last_attempt_at:
            data["last_attempt_at"] = self.last_attempt_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RetryJob":
        """Create from dictionary"""
        # Convert ISO strings back to datetime objects
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["scheduled_at"] = datetime.fromisoformat(data["scheduled_at"])
        if data.get("last_attempt_at"):
            data["last_attempt_at"] = datetime.fromisoformat(data["last_attempt_at"])

        return cls(**data)


class ExponentialBackoff:
    """Exponential backoff calculator with jitter"""

    @staticmethod
    def calculate_delay(
        attempt: int,
        base_delay: float = 1.0,
        max_delay: float = 16.0,
        jitter: bool = True,
    ) -> float:
        """Calculate delay for retry attempt"""
        import random

        # Exponential backoff: base_delay * (2 ** attempt)
        delay = base_delay * (2**attempt)
        delay = min(delay, max_delay)

        # Add jitter to prevent thundering herd
        if jitter:
            delay += random.uniform(0, delay * 0.1)

        return delay


class RetryQueue:
    """Redis-based background retry queue"""

    def __init__(
        self,
        redis_client: redis.Optional[Redis] = None,
        queue_name: str = "retry_queue",
        dlq_name: str = "dead_letter_queue",
        processing_set: str = "processing_jobs",
        max_attempts: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 16.0,
    ):
        self.redis = redis_client or redis.Redis(decode_responses=True)
        self.queue_name = queue_name
        self.dlq_name = dlq_name
        self.processing_set = processing_set
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff = ExponentialBackoff()

        # Job processors registry
        self.processors: dict[JobType, Callable] = {}

    def register_processor(self, job_type: JobType, processor: Callable) -> None:
        """Register a job processor function"""
        self.processors[job_type] = processor
        logger.info(f"Registered processor for job type: {job_type}")

    async def enqueue_job(
        self,
        job_type: JobType,
        payload: dict[str, Any],
        delay_seconds: float = 0,
        max_attempts: Optional[int] = None,
        job_id: Optional[str] = None,
    ) -> str:
        """Enqueue a job for background processing"""
        job_id = job_id or str(uuid.uuid4())
        max_attempts = max_attempts or self.max_attempts

        now = datetime.utcnow()
        scheduled_at = now + timedelta(seconds=delay_seconds)

        job = RetryJob(
            id=job_id,
            job_type=job_type,
            payload=payload,
            created_at=now,
            scheduled_at=scheduled_at,
            attempt=0,
            max_attempts=max_attempts,
            status=JobStatus.PENDING,
        )

        try:
            # Store job data
            job_key = f"job:{job_id}"
            await self._redis_hset(job_key, job.to_dict())

            # Add to scheduled queue with score as timestamp
            score = scheduled_at.timestamp()
            await self._redis_zadd(self.queue_name, {job_id: score})

            logger.info(f"Enqueued job {job_id} of type {job_type}")
            return job_id

        except RedisError as e:
            logger.error(f"Failed to enqueue job: {e}")
            raise

    async def get_ready_jobs(self, limit: int = 10) -> list[RetryJob]:
        """Get jobs ready for processing"""
        try:
            now = datetime.utcnow().timestamp()

            # Get jobs scheduled for now or earlier
            job_ids = await self._redis_zrangebyscore(self.queue_name, 0, now, 0, limit)

            if not job_ids:
                return []

            # Get job details
            jobs = []
            for job_id in job_ids:
                job_data = await self._redis_hgetall(f"job:{job_id}")
                if job_data:
                    job = RetryJob.from_dict(job_data)
                    jobs.append(job)

            return jobs

        except RedisError as e:
            logger.error(f"Failed to get ready jobs: {e}")
            return []

    async def process_job(self, job: RetryJob) -> bool:
        """Process a single job"""
        job_key = f"job:{job.id}"

        try:
            # Move to processing set
            await self._redis_zrem(self.queue_name, job.id)
            await self._redis_sadd(self.processing_set, job.id)

            # Update job status
            job.status = JobStatus.PROCESSING
            job.attempt += 1
            job.last_attempt_at = datetime.utcnow()
            await self._redis_hset(job_key, job.to_dict())

            # Get processor
            processor = self.processors.get(job.job_type)
            if not processor:
                raise ValueError(
                    f"No processor registered for job type: {job.job_type}"
                )

            # Execute processor
            await processor(job.payload)

            # Mark as completed
            job.status = JobStatus.COMPLETED
            await self._redis_hset(job_key, job.to_dict())
            await self._redis_srem(self.processing_set, job.id)

            logger.info(f"Successfully processed job {job.id}")
            return True

        except Exception as e:
            # Handle job failure
            await self._handle_job_failure(job, str(e))
            return False

    async def _handle_job_failure(self, job: RetryJob, error_message: str) -> None:
        """Handle job processing failure"""
        job_key = f"job:{job.id}"

        try:
            job.status = JobStatus.FAILED
            job.last_error = error_message
            await self._redis_hset(job_key, job.to_dict())
            await self._redis_srem(self.processing_set, job.id)

            # Check if we should retry
            if job.attempt < job.max_attempts:
                # Calculate next retry delay
                delay = self.backoff.calculate_delay(
                    job.attempt, self.base_delay, self.max_delay
                )

                # Reschedule job
                next_attempt = datetime.utcnow() + timedelta(seconds=delay)
                job.scheduled_at = next_attempt
                job.status = JobStatus.PENDING

                await self._redis_hset(job_key, job.to_dict())
                await self._redis_zadd(
                    self.queue_name, {job.id: next_attempt.timestamp()}
                )

                logger.warning(
                    f"Job {job.id} failed (attempt {job.attempt}/{job.max_attempts}), "
                    f"retrying in {delay:.1f}s: {error_message}"
                )
            else:
                # Move to dead letter queue
                await self._move_to_dlq(job)
                logger.error(
                    f"Job {job.id} exhausted all retries, moved to DLQ: {error_message}"
                )

        except RedisError as e:
            logger.error(f"Failed to handle job failure: {e}")

    async def _move_to_dlq(self, job: RetryJob) -> None:
        """Move job to dead letter queue"""
        job.status = JobStatus.DEAD

        try:
            # Store in DLQ with timestamp score
            score = datetime.utcnow().timestamp()
            await self._redis_zadd(self.dlq_name, {job.id: score})
            await self._redis_hset(f"job:{job.id}", job.to_dict())

        except RedisError as e:
            logger.error(f"Failed to move job to DLQ: {e}")

    async def get_job_status(self, job_id: str) -> Optional[RetryJob]:
        """Get current job status"""
        try:
            job_data = await self._redis_hgetall(f"job:{job_id}")
            if job_data:
                return RetryJob.from_dict(job_data)
            return None

        except RedisError as e:
            logger.error(f"Failed to get job status: {e}")
            return None

    async def get_queue_stats(self) -> dict[str, int]:
        """Get queue statistics"""
        try:
            pending_count = await self._redis_zcard(self.queue_name)
            processing_count = await self._redis_scard(self.processing_set)
            dlq_count = await self._redis_zcard(self.dlq_name)

            return {
                "pending": pending_count,
                "processing": processing_count,
                "dead_letter": dlq_count,
                "total": pending_count + processing_count + dlq_count,
            }

        except RedisError as e:
            logger.error(f"Failed to get queue stats: {e}")
            return {"pending": 0, "processing": 0, "dead_letter": 0, "total": 0}

    async def cleanup_old_jobs(self, older_than_hours: int = 24) -> int:
        """Clean up old completed/dead jobs"""
        try:
            cutoff = datetime.utcnow() - timedelta(hours=older_than_hours)
            cutoff_timestamp = cutoff.timestamp()

            # Remove from DLQ
            dlq_removed = await self._redis_zremrangebyscore(
                self.dlq_name, 0, cutoff_timestamp
            )

            # Could also clean up job data, but keep for debugging
            logger.info(f"Cleaned up {dlq_removed} old jobs from DLQ")
            return dlq_removed

        except RedisError as e:
            logger.error(f"Failed to cleanup old jobs: {e}")
            return 0

    # Redis async wrapper methods (for compatibility)
    async def _redis_hset(self, key: str, data: dict[str, Any]) -> int:
        """Async wrapper for Redis HSET"""
        return self.redis.hset(key, mapping=data)

    async def _redis_hgetall(self, key: str) -> dict[str, str]:
        """Async wrapper for Redis HGETALL"""
        return self.redis.hgetall(key)

    async def _redis_zadd(self, key: str, mapping: dict[str, float]) -> int:
        """Async wrapper for Redis ZADD"""
        return self.redis.zadd(key, mapping)

    async def _redis_zrangebyscore(
        self, key: str, min_score: float, max_score: float, start: int, num: int
    ) -> list[str]:
        """Async wrapper for Redis ZRANGEBYSCORE"""
        return self.redis.zrangebyscore(key, min_score, max_score, start, num)

    async def _redis_zrem(self, key: str, *values: Any) -> int:
        """Async wrapper for Redis ZREM"""
        return self.redis.zrem(key, *values)

    async def _redis_sadd(self, key: str, *values: Any) -> int:
        """Async wrapper for Redis SADD"""
        return self.redis.sadd(key, *values)

    async def _redis_srem(self, key: str, *values: Any) -> int:
        """Async wrapper for Redis SREM"""
        return self.redis.srem(key, *values)

    async def _redis_zcard(self, key: str) -> int:
        """Async wrapper for Redis ZCARD"""
        return self.redis.zcard(key)

    async def _redis_scard(self, key: str) -> int:
        """Async wrapper for Redis SCARD"""
        return self.redis.scard(key)

    async def _redis_zremrangebyscore(
        self, key: str, min_score: float, max_score: float
    ) -> int:
        """Async wrapper for Redis ZREMRANGEBYSCORE"""
        return self.redis.zremrangebyscore(key, min_score, max_score)


class RetryQueueWorker:
    """Background worker to process retry queue"""

    def __init__(
        self,
        retry_queue: RetryQueue,
        worker_id: Optional[str] = None,
        poll_interval: float = 1.0,
        batch_size: int = 10,
    ):
        self.queue = retry_queue
        self.worker_id = worker_id or str(uuid.uuid4())
        self.poll_interval = poll_interval
        self.batch_size = batch_size
        self.running = False

    async def start(self) -> None:
        """Start the worker"""
        self.running = True
        logger.info(f"Starting retry queue worker {self.worker_id}")

        try:
            while self.running:
                try:
                    # Get ready jobs
                    jobs = await self.queue.get_ready_jobs(self.batch_size)

                    if jobs:
                        # Process jobs concurrently
                        tasks = [self.queue.process_job(job) for job in jobs]
                        await asyncio.gather(*tasks, return_exceptions=True)
                    else:
                        # No jobs ready, wait before polling again
                        await asyncio.sleep(self.poll_interval)

                except Exception as e:
                    logger.error(f"Worker {self.worker_id} error: {e}")
                    await asyncio.sleep(self.poll_interval)

        except asyncio.CancelledError:
            logger.info(f"Worker {self.worker_id} was cancelled")
        finally:
            self.running = False
            logger.info(f"Worker {self.worker_id} stopped")

    async def stop(self) -> None:
        """Stop the worker"""
        self.running = False


# Singleton instances
_global_retry_queue: Optional[RetryQueue] = None
_global_worker: Optional[RetryQueueWorker] = None


def get_retry_queue(redis_client: redis.Optional[Redis] = None) -> RetryQueue:
    """Get global retry queue instance"""
    global _global_retry_queue
    if _global_retry_queue is None:
        _global_retry_queue = RetryQueue(redis_client)
    return _global_retry_queue


async def start_retry_worker() -> None:
    """Start global retry queue worker"""
    global _global_worker
    if _global_worker is None:
        queue = get_retry_queue()
        _global_worker = RetryQueueWorker(queue)

    if not _global_worker.running:
        await _global_worker.start()


async def stop_retry_worker() -> None:
    """Stop global retry queue worker"""
    global _global_worker
    if _global_worker and _global_worker.running:
        await _global_worker.stop()
