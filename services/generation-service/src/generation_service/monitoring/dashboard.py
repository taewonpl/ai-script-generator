"""
Monitoring dashboard for real-time performance visualization
"""

import asyncio
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any

# Import Core Module components
try:
    from ai_script_core import (
        get_service_logger,
        utc_now,
    )

    CORE_AVAILABLE = True
    logger = get_service_logger("generation-service.dashboard")
except (ImportError, RuntimeError):
    CORE_AVAILABLE = False
    import logging

    logger = logging.getLogger(__name__)

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


@dataclass
class DashboardMetric:
    """Dashboard metric display configuration"""

    name: str
    display_name: str
    unit: str
    format_type: str = "number"  # number, percentage, duration, bytes
    chart_type: str = "line"  # line, bar, gauge, counter
    color: str = "#007bff"
    target: float | None = None
    warning_threshold: float | None = None
    critical_threshold: float | None = None


@dataclass
class ChartData:
    """Chart data structure"""

    labels: list[str]
    datasets: list[dict[str, Any]]
    options: dict[str, Any]


class MonitoringDashboard:
    """
    Real-time monitoring dashboard with performance visualizations

    Features:
    - Real-time metric visualization
    - Performance target tracking
    - Health status overview
    - Alert status display
    - Historical trend analysis
    - Custom dashboard layouts
    """

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}

        # Dashboard configuration
        self.refresh_interval = self.config.get("refresh_interval", 5.0)
        self.max_data_points = self.config.get("max_data_points", 100)
        self.time_window_hours = self.config.get("time_window_hours", 1)

        # Dashboard metrics configuration
        self.dashboard_metrics = self._initialize_dashboard_metrics()

        # Data storage for real-time updates
        self._chart_data: dict[str, ChartData] = {}
        self._latest_values: dict[str, float] = {}

        # Dashboard state
        self._dashboard_enabled = False
        self._update_task: asyncio.Task[None] | None = None

        # WebSocket connections for real-time updates
        self._websocket_connections: list[Any] = []

    def _initialize_dashboard_metrics(self) -> list[DashboardMetric]:
        """Initialize dashboard metrics configuration"""

        return [
            # Workflow performance metrics
            DashboardMetric(
                name="workflow_execution_time",
                display_name="Workflow Execution Time",
                unit="seconds",
                format_type="duration",
                chart_type="line",
                color="#007bff",
                target=30.0,
                warning_threshold=45.0,
                critical_threshold=60.0,
            ),
            DashboardMetric(
                name="workflow_success_rate",
                display_name="Workflow Success Rate",
                unit="%",
                format_type="percentage",
                chart_type="gauge",
                color="#28a745",
                target=95.0,
                warning_threshold=90.0,
                critical_threshold=85.0,
            ),
            # AI API metrics
            DashboardMetric(
                name="ai_api_response_time",
                display_name="AI API Response Time",
                unit="seconds",
                format_type="duration",
                chart_type="line",
                color="#17a2b8",
                target=5.0,
                warning_threshold=10.0,
                critical_threshold=15.0,
            ),
            DashboardMetric(
                name="token_usage_per_request",
                display_name="Token Usage per Request",
                unit="tokens",
                format_type="number",
                chart_type="bar",
                color="#6f42c1",
            ),
            # Cache metrics
            DashboardMetric(
                name="cache_hit_ratio",
                display_name="Cache Hit Ratio",
                unit="%",
                format_type="percentage",
                chart_type="gauge",
                color="#fd7e14",
                target=70.0,
                warning_threshold=60.0,
                critical_threshold=50.0,
            ),
            DashboardMetric(
                name="cache_response_time",
                display_name="Cache Response Time",
                unit="ms",
                format_type="duration",
                chart_type="line",
                color="#20c997",
                target=100.0,
                warning_threshold=200.0,
                critical_threshold=500.0,
            ),
            # System metrics
            DashboardMetric(
                name="concurrent_workflows",
                display_name="Concurrent Workflows",
                unit="count",
                format_type="number",
                chart_type="counter",
                color="#e83e8c",
                target=20,
                warning_threshold=15,
                critical_threshold=18,
            ),
            DashboardMetric(
                name="memory_usage_mb",
                display_name="Memory Usage",
                unit="MB",
                format_type="bytes",
                chart_type="line",
                color="#dc3545",
                target=2048,
                warning_threshold=1600,
                critical_threshold=1900,
            ),
            DashboardMetric(
                name="cpu_usage_percent",
                display_name="CPU Usage",
                unit="%",
                format_type="percentage",
                chart_type="gauge",
                color="#ffc107",
                warning_threshold=80.0,
                critical_threshold=95.0,
            ),
            # API throughput metrics
            DashboardMetric(
                name="api_throughput_rps",
                display_name="API Throughput",
                unit="req/s",
                format_type="number",
                chart_type="line",
                color="#198754",
            ),
            DashboardMetric(
                name="api_latency_p95",
                display_name="API Latency (P95)",
                unit="ms",
                format_type="duration",
                chart_type="line",
                color="#0d6efd",
            ),
        ]

    async def start_dashboard(self) -> None:
        """Start dashboard data updates"""

        if self._dashboard_enabled:
            return

        self._dashboard_enabled = True
        self._update_task = asyncio.create_task(self._update_worker())

        logger.info("MonitoringDashboard started")

    async def stop_dashboard(self) -> None:
        """Stop dashboard updates"""

        self._dashboard_enabled = False

        if self._update_task and not self._update_task.done():
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass

        logger.info("MonitoringDashboard stopped")

    async def _update_worker(self) -> None:
        """Background worker for dashboard data updates"""

        while self._dashboard_enabled:
            try:
                # Update all dashboard data
                await self._update_dashboard_data()

                # Send updates to WebSocket connections
                await self._broadcast_updates()

                # Wait for next update
                await asyncio.sleep(self.refresh_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Dashboard update worker error: {e}")
                await asyncio.sleep(self.refresh_interval)

    async def _update_dashboard_data(self) -> None:
        """Update dashboard data from various sources"""

        try:
            # Get current metrics
            current_metrics = await self._get_current_metrics()

            # Update chart data for each metric
            for metric_config in self.dashboard_metrics:
                if metric_config.name in current_metrics:
                    value = current_metrics[metric_config.name]
                    await self._update_metric_chart_data(metric_config, value)

        except Exception as e:
            logger.error(f"Failed to update dashboard data: {e}")

    async def _get_current_metrics(self) -> dict[str, float]:
        """Get current metrics from metrics collector"""

        try:
            from .metrics_collector import get_metrics_collector

            collector = get_metrics_collector()
            if not collector:
                return {}

            current_metrics = collector.get_current_metrics()
            return current_metrics.to_dict()

        except Exception as e:
            logger.error(f"Failed to get current metrics: {e}")
            return {}

    async def _update_metric_chart_data(
        self, metric_config: DashboardMetric, value: float
    ) -> None:
        """Update chart data for a specific metric"""

        metric_name = metric_config.name

        # Initialize chart data if not exists
        if metric_name not in self._chart_data:
            self._chart_data[metric_name] = ChartData(
                labels=[],
                datasets=[
                    {
                        "label": metric_config.display_name,
                        "data": [],
                        "borderColor": metric_config.color,
                        "backgroundColor": metric_config.color + "20",
                        "fill": True,
                    }
                ],
                options=self._get_chart_options(metric_config),
            )

        chart_data = self._chart_data[metric_name]

        # Add new data point
        now = utc_now() if CORE_AVAILABLE else datetime.now()
        timestamp = now.strftime("%H:%M:%S")

        chart_data.labels.append(timestamp)
        chart_data.datasets[0]["data"].append(value)

        # Trim data to max points
        if len(chart_data.labels) > self.max_data_points:
            chart_data.labels = chart_data.labels[-self.max_data_points :]
            chart_data.datasets[0]["data"] = chart_data.datasets[0]["data"][
                -self.max_data_points :
            ]

        # Update latest value
        self._latest_values[metric_name] = value

    def _get_chart_options(self, metric_config: DashboardMetric) -> dict[str, Any]:
        """Get chart options based on metric configuration"""

        options = {
            "responsive": True,
            "plugins": {
                "title": {"display": True, "text": metric_config.display_name},
                "legend": {"display": False},
            },
            "scales": {
                "x": {"display": True, "title": {"display": True, "text": "Time"}},
                "y": {
                    "display": True,
                    "title": {"display": True, "text": metric_config.unit},
                },
            },
        }

        # Add threshold lines if configured
        if (
            metric_config.target
            or metric_config.warning_threshold
            or metric_config.critical_threshold
        ):
            annotations = []

            if metric_config.target:
                annotations.append(
                    {
                        "type": "line",
                        "scaleID": "y",
                        "value": metric_config.target,
                        "borderColor": "#28a745",
                        "borderWidth": 2,
                        "label": {
                            "content": f"Target: {metric_config.target}",
                            "enabled": True,
                        },
                    }
                )

            if metric_config.warning_threshold:
                annotations.append(
                    {
                        "type": "line",
                        "scaleID": "y",
                        "value": metric_config.warning_threshold,
                        "borderColor": "#ffc107",
                        "borderWidth": 1,
                        "label": {
                            "content": f"Warning: {metric_config.warning_threshold}",
                            "enabled": True,
                        },
                    }
                )

            if metric_config.critical_threshold:
                annotations.append(
                    {
                        "type": "line",
                        "scaleID": "y",
                        "value": metric_config.critical_threshold,
                        "borderColor": "#dc3545",
                        "borderWidth": 1,
                        "label": {
                            "content": f"Critical: {metric_config.critical_threshold}",
                            "enabled": True,
                        },
                    }
                )

            options["plugins"]["annotation"] = {"annotations": annotations}

        return options

    async def _broadcast_updates(self) -> None:
        """Broadcast updates to WebSocket connections"""

        if not self._websocket_connections:
            return

        try:
            dashboard_data = await self.get_dashboard_data()
            message = json.dumps(
                {
                    "type": "dashboard_update",
                    "data": dashboard_data,
                    "timestamp": (
                        utc_now() if CORE_AVAILABLE else datetime.now()
                    ).isoformat(),
                }
            )

            # Send to all connected clients
            for websocket in self._websocket_connections[
                :
            ]:  # Copy list to avoid modification during iteration
                try:
                    await websocket.send(message)
                except Exception:
                    # Remove disconnected clients
                    self._websocket_connections.remove(websocket)

        except Exception as e:
            logger.error(f"Failed to broadcast dashboard updates: {e}")

    def add_websocket_connection(self, websocket: Any) -> None:
        """Add WebSocket connection for real-time updates"""
        self._websocket_connections.append(websocket)

    def remove_websocket_connection(self, websocket: Any) -> None:
        """Remove WebSocket connection"""
        if websocket in self._websocket_connections:
            self._websocket_connections.remove(websocket)

    async def get_dashboard_data(self) -> dict[str, Any]:
        """Get complete dashboard data"""

        # Get health status
        health_summary = await self._get_health_summary()

        # Get alert status
        alert_summary = await self._get_alert_summary()

        # Format chart data
        charts = {}
        for metric_config in self.dashboard_metrics:
            metric_name = metric_config.name
            if metric_name in self._chart_data:
                charts[metric_name] = {
                    "config": asdict(metric_config),
                    "data": asdict(self._chart_data[metric_name]),
                    "current_value": self._latest_values.get(metric_name, 0),
                    "status": self._get_metric_status(
                        metric_config, self._latest_values.get(metric_name, 0)
                    ),
                }

        # Performance summary
        performance_summary = await self._get_performance_summary()

        return {
            "health": health_summary,
            "alerts": alert_summary,
            "charts": charts,
            "performance": performance_summary,
            "system_info": {
                "dashboard_enabled": self._dashboard_enabled,
                "refresh_interval": self.refresh_interval,
                "connected_clients": len(self._websocket_connections),
                "last_update": (
                    utc_now() if CORE_AVAILABLE else datetime.now()
                ).isoformat(),
            },
        }

    async def _get_health_summary(self) -> dict[str, Any]:
        """Get health status summary"""

        try:
            from .health_monitor import get_health_monitor

            health_monitor = get_health_monitor()
            if not health_monitor:
                return {"status": "unknown", "message": "Health monitor not available"}

            return health_monitor.get_health_summary()

        except Exception as e:
            logger.error(f"Failed to get health summary: {e}")
            return {"status": "error", "message": f"Health check failed: {e}"}

    async def _get_alert_summary(self) -> dict[str, Any]:
        """Get alert status summary"""

        try:
            from .alerting import get_alert_manager

            alert_manager = get_alert_manager()
            if not alert_manager:
                return {"active_alerts": 0, "total_rules": 0}

            return alert_manager.get_alert_summary()

        except Exception as e:
            logger.error(f"Failed to get alert summary: {e}")
            return {"error": f"Alert summary failed: {e}"}

    async def _get_performance_summary(self) -> dict[str, Any]:
        """Get performance targets summary"""

        try:
            from .metrics_collector import get_metrics_collector

            collector = get_metrics_collector()
            if not collector:
                return {}

            target_status = collector.check_performance_targets()

            summary = {
                "targets_met": sum(
                    1 for t in target_status.values() if t["meeting_target"]
                ),
                "total_targets": len(target_status),
                "targets": target_status,
            }

            return summary

        except Exception as e:
            logger.error(f"Failed to get performance summary: {e}")
            return {}

    def _get_metric_status(self, metric_config: DashboardMetric, value: float) -> str:
        """Get status for metric value based on thresholds"""

        if metric_config.critical_threshold is not None:
            if (
                metric_config.name
                in ["workflow_execution_time", "memory_usage_mb", "cpu_usage_percent"]
                and value >= metric_config.critical_threshold
            ):
                return "critical"
            elif (
                metric_config.name in ["cache_hit_ratio", "workflow_success_rate"]
                and value <= metric_config.critical_threshold
            ):
                return "critical"

        if metric_config.warning_threshold is not None:
            if (
                metric_config.name
                in ["workflow_execution_time", "memory_usage_mb", "cpu_usage_percent"]
                and value >= metric_config.warning_threshold
            ):
                return "warning"
            elif (
                metric_config.name in ["cache_hit_ratio", "workflow_success_rate"]
                and value <= metric_config.warning_threshold
            ):
                return "warning"

        return "healthy"

    async def get_historical_data(
        self, metric_name: str, hours: int = 24
    ) -> dict[str, Any]:
        """Get historical data for specific metric"""

        try:
            from .metrics_collector import get_metrics_collector

            collector = get_metrics_collector()
            if not collector:
                return {}

            since = (utc_now() if CORE_AVAILABLE else datetime.now()) - timedelta(
                hours=hours
            )
            history = collector.get_metric_history(metric_name, since)

            # Format for charting
            labels = []
            data = []

            for entry in history:
                labels.append(entry.timestamp.strftime("%Y-%m-%d %H:%M:%S"))
                data.append(entry.value)

            return {
                "labels": labels,
                "data": data,
                "metric_name": metric_name,
                "data_points": len(data),
                "time_range_hours": hours,
            }

        except Exception as e:
            logger.error(f"Failed to get historical data for {metric_name}: {e}")
            return {}

    def generate_dashboard_html(self) -> str:
        """Generate HTML dashboard page"""

        html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Generation Service - Monitoring Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .metric-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .metric-value { font-size: 2em; font-weight: bold; margin: 10px 0; }
        .metric-status { padding: 4px 8px; border-radius: 4px; color: white; font-size: 0.8em; }
        .status-healthy { background-color: #28a745; }
        .status-warning { background-color: #ffc107; color: #000; }
        .status-critical { background-color: #dc3545; }
        .chart-container { height: 300px; }
        .alerts-panel { background: white; padding: 20px; border-radius: 8px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .alert-item { padding: 10px; margin: 5px 0; border-radius: 4px; }
        .alert-warning { background-color: #fff3cd; border-left: 4px solid #ffc107; }
        .alert-error { background-color: #f8d7da; border-left: 4px solid #dc3545; }
        .alert-critical { background-color: #f5c6cb; border-left: 4px solid #721c24; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Generation Service - Monitoring Dashboard</h1>
            <div id="system-status">
                <span id="connection-status">Connecting...</span>
                <span id="last-update"></span>
            </div>
        </div>

        <div id="alerts-panel" class="alerts-panel">
            <h3>Active Alerts</h3>
            <div id="alerts-container">No active alerts</div>
        </div>

        <div id="metrics-grid" class="metrics-grid">
            <!-- Metrics will be populated by JavaScript -->
        </div>
    </div>

    <script>
        // WebSocket connection for real-time updates
        let ws = null;
        let charts = {};

        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(protocol + '//' + window.location.host + '/ws/dashboard');

            ws.onopen = function() {
                document.getElementById('connection-status').textContent = 'Connected';
                document.getElementById('connection-status').style.color = 'green';
            };

            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                if (data.type === 'dashboard_update') {
                    updateDashboard(data.data);
                }
            };

            ws.onclose = function() {
                document.getElementById('connection-status').textContent = 'Disconnected';
                document.getElementById('connection-status').style.color = 'red';
                // Reconnect after 5 seconds
                setTimeout(connectWebSocket, 5000);
            };
        }

        function updateDashboard(data) {
            updateAlerts(data.alerts);
            updateMetrics(data.charts);
            document.getElementById('last-update').textContent = 'Last update: ' + new Date(data.system_info.last_update).toLocaleTimeString();
        }

        function updateAlerts(alertData) {
            const container = document.getElementById('alerts-container');

            if (alertData.active_alerts === 0) {
                container.innerHTML = '<div style="color: green;">✓ No active alerts</div>';
                return;
            }

            let html = '';
            alertData.recent_alerts.forEach(alert => {
                const alertClass = 'alert-' + alert.severity;
                html += '<div class="alert-item ' + alertClass + '">';
                html += '<strong>' + alert.rule_name + '</strong>: ' + alert.message;
                html += '<br><small>' + new Date(alert.triggered_at).toLocaleString() + '</small>';
                html += '</div>';
            });

            container.innerHTML = html;
        }

        function updateMetrics(chartData) {
            const grid = document.getElementById('metrics-grid');

            Object.keys(chartData).forEach(metricName => {
                const metric = chartData[metricName];

                if (!charts[metricName]) {
                    createMetricCard(grid, metricName, metric);
                } else {
                    updateChart(metricName, metric);
                }
            });
        }

        function createMetricCard(container, metricName, metric) {
            const card = document.createElement('div');
            card.className = 'metric-card';
            card.innerHTML = `
                <h4>${metric.config.display_name}</h4>
                <div class="metric-value" id="value-${metricName}">
                    ${formatValue(metric.current_value, metric.config)}
                </div>
                <span class="metric-status status-${metric.status}" id="status-${metricName}">
                    ${metric.status.toUpperCase()}
                </span>
                <div class="chart-container">
                    <canvas id="chart-${metricName}"></canvas>
                </div>
            `;

            container.appendChild(card);

            // Create chart
            const ctx = document.getElementById('chart-' + metricName).getContext('2d');
            charts[metricName] = new Chart(ctx, {
                type: metric.config.chart_type === 'gauge' ? 'doughnut' : 'line',
                data: metric.data,
                options: metric.data.options
            });
        }

        function updateChart(metricName, metric) {
            const chart = charts[metricName];
            if (chart) {
                chart.data = metric.data;
                chart.update('none');
            }

            // Update value and status
            document.getElementById('value-' + metricName).textContent = formatValue(metric.current_value, metric.config);
            const statusElement = document.getElementById('status-' + metricName);
            statusElement.textContent = metric.status.toUpperCase();
            statusElement.className = 'metric-status status-' + metric.status;
        }

        function formatValue(value, config) {
            switch (config.format_type) {
                case 'percentage':
                    return (value * 100).toFixed(1) + '%';
                case 'duration':
                    return config.unit === 'ms' ? value.toFixed(0) + 'ms' : value.toFixed(2) + 's';
                case 'bytes':
                    return value.toFixed(0) + ' ' + config.unit;
                default:
                    return value.toFixed(2) + (config.unit ? ' ' + config.unit : '');
            }
        }

        // Initialize dashboard
        connectWebSocket();

        // Fetch initial data
        fetch('/api/dashboard/data')
            .then(response => response.json())
            .then(data => updateDashboard(data))
            .catch(console.error);
    </script>
</body>
</html>
        """

        return html_template


# Global dashboard instance
_monitoring_dashboard: MonitoringDashboard | None = None


def get_monitoring_dashboard() -> MonitoringDashboard | None:
    """Get global monitoring dashboard instance"""
    global _monitoring_dashboard
    return _monitoring_dashboard


def initialize_monitoring_dashboard(
    config: dict[str, Any] | None = None,
) -> MonitoringDashboard:
    """Initialize global monitoring dashboard"""
    global _monitoring_dashboard

    _monitoring_dashboard = MonitoringDashboard(config)
    return _monitoring_dashboard


async def shutdown_monitoring_dashboard() -> None:
    """Shutdown global monitoring dashboard"""
    global _monitoring_dashboard

    if _monitoring_dashboard:
        await _monitoring_dashboard.stop_dashboard()
        _monitoring_dashboard = None
