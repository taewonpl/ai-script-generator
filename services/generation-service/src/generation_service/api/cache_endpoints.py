"""
Cache management API endpoints
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

# Import Core Module components
try:
    from ai_script_core import (
        get_service_logger,
        utc_now,
    )

    CORE_AVAILABLE = True
    logger = get_service_logger("generation-service.cache_endpoints")
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


# Request/Response models
class CacheStatusResponse(BaseModel):
    """Cache status response"""

    enabled: bool
    backend: str
    statistics: dict[str, Any]
    health: dict[str, Any]


class CacheOperationRequest(BaseModel):
    """Cache operation request"""

    cache_type: str
    key_args: dict[str, Any]
    data: Any | None = None
    ttl: int | None = None


class CacheOperationResponse(BaseModel):
    """Cache operation response"""

    success: bool
    operation: str
    cache_type: str
    key: str
    result: Any | None = None
    error: str | None = None


class CacheAPI:
    """
    Cache management API endpoints

    Provides REST endpoints for:
    - Cache status and statistics
    - Cache operations (get, set, delete)
    - Cache invalidation and warming
    - Backend health monitoring
    """

    def __init__(self):
        self.router = APIRouter(prefix="/api/cache", tags=["cache"])
        self._setup_routes()

    def _setup_routes(self):
        """Setup API routes"""

        # Status and monitoring
        self.router.add_api_route(
            "/status",
            self.get_cache_status,
            methods=["GET"],
            response_model=CacheStatusResponse,
        )
        self.router.add_api_route("/stats", self.get_cache_statistics, methods=["GET"])
        self.router.add_api_route("/health", self.get_cache_health, methods=["GET"])

        # Cache operations
        self.router.add_api_route("/get", self.cache_get, methods=["POST"])
        self.router.add_api_route(
            "/set",
            self.cache_set,
            methods=["POST"],
            response_model=CacheOperationResponse,
        )
        self.router.add_api_route(
            "/delete",
            self.cache_delete,
            methods=["POST"],
            response_model=CacheOperationResponse,
        )
        self.router.add_api_route("/exists", self.cache_exists, methods=["POST"])

        # Cache management
        self.router.add_api_route(
            "/clear/{cache_type}", self.clear_cache_type, methods=["DELETE"]
        )
        self.router.add_api_route("/clear", self.clear_all_cache, methods=["DELETE"])
        self.router.add_api_route("/warm", self.warm_cache, methods=["POST"])
        self.router.add_api_route("/optimize", self.optimize_cache, methods=["POST"])

        # Cache analytics
        self.router.add_api_route(
            "/analytics", self.get_cache_analytics, methods=["GET"]
        )
        self.router.add_api_route("/hit-ratio", self.get_hit_ratio, methods=["GET"])
        self.router.add_api_route(
            "/performance", self.get_cache_performance, methods=["GET"]
        )

    async def get_cache_status(self) -> CacheStatusResponse:
        """Get overall cache system status"""

        try:
            from ..cache.cache_manager import get_cache_manager

            cache_manager = get_cache_manager()
            if not cache_manager:
                raise HTTPException(
                    status_code=503, detail="Cache system not available"
                )

            # Get cache statistics
            stats = await cache_manager.get_cache_stats()

            # Get health status
            health = await cache_manager.health_check()

            # Determine primary backend
            backend = (
                "redis"
                if cache_manager.redis_cache and cache_manager.redis_cache._connected
                else "memory"
            )

            return CacheStatusResponse(
                enabled=True, backend=backend, statistics=stats, health=health
            )

        except Exception as e:
            logger.error(f"Cache status retrieval failed: {e}")
            raise HTTPException(
                status_code=500, detail=f"Cache status retrieval failed: {e!s}"
            )

    async def get_cache_statistics(self):
        """Get detailed cache statistics"""

        try:
            from ..cache.cache_manager import get_cache_manager

            cache_manager = get_cache_manager()
            if not cache_manager:
                return {"error": "Cache system not available"}

            stats = await cache_manager.get_cache_stats()

            return {
                "timestamp": (
                    utc_now() if CORE_AVAILABLE else datetime.now()
                ).isoformat(),
                "statistics": stats,
                "cache_enabled": True,
            }

        except Exception as e:
            logger.error(f"Cache statistics retrieval failed: {e}")
            return {"error": f"Cache statistics retrieval failed: {e!s}"}

    async def get_cache_health(self):
        """Get cache system health"""

        try:
            from ..cache.cache_manager import get_cache_manager

            cache_manager = get_cache_manager()
            if not cache_manager:
                return {
                    "status": "unavailable",
                    "message": "Cache system not initialized",
                }

            health = await cache_manager.health_check()

            return {
                "timestamp": (
                    utc_now() if CORE_AVAILABLE else datetime.now()
                ).isoformat(),
                "health": health,
            }

        except Exception as e:
            logger.error(f"Cache health check failed: {e}")
            return {"status": "error", "error": str(e)}

    async def cache_get(self, request: CacheOperationRequest):
        """Get value from cache"""

        try:
            from ..cache.cache_manager import get_cache_manager
            from ..cache.cache_strategies import CacheType

            cache_manager = get_cache_manager()
            if not cache_manager:
                raise HTTPException(
                    status_code=503, detail="Cache system not available"
                )

            # Parse cache type
            try:
                cache_type = CacheType(request.cache_type)
            except ValueError:
                raise HTTPException(
                    status_code=400, detail=f"Invalid cache type: {request.cache_type}"
                )

            # Get from cache
            result = await cache_manager.get(cache_type, **request.key_args)

            return {
                "success": True,
                "operation": "get",
                "cache_type": request.cache_type,
                "key": str(request.key_args),
                "result": result,
                "found": result is not None,
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Cache get failed: {e}")
            return {
                "success": False,
                "operation": "get",
                "cache_type": request.cache_type,
                "key": str(request.key_args),
                "error": str(e),
            }

    async def cache_set(self, request: CacheOperationRequest) -> CacheOperationResponse:
        """Set value in cache"""

        try:
            from ..cache.cache_manager import get_cache_manager
            from ..cache.cache_strategies import CacheType

            cache_manager = get_cache_manager()
            if not cache_manager:
                raise HTTPException(
                    status_code=503, detail="Cache system not available"
                )

            if request.data is None:
                raise HTTPException(
                    status_code=400, detail="Data is required for cache set operation"
                )

            # Parse cache type
            try:
                cache_type = CacheType(request.cache_type)
            except ValueError:
                raise HTTPException(
                    status_code=400, detail=f"Invalid cache type: {request.cache_type}"
                )

            # Set in cache
            success = await cache_manager.set(
                cache_type,
                request.data,
                *request.key_args.values(),
                ttl_override=request.ttl,
                **request.key_args,
            )

            return CacheOperationResponse(
                success=success,
                operation="set",
                cache_type=request.cache_type,
                key=str(request.key_args),
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Cache set failed: {e}")
            return CacheOperationResponse(
                success=False,
                operation="set",
                cache_type=request.cache_type,
                key=str(request.key_args),
                error=str(e),
            )

    async def cache_delete(
        self, request: CacheOperationRequest
    ) -> CacheOperationResponse:
        """Delete value from cache"""

        try:
            from ..cache.cache_manager import get_cache_manager
            from ..cache.cache_strategies import CacheType

            cache_manager = get_cache_manager()
            if not cache_manager:
                raise HTTPException(
                    status_code=503, detail="Cache system not available"
                )

            # Parse cache type
            try:
                cache_type = CacheType(request.cache_type)
            except ValueError:
                raise HTTPException(
                    status_code=400, detail=f"Invalid cache type: {request.cache_type}"
                )

            # Delete from cache
            success = await cache_manager.delete(cache_type, **request.key_args)

            return CacheOperationResponse(
                success=success,
                operation="delete",
                cache_type=request.cache_type,
                key=str(request.key_args),
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Cache delete failed: {e}")
            return CacheOperationResponse(
                success=False,
                operation="delete",
                cache_type=request.cache_type,
                key=str(request.key_args),
                error=str(e),
            )

    async def cache_exists(self, request: CacheOperationRequest):
        """Check if key exists in cache"""

        try:
            from ..cache.cache_manager import get_cache_manager
            from ..cache.cache_strategies import CacheType

            cache_manager = get_cache_manager()
            if not cache_manager:
                raise HTTPException(
                    status_code=503, detail="Cache system not available"
                )

            # Parse cache type
            try:
                cache_type = CacheType(request.cache_type)
            except ValueError:
                raise HTTPException(
                    status_code=400, detail=f"Invalid cache type: {request.cache_type}"
                )

            # Check existence
            exists = await cache_manager.exists(cache_type, **request.key_args)

            return {
                "success": True,
                "operation": "exists",
                "cache_type": request.cache_type,
                "key": str(request.key_args),
                "exists": exists,
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Cache exists check failed: {e}")
            return {
                "success": False,
                "operation": "exists",
                "cache_type": request.cache_type,
                "key": str(request.key_args),
                "error": str(e),
            }

    async def clear_cache_type(self, cache_type: str):
        """Clear all entries of specific cache type"""

        try:
            from ..cache.cache_manager import get_cache_manager
            from ..cache.cache_strategies import CacheType

            cache_manager = get_cache_manager()
            if not cache_manager:
                raise HTTPException(
                    status_code=503, detail="Cache system not available"
                )

            # Parse cache type
            try:
                cache_type_enum = CacheType(cache_type)
            except ValueError:
                raise HTTPException(
                    status_code=400, detail=f"Invalid cache type: {cache_type}"
                )

            # Clear cache type
            cleared_count = await cache_manager.clear_type(cache_type_enum)

            return {
                "success": True,
                "operation": "clear_type",
                "cache_type": cache_type,
                "cleared_entries": cleared_count,
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Cache type clear failed: {e}")
            raise HTTPException(
                status_code=500, detail=f"Cache type clear failed: {e!s}"
            )

    async def clear_all_cache(self):
        """Clear all cache entries"""

        try:
            from ..cache.cache_manager import get_cache_manager
            from ..cache.cache_strategies import CacheType

            cache_manager = get_cache_manager()
            if not cache_manager:
                raise HTTPException(
                    status_code=503, detail="Cache system not available"
                )

            total_cleared = 0
            results = {}

            # Clear each cache type
            for cache_type in CacheType:
                try:
                    cleared_count = await cache_manager.clear_type(cache_type)
                    results[cache_type.value] = cleared_count
                    total_cleared += cleared_count
                except Exception as e:
                    results[cache_type.value] = f"Error: {e!s}"

            return {
                "success": True,
                "operation": "clear_all",
                "total_cleared": total_cleared,
                "details": results,
            }

        except Exception as e:
            logger.error(f"Cache clear all failed: {e}")
            raise HTTPException(
                status_code=500, detail=f"Cache clear all failed: {e!s}"
            )

    async def warm_cache(self, cache_type: str, warm_data: list[dict[str, Any]]):
        """Warm cache with precomputed data"""

        try:
            from ..cache.cache_manager import get_cache_manager
            from ..cache.cache_strategies import CacheType

            cache_manager = get_cache_manager()
            if not cache_manager:
                raise HTTPException(
                    status_code=503, detail="Cache system not available"
                )

            # Parse cache type
            try:
                cache_type_enum = CacheType(cache_type)
            except ValueError:
                raise HTTPException(
                    status_code=400, detail=f"Invalid cache type: {cache_type}"
                )

            # Warm cache
            warmed_count = await cache_manager.warm_cache(cache_type_enum, warm_data)

            return {
                "success": True,
                "operation": "warm",
                "cache_type": cache_type,
                "warmed_entries": warmed_count,
                "total_provided": len(warm_data),
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Cache warming failed: {e}")
            raise HTTPException(status_code=500, detail=f"Cache warming failed: {e!s}")

    async def optimize_cache(self):
        """Optimize cache performance"""

        try:
            from ..cache.cache_manager import get_cache_manager

            cache_manager = get_cache_manager()
            if not cache_manager:
                raise HTTPException(
                    status_code=503, detail="Cache system not available"
                )

            # Optimize cache
            optimization_results = await cache_manager.optimize_cache()

            return {
                "success": True,
                "operation": "optimize",
                "timestamp": (
                    utc_now() if CORE_AVAILABLE else datetime.now()
                ).isoformat(),
                "results": optimization_results,
            }

        except Exception as e:
            logger.error(f"Cache optimization failed: {e}")
            raise HTTPException(
                status_code=500, detail=f"Cache optimization failed: {e!s}"
            )

    async def get_cache_analytics(self):
        """Get cache usage analytics"""

        try:
            from ..cache.cache_manager import get_cache_manager

            cache_manager = get_cache_manager()
            if not cache_manager:
                return {"error": "Cache system not available"}

            stats = await cache_manager.get_cache_stats()

            # Calculate additional analytics
            analytics = {
                "timestamp": (
                    utc_now() if CORE_AVAILABLE else datetime.now()
                ).isoformat(),
                "basic_stats": stats,
                "performance_analysis": {},
            }

            # Hit ratio analysis
            if stats.get("hit_ratio") is not None:
                hit_ratio = stats["hit_ratio"]

                if hit_ratio >= 0.8:
                    performance_rating = "excellent"
                elif hit_ratio >= 0.6:
                    performance_rating = "good"
                elif hit_ratio >= 0.4:
                    performance_rating = "fair"
                else:
                    performance_rating = "poor"

                analytics["performance_analysis"]["hit_ratio"] = {
                    "current": hit_ratio,
                    "rating": performance_rating,
                    "target": 0.7,
                }

            # Backend analysis
            backends = stats.get("backends", {})
            if backends:
                analytics["backend_analysis"] = {}

                for backend, backend_stats in backends.items():
                    analytics["backend_analysis"][backend] = {
                        "available": backend_stats.get("connected", False),
                        "performance": (
                            "good" if backend_stats.get("connected") else "unavailable"
                        ),
                    }

            return analytics

        except Exception as e:
            logger.error(f"Cache analytics retrieval failed: {e}")
            return {"error": f"Cache analytics retrieval failed: {e!s}"}

    async def get_hit_ratio(self, hours: int = Query(default=1, ge=1, le=24)):
        """Get cache hit ratio over time"""

        try:
            from ..cache.cache_manager import get_cache_manager

            cache_manager = get_cache_manager()
            if not cache_manager:
                return {"error": "Cache system not available"}

            stats = await cache_manager.get_cache_stats()
            current_hit_ratio = stats.get("hit_ratio", 0.0)

            # For now, return current hit ratio
            # In a real implementation, you'd track hit ratio over time
            return {
                "time_range_hours": hours,
                "current_hit_ratio": current_hit_ratio,
                "target_hit_ratio": 0.7,
                "performance": (
                    "good" if current_hit_ratio >= 0.7 else "needs_improvement"
                ),
                "total_operations": stats.get("operations", 0),
                "hits": stats.get("hits", 0),
                "misses": stats.get("misses", 0),
            }

        except Exception as e:
            logger.error(f"Hit ratio retrieval failed: {e}")
            return {"error": f"Hit ratio retrieval failed: {e!s}"}

    async def get_cache_performance(self):
        """Get cache performance metrics"""

        try:
            from ..cache.cache_manager import get_cache_manager

            cache_manager = get_cache_manager()
            if not cache_manager:
                return {"error": "Cache system not available"}

            stats = await cache_manager.get_cache_stats()

            # Calculate performance metrics
            performance = {
                "timestamp": (
                    utc_now() if CORE_AVAILABLE else datetime.now()
                ).isoformat(),
                "overall_performance": {},
                "backend_performance": {},
                "strategy_performance": {},
            }

            # Overall performance
            hit_ratio = stats.get("hit_ratio", 0.0)
            total_ops = stats.get("operations", 0)

            performance["overall_performance"] = {
                "hit_ratio": hit_ratio,
                "total_operations": total_ops,
                "operations_per_minute": (
                    total_ops / 60 if total_ops > 0 else 0
                ),  # Rough estimate
                "efficiency_rating": (
                    "high"
                    if hit_ratio >= 0.8
                    else "medium" if hit_ratio >= 0.6 else "low"
                ),
            }

            # Backend performance
            backends = stats.get("backends", {})
            for backend, backend_stats in backends.items():
                performance["backend_performance"][backend] = {
                    "connected": backend_stats.get("connected", False),
                    "response_time": "fast",  # Would need actual timing data
                    "reliability": "high" if backend_stats.get("connected") else "low",
                }

            # Strategy performance
            strategies = stats.get("strategies", {})
            for strategy, strategy_info in strategies.items():
                performance["strategy_performance"][strategy] = {
                    "ttl": strategy_info.get("ttl", 0),
                    "namespace": strategy_info.get("namespace", ""),
                    "compression": strategy_info.get("compress", False),
                }

            return performance

        except Exception as e:
            logger.error(f"Cache performance retrieval failed: {e}")
            return {"error": f"Cache performance retrieval failed: {e!s}"}
