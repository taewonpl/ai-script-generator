"""
Connection pooling and resource management for external services
"""

import asyncio
import time
import weakref
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

try:
    import aiohttp

    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    aiohttp = None

# Import Core Module components
try:
    from ai_script_core import (
        get_service_logger,
        utc_now,
    )

    CORE_AVAILABLE = True
    logger = get_service_logger("generation-service.connection_pool")
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


class ConnectionStatus(str, Enum):
    """Connection status states"""

    IDLE = "idle"
    ACTIVE = "active"
    FAILED = "failed"
    CLOSED = "closed"


@dataclass
class ConnectionMetrics:
    """Metrics for connection usage"""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_response_time: float = 0.0
    average_response_time: float = 0.0
    last_used: datetime | None = None
    created_at: datetime | None = None


@dataclass
class PoolMetrics:
    """Metrics for connection pool"""

    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    failed_connections: int = 0
    total_requests: int = 0
    pool_hits: int = 0
    pool_misses: int = 0
    connection_reuse_ratio: float = 0.0


class Connection:
    """
    Wrapper for individual connections with lifecycle management
    """

    def __init__(self, connection_id: str, connection: Any, pool: "ConnectionPool"):
        self.connection_id = connection_id
        self.connection = connection
        self.pool = weakref.ref(pool)
        self.status = ConnectionStatus.IDLE
        self.metrics = ConnectionMetrics(
            created_at=utc_now() if CORE_AVAILABLE else datetime.now()
        )

        # Connection configuration
        self.max_requests = 1000  # Max requests per connection
        self.max_lifetime = timedelta(hours=1)  # Max connection lifetime
        self.idle_timeout = timedelta(minutes=5)  # Idle timeout

    async def execute_request(
        self, request_func: Callable[..., Awaitable[Any]], *args, **kwargs
    ) -> Any:
        """Execute request using this connection"""

        if self.status != ConnectionStatus.IDLE:
            raise RuntimeError(f"Connection {self.connection_id} is not available")

        self.status = ConnectionStatus.ACTIVE
        start_time = time.time()

        try:
            # Execute request
            result = await request_func(self.connection, *args, **kwargs)

            # Update metrics
            response_time = time.time() - start_time
            self.metrics.successful_requests += 1
            self.metrics.total_requests += 1
            self.metrics.total_response_time += response_time
            self.metrics.average_response_time = (
                self.metrics.total_response_time / self.metrics.total_requests
            )
            self.metrics.last_used = utc_now() if CORE_AVAILABLE else datetime.now()

            return result

        except Exception as e:
            self.metrics.failed_requests += 1
            self.metrics.total_requests += 1
            self.status = ConnectionStatus.FAILED
            raise e

        finally:
            if self.status != ConnectionStatus.FAILED:
                self.status = ConnectionStatus.IDLE

    def should_close(self) -> bool:
        """Check if connection should be closed"""

        now = utc_now() if CORE_AVAILABLE else datetime.now()

        # Check max requests
        if self.metrics.total_requests >= self.max_requests:
            return True

        # Check max lifetime
        if (
            self.metrics.created_at
            and (now - self.metrics.created_at) > self.max_lifetime
        ):
            return True

        # Check idle timeout
        if (
            self.metrics.last_used
            and (now - self.metrics.last_used) > self.idle_timeout
        ):
            return True

        # Check if failed
        if self.status == ConnectionStatus.FAILED:
            return True

        return False

    async def close(self) -> None:
        """Close the connection"""

        try:
            if hasattr(self.connection, "close"):
                await self.connection.close()
            elif hasattr(self.connection, "__aexit__"):
                await self.connection.__aexit__(None, None, None)
        except Exception as e:
            logger.warning(f"Error closing connection {self.connection_id}: {e}")

        self.status = ConnectionStatus.CLOSED


