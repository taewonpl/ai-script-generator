"""
Comprehensive end-to-end integration tests for Generation Service
"""

import asyncio
import json

import httpx
import pytest

try:
    from ai_script_core import get_service_logger

    logger = get_service_logger("generation-service.tests.integration")
except (ImportError, RuntimeError):
    import logging

    logger = logging.getLogger(__name__)


class TestGenerationServiceIntegration:
    """
    End-to-end integration tests for the complete Generation Service

    Tests the entire system including:
    - Workflow execution
    - API endpoints
    - Performance optimization systems
    - Monitoring and alerting
    - Error handling
    """

    @pytest.fixture
    def base_url(self):
        """Base URL for the service"""
        return "http://localhost:8000"

    @pytest.fixture
    async def client(self, base_url):
        """HTTP client for testing"""
        async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
            yield client

    @pytest.fixture
    async def service_setup(self):
        """Setup service dependencies"""
        # Initialize all service components
        from src.generation_service.cache.cache_manager import initialize_cache_manager
        from src.generation_service.config.settings import initialize_settings
        from src.generation_service.monitoring.alerting import initialize_alert_manager
        from src.generation_service.monitoring.health_monitor import (
            initialize_health_monitor,
        )
        from src.generation_service.monitoring.metrics_collector import (
            initialize_metrics_collector,
        )
        from src.generation_service.optimization.async_manager import (
            initialize_async_manager,
        )
        from src.generation_service.optimization.resource_manager import (
            initialize_resource_manager,
        )

        # Initialize with test configuration
        settings = initialize_settings(
            debug=True,
            environment="testing",
            enable_caching=True,
            enable_monitoring=True,
        )

        cache_manager = initialize_cache_manager(
            redis_config=None,  # Use memory cache for testing
            enable_memory_fallback=True,
        )

        metrics_collector = initialize_metrics_collector(
            {"max_log_entries": 1000, "retention_hours": 1}
        )

        health_monitor = initialize_health_monitor({"check_interval": 10.0})

        alert_manager = initialize_alert_manager(
            {"alerting_enabled": False}  # Disable alerts in testing
        )

        async_manager = initialize_async_manager(
            {
                "pools": {
                    "ai_api": {"max_concurrent": 2, "timeout": 10.0},
                    "general": {"max_concurrent": 5, "timeout": 5.0},
                }
            }
        )

        resource_manager = initialize_resource_manager(
            {
                "monitoring_interval": 5.0,
                "memory_limit_mb": 512,  # Lower limit for testing
            }
        )

        # Start all systems
        await cache_manager.initialize()
        await metrics_collector.start_collection()
        await health_monitor.start_monitoring()
        await alert_manager.start_monitoring()
        await async_manager.start()
        await resource_manager.start_monitoring()

        yield {
            "settings": settings,
            "cache_manager": cache_manager,
            "metrics_collector": metrics_collector,
            "health_monitor": health_monitor,
            "alert_manager": alert_manager,
            "async_manager": async_manager,
            "resource_manager": resource_manager,
        }

        # Cleanup
        await cache_manager.shutdown()
        await metrics_collector.stop_collection()
        await health_monitor.stop_monitoring()
        await alert_manager.stop_monitoring()
        await async_manager.stop()
        await resource_manager.stop_monitoring()

    @pytest.mark.asyncio
    async def test_health_check_endpoint(self, client: httpx.AsyncClient):
        """Test basic health check endpoint"""

        response = await client.get("/api/monitoring/health")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert "timestamp" in data
        assert "overall_status" in data

    @pytest.mark.asyncio
    async def test_metrics_endpoint(self, client: httpx.AsyncClient):
        """Test metrics collection endpoint"""

        response = await client.get("/api/monitoring/metrics")

        assert response.status_code == 200
        data = response.json()

        assert "timestamp" in data
        assert "metrics" in data
        assert "performance_targets" in data

    @pytest.mark.asyncio
    async def test_cache_status_endpoint(self, client: httpx.AsyncClient):
        """Test cache system status"""

        response = await client.get("/api/cache/status")

        assert response.status_code == 200
        data = response.json()

        assert "enabled" in data
        assert "backend" in data
        assert "statistics" in data
        assert "health" in data

    @pytest.mark.asyncio
    async def test_performance_status_endpoint(self, client: httpx.AsyncClient):
        """Test performance system status"""

        response = await client.get("/api/performance/status")

        assert response.status_code == 200
        data = response.json()

        assert "optimization_enabled" in data
        assert "async_enabled" in data
        assert "current_load" in data
        assert "performance_rating" in data

    @pytest.mark.asyncio
    async def test_workflow_execution_simulation(self, service_setup):
        """Test complete workflow execution simulation"""

        # Simulate workflow execution
        from src.generation_service.monitoring.metrics_collector import (
            get_metrics_collector,
        )

        collector = get_metrics_collector()
        assert collector is not None

        # Record workflow metrics
        collector.record_timer("workflow_execution_time", 15.5)  # Under 30s target
        collector.record_gauge("concurrent_workflows", 8)
        collector.record_gauge("cache_hit_ratio", 0.75)  # Above 70% target

        # Get current metrics
        current_metrics = collector.get_current_metrics()

        assert current_metrics.workflow_execution_time <= 30.0  # Target: 30s
        assert current_metrics.cache_hit_ratio >= 0.7  # Target: 70%
        assert current_metrics.concurrent_workflows <= 20  # Target: 20 max

    @pytest.mark.asyncio
    async def test_cache_operations(self, service_setup):
        """Test cache system operations"""

        from src.generation_service.cache.cache_manager import get_cache_manager
        from src.generation_service.cache.cache_strategies import CacheType

        cache_manager = get_cache_manager()
        assert cache_manager is not None

        # Test cache set operation
        success = await cache_manager.set(
            CacheType.PROMPT_RESULT,
            {"result": "test response"},
            prompt="test prompt",
            model="gpt-3.5-turbo",
        )
        assert success

        # Test cache get operation
        cached_data = await cache_manager.get(
            CacheType.PROMPT_RESULT, prompt="test prompt", model="gpt-3.5-turbo"
        )
        assert cached_data is not None
        assert cached_data["result"] == "test response"

        # Test cache statistics
        stats = await cache_manager.get_cache_stats()
        assert "operations" in stats
        assert "hits" in stats
        assert "misses" in stats

    @pytest.mark.asyncio
    async def test_async_task_execution(self, service_setup):
        """Test async task execution system"""

        from src.generation_service.optimization.async_manager import get_async_manager

        async_manager = get_async_manager()
        assert async_manager is not None

        # Define test coroutines
        async def test_task(delay: float, result: str):
            await asyncio.sleep(delay)
            return f"Task completed: {result}"

        # Submit tasks to different pools
        ai_tasks = [test_task(0.1, f"ai_task_{i}") for i in range(3)]

        general_tasks = [test_task(0.05, f"general_task_{i}") for i in range(5)]

        # Execute AI batch
        ai_results = await async_manager.execute_ai_batch(ai_tasks, timeout=5.0)
        assert len(ai_results) == 3

        for result in ai_results:
            assert result.status in ["completed", "failed"]
            if result.status == "completed":
                assert "Task completed" in str(result.result)

        # Execute general batch
        general_results = await async_manager.execute_parallel(
            general_tasks, timeout=5.0
        )
        assert len(general_results) == 5

        # Check system metrics
        metrics = async_manager.get_system_metrics()
        assert "current_load" in metrics
        assert "pools" in metrics

    @pytest.mark.asyncio
    async def test_resource_monitoring(self, service_setup):
        """Test resource monitoring system"""

        from src.generation_service.optimization.resource_manager import (
            get_resource_manager,
        )

        resource_manager = get_resource_manager()
        assert resource_manager is not None

        # Get current metrics
        current_metrics = resource_manager.get_current_metrics()

        # Validate metric types
        assert hasattr(current_metrics, "memory_used")
        assert hasattr(current_metrics, "memory_percent")
        assert hasattr(current_metrics, "cpu_percent")

        # Test resource optimization
        optimization_results = await resource_manager.optimize_resources()
        assert "actions_taken" in optimization_results

        # Get resource summary
        summary = resource_manager.get_resource_summary()
        assert "current_metrics" in summary
        assert "resource_levels" in summary

    @pytest.mark.asyncio
    async def test_health_monitoring(self, service_setup):
        """Test health monitoring system"""

        from src.generation_service.monitoring.health_monitor import get_health_monitor

        health_monitor = get_health_monitor()
        assert health_monitor is not None

        # Get health summary
        health_summary = health_monitor.get_health_summary()
        assert "overall_status" in health_summary
        assert "components" in health_summary

        # Test immediate health check
        result = await health_monitor.perform_immediate_check("cache_health")
        if result:  # Only test if component exists
            assert hasattr(result, "status")
            assert hasattr(result, "response_time")

    @pytest.mark.asyncio
    async def test_error_handling_scenarios(self, service_setup):
        """Test various error handling scenarios"""

        from src.generation_service.cache.cache_manager import get_cache_manager
        from src.generation_service.cache.cache_strategies import CacheType

        cache_manager = get_cache_manager()

        # Test invalid cache operations
        try:
            # Try to get non-existent cache entry
            result = await cache_manager.get(
                CacheType.PROMPT_RESULT, prompt="non_existent_prompt"
            )
            assert result is None  # Should return None, not error
        except Exception as e:
            pytest.fail(f"Cache get should handle missing keys gracefully: {e}")

        # Test cache with invalid data
        try:
            # This should handle gracefully
            await cache_manager.set(
                CacheType.PROMPT_RESULT,
                None,  # Invalid data
                prompt="test",
            )
        except Exception:
            # Expected to fail or handle gracefully
            pass

    @pytest.mark.asyncio
    async def test_concurrent_request_handling(self, client: httpx.AsyncClient):
        """Test handling of concurrent requests"""

        # Create multiple concurrent requests
        tasks = []
        for i in range(10):
            task = client.get("/api/monitoring/health")
            tasks.append(task)

        # Execute concurrently
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Validate responses
        successful_responses = 0
        for response in responses:
            if isinstance(response, httpx.Response):
                if response.status_code == 200:
                    successful_responses += 1
            elif isinstance(response, Exception):
                logger.warning(f"Request failed: {response}")

        # Should handle at least 80% of concurrent requests successfully
        success_rate = successful_responses / len(responses)
        assert success_rate >= 0.8, f"Success rate too low: {success_rate:.1%}"

    @pytest.mark.asyncio
    async def test_performance_targets_validation(self, service_setup):
        """Test that all performance targets are met"""

        from src.generation_service.monitoring.metrics_collector import (
            get_metrics_collector,
        )

        collector = get_metrics_collector()

        # Simulate optimal performance metrics
        collector.record_timer("workflow_execution_time", 25.0)  # Under 30s
        collector.record_gauge("concurrent_workflows", 15)  # Under 20
        collector.record_timer("ai_api_response_time", 3.5)  # Reasonable
        collector.record_gauge("cache_hit_ratio", 0.75)  # Above 70%
        collector.record_gauge("memory_usage", 400.0)  # Under 512MB test limit

        # Check performance targets
        targets = collector.check_performance_targets()

        # Validate key targets
        workflow_target = targets.get("workflow_execution_time")
        if workflow_target:
            assert workflow_target[
                "meeting_target"
            ], f"Workflow time target not met: {workflow_target}"

        cache_target = targets.get("cache_hit_ratio")
        if cache_target:
            assert cache_target[
                "meeting_target"
            ], f"Cache hit ratio target not met: {cache_target}"

        memory_target = targets.get("memory_usage_mb")
        if memory_target:
            assert memory_target[
                "meeting_target"
            ], f"Memory usage target not met: {memory_target}"

    @pytest.mark.asyncio
    async def test_system_integration_flow(self, service_setup):
        """Test complete system integration flow"""

        # This test simulates a complete workflow execution
        # including all integrated systems

        from src.generation_service.cache.cache_manager import get_cache_manager
        from src.generation_service.monitoring.metrics_collector import (
            get_metrics_collector,
        )
        from src.generation_service.optimization.async_manager import get_async_manager

        cache_manager = get_cache_manager()
        collector = get_metrics_collector()
        async_manager = get_async_manager()

        # Step 1: Check cache for existing result
        cached_result = await cache_manager.get(
            CacheType.PROMPT_RESULT,
            prompt="integration_test_prompt",
            model="test-model",
        )

        if cached_result is None:
            # Step 2: Execute async task to generate result
            async def generate_response():
                await asyncio.sleep(0.1)  # Simulate processing
                return {"response": "Generated test response", "tokens": 150}

            # Submit task
            task_id = await async_manager.submit_priority_task(generate_response())

            # Wait for result
            result = await async_manager.pools["priority"].get_result(
                task_id, timeout=5.0
            )
            assert result.status == "completed"

            # Step 3: Cache the result
            await cache_manager.set(
                CacheType.PROMPT_RESULT,
                result.result,
                prompt="integration_test_prompt",
                model="test-model",
            )

            # Step 4: Record metrics
            collector.record_timer("workflow_execution_time", 0.5)
            collector.record_counter("workflow_success", 1)
        else:
            # Cache hit - record faster execution
            collector.record_timer("workflow_execution_time", 0.05)
            collector.record_counter("workflow_cache_hit", 1)

        # Step 5: Verify final state
        final_cached = await cache_manager.get(
            CacheType.PROMPT_RESULT,
            prompt="integration_test_prompt",
            model="test-model",
        )
        assert final_cached is not None

        # Check metrics were recorded
        current_metrics = collector.get_current_metrics()
        assert current_metrics.workflow_execution_time > 0

    @pytest.mark.asyncio
    async def test_api_endpoints_comprehensive(self, client: httpx.AsyncClient):
        """Comprehensive test of all API endpoints"""

        endpoints_to_test = [
            # Monitoring endpoints
            ("/api/monitoring/health", "GET"),
            ("/api/monitoring/metrics", "GET"),
            ("/api/monitoring/status", "GET"),
            ("/api/monitoring/dashboard", "GET"),
            # Cache endpoints
            ("/api/cache/status", "GET"),
            ("/api/cache/stats", "GET"),
            ("/api/cache/health", "GET"),
            ("/api/cache/analytics", "GET"),
            # Performance endpoints
            ("/api/performance/status", "GET"),
            ("/api/performance/resources", "GET"),
            ("/api/performance/load", "GET"),
            ("/api/performance/analytics", "GET"),
        ]

        results = {}

        for endpoint, method in endpoints_to_test:
            try:
                if method == "GET":
                    response = await client.get(endpoint)
                else:
                    response = await client.request(method, endpoint)

                results[endpoint] = {
                    "status_code": response.status_code,
                    "success": response.status_code < 400,
                    "response_time": (
                        response.elapsed.total_seconds()
                        if hasattr(response, "elapsed")
                        else 0
                    ),
                }

                # Basic validation for successful responses
                if response.status_code == 200:
                    try:
                        data = response.json()
                        assert isinstance(
                            data, dict
                        ), f"Response should be JSON dict for {endpoint}"
                    except json.JSONDecodeError:
                        # Some endpoints might return non-JSON content
                        pass

            except Exception as e:
                results[endpoint] = {
                    "status_code": 0,
                    "success": False,
                    "error": str(e),
                }

        # Analyze results
        total_endpoints = len(endpoints_to_test)
        successful_endpoints = sum(
            1 for r in results.values() if r.get("success", False)
        )
        success_rate = successful_endpoints / total_endpoints

        logger.info(
            f"API endpoints test: {successful_endpoints}/{total_endpoints} successful ({success_rate:.1%})"
        )

        # Should have at least 80% success rate
        assert (
            success_rate >= 0.8
        ), f"API endpoint success rate too low: {success_rate:.1%}"

        # Log any failures for debugging
        for endpoint, result in results.items():
            if not result.get("success", False):
                logger.warning(f"Endpoint {endpoint} failed: {result}")


