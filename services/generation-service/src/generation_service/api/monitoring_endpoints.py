"""
Monitoring API endpoints for real-time system status and metrics
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# Import Core Module components
try:
    from ai_script_core import (
        get_service_logger,
        utc_now,
    )

    CORE_AVAILABLE = True
    logger = get_service_logger("generation-service.monitoring_endpoints")
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


# Response models
class HealthResponse(BaseModel):
    """Health check response"""

    status: str
    timestamp: datetime
    components: dict[str, Any]
    overall_status: str


class MetricsResponse(BaseModel):
    """Metrics response"""

    timestamp: datetime
    metrics: dict[str, Any]
    performance_targets: dict[str, Any]


class AlertResponse(BaseModel):
    """Alert response"""

    active_alerts: int
    recent_alerts: list[dict[str, Any]]
    alert_summary: dict[str, Any]


class DashboardResponse(BaseModel):
    """Dashboard data response"""

    health: dict[str, Any]
    metrics: dict[str, Any]
    alerts: dict[str, Any]
    charts: dict[str, Any]
    system_info: dict[str, Any]


class MonitoringAPI:
    """
    Monitoring API endpoints for system health, metrics, and alerts

    Provides REST endpoints for:
    - Health status monitoring
    - Performance metrics
    - Alert management
    - Real-time dashboard data
    - WebSocket connections for live updates
    """

    def __init__(self) -> None:
        self.router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])
        self._setup_routes()

        # WebSocket connections for real-time updates
        self._websocket_connections: list[WebSocket] = []

    def _setup_routes(self) -> None:
        """Setup API routes"""

        # Health endpoints
        self.router.add_api_route(
            "/health", self.get_health, methods=["GET"], response_model=HealthResponse
        )
        self.router.add_api_route(
            "/health/{component}", self.get_component_health, methods=["GET"]
        )
        self.router.add_api_route(
            "/health/check/{component}", self.trigger_health_check, methods=["POST"]
        )

        # Metrics endpoints
        self.router.add_api_route(
            "/metrics",
            self.get_metrics,
            methods=["GET"],
            response_model=MetricsResponse,
        )
        self.router.add_api_route(
            "/metrics/current", self.get_current_metrics, methods=["GET"]
        )
        self.router.add_api_route(
            "/metrics/history/{metric_name}", self.get_metric_history, methods=["GET"]
        )
        self.router.add_api_route(
            "/metrics/summary", self.get_metrics_summary, methods=["GET"]
        )

        # Alert endpoints
        self.router.add_api_route(
            "/alerts", self.get_alerts, methods=["GET"], response_model=AlertResponse
        )
        self.router.add_api_route(
            "/alerts/active", self.get_active_alerts, methods=["GET"]
        )
        self.router.add_api_route(
            "/alerts/history", self.get_alert_history, methods=["GET"]
        )
        self.router.add_api_route(
            "/alerts/rules", self.get_alert_rules, methods=["GET"]
        )

        # Dashboard endpoints
        self.router.add_api_route(
            "/dashboard",
            self.get_dashboard_data,
            methods=["GET"],
            response_model=DashboardResponse,
        )
        self.router.add_api_route(
            "/dashboard/charts/{metric_name}", self.get_chart_data, methods=["GET"]
        )

        # System status endpoints
        self.router.add_api_route("/status", self.get_system_status, methods=["GET"])
        self.router.add_api_route(
            "/performance", self.get_performance_summary, methods=["GET"]
        )

        # WebSocket endpoint
        self.router.add_websocket_route("/ws/dashboard", self.dashboard_websocket)

        # Dashboard HTML page
        self.router.add_api_route(
            "/dashboard/view",
            self.get_dashboard_html,
            methods=["GET"],
            response_class=HTMLResponse,
        )

    async def get_health(self) -> HealthResponse:
        """Get overall system health"""

        try:
            from ..monitoring.health_monitor import get_health_monitor

            health_monitor = get_health_monitor()
            if not health_monitor:
                raise HTTPException(
                    status_code=503, detail="Health monitoring not available"
                )

            health_summary = health_monitor.get_health_summary()

            return HealthResponse(
                status="success",
                timestamp=utc_now() if CORE_AVAILABLE else datetime.now(),
                components=health_summary.get("components", {}),
                overall_status=health_summary.get("overall_status", "unknown"),
            )

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise HTTPException(status_code=500, detail=f"Health check failed: {e!s}")

    async def get_component_health(self, component: str) -> dict[str, Any]:
        """Get health status of specific component"""

        try:
            from ..monitoring.health_monitor import get_health_monitor

            health_monitor = get_health_monitor()
            if not health_monitor:
                raise HTTPException(
                    status_code=503, detail="Health monitoring not available"
                )

            component_health = health_monitor.get_component_health(component)
            if not component_health:
                raise HTTPException(
                    status_code=404, detail=f"Component {component} not found"
                )

            return {
                "component": component,
                "status": component_health.status.value,
                "last_check": component_health.last_check.isoformat(),
                "response_time": component_health.response_time,
                "message": component_health.message,
                "details": component_health.details,
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Component health check failed: {e}")
            raise HTTPException(
                status_code=500, detail=f"Component health check failed: {e!s}"
            )

    async def trigger_health_check(self, component: str) -> dict[str, Any]:
        """Trigger immediate health check for component"""

        try:
            from ..monitoring.health_monitor import get_health_monitor

            health_monitor = get_health_monitor()
            if not health_monitor:
                raise HTTPException(
                    status_code=503, detail="Health monitoring not available"
                )

            result = await health_monitor.perform_immediate_check(component)
            if not result:
                raise HTTPException(
                    status_code=404, detail=f"Component {component} not found"
                )

            return {
                "component": component,
                "check_triggered": True,
                "result": {
                    "status": result.status.value,
                    "response_time": result.response_time,
                    "message": result.message,
                    "timestamp": result.timestamp.isoformat(),
                },
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Health check trigger failed: {e}")
            raise HTTPException(
                status_code=500, detail=f"Health check trigger failed: {e!s}"
            )

    async def get_metrics(self) -> MetricsResponse:
        """Get current system metrics"""

        try:
            from ..monitoring.metrics_collector import get_metrics_collector

            collector = get_metrics_collector()
            if not collector:
                raise HTTPException(
                    status_code=503, detail="Metrics collection not available"
                )

            current_metrics = collector.get_current_metrics()
            performance_targets = collector.check_performance_targets()

            return MetricsResponse(
                timestamp=utc_now() if CORE_AVAILABLE else datetime.now(),
                metrics=current_metrics.to_dict(),
                performance_targets=performance_targets,
            )

        except Exception as e:
            logger.error(f"Metrics retrieval failed: {e}")
            raise HTTPException(
                status_code=500, detail=f"Metrics retrieval failed: {e!s}"
            )

    async def get_current_metrics(self) -> dict[str, Any]:
        """Get current performance metrics"""

        try:
            from ..monitoring.metrics_collector import get_metrics_collector

            collector = get_metrics_collector()
            if not collector:
                return {"error": "Metrics collection not available"}

            return collector.get_current_metrics().to_dict()

        except Exception as e:
            logger.error(f"Current metrics retrieval failed: {e}")
            return {"error": f"Current metrics retrieval failed: {e!s}"}

    async def get_metric_history(
        self,
        metric_name: str,
        hours: int = Query(default=1, ge=1, le=168),
        limit: int = Query(default=1000, ge=1, le=10000),
    ) -> dict[str, Any]:
        """Get historical data for specific metric"""

        try:
            from ..monitoring.metrics_collector import get_metrics_collector

            collector = get_metrics_collector()
            if not collector:
                raise HTTPException(
                    status_code=503, detail="Metrics collection not available"
                )

            since = (utc_now() if CORE_AVAILABLE else datetime.now()) - timedelta(
                hours=hours
            )
            history = collector.get_metric_history(metric_name, since)

            # Limit results
            if len(history) > limit:
                history = history[-limit:]

            formatted_history = [
                {
                    "timestamp": entry.timestamp.isoformat(),
                    "value": entry.value,
                    "labels": entry.labels,
                }
                for entry in history
            ]

            return {
                "metric_name": metric_name,
                "time_range_hours": hours,
                "data_points": len(formatted_history),
                "history": formatted_history,
            }

        except Exception as e:
            logger.error(f"Metric history retrieval failed: {e}")
            raise HTTPException(
                status_code=500, detail=f"Metric history retrieval failed: {e!s}"
            )

    async def get_metrics_summary(self) -> dict[str, Any]:
        """Get comprehensive metrics summary"""

        try:
            from ..monitoring.metrics_collector import get_metrics_collector

            collector = get_metrics_collector()
            if not collector:
                return {"error": "Metrics collection not available"}

            return collector.get_metrics_summary()

        except Exception as e:
            logger.error(f"Metrics summary retrieval failed: {e}")
            return {"error": f"Metrics summary retrieval failed: {e!s}"}

    async def get_alerts(self) -> AlertResponse:
        """Get alert status and recent alerts"""

        try:
            from ..monitoring.alerting import get_alert_manager

            alert_manager = get_alert_manager()
            if not alert_manager:
                raise HTTPException(
                    status_code=503, detail="Alert management not available"
                )

            alert_summary = alert_manager.get_alert_summary()

            return AlertResponse(
                active_alerts=alert_summary.get("active_alerts", 0),
                recent_alerts=alert_summary.get("recent_alerts", []),
                alert_summary=alert_summary.get("statistics", {}),
            )

        except Exception as e:
            logger.error(f"Alert retrieval failed: {e}")
            raise HTTPException(
                status_code=500, detail=f"Alert retrieval failed: {e!s}"
            )

    async def get_active_alerts(self) -> dict[str, Any]:
        """Get currently active alerts"""

        try:
            from ..monitoring.alerting import get_alert_manager

            alert_manager = get_alert_manager()
            if not alert_manager:
                return {"active_alerts": []}

            active_alerts = alert_manager.get_active_alerts()

            return {
                "count": len(active_alerts),
                "alerts": [alert.to_dict() for alert in active_alerts],
            }

        except Exception as e:
            logger.error(f"Active alerts retrieval failed: {e}")
            return {"error": f"Active alerts retrieval failed: {e!s}"}

    async def get_alert_history(
        self, hours: int = Query(default=24, ge=1, le=168)
    ) -> dict[str, Any]:
        """Get alert history"""

        try:
            from ..monitoring.alerting import get_alert_manager

            alert_manager = get_alert_manager()
            if not alert_manager:
                return {"alert_history": []}

            alert_history = alert_manager.get_alert_history(hours)

            return {
                "time_range_hours": hours,
                "count": len(alert_history),
                "alerts": [alert.to_dict() for alert in alert_history],
            }

        except Exception as e:
            logger.error(f"Alert history retrieval failed: {e}")
            return {"error": f"Alert history retrieval failed: {e!s}"}

    async def get_alert_rules(self) -> dict[str, Any]:
        """Get configured alert rules"""

        try:
            from ..monitoring.alerting import get_alert_manager

            alert_manager = get_alert_manager()
            if not alert_manager:
                return {"alert_rules": []}

            alert_summary = alert_manager.get_alert_summary()

            return {
                "total_rules": alert_summary.get("active_rules", 0),
                "enabled_rules": alert_summary.get("enabled_rules", 0),
                "rules": alert_summary.get("rules", {}),
            }

        except Exception as e:
            logger.error(f"Alert rules retrieval failed: {e}")
            return {"error": f"Alert rules retrieval failed: {e!s}"}

    async def get_dashboard_data(self) -> DashboardResponse:
        """Get complete dashboard data"""

        try:
            from ..monitoring.dashboard import get_monitoring_dashboard

            dashboard = get_monitoring_dashboard()
            if not dashboard:
                raise HTTPException(
                    status_code=503, detail="Monitoring dashboard not available"
                )

            dashboard_data = await dashboard.get_dashboard_data()

            return DashboardResponse(
                health=dashboard_data.get("health", {}),
                metrics=dashboard_data.get("performance", {}),
                alerts=dashboard_data.get("alerts", {}),
                charts=dashboard_data.get("charts", {}),
                system_info=dashboard_data.get("system_info", {}),
            )

        except Exception as e:
            logger.error(f"Dashboard data retrieval failed: {e}")
            raise HTTPException(
                status_code=500, detail=f"Dashboard data retrieval failed: {e!s}"
            )

    async def get_chart_data(
        self, metric_name: str, hours: int = Query(default=1, ge=1, le=24)
    ) -> dict[str, Any]:
        """Get chart data for specific metric"""

        try:
            from ..monitoring.dashboard import get_monitoring_dashboard

            dashboard = get_monitoring_dashboard()
            if not dashboard:
                raise HTTPException(
                    status_code=503, detail="Monitoring dashboard not available"
                )

            chart_data = await dashboard.get_historical_data(metric_name, hours)

            return chart_data

        except Exception as e:
            logger.error(f"Chart data retrieval failed: {e}")
            raise HTTPException(
                status_code=500, detail=f"Chart data retrieval failed: {e!s}"
            )

    async def get_system_status(self) -> dict[str, Any]:
        """Get overall system status"""

        try:
            # Collect status from all components
            status = {
                "timestamp": (
                    utc_now() if CORE_AVAILABLE else datetime.now()
                ).isoformat(),
                "service": "generation-service",
                "version": "1.0.0",
                "status": "healthy",
            }

            # Health status
            try:
                health_response = await self.get_health()
                status["health"] = {
                    "overall_status": health_response.overall_status,
                    "components": len(health_response.components),
                }
            except Exception:
                status["health"] = {"overall_status": "unknown", "components": 0}

            # Metrics status
            try:
                metrics_response = await self.get_metrics()
                status["metrics"] = {
                    "collection_enabled": True,
                    "current_workflows": metrics_response.metrics.get(
                        "concurrent_workflows", 0
                    ),
                    "memory_usage_mb": metrics_response.metrics.get(
                        "memory_usage_mb", 0
                    ),
                }
            except Exception:
                status["metrics"] = {"collection_enabled": False}

            # Alert status
            try:
                alerts_response = await self.get_alerts()
                status["alerts"] = {
                    "active_alerts": alerts_response.active_alerts,
                    "alerting_enabled": True,
                }
            except Exception:
                status["alerts"] = {"active_alerts": 0, "alerting_enabled": False}

            return status

        except Exception as e:
            logger.error(f"System status retrieval failed: {e}")
            return {
                "timestamp": (
                    utc_now() if CORE_AVAILABLE else datetime.now()
                ).isoformat(),
                "service": "generation-service",
                "status": "error",
                "error": str(e),
            }

    async def get_performance_summary(self) -> dict[str, Any]:
        """Get performance analysis summary"""

        try:
            # Collect performance data from various sources
            summary = {
                "timestamp": (
                    utc_now() if CORE_AVAILABLE else datetime.now()
                ).isoformat(),
                "performance_analysis": {},
            }

            # Metrics summary
            try:
                from ..monitoring.metrics_collector import get_metrics_collector

                collector = get_metrics_collector()
                if collector:
                    summary["metrics"] = collector.get_metrics_summary()
                    summary["performance_targets"] = (
                        collector.check_performance_targets()
                    )
            except Exception as e:
                logger.error(f"Metrics summary failed: {e}")

            # Resource summary
            try:
                from ..optimization.resource_manager import get_resource_manager

                resource_manager = get_resource_manager()
                if resource_manager:
                    summary["resources"] = resource_manager.get_resource_summary()
            except Exception as e:
                logger.error(f"Resource summary failed: {e}")

            # Async manager summary
            try:
                from ..optimization.async_manager import get_async_manager

                async_manager = get_async_manager()
                if async_manager:
                    summary["async_performance"] = async_manager.get_system_metrics()
            except Exception as e:
                logger.error(f"Async performance summary failed: {e}")

            return summary

        except Exception as e:
            logger.error(f"Performance summary retrieval failed: {e}")
            return {"error": f"Performance summary retrieval failed: {e!s}"}

    async def dashboard_websocket(self, websocket: WebSocket) -> None:
        """WebSocket endpoint for real-time dashboard updates"""

        await websocket.accept()
        self._websocket_connections.append(websocket)

        try:
            # Send initial dashboard data
            try:
                from ..monitoring.dashboard import get_monitoring_dashboard

                dashboard = get_monitoring_dashboard()
                if dashboard:
                    dashboard.add_websocket_connection(websocket)
                    initial_data = await dashboard.get_dashboard_data()
                    await websocket.send_json(
                        {"type": "initial_data", "data": initial_data}
                    )
            except Exception as e:
                logger.error(f"Failed to send initial dashboard data: {e}")

            # Keep connection alive
            while True:
                try:
                    # Wait for ping or close
                    await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                except asyncio.TimeoutError:
                    # Send keepalive ping
                    await websocket.send_json({"type": "ping"})

        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            # Clean up connection
            if websocket in self._websocket_connections:
                self._websocket_connections.remove(websocket)

            try:
                from ..monitoring.dashboard import get_monitoring_dashboard

                dashboard = get_monitoring_dashboard()
                if dashboard:
                    dashboard.remove_websocket_connection(websocket)
            except Exception:
                pass

    async def get_dashboard_html(self) -> HTMLResponse:
        """Get monitoring dashboard HTML page"""

        try:
            from ..monitoring.dashboard import get_monitoring_dashboard

            dashboard = get_monitoring_dashboard()
            if not dashboard:
                return HTMLResponse(
                    content="<h1>Monitoring Dashboard Not Available</h1>",
                    status_code=503,
                )

            html_content = dashboard.generate_dashboard_html()
            return HTMLResponse(content=html_content)

        except Exception as e:
            logger.error(f"Dashboard HTML generation failed: {e}")
            return HTMLResponse(
                content=f"<h1>Dashboard Error</h1><p>{e!s}</p>", status_code=500
            )
