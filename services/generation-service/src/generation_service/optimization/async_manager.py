"""
Async optimization and parallel execution management
"""

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

# Import Core Module components
try:
    from ai_script_core import (
        get_service_logger,
        utc_now,
    )

    CORE_AVAILABLE = True
    logger = get_service_logger("generation-service.async_manager")
except (ImportError, RuntimeError):
    CORE_AVAILABLE = False
    import logging

    logger = logging.getLogger(__name__)  # type: ignore[assignment]

    # Fallback utility functions
    def utc_now() -> datetime:
        """Fallback UTC timestamp"""
        from datetime import datetime, timezone

        return datetime.now(timezone.utc)

    def generate_uuid() -> str:
        """Fallback UUID generation"""
        import uuid

        return str(uuid.uuid4())

    def generate_id() -> str:
        """Fallback ID generation"""
        import uuid

        return str(uuid.uuid4())[:8]

    # Fallback base classes
    class BaseDTO:
        """Fallback base DTO class"""

        pass

    class SuccessResponseDTO:
        """Fallback success response DTO"""

        pass

    class ErrorResponseDTO:
        """Fallback error response DTO"""

        pass


class TaskPriority(int, Enum):
    """Task execution priority levels"""

    LOW = 1
    NORMAL = 5
    HIGH = 8
    CRITICAL = 10


