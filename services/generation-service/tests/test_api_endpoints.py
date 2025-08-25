"""
Comprehensive API endpoint tests for Generation Service
"""

import asyncio
import json
import time

import httpx
import pytest

try:
    from ai_script_core import get_service_logger

    logger = get_service_logger("generation-service.tests.api")
except (ImportError, RuntimeError):
    import logging

    logger = logging.getLogger(__name__)


class TestMonitoringEndpoints:
    """Test all monitoring API endpoints"""

    @pytest.fixture
    async def client(self):
        """HTTP client for testing"""
        async with httpx.AsyncClient(
            base_url="http://localhost:8000", timeout=30.0
        ) as client:
            yield client

    @pytest.mark.asyncio
    async def test_health_endpoint(self, client: httpx.AsyncClient):
        """Test basic health endpoint"""
        response = await client.get("/api/monitoring/health")

        assert response.status_code == 200
        data = response.json()

        # Validate response structure
        assert "status" in data
        assert "timestamp" in data
        assert "overall_status" in data
        assert data["status"] in ["healthy", "unhealthy", "degraded"]

        # Validate components if present
        if "components" in data:
            assert isinstance(data["components"], dict)

    @pytest.mark.asyncio
    async def test_metrics_endpoint(self, client: httpx.AsyncClient):
        """Test metrics collection endpoint"""
        response = await client.get("/api/monitoring/metrics")

        assert response.status_code == 200
        data = response.json()

        # Validate response structure
        assert "timestamp" in data
        assert "metrics" in data
        assert isinstance(data["metrics"], dict)

        # Validate key metrics presence
        metrics = data["metrics"]
        expected_metrics = [
            "workflow_execution_time",
            "concurrent_workflows",
            "memory_usage_mb",
            "cpu_usage_percent",
        ]

        for metric in expected_metrics:
            if metric in metrics:
                assert isinstance(metrics[metric], (int, float))

    @pytest.mark.asyncio
    async def test_status_endpoint(self, client: httpx.AsyncClient):
        """Test detailed service status endpoint"""
        response = await client.get("/api/monitoring/status")

        assert response.status_code == 200
        data = response.json()

        # Validate basic structure
        assert "service_name" in data or "status" in data

        # If components are present, validate structure
        if "components" in data:
            assert isinstance(data["components"], list)
            for component in data["components"]:
                assert "name" in component
                assert "status" in component

    @pytest.mark.asyncio
    async def test_dashboard_endpoint(self, client: httpx.AsyncClient):
        """Test dashboard data endpoint"""
        response = await client.get("/api/monitoring/dashboard")

        # Should either return 200 with data or 404 if not implemented
        assert response.status_code in [200, 404, 501]

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_prometheus_metrics_endpoint(self, client: httpx.AsyncClient):
        """Test Prometheus metrics format endpoint"""
        response = await client.get("/api/monitoring/metrics/prometheus")

        # Should either return 200 with metrics or 404 if not implemented
        assert response.status_code in [200, 404, 501]

        if response.status_code == 200:
            # Prometheus metrics should be plain text
            assert response.headers.get("content-type", "").startswith("text/plain")

            # Basic validation of Prometheus format
            content = response.text
            if content:
                lines = content.split("\n")
                # Should have some metric lines
                metric_lines = [
                    line for line in lines if not line.startswith("#") and line.strip()
                ]
                assert len(metric_lines) > 0


