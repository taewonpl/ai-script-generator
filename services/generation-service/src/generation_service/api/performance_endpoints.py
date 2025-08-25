"""
Performance management API endpoints
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Import Core Module components
try:
    from ai_script_core import (
        get_service_logger,
        utc_now,
    )

    CORE_AVAILABLE = True
    logger = get_service_logger("generation-service.performance_endpoints")
except (ImportError, RuntimeError):
    CORE_AVAILABLE = False
    import logging

    logger = logging.getLogger(__name__)

    # Fallback utility functions
    def utc_now():
        """Fallback UTC timestamp"""
        from datetime import datetime, timezone

        return datetime.now(timezone.utc)

    def generate_uuid():
        """Fallback UUID generation"""
        import uuid

        return str(uuid.uuid4())

    def generate_id():
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
class PerformanceStatusResponse(BaseModel):
    """Performance system status response"""

    optimization_enabled: bool
    async_enabled: bool
    resource_monitoring_enabled: bool
    current_load: float
    performance_rating: str


class ResourceUsageResponse(BaseModel):
    """Resource usage response"""

    timestamp: datetime
    memory_usage: dict[str, Any]
    cpu_usage: dict[str, Any]
    system_resources: dict[str, Any]


class OptimizationResponse(BaseModel):
    """Optimization operation response"""

    success: bool
    operation: str
    results: dict[str, Any]
    timestamp: datetime


class PerformanceAPI:
    """
    Performance management API endpoints

    Provides REST endpoints for:
    - Performance system status
    - Resource usage monitoring
    - Optimization operations
    - Async task management
    - Performance analytics
    """

    def __init__(self):
        self.router = APIRouter(prefix="/api/performance", tags=["performance"])
        self._setup_routes()

    def _setup_routes(self):
        """Setup API routes"""

        # Status and monitoring
        self.router.add_api_route(
            "/status",
            self.get_performance_status,
            methods=["GET"],
            response_model=PerformanceStatusResponse,
        )
        self.router.add_api_route(
            "/resources",
            self.get_resource_usage,
            methods=["GET"],
            response_model=ResourceUsageResponse,
        )
        self.router.add_api_route("/load", self.get_system_load, methods=["GET"])

        # Optimization operations
        self.router.add_api_route(
            "/optimize",
            self.optimize_performance,
            methods=["POST"],
            response_model=OptimizationResponse,
        )
        self.router.add_api_route(
            "/optimize/memory",
            self.optimize_memory,
            methods=["POST"],
            response_model=OptimizationResponse,
        )
        self.router.add_api_route(
            "/optimize/cache",
            self.optimize_cache,
            methods=["POST"],
            response_model=OptimizationResponse,
        )

        # Async task management
        self.router.add_api_route(
            "/async/status", self.get_async_status, methods=["GET"]
        )
        self.router.add_api_route(
            "/async/tasks", self.get_running_tasks, methods=["GET"]
        )
        self.router.add_api_route("/async/pools", self.get_task_pools, methods=["GET"])

        # Resource management
        self.router.add_api_route(
            "/resources/memory", self.get_memory_details, methods=["GET"]
        )
        self.router.add_api_route(
            "/resources/connections", self.get_connection_status, methods=["GET"]
        )
        self.router.add_api_route(
            "/resources/cleanup", self.trigger_cleanup, methods=["POST"]
        )

        # Performance analytics
        self.router.add_api_route(
            "/analytics", self.get_performance_analytics, methods=["GET"]
        )
        self.router.add_api_route(
            "/bottlenecks", self.identify_bottlenecks, methods=["GET"]
        )
        self.router.add_api_route(
            "/recommendations", self.get_optimization_recommendations, methods=["GET"]
        )

        # Configuration
        self.router.add_api_route(
            "/config", self.get_performance_config, methods=["GET"]
        )
        self.router.add_api_route(
            "/config/targets", self.get_performance_targets, methods=["GET"]
        )

    async def get_performance_status(self) -> PerformanceStatusResponse:
        """Get overall performance system status"""

        try:
            # Check optimization systems
            optimization_enabled = True
            async_enabled = True
            monitoring_enabled = True
            current_load = 0.0

            # Get async manager status
            try:
                from ..optimization.async_manager import get_async_manager

                async_manager = get_async_manager()
                if async_manager:
                    metrics = async_manager.get_system_metrics()
                    current_load = metrics.get("current_load", 0.0)
                else:
                    async_enabled = False
            except Exception:
                async_enabled = False

            # Get resource manager status
            try:
                from ..optimization.resource_manager import get_resource_manager

                resource_manager = get_resource_manager()
                if not resource_manager:
                    monitoring_enabled = False
            except Exception:
                monitoring_enabled = False

            # Calculate performance rating
            if current_load < 0.5:
                performance_rating = "excellent"
            elif current_load < 0.7:
                performance_rating = "good"
            elif current_load < 0.9:
                performance_rating = "fair"
            else:
                performance_rating = "poor"

            return PerformanceStatusResponse(
                optimization_enabled=optimization_enabled,
                async_enabled=async_enabled,
                resource_monitoring_enabled=monitoring_enabled,
                current_load=current_load,
                performance_rating=performance_rating,
            )

        except Exception as e:
            logger.error(f"Performance status retrieval failed: {e}")
            raise HTTPException(
                status_code=500, detail=f"Performance status retrieval failed: {e!s}"
            )

    async def get_resource_usage(self) -> ResourceUsageResponse:
        """Get current resource usage"""

        try:
            from ..optimization.resource_manager import get_resource_manager

            resource_manager = get_resource_manager()
            if not resource_manager:
                raise HTTPException(
                    status_code=503, detail="Resource monitoring not available"
                )

            # Get current metrics
            current_metrics = resource_manager.get_current_metrics()
            memory_stats = resource_manager.memory_monitor.get_memory_stats()

            return ResourceUsageResponse(
                timestamp=utc_now() if CORE_AVAILABLE else datetime.now(),
                memory_usage=memory_stats,
                cpu_usage={
                    "cpu_percent": current_metrics.cpu_percent,
                    "process_count": current_metrics.process_count,
                    "thread_count": current_metrics.thread_count,
                },
                system_resources={
                    "memory_used_mb": current_metrics.memory_used,
                    "memory_percent": current_metrics.memory_percent,
                    "disk_used_gb": current_metrics.disk_used,
                    "disk_percent": current_metrics.disk_percent,
                    "network_connections": current_metrics.network_connections,
                    "open_files": current_metrics.open_files,
                },
            )

        except Exception as e:
            logger.error(f"Resource usage retrieval failed: {e}")
            raise HTTPException(
                status_code=500, detail=f"Resource usage retrieval failed: {e!s}"
            )

    async def get_system_load(self):
        """Get current system load"""

        try:
            load_info = {
                "timestamp": (
                    utc_now() if CORE_AVAILABLE else datetime.now()
                ).isoformat(),
                "system_load": 0.0,
                "load_sources": {},
            }

            # Get async manager load
            try:
                from ..optimization.async_manager import get_async_manager

                async_manager = get_async_manager()
                if async_manager:
                    metrics = async_manager.get_system_metrics()
                    load_info["system_load"] = metrics.get("current_load", 0.0)
                    load_info["load_sources"]["async_tasks"] = metrics.get("pools", {})
            except Exception as e:
                logger.error(f"Async load retrieval failed: {e}")

            # Get resource load
            try:
                from ..optimization.resource_manager import get_resource_manager

                resource_manager = get_resource_manager()
                if resource_manager:
                    current_metrics = resource_manager.get_current_metrics()
                    load_info["load_sources"]["resources"] = {
                        "memory_percent": current_metrics.memory_percent,
                        "cpu_percent": current_metrics.cpu_percent,
                        "disk_percent": current_metrics.disk_percent,
                    }
            except Exception as e:
                logger.error(f"Resource load retrieval failed: {e}")

            return load_info

        except Exception as e:
            logger.error(f"System load retrieval failed: {e}")
            return {"error": f"System load retrieval failed: {e!s}"}

    async def optimize_performance(self) -> OptimizationResponse:
        """Perform comprehensive performance optimization"""

        try:
            optimization_results = {
                "memory_optimization": {},
                "cache_optimization": {},
                "resource_cleanup": {},
                "async_optimization": {},
            }

            # Memory optimization
            try:
                memory_result = await self._optimize_memory_internal()
                optimization_results["memory_optimization"] = memory_result
            except Exception as e:
                optimization_results["memory_optimization"] = {"error": str(e)}

            # Cache optimization
            try:
                cache_result = await self._optimize_cache_internal()
                optimization_results["cache_optimization"] = cache_result
            except Exception as e:
                optimization_results["cache_optimization"] = {"error": str(e)}

            # Resource cleanup
            try:
                cleanup_result = await self._cleanup_resources_internal()
                optimization_results["resource_cleanup"] = cleanup_result
            except Exception as e:
                optimization_results["resource_cleanup"] = {"error": str(e)}

            return OptimizationResponse(
                success=True,
                operation="comprehensive_optimization",
                results=optimization_results,
                timestamp=utc_now() if CORE_AVAILABLE else datetime.now(),
            )

        except Exception as e:
            logger.error(f"Performance optimization failed: {e}")
            return OptimizationResponse(
                success=False,
                operation="comprehensive_optimization",
                results={"error": str(e)},
                timestamp=utc_now() if CORE_AVAILABLE else datetime.now(),
            )

    async def optimize_memory(self) -> OptimizationResponse:
        """Optimize memory usage"""

        try:
            results = await self._optimize_memory_internal()

            return OptimizationResponse(
                success=True,
                operation="memory_optimization",
                results=results,
                timestamp=utc_now() if CORE_AVAILABLE else datetime.now(),
            )

        except Exception as e:
            logger.error(f"Memory optimization failed: {e}")
            return OptimizationResponse(
                success=False,
                operation="memory_optimization",
                results={"error": str(e)},
                timestamp=utc_now() if CORE_AVAILABLE else datetime.now(),
            )

    async def _optimize_memory_internal(self) -> dict[str, Any]:
        """Internal memory optimization"""

        from ..optimization.resource_manager import get_resource_manager

        resource_manager = get_resource_manager()
        if not resource_manager:
            return {"error": "Resource manager not available"}

        return await resource_manager.optimize_resources()

    async def optimize_cache(self) -> OptimizationResponse:
        """Optimize cache performance"""

        try:
            results = await self._optimize_cache_internal()

            return OptimizationResponse(
                success=True,
                operation="cache_optimization",
                results=results,
                timestamp=utc_now() if CORE_AVAILABLE else datetime.now(),
            )

        except Exception as e:
            logger.error(f"Cache optimization failed: {e}")
            return OptimizationResponse(
                success=False,
                operation="cache_optimization",
                results={"error": str(e)},
                timestamp=utc_now() if CORE_AVAILABLE else datetime.now(),
            )

    async def _optimize_cache_internal(self) -> dict[str, Any]:
        """Internal cache optimization"""

        from ..cache.cache_manager import get_cache_manager

        cache_manager = get_cache_manager()
        if not cache_manager:
            return {"error": "Cache manager not available"}

        return await cache_manager.optimize_cache()

    async def get_async_status(self):
        """Get async task system status"""

        try:
            from ..optimization.async_manager import get_async_manager

            async_manager = get_async_manager()
            if not async_manager:
                return {"error": "Async manager not available"}

            metrics = async_manager.get_system_metrics()

            return {
                "timestamp": (
                    utc_now() if CORE_AVAILABLE else datetime.now()
                ).isoformat(),
                "system_metrics": metrics,
                "status": (
                    "healthy" if metrics.get("current_load", 0) < 0.8 else "high_load"
                ),
            }

        except Exception as e:
            logger.error(f"Async status retrieval failed: {e}")
            return {"error": f"Async status retrieval failed: {e!s}"}

    async def get_running_tasks(self):
        """Get currently running tasks"""

        try:
            from ..optimization.async_manager import get_async_manager

            async_manager = get_async_manager()
            if not async_manager:
                return {"error": "Async manager not available"}

            metrics = async_manager.get_system_metrics()

            # Extract running task information
            running_tasks = {}
            for pool_name, pool_info in metrics.get("pools", {}).items():
                running_tasks[pool_name] = {
                    "running_tasks": pool_info.get("running_tasks", 0),
                    "pending_tasks": pool_info.get("pending_tasks", 0),
                    "metrics": pool_info.get("metrics", {}),
                }

            return {
                "timestamp": (
                    utc_now() if CORE_AVAILABLE else datetime.now()
                ).isoformat(),
                "total_running": sum(
                    info.get("running_tasks", 0) for info in running_tasks.values()
                ),
                "total_pending": sum(
                    info.get("pending_tasks", 0) for info in running_tasks.values()
                ),
                "pools": running_tasks,
            }

        except Exception as e:
            logger.error(f"Running tasks retrieval failed: {e}")
            return {"error": f"Running tasks retrieval failed: {e!s}"}

    async def get_task_pools(self):
        """Get task pool information"""

        try:
            from ..optimization.async_manager import get_async_manager

            async_manager = get_async_manager()
            if not async_manager:
                return {"error": "Async manager not available"}

            metrics = async_manager.get_system_metrics()

            return {
                "timestamp": (
                    utc_now() if CORE_AVAILABLE else datetime.now()
                ).isoformat(),
                "current_load": metrics.get("current_load", 0.0),
                "pools": metrics.get("pools", {}),
            }

        except Exception as e:
            logger.error(f"Task pools retrieval failed: {e}")
            return {"error": f"Task pools retrieval failed: {e!s}"}

    async def get_memory_details(self):
        """Get detailed memory information"""

        try:
            from ..optimization.resource_manager import get_resource_manager

            resource_manager = get_resource_manager()
            if not resource_manager:
                return {"error": "Resource manager not available"}

            memory_stats = resource_manager.memory_monitor.get_memory_stats()

            return {
                "timestamp": (
                    utc_now() if CORE_AVAILABLE else datetime.now()
                ).isoformat(),
                "memory_details": memory_stats,
            }

        except Exception as e:
            logger.error(f"Memory details retrieval failed: {e}")
            return {"error": f"Memory details retrieval failed: {e!s}"}

    async def get_connection_status(self):
        """Get connection pool status"""

        try:
            from ..optimization.connection_pool import get_ai_provider_pool

            ai_pool = get_ai_provider_pool()
            if not ai_pool:
                return {"error": "AI provider pool not available"}

            metrics = ai_pool.get_provider_metrics()

            return {
                "timestamp": (
                    utc_now() if CORE_AVAILABLE else datetime.now()
                ).isoformat(),
                "provider_metrics": metrics,
            }

        except Exception as e:
            logger.error(f"Connection status retrieval failed: {e}")
            return {"error": f"Connection status retrieval failed: {e!s}"}

    async def trigger_cleanup(self):
        """Trigger manual resource cleanup"""

        try:
            results = await self._cleanup_resources_internal()

            return {
                "success": True,
                "operation": "manual_cleanup",
                "timestamp": (
                    utc_now() if CORE_AVAILABLE else datetime.now()
                ).isoformat(),
                "results": results,
            }

        except Exception as e:
            logger.error(f"Manual cleanup failed: {e}")
            return {
                "success": False,
                "operation": "manual_cleanup",
                "timestamp": (
                    utc_now() if CORE_AVAILABLE else datetime.now()
                ).isoformat(),
                "error": str(e),
            }

    async def _cleanup_resources_internal(self) -> dict[str, Any]:
        """Internal resource cleanup"""

        cleanup_results = {"memory_cleanup": {}, "connection_cleanup": {}}

        # Memory cleanup
        try:
            from ..optimization.resource_manager import get_resource_manager

            resource_manager = get_resource_manager()
            if resource_manager:
                memory_result = await resource_manager.optimize_resources()
                cleanup_results["memory_cleanup"] = memory_result
        except Exception as e:
            cleanup_results["memory_cleanup"] = {"error": str(e)}

        return cleanup_results

    async def get_performance_analytics(self):
        """Get performance analytics and insights"""

        try:
            analytics = {
                "timestamp": (
                    utc_now() if CORE_AVAILABLE else datetime.now()
                ).isoformat(),
                "performance_overview": {},
                "resource_analysis": {},
                "optimization_opportunities": [],
            }

            # Performance overview
            try:
                from ..monitoring.metrics_collector import get_metrics_collector

                collector = get_metrics_collector()
                if collector:
                    current_metrics = collector.get_current_metrics()
                    targets = collector.check_performance_targets()

                    analytics["performance_overview"] = {
                        "current_metrics": current_metrics.to_dict(),
                        "target_compliance": targets,
                    }
            except Exception as e:
                analytics["performance_overview"] = {"error": str(e)}

            # Resource analysis
            try:
                from ..optimization.resource_manager import get_resource_manager

                resource_manager = get_resource_manager()
                if resource_manager:
                    resource_summary = resource_manager.get_resource_summary()
                    analytics["resource_analysis"] = resource_summary
            except Exception as e:
                analytics["resource_analysis"] = {"error": str(e)}

            # Identify optimization opportunities
            analytics["optimization_opportunities"] = (
                await self._identify_optimization_opportunities()
            )

            return analytics

        except Exception as e:
            logger.error(f"Performance analytics retrieval failed: {e}")
            return {"error": f"Performance analytics retrieval failed: {e!s}"}

    async def identify_bottlenecks(self):
        """Identify performance bottlenecks"""

        try:
            bottlenecks = {
                "timestamp": (
                    utc_now() if CORE_AVAILABLE else datetime.now()
                ).isoformat(),
                "detected_bottlenecks": [],
                "performance_issues": [],
                "recommendations": [],
            }

            # Check memory bottlenecks
            try:
                from ..optimization.resource_manager import get_resource_manager

                resource_manager = get_resource_manager()
                if resource_manager:
                    current_metrics = resource_manager.get_current_metrics()

                    if current_metrics.memory_percent > 80:
                        bottlenecks["detected_bottlenecks"].append(
                            {
                                "type": "memory",
                                "severity": (
                                    "high"
                                    if current_metrics.memory_percent > 90
                                    else "medium"
                                ),
                                "current_value": current_metrics.memory_percent,
                                "threshold": 80,
                            }
                        )

                    if current_metrics.cpu_percent > 80:
                        bottlenecks["detected_bottlenecks"].append(
                            {
                                "type": "cpu",
                                "severity": (
                                    "high"
                                    if current_metrics.cpu_percent > 90
                                    else "medium"
                                ),
                                "current_value": current_metrics.cpu_percent,
                                "threshold": 80,
                            }
                        )
            except Exception as e:
                bottlenecks["performance_issues"].append(f"Resource check failed: {e}")

            # Check async bottlenecks
            try:
                from ..optimization.async_manager import get_async_manager

                async_manager = get_async_manager()
                if async_manager:
                    metrics = async_manager.get_system_metrics()
                    current_load = metrics.get("current_load", 0.0)

                    if current_load > 0.8:
                        bottlenecks["detected_bottlenecks"].append(
                            {
                                "type": "async_load",
                                "severity": "high" if current_load > 0.9 else "medium",
                                "current_value": current_load,
                                "threshold": 0.8,
                            }
                        )
            except Exception as e:
                bottlenecks["performance_issues"].append(f"Async check failed: {e}")

            # Generate recommendations
            if bottlenecks["detected_bottlenecks"]:
                for bottleneck in bottlenecks["detected_bottlenecks"]:
                    if bottleneck["type"] == "memory":
                        bottlenecks["recommendations"].append(
                            "Consider triggering garbage collection or increasing memory limits"
                        )
                    elif bottleneck["type"] == "cpu":
                        bottlenecks["recommendations"].append(
                            "Consider reducing concurrent operations or optimizing CPU-intensive tasks"
                        )
                    elif bottleneck["type"] == "async_load":
                        bottlenecks["recommendations"].append(
                            "Consider reducing concurrent async tasks or optimizing task execution"
                        )
            else:
                bottlenecks["recommendations"].append(
                    "No performance bottlenecks detected"
                )

            return bottlenecks

        except Exception as e:
            logger.error(f"Bottleneck identification failed: {e}")
            return {"error": f"Bottleneck identification failed: {e!s}"}

    async def get_optimization_recommendations(self):
        """Get optimization recommendations"""

        try:
            recommendations = await self._identify_optimization_opportunities()

            return {
                "timestamp": (
                    utc_now() if CORE_AVAILABLE else datetime.now()
                ).isoformat(),
                "recommendations": recommendations,
            }

        except Exception as e:
            logger.error(f"Optimization recommendations retrieval failed: {e}")
            return {"error": f"Optimization recommendations retrieval failed: {e!s}"}

    async def _identify_optimization_opportunities(self) -> list[dict[str, Any]]:
        """Identify optimization opportunities"""

        opportunities = []

        try:
            # Check cache performance
            from ..cache.cache_manager import get_cache_manager

            cache_manager = get_cache_manager()
            if cache_manager:
                stats = await cache_manager.get_cache_stats()
                hit_ratio = stats.get("hit_ratio", 0.0)

                if hit_ratio < 0.7:
                    opportunities.append(
                        {
                            "type": "cache_optimization",
                            "priority": "high",
                            "description": f"Cache hit ratio is {hit_ratio:.1%}, below target of 70%",
                            "action": "Review cache strategies and TTL settings",
                        }
                    )
        except Exception:
            pass

        try:
            # Check resource usage
            from ..optimization.resource_manager import get_resource_manager

            resource_manager = get_resource_manager()
            if resource_manager:
                current_metrics = resource_manager.get_current_metrics()

                if current_metrics.memory_percent > 75:
                    opportunities.append(
                        {
                            "type": "memory_optimization",
                            "priority": "medium",
                            "description": f"Memory usage is {current_metrics.memory_percent:.1f}%",
                            "action": "Consider memory cleanup or limit adjustment",
                        }
                    )
        except Exception:
            pass

        # Add general recommendations if no specific issues found
        if not opportunities:
            opportunities.append(
                {
                    "type": "general",
                    "priority": "low",
                    "description": "System performance is within acceptable ranges",
                    "action": "Continue monitoring for optimization opportunities",
                }
            )

        return opportunities

    async def get_performance_config(self):
        """Get current performance configuration"""

        try:
            from ..config.settings import get_settings

            settings = get_settings()

            return {
                "timestamp": (
                    utc_now() if CORE_AVAILABLE else datetime.now()
                ).isoformat(),
                "cache_config": settings.get_cache_config(),
                "async_config": settings.get_async_config(),
                "resource_config": settings.get_resource_config(),
                "monitoring_config": settings.get_monitoring_config(),
            }

        except Exception as e:
            logger.error(f"Performance config retrieval failed: {e}")
            return {"error": f"Performance config retrieval failed: {e!s}"}

    async def get_performance_targets(self):
        """Get performance targets and current status"""

        try:
            from ..config.settings import get_settings
            from ..monitoring.metrics_collector import get_metrics_collector

            settings = get_settings()
            targets = settings.get_performance_targets()

            # Get current status vs targets
            collector = get_metrics_collector()
            if collector:
                target_status = collector.check_performance_targets()
                targets["current_status"] = target_status

            return {
                "timestamp": (
                    utc_now() if CORE_AVAILABLE else datetime.now()
                ).isoformat(),
                "targets": targets,
            }

        except Exception as e:
            logger.error(f"Performance targets retrieval failed: {e}")
            return {"error": f"Performance targets retrieval failed: {e!s}"}
