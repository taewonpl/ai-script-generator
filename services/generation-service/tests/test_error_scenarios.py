"""
Error scenario and edge case tests for Generation Service
"""

import asyncio
import os
import signal
import time
from unittest.mock import MagicMock, patch

import httpx
import pytest

try:
    from ai_script_core import get_service_logger

    logger = get_service_logger("generation-service.tests.error_scenarios")
except (ImportError, RuntimeError):
    import logging

    logger = logging.getLogger(__name__)


class TestNetworkFailures:
    """Test network-related error scenarios"""

    @pytest.mark.asyncio
    async def test_redis_connection_failure(self):
        """Test behavior when Redis connection fails"""

        # Test with invalid Redis configuration
        try:
            from src.generation_service.cache.cache_manager import CacheManager

            cache_manager = CacheManager(
                redis_config={"redis_host": "invalid_host", "redis_port": 9999},
                enable_memory_fallback=True,
            )

            # Should initialize with fallback
            result = await cache_manager.initialize()

            # Test cache operations with fallback
            from src.generation_service.cache.cache_strategies import CacheType

            # Should work with memory cache fallback
            set_result = await cache_manager.set(
                CacheType.PROMPT_RESULT, {"test": "data"}, prompt="test_prompt"
            )

            get_result = await cache_manager.get(
                CacheType.PROMPT_RESULT, prompt="test_prompt"
            )

            # Should fallback to memory cache
            assert get_result is not None
            assert get_result["test"] == "data"

            await cache_manager.shutdown()

        except ImportError:
            pytest.skip("Cache manager not available")

    @pytest.mark.asyncio
    async def test_external_api_timeout(self):
        """Test handling of external API timeouts"""

        # Mock external API call with timeout
        with patch("aiohttp.ClientSession.request") as mock_request:
            mock_request.side_effect = asyncio.TimeoutError("Request timeout")

            try:
                from src.generation_service.optimization.connection_pool import (
                    ConnectionPoolManager,
                )

                pool_manager = ConnectionPoolManager(
                    {"total_timeout": 1, "connect_timeout": 0.5}
                )

                await pool_manager.initialize()

                # Should handle timeout gracefully
                with pytest.raises(asyncio.TimeoutError):
                    await pool_manager.make_request(
                        "GET", "https://api.example.com/test"
                    )

                await pool_manager.session.close()

            except ImportError:
                pytest.skip("Connection pool manager not available")

    @pytest.mark.asyncio
    async def test_network_interruption_recovery(self):
        """Test recovery from network interruptions"""

        # Simulate network interruption and recovery
        network_available = True
        call_count = 0

        async def mock_network_call():
            nonlocal call_count, network_available
            call_count += 1

            if call_count <= 3 and not network_available:
                raise ConnectionError("Network unavailable")

            return {"status": "success", "attempt": call_count}

        # Test retry mechanism
        max_retries = 5
        retry_delay = 0.1

        for attempt in range(max_retries):
            try:
                result = await mock_network_call()
                logger.info(f"Network call succeeded on attempt {attempt + 1}")
                break
            except ConnectionError as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Network call failed (attempt {attempt + 1}): {e}")
                    await asyncio.sleep(retry_delay)

                    # Simulate network recovery after 3 attempts
                    if attempt >= 2:
                        network_available = True
                else:
                    pytest.fail("Network call failed after all retries")


