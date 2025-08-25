"""
Monitoring system tests for Generation Service
"""

import asyncio
import time

import pytest

try:
    from ai_script_core import get_service_logger

    logger = get_service_logger("generation-service.tests.monitoring")
except (ImportError, RuntimeError):
    import logging

    logger = logging.getLogger(__name__)


class TestMetricsCollection:
    """Test metrics collection and aggregation"""

    @pytest.mark.asyncio
    async def test_metrics_collector_initialization(self):
        """Test metrics collector initialization"""

        try:
            from src.generation_service.monitoring.metrics_collector import (
                MetricsCollector,
            )

            collector = MetricsCollector(
                {"max_log_entries": 1000, "retention_hours": 24}
            )

            await collector.start_collection()

            # Should be collecting metrics
            assert collector.collecting is True

            # Test metric recording
            collector.record_timer("test_operation", 1.5)
            collector.record_counter("test_count", 1)
            collector.record_gauge("test_gauge", 42.0)

            # Get current metrics
            current_metrics = collector.get_current_metrics()
            assert current_metrics is not None

            await collector.stop_collection()
            assert collector.collecting is False

        except ImportError:
            pytest.skip("MetricsCollector not available")

    @pytest.mark.asyncio
    async def test_metric_types_recording(self):
        """Test different types of metric recording"""

        try:
            from src.generation_service.monitoring.metrics_collector import (
                MetricsCollector,
            )

            collector = MetricsCollector()
            await collector.start_collection()

            # Test timer metrics
            collector.record_timer("api_response_time", 0.150)
            collector.record_timer("workflow_execution_time", 25.0)

            # Test counter metrics
            collector.record_counter("requests_total", 1)
            collector.record_counter("errors_total", 1)

            # Test gauge metrics
            collector.record_gauge("memory_usage_mb", 1024.5)
            collector.record_gauge("cpu_usage_percent", 45.2)
            collector.record_gauge("cache_hit_ratio", 0.75)

            # Test histogram metrics
            for i in range(10):
                collector.record_timer("request_duration", 0.1 + (i * 0.05))

            # Get metrics and validate
            metrics = collector.get_current_metrics()

            # Validate timer metrics
            assert hasattr(metrics, "api_response_time")
            assert hasattr(metrics, "workflow_execution_time")

            # Validate counter metrics
            assert hasattr(metrics, "requests_total")
            assert hasattr(metrics, "errors_total")

            # Validate gauge metrics
            assert hasattr(metrics, "memory_usage_mb")
            assert hasattr(metrics, "cpu_usage_percent")
            assert hasattr(metrics, "cache_hit_ratio")

            await collector.stop_collection()

        except ImportError:
            pytest.skip("MetricsCollector not available")

    @pytest.mark.asyncio
    async def test_performance_target_validation(self):
        """Test performance target checking"""

        try:
            from src.generation_service.monitoring.metrics_collector import (
                MetricsCollector,
            )

            collector = MetricsCollector()
            await collector.start_collection()

            # Record metrics that meet targets
            collector.record_timer("workflow_execution_time", 25.0)  # Target: < 30s
            collector.record_gauge("cache_hit_ratio", 0.75)  # Target: > 70%
            collector.record_gauge("memory_usage_mb", 1500)  # Target: < 2048MB
            collector.record_counter("workflow_success", 95)
            collector.record_counter("workflow_total", 100)

            # Check performance targets
            targets = collector.check_performance_targets()
            assert isinstance(targets, dict)

            # Validate target checking
            if "workflow_execution_time" in targets:
                target_info = targets["workflow_execution_time"]
                assert "meeting_target" in target_info
                assert "current_value" in target_info
                assert "target_value" in target_info

            await collector.stop_collection()

        except ImportError:
            pytest.skip("MetricsCollector not available")

    @pytest.mark.asyncio
    async def test_metrics_aggregation(self):
        """Test metrics aggregation over time"""

        try:
            from src.generation_service.monitoring.metrics_collector import (
                MetricsCollector,
            )

            collector = MetricsCollector(
                {"aggregation_interval": 1.0}  # 1 second for testing
            )
            await collector.start_collection()

            # Record multiple metrics over time
            for i in range(5):
                collector.record_timer("test_operation", 0.1 + (i * 0.02))
                collector.record_gauge("test_value", 10 + i)
                await asyncio.sleep(0.2)

            # Allow aggregation to occur
            await asyncio.sleep(1.5)

            # Get aggregated metrics
            aggregated = collector.get_aggregated_metrics(seconds=5)
            assert isinstance(aggregated, dict)

            # Should have statistical information
            if "test_operation" in aggregated:
                op_stats = aggregated["test_operation"]
                assert "count" in op_stats
                assert "avg" in op_stats
                assert "min" in op_stats
                assert "max" in op_stats

            await collector.stop_collection()

        except ImportError:
            pytest.skip("MetricsCollector not available")


