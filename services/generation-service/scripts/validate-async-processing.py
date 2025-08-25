#!/usr/bin/env python3
"""
Async processing validation script for Generation Service
"""

import asyncio
import inspect
import logging
import os
import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("async-validator")


class AsyncProcessingValidator:
    """Validate async processing components and error handling"""

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.validated_items = []

    async def validate_all(self):
        """Run all async processing validations"""
        logger.info("Starting async processing validation...")

        try:
            # Import validation
            await self.validate_imports()

            # Provider async compatibility
            await self.validate_provider_async_methods()

            # Timeout handling
            await self.validate_timeout_handling()

            # Error handling and retries
            await self.validate_error_handling()

            # Concurrency control
            await self.validate_concurrency_control()

            # Resource management
            await self.validate_resource_management()

            # Task pool functionality
            await self.validate_task_pools()

            # Rate limiting
            await self.validate_rate_limiting()

            return len(self.errors) == 0, self.errors, self.warnings

        except Exception as e:
            import traceback

            error_details = traceback.format_exc()
            self.errors.append(f"Validation failed with unexpected error: {e}")
            logger.error(f"Validation error details:\n{error_details}")
            return False, self.errors, self.warnings

    async def validate_imports(self):
        """Validate async processing imports"""
        logger.info("Validating async processing imports...")

        try:
            # Test base provider import
            from generation_service.ai.providers.base_provider import (
                BaseProvider,
                ProviderConnectionError,
                ProviderError,
                ProviderQuotaError,
                ProviderRateLimitError,
            )

            self.validated_items.append("base_provider_import")
            logger.info("✓ Base provider imports successful")

            # Test async manager import
            from generation_service.optimization.async_manager import (
                AsyncManager,
                AsyncTaskPool,
                TaskPriority,
                TaskResult,
                TaskStatus,
            )

            self.validated_items.append("async_manager_import")
            logger.info("✓ Async manager imports successful")

            # Test provider factory import
            from generation_service.ai.providers.provider_factory import ProviderFactory

            self.validated_items.append("provider_factory_import")
            logger.info("✓ Provider factory imports successful")

        except ImportError as e:
            self.errors.append(f"Failed to import async processing modules: {e}")

    async def validate_provider_async_methods(self):
        """Validate async methods in AI providers"""
        logger.info("Validating provider async methods...")

        try:
            from generation_service.ai.providers.base_provider import BaseProvider

            # Check abstract methods
            abstract_methods = ["generate", "generate_stream", "validate_connection"]

            missing_methods = []
            for method_name in abstract_methods:
                if not hasattr(BaseProvider, method_name):
                    missing_methods.append(method_name)

            if missing_methods:
                self.errors.append(
                    f"Missing abstract methods in BaseProvider: {missing_methods}"
                )
            else:
                self.validated_items.append("base_provider_abstract_methods")
                logger.info(f"✓ All {len(abstract_methods)} abstract methods present")

            # Check async compatibility
            for method_name in abstract_methods:
                if hasattr(BaseProvider, method_name):
                    method = getattr(BaseProvider, method_name)
                    if hasattr(method, "__annotations__"):
                        # Check if method is declared as async (abstract methods might not be)
                        pass

            # Test concrete provider implementations
            try:
                from generation_service.ai.providers.openai_provider import (
                    OpenAIProvider,
                )

                # Check if concrete methods are async
                async_methods = ["generate", "generate_stream", "validate_connection"]
                for method_name in async_methods:
                    if hasattr(OpenAIProvider, method_name):
                        method = getattr(OpenAIProvider, method_name)
                        # generate_stream is an async generator, others are coroutines
                        if method_name == "generate_stream":
                            if not inspect.isasyncgenfunction(method):
                                self.errors.append(
                                    f"OpenAI provider method {method_name} is not async generator"
                                )
                        else:
                            if not inspect.iscoroutinefunction(method):
                                self.errors.append(
                                    f"OpenAI provider method {method_name} is not async"
                                )

                self.validated_items.append("openai_provider_async_methods")
                logger.info("✓ OpenAI provider async methods validated")

            except ImportError:
                self.warnings.append(
                    "OpenAI provider not available for async validation"
                )

            try:
                from generation_service.ai.providers.anthropic_provider import (
                    AnthropicProvider,
                )

                # Check if concrete methods are async
                for method_name in async_methods:
                    if hasattr(AnthropicProvider, method_name):
                        method = getattr(AnthropicProvider, method_name)
                        # generate_stream is an async generator, others are coroutines
                        if method_name == "generate_stream":
                            if not inspect.isasyncgenfunction(method):
                                self.errors.append(
                                    f"Anthropic provider method {method_name} is not async generator"
                                )
                        else:
                            if not inspect.iscoroutinefunction(method):
                                self.errors.append(
                                    f"Anthropic provider method {method_name} is not async"
                                )

                self.validated_items.append("anthropic_provider_async_methods")
                logger.info("✓ Anthropic provider async methods validated")

            except ImportError:
                self.warnings.append(
                    "Anthropic provider not available for async validation"
                )

        except Exception as e:
            self.errors.append(f"Provider async method validation failed: {e}")

    async def validate_timeout_handling(self):
        """Validate timeout handling in async operations"""
        logger.info("Validating timeout handling...")

        try:
            from generation_service.optimization.async_manager import (
                AsyncTaskPool,
                TaskStatus,
            )

            # Test timeout functionality
            pool = AsyncTaskPool(max_concurrent_tasks=2, default_timeout=1.0)
            await pool.start()

            try:
                # Create a slow coroutine that should timeout
                async def slow_operation():
                    await asyncio.sleep(2.0)  # Longer than timeout
                    return "completed"

                # Submit task with timeout
                task_id = await pool.submit_task(slow_operation(), timeout=0.5)

                # Wait for result
                start_time = time.time()
                result = await pool.get_result(task_id, timeout=3.0)
                end_time = time.time()

                # Should have timed out
                if result.status != TaskStatus.TIMEOUT:
                    self.warnings.append(
                        f"Task didn't timeout as expected: {result.status}"
                    )
                else:
                    self.validated_items.append("task_timeout_handling")
                    logger.info("✓ Task timeout handling works correctly")

                # Execution should be fast (timeout occurred)
                execution_time = end_time - start_time
                if execution_time > 2.0:
                    self.warnings.append(
                        f"Timeout took too long: {execution_time:.2f}s"
                    )

            finally:
                await pool.stop()

            # Test asyncio timeout handling
            try:
                await asyncio.wait_for(asyncio.sleep(1.0), timeout=0.1)
                self.errors.append("asyncio.wait_for didn't timeout as expected")
            except asyncio.TimeoutError:
                self.validated_items.append("asyncio_timeout_handling")
                logger.info("✓ asyncio timeout handling works correctly")

        except Exception as e:
            self.errors.append(f"Timeout handling validation failed: {e}")

    async def validate_error_handling(self):
        """Validate error handling and retry logic"""
        logger.info("Validating error handling and retries...")

        try:
            from generation_service.ai.providers.base_provider import (
                ProviderConnectionError,
                ProviderError,
                ProviderQuotaError,
                ProviderRateLimitError,
            )

            # Test exception hierarchy
            test_errors = [
                ProviderConnectionError("Connection failed", "test_provider"),
                ProviderRateLimitError("Rate limited", "test_provider", retry_after=60),
                ProviderQuotaError("Quota exceeded", "test_provider"),
                ProviderError("Generic error", "test_provider", retryable=True),
            ]

            for error in test_errors:
                # Check that exceptions have required attributes
                if not hasattr(error, "provider"):
                    self.errors.append(
                        f"Exception {type(error).__name__} missing provider attribute"
                    )

                # Check retryable attribute
                if hasattr(error, "retryable"):
                    if isinstance(
                        error, (ProviderConnectionError, ProviderRateLimitError)
                    ):
                        if not error.retryable:
                            self.warnings.append(
                                f"{type(error).__name__} should be retryable"
                            )
                    elif isinstance(error, ProviderQuotaError):
                        if error.retryable:
                            self.warnings.append(
                                f"{type(error).__name__} should not be retryable"
                            )

            self.validated_items.append("provider_exception_hierarchy")
            logger.info("✓ Provider exception hierarchy validated")

            # Test retry logic simulation
            await self._test_retry_logic()

        except Exception as e:
            self.errors.append(f"Error handling validation failed: {e}")

    async def _test_retry_logic(self):
        """Test retry logic with simulated failures"""

        try:
            from generation_service.ai.providers.base_provider import (
                ProviderConnectionError,
                ProviderRateLimitError,
            )

            attempt_count = 0
            max_retries = 3

            async def failing_operation():
                nonlocal attempt_count
                attempt_count += 1

                if attempt_count <= 2:
                    # Fail first two attempts
                    if attempt_count == 1:
                        raise ProviderConnectionError(
                            "Connection failed", "test_provider"
                        )
                    else:
                        raise ProviderRateLimitError(
                            "Rate limited", "test_provider", retry_after=0.1
                        )
                else:
                    # Succeed on third attempt
                    return "success"

            # Simulate basic retry logic
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    result = await failing_operation()
                    if result == "success":
                        self.validated_items.append("retry_logic_simulation")
                        logger.info("✓ Retry logic simulation successful")
                        break
                except (ProviderConnectionError, ProviderRateLimitError) as e:
                    last_exception = e
                    if attempt < max_retries:
                        await asyncio.sleep(0.1)  # Small delay
                        continue
                    else:
                        # Should not reach here if retry logic works
                        self.errors.append("Retry logic failed - too many attempts")
                        break

        except Exception as e:
            self.errors.append(f"Retry logic simulation failed: {e}")

    async def validate_concurrency_control(self):
        """Validate concurrency control mechanisms"""
        logger.info("Validating concurrency control...")

        try:
            from generation_service.optimization.async_manager import (
                AsyncTaskPool,
                TaskStatus,
            )

            # Test concurrency limiting
            max_concurrent = 2
            pool = AsyncTaskPool(
                max_concurrent_tasks=max_concurrent, default_timeout=5.0
            )
            await pool.start()

            try:
                # Track concurrent executions
                concurrent_count = 0
                max_observed_concurrent = 0

                async def concurrent_task():
                    nonlocal concurrent_count, max_observed_concurrent

                    concurrent_count += 1
                    max_observed_concurrent = max(
                        max_observed_concurrent, concurrent_count
                    )

                    await asyncio.sleep(0.5)  # Hold for a bit

                    concurrent_count -= 1
                    return "task_completed"

                # Submit more tasks than the limit
                task_count = 5
                task_ids = []

                for i in range(task_count):
                    task_id = await pool.submit_task(concurrent_task())
                    task_ids.append(task_id)

                # Wait for all tasks to complete
                results = await pool.wait_for_tasks(task_ids, timeout=10.0)

                # Check that concurrency was limited
                if max_observed_concurrent > max_concurrent:
                    self.errors.append(
                        f"Concurrency limit exceeded: {max_observed_concurrent} > {max_concurrent}"
                    )
                else:
                    self.validated_items.append("concurrency_limiting")
                    logger.info(f"✓ Concurrency properly limited to {max_concurrent}")

                # Check that all tasks completed
                completed_count = sum(
                    1 for r in results if r.status == TaskStatus.COMPLETED
                )
                if completed_count != task_count:
                    self.warnings.append(
                        f"Not all tasks completed: {completed_count}/{task_count}"
                    )
                else:
                    self.validated_items.append("concurrent_task_completion")
                    logger.info(f"✓ All {task_count} concurrent tasks completed")

            finally:
                await pool.stop()

        except Exception as e:
            self.errors.append(f"Concurrency control validation failed: {e}")

    async def validate_resource_management(self):
        """Validate resource management and cleanup"""
        logger.info("Validating resource management...")

        try:
            from generation_service.optimization.async_manager import (
                AsyncTaskPool,
                TaskStatus,
            )

            # Test resource cleanup
            pool = AsyncTaskPool(max_concurrent_tasks=3, default_timeout=2.0)
            await pool.start()

            try:
                # Submit and cancel tasks to test cleanup
                async def simple_task():
                    await asyncio.sleep(0.1)
                    return "completed"

                task_ids = []

                # Submit several tasks
                for i in range(5):
                    task_id = await pool.submit_task(simple_task())
                    task_ids.append(task_id)

                # Cancel some tasks
                cancelled_count = 0
                for i in range(0, len(task_ids), 2):  # Cancel every other task
                    if await pool.cancel_task(task_ids[i]):
                        cancelled_count += 1

                # Wait for remaining tasks
                await asyncio.sleep(1.0)

                # Check that cancelled tasks are marked correctly
                cancelled_tasks = []
                for task_id in task_ids:
                    status = pool.get_task_status(task_id)
                    if status == TaskStatus.CANCELLED:
                        cancelled_tasks.append(task_id)

                if len(cancelled_tasks) != cancelled_count:
                    self.warnings.append(
                        f"Cancelled task count mismatch: {len(cancelled_tasks)} != {cancelled_count}"
                    )
                else:
                    self.validated_items.append("task_cancellation")
                    logger.info(
                        f"✓ Task cancellation works correctly ({cancelled_count} tasks)"
                    )

                # Test metrics collection
                metrics = pool.get_metrics()
                if hasattr(metrics, "total_tasks") and metrics.total_tasks >= len(
                    task_ids
                ):
                    self.validated_items.append("metrics_collection")
                    logger.info("✓ Metrics collection working")
                else:
                    self.warnings.append(
                        "Metrics collection may not be working correctly"
                    )

            finally:
                await pool.stop()

        except Exception as e:
            self.errors.append(f"Resource management validation failed: {e}")

    async def validate_task_pools(self):
        """Validate task pool functionality"""
        logger.info("Validating task pool functionality...")

        try:
            from generation_service.optimization.async_manager import (
                AsyncManager,
                TaskStatus,
            )

            # Test async manager with multiple pools
            manager = AsyncManager(
                {
                    "pools": {
                        "test_pool": {"max_concurrent": 2, "timeout": 5.0},
                        "priority_pool": {"max_concurrent": 1, "timeout": 10.0},
                    }
                }
            )

            await manager.start()

            try:
                # Test batch execution
                async def batch_task(task_id: int):
                    await asyncio.sleep(0.1)
                    return f"batch_result_{task_id}"

                batch_coroutines = [batch_task(i) for i in range(3)]
                results = await manager.execute_parallel(
                    batch_coroutines, pool_name="general"
                )

                # Check batch results
                completed_results = [
                    r for r in results if r.status == TaskStatus.COMPLETED
                ]
                if len(completed_results) != len(batch_coroutines):
                    self.warnings.append(
                        f"Batch execution incomplete: {len(completed_results)}/{len(batch_coroutines)}"
                    )
                else:
                    self.validated_items.append("batch_execution")
                    logger.info(
                        f"✓ Batch execution completed ({len(completed_results)} tasks)"
                    )

                # Test priority task submission
                async def priority_task():
                    await asyncio.sleep(0.1)
                    return "priority_completed"

                priority_task_id = await manager.submit_priority_task(priority_task())

                # Wait for priority task
                await asyncio.sleep(1.0)

                # Check priority task completion
                if "priority" in manager.pools:
                    priority_pool = manager.pools["priority"]
                    status = priority_pool.get_task_status(priority_task_id)
                    if status == TaskStatus.COMPLETED:
                        self.validated_items.append("priority_task_execution")
                        logger.info("✓ Priority task execution working")

                # Test system metrics
                metrics = manager.get_system_metrics()
                if isinstance(metrics, dict) and "pools" in metrics:
                    self.validated_items.append("system_metrics")
                    logger.info("✓ System metrics collection working")

            finally:
                await manager.stop()

        except Exception as e:
            self.errors.append(f"Task pool validation failed: {e}")

    async def validate_rate_limiting(self):
        """Validate rate limiting functionality"""
        logger.info("Validating rate limiting...")

        try:
            from generation_service.optimization.async_manager import AsyncManager

            manager = AsyncManager()
            await manager.start()

            try:
                # Create rate limiter
                rate_limit = 2
                manager.create_rate_limiter("test_service", rate_limit)

                # Test rate limiting
                call_times = []

                async def rate_limited_operation():
                    start_time = time.time()

                    async def actual_operation():
                        await asyncio.sleep(0.1)
                        return "rate_limited_result"

                    result = await manager.rate_limited_call(
                        "test_service", actual_operation()
                    )
                    end_time = time.time()
                    call_times.append((start_time, end_time))
                    return result

                # Make multiple concurrent calls
                tasks = [rate_limited_operation() for _ in range(4)]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Check that rate limiting worked
                successful_results = [r for r in results if isinstance(r, str)]
                if len(successful_results) == 4:
                    self.validated_items.append("rate_limiting_functionality")
                    logger.info("✓ Rate limiting allows correct number of calls")
                else:
                    self.warnings.append(
                        f"Rate limiting may not be working: {len(successful_results)} results"
                    )

                # Analyze timing to verify rate limiting
                if len(call_times) >= 2:
                    # Check that calls were delayed due to rate limiting
                    start_times = [t[0] for t in call_times]
                    max_time_diff = max(start_times) - min(start_times)
                    if max_time_diff > 0.05:  # Some delay should occur
                        self.validated_items.append("rate_limiting_timing")
                        logger.info("✓ Rate limiting introduces appropriate delays")

            finally:
                await manager.stop()

        except Exception as e:
            self.errors.append(f"Rate limiting validation failed: {e}")