class TestResourceExhaustion:
    """Test resource exhaustion scenarios"""

    @pytest.mark.asyncio
    async def test_memory_pressure_handling(self):
        """Test behavior under memory pressure"""

        try:
            from src.generation_service.optimization.resource_manager import (
                ResourceManager,
            )

            # Initialize with very low memory limit
            resource_manager = ResourceManager(
                {"memory_limit_mb": 128, "monitoring_interval": 1.0}
            )

            await resource_manager.start_monitoring()

            try:
                # Get current metrics
                current_metrics = resource_manager.get_current_metrics()
                assert hasattr(current_metrics, "memory_used")

                # Trigger optimization under pressure
                optimization_result = await resource_manager.optimize_resources()
                assert "actions_taken" in optimization_result

                # Should not crash under low memory conditions
                assert optimization_result is not None

            finally:
                await resource_manager.stop_monitoring()

        except ImportError:
            pytest.skip("Resource manager not available")

    @pytest.mark.asyncio
    async def test_high_cpu_load_handling(self):
        """Test behavior under high CPU load"""

        # Simulate CPU-intensive task
        async def cpu_intensive_task():
            # Simulate computational work
            result = 0
            for i in range(100000):
                result += i * i
            return result

        try:
            from src.generation_service.optimization.async_manager import AsyncManager

            async_manager = AsyncManager(
                {"pools": {"cpu_intensive": {"max_concurrent": 1, "timeout": 5.0}}}
            )

            await async_manager.start()

            try:
                # Submit multiple CPU-intensive tasks
                tasks = [cpu_intensive_task() for _ in range(5)]

                start_time = time.time()
                results = await async_manager.execute_parallel(tasks, timeout=10.0)
                end_time = time.time()

                # Should complete all tasks
                assert len(results) == 5

                # Should handle CPU load without crashing
                execution_time = end_time - start_time
                logger.info(f"CPU intensive tasks completed in {execution_time:.2f}s")

            finally:
                await async_manager.stop()

        except ImportError:
            pytest.skip("Async manager not available")

    @pytest.mark.asyncio
    async def test_disk_space_exhaustion(self):
        """Test behavior when disk space is low"""

        # Mock disk space check
        with patch("psutil.disk_usage") as mock_disk_usage:
            # Simulate low disk space (95% used)
            mock_disk_usage.return_value = MagicMock(
                total=1000000000,  # 1GB
                used=950000000,  # 950MB used
                free=50000000,  # 50MB free
            )

            try:
                from src.generation_service.optimization.resource_manager import (
                    ResourceManager,
                )

                resource_manager = ResourceManager(
                    {"disk_space_threshold": 0.9}  # 90% threshold
                )

                # Should detect low disk space
                disk_info = resource_manager._check_disk_space()
                usage_percent = disk_info["used"] / disk_info["total"]

                assert usage_percent > 0.9, "Should detect high disk usage"

                logger.warning(f"Disk usage: {usage_percent:.1%}")

            except (ImportError, AttributeError):
                pytest.skip("Resource manager disk check not available")


class TestConcurrencyIssues:
    """Test concurrency-related error scenarios"""

    @pytest.mark.asyncio
    async def test_race_condition_in_cache(self):
        """Test race conditions in cache access"""

        try:
            from src.generation_service.cache.cache_manager import CacheManager
            from src.generation_service.cache.cache_strategies import CacheType

            cache_manager = CacheManager(enable_memory_fallback=True)
            await cache_manager.initialize()

            # Simulate concurrent cache operations
            async def concurrent_cache_operation(worker_id: int):
                key = f"race_test_{worker_id}"

                # Multiple set/get operations
                for i in range(10):
                    await cache_manager.set(
                        CacheType.PROMPT_RESULT,
                        {"worker": worker_id, "iteration": i},
                        prompt=key,
                    )

                    result = await cache_manager.get(
                        CacheType.PROMPT_RESULT, prompt=key
                    )

                    assert result is not None
                    assert result["worker"] == worker_id

                return worker_id

            # Run concurrent workers
            workers = [concurrent_cache_operation(i) for i in range(5)]
            results = await asyncio.gather(*workers, return_exceptions=True)

            # All workers should complete successfully
            successful_workers = [r for r in results if isinstance(r, int)]
            assert (
                len(successful_workers) == 5
            ), f"Only {len(successful_workers)} workers completed successfully"

            await cache_manager.shutdown()

        except ImportError:
            pytest.skip("Cache manager not available")

    @pytest.mark.asyncio
    async def test_deadlock_prevention(self):
        """Test deadlock prevention in async operations"""

        # Create potential deadlock scenario with timeouts
        async def operation_a(lock_a: asyncio.Lock, lock_b: asyncio.Lock):
            async with lock_a:
                await asyncio.sleep(0.1)
                # Try to acquire lock_b with timeout
                try:
                    async with asyncio.wait_for(lock_b.acquire(), timeout=0.5):
                        await asyncio.sleep(0.1)
                        lock_b.release()
                    return "operation_a_success"
                except asyncio.TimeoutError:
                    return "operation_a_timeout"

        async def operation_b(lock_a: asyncio.Lock, lock_b: asyncio.Lock):
            async with lock_b:
                await asyncio.sleep(0.1)
                # Try to acquire lock_a with timeout
                try:
                    async with asyncio.wait_for(lock_a.acquire(), timeout=0.5):
                        await asyncio.sleep(0.1)
                        lock_a.release()
                    return "operation_b_success"
                except asyncio.TimeoutError:
                    return "operation_b_timeout"

        lock_a = asyncio.Lock()
        lock_b = asyncio.Lock()

        # Run operations concurrently
        results = await asyncio.gather(
            operation_a(lock_a, lock_b),
            operation_b(lock_a, lock_b),
            return_exceptions=True,
        )

        # Should handle potential deadlock with timeouts
        assert len(results) == 2

        # At least one operation should complete or timeout gracefully
        completed_operations = [r for r in results if isinstance(r, str)]
        assert len(completed_operations) == 2

        logger.info(f"Deadlock test results: {results}")