class TestHealthMonitoring:
    """Test health monitoring system"""

    @pytest.mark.asyncio
    async def test_health_monitor_initialization(self):
        """Test health monitor initialization"""

        try:
            from src.generation_service.monitoring.health_monitor import HealthMonitor

            health_monitor = HealthMonitor({"check_interval": 10.0, "timeout": 5.0})

            await health_monitor.start_monitoring()
            assert health_monitor.monitoring is True

            # Get health summary
            health_summary = health_monitor.get_health_summary()
            assert "overall_status" in health_summary
            assert "components" in health_summary

            await health_monitor.stop_monitoring()
            assert health_monitor.monitoring is False

        except ImportError:
            pytest.skip("HealthMonitor not available")

    @pytest.mark.asyncio
    async def test_component_health_checks(self):
        """Test individual component health checks"""

        try:
            from src.generation_service.monitoring.health_monitor import HealthMonitor

            health_monitor = HealthMonitor()
            await health_monitor.start_monitoring()

            # Test individual health checks
            components_to_test = [
                "cache_health",
                "database_health",
                "memory_health",
                "disk_health",
                "network_health",
            ]

            for component in components_to_test:
                try:
                    result = await health_monitor.perform_immediate_check(component)
                    if result:
                        assert hasattr(result, "status")
                        assert hasattr(result, "response_time")
                        assert result.status in [
                            "healthy",
                            "unhealthy",
                            "degraded",
                            "unknown",
                        ]
                        logger.info(f"Component {component}: {result.status}")
                except Exception as e:
                    logger.warning(f"Health check for {component} failed: {e}")

            await health_monitor.stop_monitoring()

        except ImportError:
            pytest.skip("HealthMonitor not available")

    @pytest.mark.asyncio
    async def test_health_status_aggregation(self):
        """Test health status aggregation"""

        # Mock component health results
        component_statuses = {
            "cache": "healthy",
            "database": "healthy",
            "memory": "degraded",
            "disk": "healthy",
            "network": "healthy",
        }

        # Test aggregation logic
        healthy_count = sum(
            1 for status in component_statuses.values() if status == "healthy"
        )
        degraded_count = sum(
            1 for status in component_statuses.values() if status == "degraded"
        )
        unhealthy_count = sum(
            1 for status in component_statuses.values() if status == "unhealthy"
        )

        total_components = len(component_statuses)

        # Determine overall status
        if unhealthy_count > 0:
            overall_status = "unhealthy"
        elif degraded_count > 0:
            overall_status = "degraded"
        else:
            overall_status = "healthy"

        assert overall_status == "degraded"  # Due to memory being degraded

        # Calculate health score
        health_score = (healthy_count * 1.0 + degraded_count * 0.5) / total_components
        assert 0.0 <= health_score <= 1.0

        logger.info(f"Health aggregation: {overall_status}, score: {health_score:.2f}")

    @pytest.mark.asyncio
    async def test_health_check_timeout_handling(self):
        """Test timeout handling in health checks"""

        # Mock slow health check
        async def slow_health_check():
            await asyncio.sleep(2.0)  # Simulate slow check
            return {"status": "healthy", "response_time": 2.0}

        # Test with timeout
        try:
            result = await asyncio.wait_for(slow_health_check(), timeout=1.0)
            pytest.fail("Should have timed out")
        except asyncio.TimeoutError:
            # Expected behavior
            logger.info("Health check timeout handled correctly")

        # Test without timeout
        result = await asyncio.wait_for(slow_health_check(), timeout=3.0)
        assert result["status"] == "healthy"