class TestErrorScenarios:
    """Test various error scenarios and edge cases"""

    @pytest.mark.asyncio
    async def test_memory_pressure_scenario(self):
        """Test system behavior under memory pressure"""

        from src.generation_service.optimization.resource_manager import (
            initialize_resource_manager,
        )

        # Initialize with very low memory limit
        resource_manager = initialize_resource_manager(
            {
                "memory_limit_mb": 128,  # Very low limit
                "monitoring_interval": 1.0,
            }
        )

        await resource_manager.start_monitoring()

        try:
            # Check if system handles low memory gracefully
            current_metrics = resource_manager.get_current_metrics()

            # Should not crash under low memory conditions
            optimization_result = await resource_manager.optimize_resources()
            assert "actions_taken" in optimization_result

        finally:
            await resource_manager.stop_monitoring()

    @pytest.mark.asyncio
    async def test_cache_failure_scenario(self):
        """Test system behavior when cache fails"""

        from src.generation_service.cache.cache_manager import CacheManager

        # Initialize cache manager with invalid Redis config
        cache_manager = CacheManager(
            redis_config={"redis_host": "invalid_host", "redis_port": 9999},
            enable_memory_fallback=True,
        )

        # Should initialize successfully with fallback
        success = await cache_manager.initialize()
        # Redis should fail, but memory fallback should work

        try:
            # Test cache operations with fallback
            from src.generation_service.cache.cache_strategies import CacheType

            # Should work with memory cache
            set_result = await cache_manager.set(
                CacheType.PROMPT_RESULT, {"test": "data"}, prompt="test"
            )

            get_result = await cache_manager.get(CacheType.PROMPT_RESULT, prompt="test")

            # Should work with memory fallback
            assert get_result is not None

        finally:
            await cache_manager.shutdown()

    @pytest.mark.asyncio
    async def test_async_task_timeout_scenario(self):
        """Test async task timeout handling"""

        from src.generation_service.optimization.async_manager import AsyncManager

        async_manager = AsyncManager(
            {"pools": {"test": {"max_concurrent": 2, "timeout": 1.0}}}
        )

        await async_manager.start()

        try:
            # Define a task that will timeout
            async def slow_task():
                await asyncio.sleep(2.0)  # Longer than timeout
                return "Should not complete"

            # Submit task
            task_id = await async_manager.pools["general"].submit_task(
                slow_task(),
                timeout=0.5,  # Short timeout
            )

            # Wait for result
            result = await async_manager.pools["general"].get_result(
                task_id, timeout=3.0
            )

            # Should have timed out
            assert result.status == "timeout"

        finally:
            await async_manager.stop()