def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_results(results: list, result_type: str, icon: str):
    """Print validation results"""
    if results:
        print(f"\n{icon} {result_type.upper()} ({len(results)}):")
        for i, result in enumerate(results, 1):
            print(f"  {i}. {result}")
    else:
        print(f"\n✅ No {result_type.lower()}")


async def main():
    """Main validation routine"""
    print("🔍 Async Processing Validation")
    print(f"Python: {sys.version}")
    print(f"Working Directory: {os.getcwd()}")

    print_section("Async Processing Validation")

    validator = AsyncProcessingValidator()
    is_valid, errors, warnings = await validator.validate_all()

    print(f"\nValidated {len(validator.validated_items)} async processing components")

    print_results(errors, "errors", "❌")
    print_results(warnings, "warnings", "⚠️")

    print_section("Validation Summary")

    if is_valid:
        print("🎉 Async processing validation PASSED")
        print("✅ Async processing, timeouts, and error handling are working correctly")
        exit_code = 0
    else:
        print("❌ Async processing validation FAILED")
        print("🚨 Critical async processing issues must be resolved")
        exit_code = 1

    # Summary stats
    print("\nValidation Results:")
    print(f"  Async components validated: {len(validator.validated_items)}")
    print(f"  Errors found: {len(errors)}")
    print(f"  Warnings: {len(warnings)}")

    if errors:
        print(f"\n🚨 {len(errors)} critical async processing issues found")

    if warnings:
        print(f"⚠️  {len(warnings)} async processing warnings - review for optimization")

    # List validated components
    if validator.validated_items:
        print("\n✅ Successfully validated components:")
        for item in validator.validated_items:
            print(f"  • {item.replace('_', ' ').title()}")

    return exit_code


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️  Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Validation failed with unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
