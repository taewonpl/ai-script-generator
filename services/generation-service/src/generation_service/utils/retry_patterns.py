"""
Common retry and timeout patterns for robust operations
"""

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryStrategy(str, Enum):
    """Available retry strategies"""

    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    EXPONENTIAL_JITTER = "exponential_jitter"


@dataclass
class RetryConfig:
    """Configuration for retry operations"""

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    backoff_multiplier: float = 2.0
    jitter: bool = True
    exceptions: tuple[type[Exception], ...] = (Exception,)
    timeout: float | None = None


class RetryError(Exception):
    """Exception raised when all retry attempts are exhausted"""

    def __init__(self, message: str, attempts: int, last_exception: Exception):
        super().__init__(message)
        self.attempts = attempts
        self.last_exception = last_exception


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """Calculate delay for retry attempt based on strategy"""
    if config.strategy == RetryStrategy.FIXED:
        delay = config.base_delay
    elif config.strategy == RetryStrategy.LINEAR:
        delay = config.base_delay * attempt
    elif config.strategy == RetryStrategy.EXPONENTIAL:
        delay = config.base_delay * (config.backoff_multiplier ** (attempt - 1))
    elif config.strategy == RetryStrategy.EXPONENTIAL_JITTER:
        base_delay = config.base_delay * (config.backoff_multiplier ** (attempt - 1))
        # Add random jitter (±25%)
        import random

        jitter_factor = 0.75 + (random.random() * 0.5)  # 0.75 to 1.25
        delay = base_delay * jitter_factor
    else:
        delay = config.base_delay

    # Apply max delay limit
    return min(delay, config.max_delay)


async def async_retry(
    func: Callable[..., Any], config: RetryConfig, *args: Any, **kwargs: Any
) -> Any:
    """Execute async function with retry logic"""

    last_exception = None
    start_time = time.time()

    for attempt in range(1, config.max_attempts + 1):
        try:
            # Check timeout
            if config.timeout and (time.time() - start_time) >= config.timeout:
                raise TimeoutError(f"Operation timed out after {config.timeout}s")

            # Execute function
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            # Success - log if retries were needed
            if attempt > 1:
                elapsed = time.time() - start_time
                logger.info(
                    f"Function {func.__name__} succeeded on attempt {attempt}/{config.max_attempts} "
                    f"after {elapsed:.2f}s"
                )

            return result

        except config.exceptions as e:
            last_exception = e
            elapsed = time.time() - start_time

            logger.warning(
                f"Function {func.__name__} failed on attempt {attempt}/{config.max_attempts}: {e} "
                f"(elapsed: {elapsed:.2f}s)"
            )

            # Don't wait after the last attempt
            if attempt < config.max_attempts:
                delay = calculate_delay(attempt, config)

                # Check if delay would exceed timeout
                if config.timeout and (elapsed + delay) >= config.timeout:
                    remaining = config.timeout - elapsed
                    if remaining > 0:
                        logger.info(
                            f"Reducing delay to {remaining:.2f}s due to timeout"
                        )
                        await asyncio.sleep(remaining)
                    break
                else:
                    logger.info(f"Retrying in {delay:.2f}s...")
                    await asyncio.sleep(delay)

        except Exception as e:
            # Non-retryable exception
            logger.error(
                f"Function {func.__name__} failed with non-retryable error: {e}"
            )
            raise

    # All attempts exhausted
    total_elapsed = time.time() - start_time
    error_msg = (
        f"Function {func.__name__} failed after {config.max_attempts} attempts "
        f"over {total_elapsed:.2f}s. Last error: {last_exception}"
    )
    logger.error(error_msg)
    raise RetryError(error_msg, config.max_attempts, last_exception)


def sync_retry(
    func: Callable[..., Any], config: RetryConfig, *args: Any, **kwargs: Any
) -> Any:
    """Execute sync function with retry logic"""

    last_exception = None
    start_time = time.time()

    for attempt in range(1, config.max_attempts + 1):
        try:
            # Check timeout
            if config.timeout and (time.time() - start_time) >= config.timeout:
                raise TimeoutError(f"Operation timed out after {config.timeout}s")

            # Execute function
            result = func(*args, **kwargs)

            # Success - log if retries were needed
            if attempt > 1:
                elapsed = time.time() - start_time
                logger.info(
                    f"Function {func.__name__} succeeded on attempt {attempt}/{config.max_attempts} "
                    f"after {elapsed:.2f}s"
                )

            return result

        except config.exceptions as e:
            last_exception = e
            elapsed = time.time() - start_time

            logger.warning(
                f"Function {func.__name__} failed on attempt {attempt}/{config.max_attempts}: {e} "
                f"(elapsed: {elapsed:.2f}s)"
            )

            # Don't wait after the last attempt
            if attempt < config.max_attempts:
                delay = calculate_delay(attempt, config)

                # Check if delay would exceed timeout
                if config.timeout and (elapsed + delay) >= config.timeout:
                    remaining = config.timeout - elapsed
                    if remaining > 0:
                        logger.info(
                            f"Reducing delay to {remaining:.2f}s due to timeout"
                        )
                        time.sleep(remaining)
                    break
                else:
                    logger.info(f"Retrying in {delay:.2f}s...")
                    time.sleep(delay)

        except Exception as e:
            # Non-retryable exception
            logger.error(
                f"Function {func.__name__} failed with non-retryable error: {e}"
            )
            raise

    # All attempts exhausted
    total_elapsed = time.time() - start_time
    error_msg = (
        f"Function {func.__name__} failed after {config.max_attempts} attempts "
        f"over {total_elapsed:.2f}s. Last error: {last_exception}"
    )
    logger.error(error_msg)
    raise RetryError(error_msg, config.max_attempts, last_exception)