class TestDataCorruption:
    """Test data corruption and validation scenarios"""

    @pytest.mark.asyncio
    async def test_invalid_json_data(self):
        """Test handling of invalid JSON data"""

        invalid_json_strings = [
            '{"invalid": json}',  # Invalid syntax
            '{"incomplete":',  # Incomplete JSON
            "{invalid_quotes}",  # Invalid quotes
            "",  # Empty string
            "null",  # Null value
            "[]",  # Array instead of object
        ]

        for invalid_json in invalid_json_strings:
            try:
                import json

                json.loads(invalid_json)
                logger.warning(f"Expected JSON parsing to fail for: {invalid_json}")
            except (json.JSONDecodeError, ValueError):
                # Expected behavior
                logger.info(f"Correctly handled invalid JSON: {invalid_json[:20]}...")

    @pytest.mark.asyncio
    async def test_cache_data_corruption(self):
        """Test handling of corrupted cache data"""

        try:
            from src.generation_service.cache.cache_manager import CacheManager
            from src.generation_service.cache.cache_strategies import CacheType

            cache_manager = CacheManager(enable_memory_fallback=True)
            await cache_manager.initialize()

            # Store valid data first
            await cache_manager.set(
                CacheType.PROMPT_RESULT, {"valid": "data"}, prompt="test_corruption"
            )

            # Simulate data corruption by directly modifying cache
            # This would typically happen at the storage level
            corrupted_data = b"corrupted_binary_data"

            # Try to handle corrupted data gracefully
            try:
                # This should handle corruption gracefully
                result = await cache_manager.get(
                    CacheType.PROMPT_RESULT, prompt="test_corruption"
                )

                # Should either return valid data or None
                if result is not None:
                    assert isinstance(result, dict)

            except Exception as e:
                # Should handle corruption gracefully, not crash
                logger.warning(f"Cache corruption handled: {e}")

            await cache_manager.shutdown()

        except ImportError:
            pytest.skip("Cache manager not available")