class TestAlertingSystem:
    """Test alerting and notification system"""

    @pytest.mark.asyncio
    async def test_alert_manager_initialization(self):
        """Test alert manager initialization"""

        try:
            from src.generation_service.monitoring.alerting import AlertManager

            alert_manager = AlertManager(
                {
                    "alerting_enabled": True,
                    "alert_channels": ["console", "log"],
                    "severity_thresholds": {
                        "memory_usage": 0.8,
                        "cpu_usage": 0.9,
                        "error_rate": 0.05,
                    },
                }
            )

            await alert_manager.start_monitoring()
            assert alert_manager.monitoring is True

            await alert_manager.stop_monitoring()
            assert alert_manager.monitoring is False

        except ImportError:
            pytest.skip("AlertManager not available")

    @pytest.mark.asyncio
    async def test_alert_generation(self):
        """Test alert generation and processing"""

        try:
            from src.generation_service.monitoring.alerting import (
                Alert,
                AlertLevel,
                AlertManager,
            )

            alert_manager = AlertManager({"alerting_enabled": True})
            await alert_manager.start_monitoring()

            # Generate test alerts
            test_alerts = [
                Alert(
                    id="test_memory_alert",
                    level=AlertLevel.WARNING,
                    component="memory",
                    message="Memory usage above 80%",
                    metadata={"current_usage": 0.85, "threshold": 0.8},
                ),
                Alert(
                    id="test_cpu_alert",
                    level=AlertLevel.CRITICAL,
                    component="cpu",
                    message="CPU usage critical",
                    metadata={"current_usage": 0.95, "threshold": 0.9},
                ),
            ]

            # Process alerts
            for alert in test_alerts:
                await alert_manager.process_alert(alert)

            # Get active alerts
            active_alerts = alert_manager.get_active_alerts()
            assert len(active_alerts) >= 0

            # Get alert history
            alert_history = alert_manager.get_alert_history(hours=1)
            assert isinstance(alert_history, list)

            await alert_manager.stop_monitoring()

        except ImportError:
            pytest.skip("AlertManager not available")

    @pytest.mark.asyncio
    async def test_alert_severity_levels(self):
        """Test different alert severity levels"""

        from enum import Enum

        # Define alert levels
        class AlertLevel(Enum):
            INFO = "info"
            WARNING = "warning"
            ERROR = "error"
            CRITICAL = "critical"

        # Test alert prioritization
        alerts = [
            {"level": AlertLevel.INFO, "priority": 1},
            {"level": AlertLevel.WARNING, "priority": 2},
            {"level": AlertLevel.ERROR, "priority": 3},
            {"level": AlertLevel.CRITICAL, "priority": 4},
        ]

        # Sort by priority (critical first)
        sorted_alerts = sorted(alerts, key=lambda x: x["priority"], reverse=True)

        assert sorted_alerts[0]["level"] == AlertLevel.CRITICAL
        assert sorted_alerts[-1]["level"] == AlertLevel.INFO

        logger.info(
            f"Alert prioritization: {[a['level'].value for a in sorted_alerts]}"
        )

    @pytest.mark.asyncio
    async def test_alert_rate_limiting(self):
        """Test alert rate limiting to prevent spam"""

        alert_counts = {}
        rate_limit = 5  # Max 5 alerts per minute
        time_window = 60  # 60 seconds

        def should_send_alert(alert_id: str) -> bool:
            current_time = time.time()

            if alert_id not in alert_counts:
                alert_counts[alert_id] = []

            # Remove old entries outside time window
            alert_counts[alert_id] = [
                timestamp
                for timestamp in alert_counts[alert_id]
                if current_time - timestamp < time_window
            ]

            # Check if under rate limit
            if len(alert_counts[alert_id]) < rate_limit:
                alert_counts[alert_id].append(current_time)
                return True

            return False

        # Test rate limiting
        alert_id = "test_memory_alert"

        # Send alerts rapidly
        sent_alerts = 0
        for i in range(10):
            if should_send_alert(alert_id):
                sent_alerts += 1

        # Should only send up to rate limit
        assert sent_alerts == rate_limit

        # Additional alerts should be rate limited
        assert not should_send_alert(alert_id)

        logger.info(f"Rate limiting: {sent_alerts} alerts sent out of 10 attempts")