class TestCacheEndpoints:
    """Test all cache management API endpoints"""

    @pytest.fixture
    async def client(self):
        """HTTP client for testing"""
        async with httpx.AsyncClient(
            base_url="http://localhost:8000", timeout=30.0
        ) as client:
            yield client

    @pytest.mark.asyncio
    async def test_cache_status_endpoint(self, client: httpx.AsyncClient):
        """Test cache status endpoint"""
        response = await client.get("/api/cache/status")

        assert response.status_code == 200
        data = response.json()

        # Validate response structure
        assert "enabled" in data
        assert "backend" in data
        assert "health" in data
        assert isinstance(data["enabled"], bool)

        # Validate statistics if present
        if "statistics" in data:
            stats = data["statistics"]
            assert isinstance(stats, dict)

            # Check for expected statistics
            expected_stats = ["hits", "misses", "hit_ratio", "total_operations"]
            for stat in expected_stats:
                if stat in stats:
                    assert isinstance(stats[stat], (int, float))

    @pytest.mark.asyncio
    async def test_cache_stats_endpoint(self, client: httpx.AsyncClient):
        """Test detailed cache statistics endpoint"""
        response = await client.get("/api/cache/stats")

        assert response.status_code == 200
        data = response.json()

        # Validate operations section
        if "operations" in data:
            ops = data["operations"]
            assert isinstance(ops, dict)

            # Validate operation counters
            for key in ["total", "hits", "misses"]:
                if key in ops:
                    assert isinstance(ops[key], int)
                    assert ops[key] >= 0

    @pytest.mark.asyncio
    async def test_cache_health_endpoint(self, client: httpx.AsyncClient):
        """Test cache health check endpoint"""
        response = await client.get("/api/cache/health")

        # Should return 200 for healthy or 503 for unhealthy
        assert response.status_code in [200, 503]

        if response.status_code == 200:
            data = response.json()
            assert "status" in data or "component" in data

    @pytest.mark.asyncio
    async def test_cache_analytics_endpoint(self, client: httpx.AsyncClient):
        """Test cache analytics endpoint"""
        # Test default period
        response = await client.get("/api/cache/analytics")
        assert response.status_code in [200, 404, 501]

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)

            if "period" in data:
                assert data["period"] in ["1h", "24h", "7d", "30d"]

        # Test specific period
        response = await client.get("/api/cache/analytics?period=1h")
        assert response.status_code in [200, 404, 501]

    @pytest.mark.asyncio
    async def test_cache_clear_endpoint_without_auth(self, client: httpx.AsyncClient):
        """Test cache clear endpoint without authentication (should fail)"""
        response = await client.post("/api/cache/clear", json={"confirm": True})

        # Should require authentication
        assert response.status_code in [401, 403, 405, 501]


class TestPerformanceEndpoints:
    """Test all performance monitoring API endpoints"""

    @pytest.fixture
    async def client(self):
        """HTTP client for testing"""
        async with httpx.AsyncClient(
            base_url="http://localhost:8000", timeout=30.0
        ) as client:
            yield client

    @pytest.mark.asyncio
    async def test_performance_status_endpoint(self, client: httpx.AsyncClient):
        """Test performance status endpoint"""
        response = await client.get("/api/performance/status")

        assert response.status_code == 200
        data = response.json()

        # Validate response structure
        expected_fields = [
            "optimization_enabled",
            "async_enabled",
            "current_load",
            "performance_rating",
        ]

        for field in expected_fields:
            if field in data:
                if field.endswith("_enabled"):
                    assert isinstance(data[field], bool)
                elif field == "current_load":
                    assert isinstance(data[field], (int, float))
                    assert 0 <= data[field] <= 1
                elif field == "performance_rating":
                    assert data[field] in ["excellent", "good", "fair", "poor"]

    @pytest.mark.asyncio
    async def test_performance_resources_endpoint(self, client: httpx.AsyncClient):
        """Test resource usage metrics endpoint"""
        response = await client.get("/api/performance/resources")

        assert response.status_code == 200
        data = response.json()

        # Should contain resource information
        assert isinstance(data, dict)

        # Validate resource sections
        resource_sections = ["memory", "cpu", "disk", "network"]
        for section in resource_sections:
            if section in data:
                assert isinstance(data[section], dict)

    @pytest.mark.asyncio
    async def test_performance_load_endpoint(self, client: httpx.AsyncClient):
        """Test system load endpoint"""
        response = await client.get("/api/performance/load")

        assert response.status_code == 200
        data = response.json()

        # Validate load information
        assert isinstance(data, dict)

        if "current_load" in data:
            assert isinstance(data["current_load"], (int, float))
            assert data["current_load"] >= 0

    @pytest.mark.asyncio
    async def test_performance_analytics_endpoint(self, client: httpx.AsyncClient):
        """Test performance analytics endpoint"""
        # Test default parameters
        response = await client.get("/api/performance/analytics")
        assert response.status_code in [200, 404, 501]

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)

        # Test with specific period
        response = await client.get("/api/performance/analytics?period=1h")
        assert response.status_code in [200, 404, 501]

        # Test with specific metrics
        response = await client.get(
            "/api/performance/analytics?metrics=response_time,throughput"
        )
        assert response.status_code in [200, 404, 501]

    @pytest.mark.asyncio
    async def test_performance_optimize_endpoint_without_auth(
        self, client: httpx.AsyncClient
    ):
        """Test performance optimization endpoint without authentication"""
        response = await client.post(
            "/api/performance/optimize", json={"optimization_type": "memory"}
        )

        # Should require authentication
        assert response.status_code in [401, 403, 405, 501]