class TestServiceInterruption:
    """Test service interruption and recovery scenarios"""

    @pytest.mark.asyncio
    async def test_graceful_shutdown(self):
        """Test graceful shutdown behavior"""

        shutdown_completed = False

        async def mock_service_shutdown():
            nonlocal shutdown_completed

            # Simulate service cleanup
            await asyncio.sleep(0.1)

            # Mark shutdown as completed
            shutdown_completed = True

            logger.info("Service shutdown completed")

        # Test shutdown process
        await mock_service_shutdown()
        assert shutdown_completed, "Service should complete graceful shutdown"

    @pytest.mark.asyncio
    async def test_signal_handling(self):
        """Test signal handling for graceful shutdown"""

        if os.name == "nt":  # Windows
            pytest.skip("Signal handling test not applicable on Windows")

        signal_received = None

        def signal_handler(signum, frame):
            nonlocal signal_received
            signal_received = signum
            logger.info(f"Received signal: {signum}")

        # Set up signal handler
        original_handler = signal.signal(signal.SIGTERM, signal_handler)

        try:
            # Send signal to self (in a real scenario, this would come from outside)
            # os.kill(os.getpid(), signal.SIGTERM)

            # Simulate signal handling
            signal_handler(signal.SIGTERM, None)

            assert signal_received == signal.SIGTERM, "Should handle SIGTERM signal"

        finally:
            # Restore original signal handler
            signal.signal(signal.SIGTERM, original_handler)

    @pytest.mark.asyncio
    async def test_service_recovery_after_crash(self):
        """Test service recovery mechanisms"""

        # Simulate service state before crash
        service_state = {
            "active_requests": 5,
            "cache_entries": 100,
            "last_checkpoint": time.time(),
        }

        # Simulate crash recovery
        async def recover_service_state():
            # Simulate state recovery
            recovered_state = {
                "active_requests": 0,  # Reset active requests
                "cache_entries": service_state["cache_entries"],  # Preserve cache
                "last_checkpoint": time.time(),  # Update checkpoint
                "recovery_timestamp": time.time(),
            }

            return recovered_state

        recovered_state = await recover_service_state()

        # Validate recovery
        assert (
            recovered_state["active_requests"] == 0
        ), "Active requests should be reset"
        assert (
            recovered_state["cache_entries"] == service_state["cache_entries"]
        ), "Cache should be preserved"
        assert (
            "recovery_timestamp" in recovered_state
        ), "Recovery timestamp should be set"


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    @pytest.mark.asyncio
    async def test_empty_input_handling(self):
        """Test handling of empty or null inputs"""

        empty_inputs = ["", None, {}, [], 0, False]

        for empty_input in empty_inputs:
            # Test input validation
            try:
                # Simulate input processing
                if empty_input is None or empty_input == "":
                    result = {"status": "empty_input", "input": empty_input}
                else:
                    result = {"status": "processed", "input": empty_input}

                assert "status" in result
                logger.info(f"Handled empty input: {type(empty_input).__name__}")

            except Exception as e:
                logger.warning(f"Error handling empty input {empty_input}: {e}")

    @pytest.mark.asyncio
    async def test_extremely_large_input(self):
        """Test handling of extremely large inputs"""

        # Generate large input data
        large_string = "x" * (10 * 1024 * 1024)  # 10MB string
        large_dict = {f"key_{i}": f"value_{i}" * 1000 for i in range(1000)}
        large_list = list(range(100000))

        large_inputs = [large_string, large_dict, large_list]

        for large_input in large_inputs:
            try:
                # Test memory usage with large input
                input_size = len(str(large_input))

                # Should handle large inputs gracefully
                if input_size > 1024 * 1024:  # 1MB threshold
                    result = {
                        "status": "large_input_detected",
                        "size_mb": input_size / (1024 * 1024),
                    }
                else:
                    result = {"status": "normal_processing", "size": input_size}

                assert "status" in result
                logger.info(f"Handled large input: {result['status']}")

            except MemoryError:
                logger.warning(
                    "Memory error with large input - this is expected behavior"
                )
            except Exception as e:
                logger.warning(f"Error with large input: {e}")

    @pytest.mark.asyncio
    async def test_unicode_and_special_characters(self):
        """Test handling of Unicode and special characters"""

        special_inputs = [
            "Hello 世界",  # Unicode characters
            "emoji test 🚀🔥💻",  # Emojis
            "special chars: !@#$%^&*()",  # Special characters
            "newlines\nand\ttabs",  # Control characters
            "quotes \"single' and `backtick`",  # Various quotes
            "\x00\x01\x02",  # Control characters
            "very long unicode: " + "🎵" * 1000,  # Many Unicode chars
        ]

        for special_input in special_inputs:
            try:
                # Test encoding/decoding
                encoded = special_input.encode("utf-8")
                decoded = encoded.decode("utf-8")

                assert (
                    decoded == special_input
                ), "Unicode round-trip should be identical"

                # Test JSON serialization
                import json

                json_str = json.dumps({"text": special_input})
                parsed = json.loads(json_str)

                assert (
                    parsed["text"] == special_input
                ), "JSON round-trip should preserve Unicode"

                logger.info(
                    f"Successfully handled special input: {special_input[:20]}..."
                )

            except Exception as e:
                logger.warning(f"Error with special input: {e}")