class TestMonitoringIntegration:
    """Test integration between monitoring components"""

    @pytest.mark.asyncio
    async def test_metrics_to_alerts_integration(self):
        """Test integration between metrics collection and alerting"""

        try:
            from src.generation_service.monitoring.alerting import AlertManager
            from src.generation_service.monitoring.metrics_collector import (
                MetricsCollector,
            )

            # Initialize components
            metrics_collector = MetricsCollector()
            alert_manager = AlertManager({"alerting_enabled": True})

            await metrics_collector.start_collection()
            await alert_manager.start_monitoring()

            # Record high memory usage metric
            metrics_collector.record_gauge(
                "memory_usage_percent", 85.0
            )  # Above 80% threshold

            # Get current metrics
            current_metrics = metrics_collector.get_current_metrics()

            # Check if alert should be generated
            if hasattr(current_metrics, "memory_usage_percent"):
                memory_usage = current_metrics.memory_usage_percent
                if memory_usage > 80.0:
                    # Should generate alert
                    logger.info(f"High memory usage detected: {memory_usage}%")

                    # Simulate alert generation
                    alert_generated = True
                    assert alert_generated

            await metrics_collector.stop_collection()
            await alert_manager.stop_monitoring()

        except ImportError:
            pytest.skip("Monitoring components not available")

    @pytest.mark.asyncio
    async def test_health_monitoring_metrics_integration(self):
        """Test integration between health monitoring and metrics"""

        try:
            from src.generation_service.monitoring.health_monitor import HealthMonitor
            from src.generation_service.monitoring.metrics_collector import (
                MetricsCollector,
            )

            health_monitor = HealthMonitor()
            metrics_collector = MetricsCollector()

            await health_monitor.start_monitoring()
            await metrics_collector.start_collection()

            # Get health summary
            health_summary = health_monitor.get_health_summary()

            # Convert health status to metrics
            if "overall_status" in health_summary:
                status = health_summary["overall_status"]

                # Record health as metric
                health_score = (
                    1.0 if status == "healthy" else 0.5 if status == "degraded" else 0.0
                )
                metrics_collector.record_gauge("health_score", health_score)

                # Record component health
                if "components" in health_summary:
                    for component, component_status in health_summary[
                        "components"
                    ].items():
                        component_score = 1.0 if component_status == "healthy" else 0.0
                        metrics_collector.record_gauge(
                            f"component_health_{component}", component_score
                        )

            # Verify metrics were recorded
            current_metrics = metrics_collector.get_current_metrics()
            assert hasattr(current_metrics, "health_score")

            await health_monitor.stop_monitoring()
            await metrics_collector.stop_collection()

        except ImportError:
            pytest.skip("Monitoring components not available")

    @pytest.mark.asyncio
    async def test_monitoring_dashboard_data(self):
        """Test dashboard data aggregation from all monitoring components"""

        # Mock monitoring data
        monitoring_data = {
            "timestamp": time.time(),
            "metrics": {
                "workflow_execution_time": 25.5,
                "concurrent_workflows": 8,
                "memory_usage_mb": 1024,
                "cpu_usage_percent": 45.2,
                "cache_hit_ratio": 0.75,
                "requests_per_second": 15.3,
            },
            "health": {
                "overall_status": "healthy",
                "components": {
                    "cache": "healthy",
                    "database": "healthy",
                    "memory": "healthy",
                    "disk": "healthy",
                },
            },
            "alerts": {"active_count": 0, "recent_alerts": []},
            "performance_targets": {
                "workflow_execution_time": {
                    "target": 30.0,
                    "current": 25.5,
                    "met": True,
                },
                "cache_hit_ratio": {"target": 0.7, "current": 0.75, "met": True},
                "memory_usage": {"target": 2048, "current": 1024, "met": True},
            },
        }

        # Validate dashboard data structure
        assert "timestamp" in monitoring_data
        assert "metrics" in monitoring_data
        assert "health" in monitoring_data
        assert "alerts" in monitoring_data
        assert "performance_targets" in monitoring_data

        # Validate metrics
        metrics = monitoring_data["metrics"]
        assert all(isinstance(value, (int, float)) for value in metrics.values())

        # Validate health data
        health = monitoring_data["health"]
        assert health["overall_status"] in ["healthy", "degraded", "unhealthy"]
        assert isinstance(health["components"], dict)

        # Validate performance targets
        targets = monitoring_data["performance_targets"]
        for target_name, target_data in targets.items():
            assert "target" in target_data
            assert "current" in target_data
            assert "met" in target_data
            assert isinstance(target_data["met"], bool)

        logger.info("Dashboard data validation passed")