class TestAPIResponseValidation:
    """Test API response format and validation"""

    @pytest.fixture
    async def client(self):
        """HTTP client for testing"""
        async with httpx.AsyncClient(
            base_url="http://localhost:8000", timeout=30.0
        ) as client:
            yield client

    @pytest.mark.asyncio
    async def test_response_headers(self, client: httpx.AsyncClient):
        """Test that responses have proper headers"""
        endpoints = [
            "/api/monitoring/health",
            "/api/monitoring/metrics",
            "/api/cache/status",
            "/api/performance/status",
        ]

        for endpoint in endpoints:
            response = await client.get(endpoint)

            if response.status_code == 200:
                # Should have proper content type for JSON
                if response.headers.get("content-type"):
                    assert "application/json" in response.headers["content-type"]

                # Should be valid JSON
                try:
                    response.json()
                except json.JSONDecodeError:
                    pytest.fail(f"Invalid JSON response from {endpoint}")

    @pytest.mark.asyncio
    async def test_error_response_format(self, client: httpx.AsyncClient):
        """Test error response format"""
        # Test non-existent endpoint
        response = await client.get("/api/nonexistent/endpoint")

        assert response.status_code == 404

        # If it returns JSON, validate error format
        if response.headers.get("content-type", "").startswith("application/json"):
            try:
                data = response.json()
                # Common error response fields
                error_fields = ["error", "message", "detail"]
                assert any(field in data for field in error_fields)
            except json.JSONDecodeError:
                # Non-JSON error responses are also acceptable
                pass

    @pytest.mark.asyncio
    async def test_cors_headers(self, client: httpx.AsyncClient):
        """Test CORS headers if applicable"""
        response = await client.options("/api/monitoring/health")

        # OPTIONS should be handled
        assert response.status_code in [200, 204, 405]

        # Check for CORS headers if present
        cors_headers = [
            "access-control-allow-origin",
            "access-control-allow-methods",
            "access-control-allow-headers",
        ]

        has_cors = any(header in response.headers for header in cors_headers)
        if has_cors:
            logger.info("CORS headers detected and available")


class TestAPIPerformance:
    """Test API endpoint performance"""

    @pytest.fixture
    async def client(self):
        """HTTP client for testing"""
        async with httpx.AsyncClient(
            base_url="http://localhost:8000", timeout=30.0
        ) as client:
            yield client

    @pytest.mark.asyncio
    async def test_response_times(self, client: httpx.AsyncClient):
        """Test API response times meet performance targets"""
        endpoints = [
            "/api/monitoring/health",
            "/api/monitoring/metrics",
            "/api/cache/status",
            "/api/performance/status",
        ]

        # Performance targets
        health_target = 1.0  # 1 second for health check
        metrics_target = 5.0  # 5 seconds for metrics

        for endpoint in endpoints:
            start_time = time.time()
            response = await client.get(endpoint)
            end_time = time.time()

            duration = end_time - start_time

            if response.status_code == 200:
                # Health endpoint should be fast
                if "health" in endpoint:
                    assert (
                        duration < health_target
                    ), f"Health endpoint too slow: {duration:.2f}s"
                else:
                    assert (
                        duration < metrics_target
                    ), f"Endpoint too slow: {endpoint} - {duration:.2f}s"

                logger.info(f"Endpoint {endpoint}: {duration:.3f}s")

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, client: httpx.AsyncClient):
        """Test handling of concurrent requests"""
        endpoint = "/api/monitoring/health"
        concurrent_requests = 10

        # Create concurrent requests
        tasks = [client.get(endpoint) for _ in range(concurrent_requests)]

        start_time = time.time()
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()

        total_time = end_time - start_time

        # Analyze responses
        successful_responses = 0
        for response in responses:
            if isinstance(response, httpx.Response) and response.status_code == 200:
                successful_responses += 1
            elif isinstance(response, Exception):
                logger.warning(f"Request failed: {response}")

        # Should handle concurrent requests reasonably well
        success_rate = successful_responses / concurrent_requests
        assert (
            success_rate >= 0.8
        ), f"Low success rate for concurrent requests: {success_rate:.1%}"

        # Should complete in reasonable time
        assert (
            total_time < 10.0
        ), f"Concurrent requests took too long: {total_time:.2f}s"

        logger.info(
            f"Concurrent requests: {successful_responses}/{concurrent_requests} successful in {total_time:.2f}s"
        )

    @pytest.mark.asyncio
    async def test_rate_limiting_behavior(self, client: httpx.AsyncClient):
        """Test rate limiting behavior if implemented"""
        endpoint = "/api/monitoring/health"

        # Send many rapid requests
        responses = []
        for i in range(50):
            try:
                response = await client.get(endpoint)
                responses.append(response.status_code)

                # Small delay to avoid overwhelming
                await asyncio.sleep(0.01)
            except Exception as e:
                logger.warning(f"Request {i} failed: {e}")
                responses.append(0)

        # Analyze response codes
        success_codes = [code for code in responses if code == 200]
        rate_limit_codes = [code for code in responses if code == 429]

        # If rate limiting is implemented, should see 429 responses
        if rate_limit_codes:
            logger.info(
                f"Rate limiting detected: {len(rate_limit_codes)} requests rate limited"
            )

        # Should have some successful responses
        assert len(success_codes) > 0, "No successful responses received"