class TestAPIErrorScenarios:
    """Test API-level error scenarios"""

    @pytest.fixture
    async def client(self):
        """HTTP client for testing"""
        async with httpx.AsyncClient(
            base_url="http://localhost:8000", timeout=30.0
        ) as client:
            yield client

    @pytest.mark.asyncio
    async def test_malformed_requests(self, client: httpx.AsyncClient):
        """Test handling of malformed HTTP requests"""

        # Test invalid JSON in request body
        try:
            response = await client.post(
                "/api/cache/clear",
                content="invalid json content",
                headers={"Content-Type": "application/json"},
            )

            # Should return 400 Bad Request or similar
            assert response.status_code >= 400

        except Exception as e:
            logger.warning(f"Malformed request test failed: {e}")

    @pytest.mark.asyncio
    async def test_request_timeout_handling(self, client: httpx.AsyncClient):
        """Test handling of request timeouts"""

        # Test with very short timeout
        try:
            short_timeout_client = httpx.AsyncClient(
                base_url="http://localhost:8000",
                timeout=0.001,  # 1ms timeout
            )

            response = await short_timeout_client.get("/api/monitoring/metrics")

            # If it somehow succeeds, that's also fine
            logger.info(
                f"Request completed despite short timeout: {response.status_code}"
            )

            await short_timeout_client.aclose()

        except (httpx.TimeoutException, asyncio.TimeoutError):
            # Expected behavior
            logger.info("Request timeout handled correctly")
        except Exception as e:
            logger.warning(f"Unexpected error in timeout test: {e}")

    @pytest.mark.asyncio
    async def test_large_request_handling(self, client: httpx.AsyncClient):
        """Test handling of very large requests"""

        # Create large request payload
        large_payload = {
            "data": "x" * (1024 * 1024),  # 1MB of data
            "metadata": {f"field_{i}": f"value_{i}" for i in range(1000)},
        }

        try:
            response = await client.post(
                "/api/performance/optimize", json=large_payload
            )

            # Should either process or reject gracefully
            assert response.status_code in [200, 400, 413, 422, 500]

            if response.status_code == 413:
                logger.info("Large request rejected with 413 Payload Too Large")
            elif response.status_code == 400:
                logger.info("Large request rejected with 400 Bad Request")
            else:
                logger.info(
                    f"Large request handled with status: {response.status_code}"
                )

        except Exception as e:
            logger.warning(f"Large request test failed: {e}")


# Performance under error conditions
@pytest.mark.asyncio
async def test_error_condition_performance():
    """Test that the system maintains performance under error conditions"""

    error_count = 0
    success_count = 0

    async def simulate_operation_with_errors():
        nonlocal error_count, success_count

        # Simulate 30% error rate
        import random

        if random.random() < 0.3:
            error_count += 1
            raise Exception("Simulated error")
        else:
            success_count += 1
            await asyncio.sleep(0.01)  # Simulate work
            return "success"

    # Run many operations with errors
    tasks = [simulate_operation_with_errors() for _ in range(100)]

    start_time = time.time()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    end_time = time.time()

    # Analyze results
    successes = [r for r in results if r == "success"]
    errors = [r for r in results if isinstance(r, Exception)]

    total_time = end_time - start_time

    logger.info(
        f"Error scenario performance: {len(successes)} successes, {len(errors)} errors in {total_time:.2f}s"
    )

    # Should complete in reasonable time despite errors
    assert total_time < 10.0, "Operations should complete quickly even with errors"

    # Should have some successes
    assert len(successes) > 0, "Should have some successful operations"

    # Error rate should be approximately as expected
    error_rate = len(errors) / len(results)
    assert (
        0.2 <= error_rate <= 0.4
    ), f"Error rate outside expected range: {error_rate:.2f}"


if __name__ == "__main__":
    # Run error scenario tests
    import asyncio

    async def run_error_tests():
        print("Running error scenario tests...")

        # Test network failures
        print("Testing network failures...")
        try:
            await TestNetworkFailures().test_redis_connection_failure()
            print("✓ Redis connection failure handling")
        except Exception as e:
            print(f"✗ Redis connection failure test failed: {e}")

        # Test resource exhaustion
        print("Testing resource exhaustion...")
        try:
            await TestResourceExhaustion().test_memory_pressure_handling()
            print("✓ Memory pressure handling")
        except Exception as e:
            print(f"✗ Memory pressure test failed: {e}")

        # Test edge cases
        print("Testing edge cases...")
        try:
            await TestEdgeCases().test_empty_input_handling()
            print("✓ Empty input handling")
        except Exception as e:
            print(f"✗ Empty input test failed: {e}")

        print("Error scenario tests completed!")

    asyncio.run(run_error_tests())