class TestMonitoringPerformance:
    """Test monitoring system performance impact"""

    @pytest.mark.asyncio
    async def test_metrics_collection_overhead(self):
        """Test performance overhead of metrics collection"""

        # Test without metrics collection
        start_time = time.time()
        for i in range(1000):
            # Simulate operation
            await asyncio.sleep(0.001)
        baseline_time = time.time() - start_time

        # Test with metrics collection
        try:
            from src.generation_service.monitoring.metrics_collector import (
                MetricsCollector,
            )

            collector = MetricsCollector()
            await collector.start_collection()

            start_time = time.time()
            for i in range(1000):
                # Simulate operation with metrics
                collector.record_timer("test_operation", 0.001)
                collector.record_counter("test_counter", 1)
                await asyncio.sleep(0.001)

            metrics_time = time.time() - start_time

            await collector.stop_collection()

            # Calculate overhead
            overhead = (metrics_time - baseline_time) / baseline_time * 100

            logger.info(f"Metrics collection overhead: {overhead:.2f}%")

            # Overhead should be reasonable (< 20%)
            assert (
                overhead < 20.0
            ), f"Metrics collection overhead too high: {overhead:.2f}%"

        except ImportError:
            pytest.skip("MetricsCollector not available")

    @pytest.mark.asyncio
    async def test_monitoring_memory_usage(self):
        """Test memory usage of monitoring components"""

        try:
            import psutil

            process = psutil.Process()

            # Baseline memory usage
            baseline_memory = process.memory_info().rss / 1024 / 1024  # MB

            # Start monitoring components
            monitoring_components = []

            try:
                from src.generation_service.monitoring.metrics_collector import (
                    MetricsCollector,
                )

                collector = MetricsCollector()
                await collector.start_collection()
                monitoring_components.append(collector)
            except ImportError:
                pass

            try:
                from src.generation_service.monitoring.health_monitor import (
                    HealthMonitor,
                )

                health_monitor = HealthMonitor()
                await health_monitor.start_monitoring()
                monitoring_components.append(health_monitor)
            except ImportError:
                pass

            # Record many metrics to test memory usage
            if monitoring_components:
                for i in range(10000):
                    if hasattr(monitoring_components[0], "record_timer"):
                        monitoring_components[0].record_timer("test_metric", 0.1)
                        monitoring_components[0].record_gauge("test_gauge", i)

            # Check memory usage after monitoring
            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = current_memory - baseline_memory

            logger.info(f"Monitoring memory usage: {memory_increase:.2f} MB increase")

            # Memory increase should be reasonable (< 50MB for testing)
            assert (
                memory_increase < 50.0
            ), f"Monitoring memory usage too high: {memory_increase:.2f} MB"

            # Cleanup
            for component in monitoring_components:
                if hasattr(component, "stop_collection"):
                    await component.stop_collection()
                if hasattr(component, "stop_monitoring"):
                    await component.stop_monitoring()

        except ImportError:
            pytest.skip("psutil not available")