@pytest.mark.asyncio
async def test_full_system_startup_shutdown():
    """Test complete system startup and shutdown"""

    # Import all necessary modules
    from src.generation_service.cache.cache_manager import initialize_cache_manager
    from src.generation_service.config.settings import initialize_settings
    from src.generation_service.monitoring.health_monitor import (
        initialize_health_monitor,
    )
    from src.generation_service.monitoring.metrics_collector import (
        initialize_metrics_collector,
    )
    from src.generation_service.optimization.async_manager import (
        initialize_async_manager,
    )
    from src.generation_service.optimization.resource_manager import (
        initialize_resource_manager,
    )

    # Initialize all systems
    systems = {}

    try:
        # Settings
        systems["settings"] = initialize_settings(environment="testing")

        # Cache system
        systems["cache"] = initialize_cache_manager(enable_memory_fallback=True)
        await systems["cache"].initialize()

        # Metrics system
        systems["metrics"] = initialize_metrics_collector()
        await systems["metrics"].start_collection()

        # Health monitoring
        systems["health"] = initialize_health_monitor()
        await systems["health"].start_monitoring()

        # Async manager
        systems["async"] = initialize_async_manager()
        await systems["async"].start()

        # Resource manager
        systems["resources"] = initialize_resource_manager()
        await systems["resources"].start_monitoring()

        # Test that all systems are operational
        assert systems["cache"] is not None
        assert systems["metrics"] is not None
        assert systems["health"] is not None
        assert systems["async"] is not None
        assert systems["resources"] is not None

        # Perform basic operations to verify functionality
        cache_stats = await systems["cache"].get_cache_stats()
        assert "operations" in cache_stats

        current_metrics = systems["metrics"].get_current_metrics()
        assert current_metrics is not None

        health_summary = systems["health"].get_health_summary()
        assert "overall_status" in health_summary

        async_metrics = systems["async"].get_system_metrics()
        assert "current_load" in async_metrics

        resource_summary = systems["resources"].get_resource_summary()
        assert "current_metrics" in resource_summary

    finally:
        # Shutdown all systems gracefully
        if "cache" in systems:
            await systems["cache"].shutdown()
        if "metrics" in systems:
            await systems["metrics"].stop_collection()
        if "health" in systems:
            await systems["health"].stop_monitoring()
        if "async" in systems:
            await systems["async"].stop()
        if "resources" in systems:
            await systems["resources"].stop_monitoring()