class TestAPIDocumentation:
    """Test API documentation endpoints"""

    @pytest.fixture
    async def client(self):
        """HTTP client for testing"""
        async with httpx.AsyncClient(
            base_url="http://localhost:8000", timeout=30.0
        ) as client:
            yield client

    @pytest.mark.asyncio
    async def test_openapi_docs(self, client: httpx.AsyncClient):
        """Test OpenAPI documentation endpoints"""
        # Test OpenAPI JSON endpoint
        response = await client.get("/openapi.json")
        if response.status_code == 200:
            data = response.json()
            assert "openapi" in data or "swagger" in data
            assert "info" in data
            assert "paths" in data

    @pytest.mark.asyncio
    async def test_swagger_ui(self, client: httpx.AsyncClient):
        """Test Swagger UI endpoint"""
        response = await client.get("/docs")

        # Should either have docs or redirect
        assert response.status_code in [200, 301, 302, 404]

        if response.status_code == 200:
            # Should be HTML content
            assert "text/html" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_redoc_ui(self, client: httpx.AsyncClient):
        """Test ReDoc UI endpoint"""
        response = await client.get("/redoc")

        # Should either have docs or redirect
        assert response.status_code in [200, 301, 302, 404]

        if response.status_code == 200:
            # Should be HTML content
            assert "text/html" in response.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_api_comprehensive_validation():
    """Comprehensive API validation test"""

    async with httpx.AsyncClient(
        base_url="http://localhost:8000", timeout=30.0
    ) as client:
        # Test core endpoints availability
        core_endpoints = [
            "/api/monitoring/health",
            "/api/monitoring/metrics",
            "/api/cache/status",
            "/api/performance/status",
        ]

        available_endpoints = []

        for endpoint in core_endpoints:
            try:
                response = await client.get(endpoint)
                if response.status_code == 200:
                    available_endpoints.append(endpoint)

                    # Validate JSON response
                    try:
                        data = response.json()
                        assert isinstance(data, dict)
                    except json.JSONDecodeError:
                        logger.warning(f"Non-JSON response from {endpoint}")

            except Exception as e:
                logger.warning(f"Failed to test endpoint {endpoint}: {e}")

        # Should have at least health endpoint working
        assert len(available_endpoints) > 0, "No core endpoints are available"
        assert (
            "/api/monitoring/health" in available_endpoints
        ), "Health endpoint not available"

        logger.info(f"Available endpoints: {available_endpoints}")


# Integration with existing test framework
if __name__ == "__main__":
    # Run basic endpoint tests
    import asyncio

    async def run_basic_tests():
        async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
            # Test health endpoint
            response = await client.get("/api/monitoring/health")
            print(f"Health endpoint: {response.status_code}")

            # Test metrics endpoint
            response = await client.get("/api/monitoring/metrics")
            print(f"Metrics endpoint: {response.status_code}")

            # Test cache endpoint
            response = await client.get("/api/cache/status")
            print(f"Cache endpoint: {response.status_code}")

    asyncio.run(run_basic_tests())