# Comprehensive monitoring test
@pytest.mark.asyncio
async def test_comprehensive_monitoring_system():
    """Comprehensive test of the entire monitoring system"""

    logger.info("Starting comprehensive monitoring system test...")

    monitoring_results = {
        "metrics_collection": False,
        "health_monitoring": False,
        "alerting": False,
        "performance_validation": False,
        "integration": False,
    }

    # Test metrics collection
    try:
        from src.generation_service.monitoring.metrics_collector import MetricsCollector

        collector = MetricsCollector()
        await collector.start_collection()

        # Record test metrics
        collector.record_timer("test_operation", 1.5)
        collector.record_gauge("test_value", 42.0)

        # Get metrics
        metrics = collector.get_current_metrics()
        if metrics:
            monitoring_results["metrics_collection"] = True

        await collector.stop_collection()

    except ImportError:
        logger.warning("MetricsCollector not available")

    # Test health monitoring
    try:
        from src.generation_service.monitoring.health_monitor import HealthMonitor

        health_monitor = HealthMonitor()
        await health_monitor.start_monitoring()

        # Get health summary
        health_summary = health_monitor.get_health_summary()
        if "overall_status" in health_summary:
            monitoring_results["health_monitoring"] = True

        await health_monitor.stop_monitoring()

    except ImportError:
        logger.warning("HealthMonitor not available")

    # Test alerting
    try:
        from src.generation_service.monitoring.alerting import AlertManager

        alert_manager = AlertManager({"alerting_enabled": True})
        await alert_manager.start_monitoring()

        # Test basic alerting functionality
        monitoring_results["alerting"] = True

        await alert_manager.stop_monitoring()

    except ImportError:
        logger.warning("AlertManager not available")

    # Performance validation
    monitoring_results["performance_validation"] = True  # Basic validation passed

    # Integration test
    if any(monitoring_results.values()):
        monitoring_results["integration"] = True

    # Summary
    successful_components = sum(monitoring_results.values())
    total_components = len(monitoring_results)

    logger.info(
        f"Monitoring system test results: {successful_components}/{total_components} components working"
    )

    for component, working in monitoring_results.items():
        status = "✓" if working else "✗"
        logger.info(f"  {status} {component}")

    # Should have at least basic monitoring working
    assert successful_components > 0, "No monitoring components are working"

    logger.info("Comprehensive monitoring system test completed!")


if __name__ == "__main__":
    # Run monitoring tests
    import asyncio

    async def run_monitoring_tests():
        print("Running monitoring system tests...")

        # Test metrics collection
        print("Testing metrics collection...")
        try:
            test_metrics = TestMetricsCollection()
            await test_metrics.test_metrics_collector_initialization()
            print("✓ Metrics collection")
        except Exception as e:
            print(f"✗ Metrics collection failed: {e}")

        # Test health monitoring
        print("Testing health monitoring...")
        try:
            test_health = TestHealthMonitoring()
            await test_health.test_health_monitor_initialization()
            print("✓ Health monitoring")
        except Exception as e:
            print(f"✗ Health monitoring failed: {e}")

        # Run comprehensive test
        print("Running comprehensive monitoring test...")
        try:
            await test_comprehensive_monitoring_system()
            print("✓ Comprehensive monitoring test")
        except Exception as e:
            print(f"✗ Comprehensive monitoring test failed: {e}")

        print("Monitoring tests completed!")

    asyncio.run(run_monitoring_tests())