class ConnectionPool:
    """
    Generic connection pool for managing reusable connections

    Features:
    - Connection lifecycle management
    - Automatic connection recycling
    - Health monitoring
    - Load balancing
    - Metrics collection
    """

    def __init__(
        self,
        name: str,
        connection_factory: Callable[[], Awaitable[Any]],
        min_connections: int = 2,
        max_connections: int = 10,
        connection_timeout: float = 30.0,
        health_check_interval: float = 60.0,
    ):
        self.name = name
        self.connection_factory = connection_factory
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        self.health_check_interval = health_check_interval

        # Connection management
        self._connections: dict[str, Connection] = {}
        self._idle_connections: asyncio.Queue = asyncio.Queue()
        self._connection_semaphore = asyncio.Semaphore(max_connections)
        self._connection_counter = 0

        # Pool state
        self._initialized = False
        self._health_check_task: asyncio.Task | None = None
        self._shutdown_event = asyncio.Event()

        # Metrics
        self.metrics = PoolMetrics()

        if CORE_AVAILABLE:
            logger.info(
                f"ConnectionPool '{name}' created",
                extra={
                    "min_connections": min_connections,
                    "max_connections": max_connections,
                },
            )

    async def initialize(self) -> None:
        """Initialize the connection pool"""

        if self._initialized:
            return

        # Create minimum connections
        for _ in range(self.min_connections):
            try:
                await self._create_connection()
            except Exception as e:
                logger.error(f"Failed to create initial connection: {e}")

        # Start health check task
        self._health_check_task = asyncio.create_task(self._health_check_worker())

        self._initialized = True
        logger.info(
            f"ConnectionPool '{self.name}' initialized with {len(self._connections)} connections"
        )

    async def shutdown(self) -> None:
        """Shutdown the connection pool"""

        self._shutdown_event.set()

        # Stop health check
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        # Close all connections
        for connection in list(self._connections.values()):
            await connection.close()

        self._connections.clear()
        self._initialized = False

        logger.info(f"ConnectionPool '{self.name}' shutdown")

    async def acquire_connection(self, timeout: float | None = None) -> Connection:
        """Acquire a connection from the pool"""

        if not self._initialized:
            await self.initialize()

        acquire_timeout = timeout or self.connection_timeout

        try:
            # Wait for available connection slot
            await asyncio.wait_for(
                self._connection_semaphore.acquire(), timeout=acquire_timeout
            )

            # Try to get idle connection
            connection = await self._get_idle_connection()

            if connection:
                self.metrics.pool_hits += 1
                return connection

            # Create new connection if needed
            if len(self._connections) < self.max_connections:
                connection = await self._create_connection()
                self.metrics.pool_misses += 1
                return connection

            # Wait for connection to become available
            connection = await asyncio.wait_for(
                self._idle_connections.get(), timeout=acquire_timeout
            )

            self.metrics.pool_hits += 1
            return connection

        except asyncio.TimeoutError:
            self._connection_semaphore.release()
            raise asyncio.TimeoutError(
                f"Timeout acquiring connection from pool '{self.name}'"
            )
        except Exception as e:
            self._connection_semaphore.release()
            raise e

    async def release_connection(self, connection: Connection) -> None:
        """Release a connection back to the pool"""

        try:
            # Check if connection should be closed
            if connection.should_close():
                await self._close_connection(connection)
            else:
                # Return to idle pool
                connection.status = ConnectionStatus.IDLE
                await self._idle_connections.put(connection)

        finally:
            self._connection_semaphore.release()

    async def execute_with_connection(
        self,
        request_func: Callable[..., Awaitable[Any]],
        *args,
        timeout: float | None = None,
        **kwargs,
    ) -> Any:
        """Execute request using a pooled connection"""

        connection = await self.acquire_connection(timeout)

        try:
            result = await connection.execute_request(request_func, *args, **kwargs)
            self.metrics.total_requests += 1
            return result

        finally:
            await self.release_connection(connection)

    async def _create_connection(self) -> Connection:
        """Create a new connection"""

        try:
            # Create connection using factory
            raw_connection = await self.connection_factory()

            # Wrap in Connection object
            self._connection_counter += 1
            connection_id = f"{self.name}_{self._connection_counter}"

            connection = Connection(connection_id, raw_connection, self)
            self._connections[connection_id] = connection

            self.metrics.total_connections += 1

            logger.debug(f"Created connection {connection_id}")
            return connection

        except Exception as e:
            logger.error(f"Failed to create connection: {e}")
            raise

    async def _get_idle_connection(self) -> Connection | None:
        """Get an idle connection if available"""

        try:
            connection = self._idle_connections.get_nowait()

            # Verify connection is still valid
            if connection.should_close():
                await self._close_connection(connection)
                return None

            return connection

        except asyncio.QueueEmpty:
            return None

    async def _close_connection(self, connection: Connection):
        """Close and remove a connection"""

        try:
            await connection.close()
            self._connections.pop(connection.connection_id, None)
            self.metrics.total_connections -= 1

            logger.debug(f"Closed connection {connection.connection_id}")

        except Exception as e:
            logger.error(f"Error closing connection {connection.connection_id}: {e}")

    async def _health_check_worker(self):
        """Background worker for connection health checks"""

        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(self.health_check_interval)

                # Check all connections
                for connection in list(self._connections.values()):
                    if connection.should_close():
                        await self._close_connection(connection)

                # Ensure minimum connections
                current_count = len(self._connections)
                if current_count < self.min_connections:
                    needed = self.min_connections - current_count
                    for _ in range(needed):
                        try:
                            await self._create_connection()
                        except Exception as e:
                            logger.error(
                                f"Failed to create connection during health check: {e}"
                            )
                            break

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")

    def get_metrics(self) -> dict[str, Any]:
        """Get pool metrics"""

        active_count = sum(
            1 for c in self._connections.values() if c.status == ConnectionStatus.ACTIVE
        )
        idle_count = sum(
            1 for c in self._connections.values() if c.status == ConnectionStatus.IDLE
        )
        failed_count = sum(
            1 for c in self._connections.values() if c.status == ConnectionStatus.FAILED
        )

        self.metrics.active_connections = active_count
        self.metrics.idle_connections = idle_count
        self.metrics.failed_connections = failed_count
        self.metrics.total_connections = len(self._connections)

        # Calculate reuse ratio
        total_operations = self.metrics.pool_hits + self.metrics.pool_misses
        if total_operations > 0:
            self.metrics.connection_reuse_ratio = (
                self.metrics.pool_hits / total_operations
            )

        return {
            "name": self.name,
            "total_connections": self.metrics.total_connections,
            "active_connections": self.metrics.active_connections,
            "idle_connections": self.metrics.idle_connections,
            "failed_connections": self.metrics.failed_connections,
            "total_requests": self.metrics.total_requests,
            "pool_hits": self.metrics.pool_hits,
            "pool_misses": self.metrics.pool_misses,
            "connection_reuse_ratio": self.metrics.connection_reuse_ratio,
            "queue_size": self._idle_connections.qsize(),
        }