def retry_decorator(
    config: RetryConfig,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for adding retry logic to functions"""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            return await async_retry(func, config, *args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            return sync_retry(func, config, *args, **kwargs)

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# Predefined retry configurations for common use cases
class RetryConfigs:
    """Predefined retry configurations for common scenarios"""

    # API calls
    API_CALL = RetryConfig(
        max_attempts=3,
        base_delay=1.0,
        max_delay=30.0,
        strategy=RetryStrategy.EXPONENTIAL_JITTER,
        backoff_multiplier=2.0,
        exceptions=(
            ConnectionError,
            TimeoutError,
            OSError,  # Network errors
        ),
        timeout=60.0,
    )

    # Database operations
    DATABASE = RetryConfig(
        max_attempts=5,
        base_delay=0.5,
        max_delay=10.0,
        strategy=RetryStrategy.EXPONENTIAL,
        backoff_multiplier=1.5,
        exceptions=(
            ConnectionError,
            TimeoutError,
        ),
        timeout=30.0,
    )

    # File operations
    FILE_IO = RetryConfig(
        max_attempts=3,
        base_delay=0.1,
        max_delay=5.0,
        strategy=RetryStrategy.LINEAR,
        exceptions=(
            OSError,
            IOError,
            PermissionError,
        ),
        timeout=15.0,
    )

    # AI Provider calls (more aggressive retry)
    AI_PROVIDER = RetryConfig(
        max_attempts=5,
        base_delay=2.0,
        max_delay=60.0,
        strategy=RetryStrategy.EXPONENTIAL_JITTER,
        backoff_multiplier=2.0,
        exceptions=(
            ConnectionError,
            TimeoutError,
            OSError,
        ),
        timeout=300.0,  # 5 minutes for AI calls
    )

    # Quick operations
    QUICK = RetryConfig(
        max_attempts=2,
        base_delay=0.1,
        max_delay=1.0,
        strategy=RetryStrategy.FIXED,
        timeout=5.0,
    )

    # Heavy operations
    HEAVY = RetryConfig(
        max_attempts=3,
        base_delay=5.0,
        max_delay=120.0,
        strategy=RetryStrategy.EXPONENTIAL,
        backoff_multiplier=3.0,
        timeout=600.0,  # 10 minutes
    )


# Convenience decorators
retry_api_call = retry_decorator(RetryConfigs.API_CALL)
retry_database = retry_decorator(RetryConfigs.DATABASE)
retry_file_io = retry_decorator(RetryConfigs.FILE_IO)
retry_ai_provider = retry_decorator(RetryConfigs.AI_PROVIDER)
retry_quick = retry_decorator(RetryConfigs.QUICK)
retry_heavy = retry_decorator(RetryConfigs.HEAVY)


class TimeoutContext:
    """Context manager for operation timeouts"""

    def __init__(self, timeout: float, operation_name: str = "operation"):
        self.timeout = timeout
        self.operation_name = operation_name
        self.start_time: float | None = None

    def __enter__(self) -> "TimeoutContext":
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.start_time:
            elapsed = time.time() - self.start_time
            if elapsed > self.timeout:
                logger.warning(
                    f"{self.operation_name} took {elapsed:.2f}s "
                    f"(exceeded timeout of {self.timeout}s)"
                )

    def check_timeout(self) -> None:
        """Check if timeout has been exceeded"""
        if self.start_time:
            elapsed = time.time() - self.start_time
            if elapsed >= self.timeout:
                raise TimeoutError(
                    f"{self.operation_name} timed out after {elapsed:.2f}s "
                    f"(limit: {self.timeout}s)"
                )

    def remaining_time(self) -> float:
        """Get remaining time before timeout"""
        if self.start_time:
            elapsed = time.time() - self.start_time
            return max(0, self.timeout - elapsed)
        return self.timeout


async def with_timeout(
    coro: Any, timeout: float, operation_name: str = "operation"
) -> Any:
    """Execute coroutine with timeout"""
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        logger.error(f"{operation_name} timed out after {timeout}s")
        raise TimeoutError(f"{operation_name} timed out after {timeout}s")


# Circuit breaker pattern for failing services
class CircuitBreakerState(str, Enum):
    """Circuit breaker states"""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""

    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    expected_exception: type = Exception


class CircuitBreaker:
    """Circuit breaker for preventing cascading failures"""

    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time: float | None = None
        self.success_count = 0

    async def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute function through circuit breaker"""

        if self.state == CircuitBreakerState.OPEN:
            # Check if we should transition to half-open
            if (
                self.last_failure_time
                and time.time() - self.last_failure_time >= self.config.recovery_timeout
            ):
                self.state = CircuitBreakerState.HALF_OPEN
                logger.info("Circuit breaker transitioning to HALF_OPEN")
            else:
                raise Exception("Circuit breaker is OPEN - service unavailable")

        try:
            # Execute function
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            # Success - handle state transitions
            if self.state == CircuitBreakerState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= 3:  # Require 3 successes to close
                    self.state = CircuitBreakerState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0
                    logger.info("Circuit breaker transitioning to CLOSED")

            return result

        except self.config.expected_exception:
            # Handle failure
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.state == CircuitBreakerState.HALF_OPEN:
                # Failed during testing - back to open
                self.state = CircuitBreakerState.OPEN
                self.success_count = 0
                logger.warning("Circuit breaker transitioning back to OPEN")
            elif (
                self.state == CircuitBreakerState.CLOSED
                and self.failure_count >= self.config.failure_threshold
            ):
                # Too many failures - open circuit
                self.state = CircuitBreakerState.OPEN
                logger.error(
                    f"Circuit breaker transitioning to OPEN after "
                    f"{self.failure_count} failures"
                )

            raise