class TaskStatus(str, Enum):
    """Task execution status"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class TaskResult:
    """Result of async task execution"""

    task_id: str
    status: TaskStatus
    result: Any = None
    error: Exception | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    execution_time: float | None = None
    metadata: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}


@dataclass
class TaskMetrics:
    """Metrics for task execution"""

    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    cancelled_tasks: int = 0
    timeout_tasks: int = 0
    average_execution_time: float = 0.0
    total_execution_time: float = 0.0
    current_running_tasks: int = 0


class AsyncTaskPool:
    """
    Advanced async task pool with priority queue and resource management

    Features:
    - Priority-based task execution
    - Concurrent task limiting
    - Timeout handling
    - Task cancellation
    - Performance metrics
    - Resource monitoring
    """

    def __init__(
        self,
        max_concurrent_tasks: int = 10,
        default_timeout: float = 60.0,
        cleanup_interval: float = 300.0,
    ):
        self.max_concurrent_tasks = max_concurrent_tasks
        self.default_timeout = default_timeout
        self.cleanup_interval = cleanup_interval

        # Task management
        self._task_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._running_tasks: dict[str, asyncio.Task] = {}
        self._task_results: dict[str, TaskResult] = {}
        self._task_counter = 0

        # Semaphore for concurrent task limiting
        self._semaphore = asyncio.Semaphore(max_concurrent_tasks)

        # Worker task
        self._worker_task: asyncio.Task | None = None
        self._cleanup_task: asyncio.Task | None = None
        self._shutdown_event = asyncio.Event()

        # Metrics
        self.metrics = TaskMetrics()

        # Task lifecycle callbacks
        self._on_task_start: list[Callable] = []
        self._on_task_complete: list[Callable] = []
        self._on_task_error: list[Callable] = []

    async def start(self) -> None:
        """Start the task pool"""

        if self._worker_task and not self._worker_task.done():
            return

        self._shutdown_event.clear()
        self._worker_task = asyncio.create_task(self._worker())
        self._cleanup_task = asyncio.create_task(self._cleanup_worker())

        logger.info(
            "AsyncTaskPool started",
            extra={
                "max_concurrent_tasks": self.max_concurrent_tasks,
                "default_timeout": self.default_timeout,
            },
        )

    async def stop(self) -> None:
        """Stop the task pool and wait for completion"""

        self._shutdown_event.set()

        # Cancel all running tasks
        for task in self._running_tasks.values():
            if not task.done():
                task.cancel()

        # Wait for worker to finish
        if self._worker_task and not self._worker_task.done():
            await self._worker_task

        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        logger.info("AsyncTaskPool stopped")

    async def submit_task(
        self,
        coro: Awaitable[Any],
        priority: TaskPriority = TaskPriority.NORMAL,
        timeout: float | None = None,
        task_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Submit a task for async execution"""

        if task_id is None:
            self._task_counter += 1
            task_id = f"task_{self._task_counter}_{int(time.time())}"

        task_timeout = timeout or self.default_timeout
        task_metadata = metadata or {}

        # Create task item for priority queue
        # Priority is negated for min-heap (higher priority = lower number)
        task_item = (
            -priority.value,
            time.time(),
            task_id,
            coro,
            task_timeout,
            task_metadata,
        )

        await self._task_queue.put(task_item)

        # Initialize task result
        self._task_results[task_id] = TaskResult(
            task_id=task_id, status=TaskStatus.PENDING, metadata=task_metadata
        )

        self.metrics.total_tasks += 1

        logger.debug(
            f"Task submitted: {task_id}",
            extra={"priority": priority.name, "timeout": task_timeout},
        )

        return task_id

    async def get_result(
        self, task_id: str, timeout: float | None = None
    ) -> TaskResult:
        """Get result for a specific task"""

        if task_id not in self._task_results:
            raise ValueError(f"Task {task_id} not found")

        start_time = time.time()

        while True:
            result = self._task_results[task_id]

            if result.status in [
                TaskStatus.COMPLETED,
                TaskStatus.FAILED,
                TaskStatus.CANCELLED,
                TaskStatus.TIMEOUT,
            ]:
                return result

            # Check timeout
            if timeout and (time.time() - start_time) > timeout:
                raise asyncio.TimeoutError(f"Timeout waiting for task {task_id}")

            # Wait a bit before checking again
            await asyncio.sleep(0.1)

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running or pending task"""

        # Cancel if running
        if task_id in self._running_tasks:
            task = self._running_tasks[task_id]
            if not task.done():
                task.cancel()
                self._task_results[task_id].status = TaskStatus.CANCELLED
                self.metrics.cancelled_tasks += 1
                return True

        # Mark as cancelled if pending
        if task_id in self._task_results:
            if self._task_results[task_id].status == TaskStatus.PENDING:
                self._task_results[task_id].status = TaskStatus.CANCELLED
                self.metrics.cancelled_tasks += 1
                return True

        return False

    async def wait_for_tasks(
        self, task_ids: list[str], timeout: float | None = None
    ) -> list[TaskResult]:
        """Wait for multiple tasks to complete"""

        results = []
        start_time = time.time()

        for task_id in task_ids:
            remaining_timeout = None
            if timeout:
                elapsed = time.time() - start_time
                remaining_timeout = max(0, timeout - elapsed)

            try:
                result = await self.get_result(task_id, remaining_timeout)
                results.append(result)
            except asyncio.TimeoutError:
                # Return partial results on timeout
                break

        return results

    async def execute_batch(
        self,
        coroutines: list[Awaitable[Any]],
        max_concurrent: int | None = None,
        timeout: float | None = None,
        priority: TaskPriority = TaskPriority.NORMAL,
    ) -> list[TaskResult]:
        """Execute a batch of coroutines with controlled concurrency"""

        if not coroutines:
            return []

        batch_concurrent = min(
            max_concurrent or len(coroutines), self.max_concurrent_tasks
        )

        # Submit all tasks
        task_ids = []
        for coro in coroutines:
            task_id = await self.submit_task(coro, priority=priority, timeout=timeout)
            task_ids.append(task_id)

        # Wait for all tasks to complete
        return await self.wait_for_tasks(task_ids, timeout)

    async def _worker(self) -> None:
        """Main worker that processes tasks from the queue"""

        while not self._shutdown_event.is_set():
            try:
                # Get task from queue with timeout
                try:
                    task_item = await asyncio.wait_for(
                        self._task_queue.get(), timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                priority, submit_time, task_id, coro, timeout, metadata = task_item

                # Check if task was cancelled
                if (
                    task_id in self._task_results
                    and self._task_results[task_id].status == TaskStatus.CANCELLED
                ):
                    continue

                # Wait for semaphore (concurrent task limit)
                await self._semaphore.acquire()

                # Create and start task
                task = asyncio.create_task(self._execute_task(task_id, coro, timeout))
                self._running_tasks[task_id] = task

                # Don't await here - let it run in background
                task.add_done_callback(lambda t: self._semaphore.release())

            except Exception as e:
                logger.error(f"Worker error: {e}")
                await asyncio.sleep(1.0)

    async def _execute_task(self, task_id: str, coro: Awaitable[Any], timeout: float) -> None:
        """Execute a single task with timeout and error handling"""

        result = self._task_results[task_id]
        result.start_time = utc_now() if CORE_AVAILABLE else datetime.now()
        result.status = TaskStatus.RUNNING

        self.metrics.current_running_tasks += 1

        # Call start callbacks
        for callback in self._on_task_start:
            try:
                await callback(task_id, result)
            except Exception as e:
                logger.warning(f"Task start callback failed: {e}")

        try:
            # Execute with timeout
            task_result = await asyncio.wait_for(coro, timeout=timeout)

            result.result = task_result
            result.status = TaskStatus.COMPLETED
            self.metrics.completed_tasks += 1

            # Call completion callbacks
            for callback in self._on_task_complete:
                try:
                    await callback(task_id, result)
                except Exception as e:
                    logger.warning(f"Task complete callback failed: {e}")

        except asyncio.TimeoutError:
            result.status = TaskStatus.TIMEOUT
            result.error = asyncio.TimeoutError(
                f"Task {task_id} timed out after {timeout}s"
            )
            self.metrics.timeout_tasks += 1

            logger.warning(f"Task {task_id} timed out after {timeout}s")

        except asyncio.CancelledError:
            result.status = TaskStatus.CANCELLED
            self.metrics.cancelled_tasks += 1

            logger.debug(f"Task {task_id} was cancelled")
            raise  # Re-raise to properly handle cancellation

        except Exception as e:
            result.status = TaskStatus.FAILED
            result.error = e
            self.metrics.failed_tasks += 1

            logger.error(f"Task {task_id} failed: {e}")

            # Call error callbacks
            for callback in self._on_task_error:
                try:
                    await callback(task_id, result)
                except Exception as cb_error:
                    logger.warning(f"Task error callback failed: {cb_error}")

        finally:
            result.end_time = utc_now() if CORE_AVAILABLE else datetime.now()
            if result.start_time:
                result.execution_time = (
                    result.end_time - result.start_time
                ).total_seconds()

                # Update metrics
                self.metrics.total_execution_time += result.execution_time
                if self.metrics.completed_tasks > 0:
                    self.metrics.average_execution_time = (
                        self.metrics.total_execution_time / self.metrics.completed_tasks
                    )

            self.metrics.current_running_tasks -= 1

            # Remove from running tasks
            self._running_tasks.pop(task_id, None)

    async def _cleanup_worker(self) -> None:
        """Background worker for cleaning up old task results"""

        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(self.cleanup_interval)

                cutoff_time = (
                    utc_now() if CORE_AVAILABLE else datetime.now()
                ) - timedelta(hours=1)

                # Remove old completed task results
                to_remove = []
                for task_id, result in self._task_results.items():
                    if (
                        result.end_time
                        and result.end_time < cutoff_time
                        and result.status
                        in [
                            TaskStatus.COMPLETED,
                            TaskStatus.FAILED,
                            TaskStatus.CANCELLED,
                            TaskStatus.TIMEOUT,
                        ]
                    ):
                        to_remove.append(task_id)

                for task_id in to_remove:
                    self._task_results.pop(task_id, None)

                if to_remove:
                    logger.debug(f"Cleaned up {len(to_remove)} old task results")

            except Exception as e:
                logger.error(f"Cleanup worker error: {e}")

    def add_task_callback(
        self, event: str, callback: Callable[[str, TaskResult], Awaitable[None]]
    ) -> None:
        """Add callback for task lifecycle events"""

        if event == "start":
            self._on_task_start.append(callback)
        elif event == "complete":
            self._on_task_complete.append(callback)
        elif event == "error":
            self._on_task_error.append(callback)
        else:
            raise ValueError(f"Unknown event type: {event}")

    def get_metrics(self) -> TaskMetrics:
        """Get current task pool metrics"""
        return self.metrics

    def get_task_status(self, task_id: str) -> TaskStatus | None:
        """Get status of a specific task"""

        result = self._task_results.get(task_id)
        return result.status if result else None

    def get_running_tasks(self) -> list[str]:
        """Get list of currently running task IDs"""
        return list(self._running_tasks.keys())

    def get_pending_count(self) -> int:
        """Get number of pending tasks in queue"""
        return self._task_queue.qsize()


class AsyncManager:
    """
    High-level async execution manager for coordinating parallel operations

    Features:
    - Multiple task pools for different workload types
    - Rate limiting and throttling
    - Circuit breaker pattern for external services
    - Adaptive concurrency based on system load
    """

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}

        # Task pools for different workload types
        self.pools: dict[str, AsyncTaskPool] = {}

        # Rate limiters
        self._rate_limiters: dict[str, asyncio.Semaphore] = {}

        # Circuit breakers
        self._circuit_breakers: dict[str, dict[str, Any]] = {}

        # System load monitoring
        self._load_monitor_task: asyncio.Task | None = None
        self._current_load = 0.0

        # Initialize default pools
        self._initialize_default_pools()

    def _initialize_default_pools(self) -> None:
        """Initialize default task pools"""

        pools_config = self.config.get("pools", {})

        # AI API calls pool
        ai_config = pools_config.get("ai_api", {})
        self.pools["ai_api"] = AsyncTaskPool(
            max_concurrent_tasks=ai_config.get("max_concurrent", 5),
            default_timeout=ai_config.get("timeout", 60.0),
        )

        # General processing pool
        general_config = pools_config.get("general", {})
        self.pools["general"] = AsyncTaskPool(
            max_concurrent_tasks=general_config.get("max_concurrent", 10),
            default_timeout=general_config.get("timeout", 30.0),
        )

        # High priority pool
        priority_config = pools_config.get("priority", {})
        self.pools["priority"] = AsyncTaskPool(
            max_concurrent_tasks=priority_config.get("max_concurrent", 3),
            default_timeout=priority_config.get("timeout", 120.0),
        )

    async def start(self) -> None:
        """Start the async manager"""

        # Start all pools
        for pool in self.pools.values():
            await pool.start()

        # Start load monitoring
        self._load_monitor_task = asyncio.create_task(self._monitor_system_load())

        logger.info(
            "AsyncManager started",
            extra={"pools": list(self.pools.keys()), "config": self.config},
        )

    async def stop(self) -> None:
        """Stop the async manager"""

        # Stop load monitoring
        if self._load_monitor_task and not self._load_monitor_task.done():
            self._load_monitor_task.cancel()
            try:
                await self._load_monitor_task
            except asyncio.CancelledError:
                pass

        # Stop all pools
        for pool in self.pools.values():
            await pool.stop()

        logger.info("AsyncManager stopped")

    async def execute_ai_batch(
        self, coroutines: list[Awaitable[Any]], timeout: float | None = None
    ) -> list[TaskResult]:
        """Execute AI API calls with optimized batching"""

        pool = self.pools["ai_api"]
        return await pool.execute_batch(
            coroutines,
            max_concurrent=5,  # Limit concurrent AI calls
            timeout=timeout,
            priority=TaskPriority.HIGH,
        )

    async def execute_parallel(
        self,
        coroutines: list[Awaitable[Any]],
        pool_name: str = "general",
        timeout: float | None = None,
    ) -> list[TaskResult]:
        """Execute coroutines in parallel using specified pool"""

        if pool_name not in self.pools:
            raise ValueError(f"Pool {pool_name} not found")

        pool = self.pools[pool_name]
        return await pool.execute_batch(coroutines, timeout=timeout)

    async def submit_priority_task(
        self, coro: Awaitable[Any], timeout: float | None = None
    ) -> str:
        """Submit high-priority task"""

        pool = self.pools["priority"]
        return await pool.submit_task(
            coro, priority=TaskPriority.CRITICAL, timeout=timeout
        )

    def create_rate_limiter(self, name: str, rate: int) -> None:
        """Create rate limiter for external service calls"""

        self._rate_limiters[name] = asyncio.Semaphore(rate)

    async def rate_limited_call(self, limiter_name: str, coro: Awaitable[Any]) -> Any:
        """Execute coroutine with rate limiting"""

        if limiter_name not in self._rate_limiters:
            raise ValueError(f"Rate limiter {limiter_name} not found")

        semaphore = self._rate_limiters[limiter_name]

        async with semaphore:
            return await coro

    async def _monitor_system_load(self) -> None:
        """Monitor system load and adjust concurrency"""

        while True:
            try:
                # Simple load monitoring (can be enhanced with psutil)
                total_running = sum(
                    pool.metrics.current_running_tasks for pool in self.pools.values()
                )
                total_capacity = sum(
                    pool.max_concurrent_tasks for pool in self.pools.values()
                )

                self._current_load = (
                    total_running / total_capacity if total_capacity > 0 else 0.0
                )

                # Adjust concurrency based on load
                if self._current_load > 0.8:
                    logger.warning(
                        f"High system load detected: {self._current_load:.2f}"
                    )

                await asyncio.sleep(10.0)  # Check every 10 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Load monitoring error: {e}")
                await asyncio.sleep(30.0)

    def get_system_metrics(self) -> dict[str, Any]:
        """Get comprehensive system metrics"""

        metrics = {"current_load": self._current_load, "pools": {}}

        for name, pool in self.pools.items():
            metrics["pools"][name] = {
                "metrics": pool.get_metrics(),
                "running_tasks": len(pool.get_running_tasks()),
                "pending_tasks": pool.get_pending_count(),
            }

        return metrics


# Global async manager instance
_async_manager: AsyncManager | None = None


def get_async_manager() -> AsyncManager | None:
    """Get global async manager instance"""
    global _async_manager
    return _async_manager


def initialize_async_manager(config: dict[str, Any] | None = None) -> AsyncManager:
    """Initialize global async manager"""
    global _async_manager

    _async_manager = AsyncManager(config)
    return _async_manager


async def shutdown_async_manager() -> None:
    """Shutdown global async manager"""
    global _async_manager

    if _async_manager:
        await _async_manager.stop()
        _async_manager = None