class AIProviderPool:
    """
    Specialized connection pool for AI providers with rate limiting

    Features:
    - Provider-specific connection pools
    - Rate limiting per provider
    - Automatic retry and circuit breaker
    - Load balancing across providers
    """

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.pools: dict[str, ConnectionPool] = {}
        self.rate_limiters: dict[str, asyncio.Semaphore] = {}

        # Circuit breaker state
        self.circuit_breakers: dict[str, dict[str, Any]] = {}

        # Initialize pools for each provider
        self._initialize_provider_pools()

    def _initialize_provider_pools(self) -> None:
        """Initialize connection pools for AI providers"""

        providers_config = self.config.get("providers", {})

        for provider_name, provider_config in providers_config.items():
            # Create connection factory
            connection_factory = self._create_connection_factory(
                provider_name, provider_config
            )

            # Create pool
            pool = ConnectionPool(
                name=f"ai_provider_{provider_name}",
                connection_factory=connection_factory,
                min_connections=provider_config.get("min_connections", 1),
                max_connections=provider_config.get("max_connections", 5),
                connection_timeout=provider_config.get("timeout", 30.0),
            )

            self.pools[provider_name] = pool

            # Create rate limiter
            rate_limit = provider_config.get("rate_limit", 10)
            self.rate_limiters[provider_name] = asyncio.Semaphore(rate_limit)

            # Initialize circuit breaker
            self.circuit_breakers[provider_name] = {
                "state": "closed",  # closed, open, half_open
                "failure_count": 0,
                "last_failure": None,
                "failure_threshold": provider_config.get("failure_threshold", 5),
                "recovery_timeout": provider_config.get("recovery_timeout", 60.0),
            }

    def _create_connection_factory(self, provider_name: str, config: dict[str, Any]):
        """Create connection factory for specific provider"""

        async def factory():
            if AIOHTTP_AVAILABLE:
                # Create HTTP session for API calls
                timeout = aiohttp.ClientTimeout(total=config.get("timeout", 30.0))
                connector = aiohttp.TCPConnector(
                    limit=config.get("max_connections", 5),
                    limit_per_host=config.get("max_connections_per_host", 2),
                )

                session = aiohttp.ClientSession(
                    timeout=timeout,
                    connector=connector,
                    headers=config.get("headers", {}),
                )

                return session
            else:
                # Fallback to simple connection object
                return {"provider": provider_name, "config": config}

        return factory

    async def initialize(self) -> None:
        """Initialize all provider pools"""

        for pool in self.pools.values():
            await pool.initialize()

        logger.info(
            "AIProviderPool initialized", extra={"providers": list(self.pools.keys())}
        )

    async def shutdown(self) -> None:
        """Shutdown all provider pools"""

        for pool in self.pools.values():
            await pool.shutdown()

        logger.info("AIProviderPool shutdown")

    async def execute_ai_request(
        self,
        provider_name: str,
        request_func: Callable[..., Awaitable[Any]],
        *args,
        timeout: float | None = None,
        **kwargs,
    ) -> Any:
        """Execute AI request with connection pooling and rate limiting"""

        if provider_name not in self.pools:
            raise ValueError(f"Provider {provider_name} not configured")

        # Check circuit breaker
        if not self._is_circuit_closed(provider_name):
            raise RuntimeError(f"Circuit breaker open for provider {provider_name}")

        pool = self.pools[provider_name]
        rate_limiter = self.rate_limiters[provider_name]

        # Apply rate limiting
        async with rate_limiter:
            try:
                result = await pool.execute_with_connection(
                    request_func, *args, timeout=timeout, **kwargs
                )

                # Reset circuit breaker on success
                self._reset_circuit_breaker(provider_name)
                return result

            except Exception as e:
                # Update circuit breaker on failure
                self._record_failure(provider_name)
                raise e

    def _is_circuit_closed(self, provider_name: str) -> bool:
        """Check if circuit breaker is closed (allowing requests)"""

        cb = self.circuit_breakers[provider_name]

        if cb["state"] == "closed":
            return True
        elif cb["state"] == "open":
            # Check if recovery timeout has passed
            if cb["last_failure"]:
                now = utc_now() if CORE_AVAILABLE else datetime.now()
                time_since_failure = (now - cb["last_failure"]).total_seconds()

                if time_since_failure > cb["recovery_timeout"]:
                    cb["state"] = "half_open"
                    return True
            return False
        elif cb["state"] == "half_open":
            return True

        return False

    def _record_failure(self, provider_name: str) -> None:
        """Record failure for circuit breaker"""

        cb = self.circuit_breakers[provider_name]
        cb["failure_count"] += 1
        cb["last_failure"] = utc_now() if CORE_AVAILABLE else datetime.now()

        if cb["failure_count"] >= cb["failure_threshold"]:
            cb["state"] = "open"
            logger.warning(f"Circuit breaker opened for provider {provider_name}")

    def _reset_circuit_breaker(self, provider_name: str) -> None:
        """Reset circuit breaker on successful request"""

        cb = self.circuit_breakers[provider_name]
        cb["failure_count"] = 0
        cb["state"] = "closed"

    def get_provider_metrics(self) -> dict[str, Any]:
        """Get metrics for all providers"""

        metrics = {}

        for provider_name, pool in self.pools.items():
            pool_metrics = pool.get_metrics()
            cb_state = self.circuit_breakers[provider_name]

            metrics[provider_name] = {
                "pool_metrics": pool_metrics,
                "circuit_breaker": {
                    "state": cb_state["state"],
                    "failure_count": cb_state["failure_count"],
                    "last_failure": (
                        cb_state["last_failure"].isoformat()
                        if cb_state["last_failure"]
                        else None
                    ),
                },
                "rate_limit_available": self.rate_limiters[provider_name]._value,
            }

        return metrics


# Global instances
_ai_provider_pool: AIProviderPool | None = None


def get_ai_provider_pool() -> AIProviderPool | None:
    """Get global AI provider pool"""
    global _ai_provider_pool
    return _ai_provider_pool


def initialize_ai_provider_pool(config: dict[str, Any]) -> AIProviderPool:
    """Initialize global AI provider pool"""
    global _ai_provider_pool

    _ai_provider_pool = AIProviderPool(config)
    return _ai_provider_pool


async def shutdown_ai_provider_pool() -> None:
    """Shutdown global AI provider pool"""
    global _ai_provider_pool

    if _ai_provider_pool:
        await _ai_provider_pool.shutdown()
        _ai_provider_pool = None
