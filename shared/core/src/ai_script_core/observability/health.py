"""
Health check system for service monitoring and dependency validation.
"""

import asyncio
import time
from collections.abc import Awaitable, Callable
from datetime import datetime
from enum import Enum
from typing import Any, Union, Optional, List, Dict

import aiohttp
import requests
from pydantic import BaseModel, Field


class HealthStatus(str, Enum):
    """Health status enumeration."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class DependencyHealth(BaseModel):
    """Health status of a service dependency."""

    name: str = Field(..., description="Dependency name")
    status: HealthStatus = Field(..., description="Health status")
    response_time: Optional[int] = Field(
        default=None, description="Response time in milliseconds"
    )
    message: Optional[str] = Field(
        default=None, description="Status message or error details"
    )
    last_check: datetime = Field(
        default_factory=datetime.utcnow, description="Last check timestamp"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() + "Z"}


class ServiceHealth(BaseModel):
    """Overall service health status."""

    status: HealthStatus = Field(..., description="Overall health status")
    service: str = Field(..., description="Service name")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Health check timestamp"
    )
    version: str = Field(default="1.0.0", description="Service version")
    dependencies: list[DependencyHealth] = Field(
        default_factory=list, description="Dependency health checks"
    )
    uptime: Optional[int] = Field(default=None, description="Service uptime in seconds")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional health metadata"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() + "Z"}


# Type definitions for health checkers
SyncHealthChecker = Callable[[], bool]
AsyncHealthChecker = Callable[[], Awaitable[bool]]
HealthChecker = Union[SyncHealthChecker, AsyncHealthChecker]


class HealthCheckRegistry:
    """Registry for health check functions."""

    def __init__(self) -> None:
        self.checks: dict[str, HealthChecker] = {}
        self.timeouts: dict[str, float] = {}
        self.descriptions: dict[str, str] = {}

    def register(
        self,
        name: str,
        checker: HealthChecker,
        timeout: float = 5.0,
        description: Optional[str] = None,
    ) -> None:
        """Register a health check function."""
        self.checks[name] = checker
        self.timeouts[name] = timeout
        self.descriptions[name] = description or f"Health check for {name}"

    def unregister(self, name: str) -> None:
        """Unregister a health check function."""
        self.checks.pop(name, None)
        self.timeouts.pop(name, None)
        self.descriptions.pop(name, None)

    def get_all_checks(self) -> dict[str, HealthChecker]:
        """Get all registered health checks."""
        return self.checks.copy()


class HealthCheckManager:
    """Main health checking service."""

    def __init__(
        self,
        service_name: str,
        version: str = "1.0.0",
        start_time: Optional[datetime] = None,
    ) -> None:
        self.service_name = service_name
        self.version = version
        self.start_time = start_time or datetime.utcnow()
        self.registry = HealthCheckRegistry()

        # Register default checks
        self._register_default_checks()

    def _register_default_checks(self) -> None:
        """Register default system health checks."""
        self.registry.register(
            "system_time",
            self._check_system_time,
            timeout=1.0,
            description="System time availability",
        )

    def _check_system_time(self) -> bool:
        """Basic system time check."""
        try:
            return time.time() > 0
        except Exception:
            return False

    async def check_dependency_health(
        self,
        name: str,
        url: Optional[str] = None,
        timeout: float = 5.0,
        expected_status: int = 200,
        custom_checker: Optional[HealthChecker] = None,
    ) -> DependencyHealth:
        """Check health of a dependency."""
        start_time = time.time()

        try:
            if custom_checker:
                # Use custom checker
                if asyncio.iscoroutinefunction(custom_checker):
                    result = await asyncio.wait_for(custom_checker(), timeout=timeout)
                else:
                    result = custom_checker()

                response_time = int((time.time() - start_time) * 1000)

                return DependencyHealth(
                    name=name,
                    status=HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY,
                    response_time=response_time,
                    message="OK" if result else "Custom health check failed",
                )

            elif url:
                # HTTP health check
                return await self._http_health_check(
                    name, url, timeout, expected_status
                )

            else:
                # Check if registered
                if name in self.registry.checks:
                    checker = self.registry.checks[name]
                    check_timeout = self.registry.timeouts.get(name, timeout)

                    if asyncio.iscoroutinefunction(checker):
                        result = await asyncio.wait_for(
                            checker(), timeout=check_timeout
                        )
                    else:
                        result = checker()

                    response_time = int((time.time() - start_time) * 1000)

                    return DependencyHealth(
                        name=name,
                        status=(
                            HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY
                        ),
                        response_time=response_time,
                        message="OK" if result else "Health check failed",
                    )

                else:
                    return DependencyHealth(
                        name=name,
                        status=HealthStatus.UNHEALTHY,
                        response_time=None,
                        message=f"No health checker configured for {name}",
                    )

        except asyncio.TimeoutError:
            response_time = int(timeout * 1000)
            return DependencyHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                response_time=response_time,
                message=f"Health check timeout after {timeout}s",
            )

        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            return DependencyHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                response_time=response_time,
                message=f"Health check error: {e!s}",
            )

    async def _http_health_check(
        self, name: str, url: str, timeout: float, expected_status: int
    ) -> DependencyHealth:
        """Perform HTTP-based health check."""
        start_time = time.time()

        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as session:
                async with session.get(url) as response:
                    response_time = int((time.time() - start_time) * 1000)

                    if response.status == expected_status:
                        return DependencyHealth(
                            name=name,
                            status=HealthStatus.HEALTHY,
                            response_time=response_time,
                            message=f"HTTP {response.status} OK",
                        )
                    else:
                        return DependencyHealth(
                            name=name,
                            status=HealthStatus.DEGRADED,
                            response_time=response_time,
                            message=f"HTTP {response.status} (expected {expected_status})",
                        )

        except aiohttp.ClientError as e:
            response_time = int((time.time() - start_time) * 1000)
            return DependencyHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                response_time=response_time,
                message=f"HTTP error: {e!s}",
            )

    def check_dependency_health_sync(
        self,
        name: str,
        url: Optional[str] = None,
        timeout: float = 5.0,
        expected_status: int = 200,
    ) -> DependencyHealth:
        """Synchronous dependency health check."""
        start_time = time.time()

        try:
            if url:
                response = requests.get(url, timeout=timeout)
                response_time = int((time.time() - start_time) * 1000)

                if response.status_code == expected_status:
                    return DependencyHealth(
                        name=name,
                        status=HealthStatus.HEALTHY,
                        response_time=response_time,
                        message=f"HTTP {response.status_code} OK",
                    )
                else:
                    return DependencyHealth(
                        name=name,
                        status=HealthStatus.DEGRADED,
                        response_time=response_time,
                        message=f"HTTP {response.status_code} (expected {expected_status})",
                    )

            elif name in self.registry.checks:
                checker = self.registry.checks[name]
                if not asyncio.iscoroutinefunction(checker):
                    result = checker()
                    response_time = int((time.time() - start_time) * 1000)

                    return DependencyHealth(
                        name=name,
                        status=(
                            HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY
                        ),
                        response_time=response_time,
                        message="OK" if result else "Health check failed",
                    )
                else:
                    return DependencyHealth(
                        name=name,
                        status=HealthStatus.UNHEALTHY,
                        response_time=None,
                        message="Async health checker requires async context",
                    )

            else:
                return DependencyHealth(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    response_time=None,
                    message=f"No health checker configured for {name}",
                )

        except requests.RequestException as e:
            response_time = int((time.time() - start_time) * 1000)
            return DependencyHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                response_time=response_time,
                message=f"HTTP error: {e!s}",
            )

        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            return DependencyHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                response_time=response_time,
                message=f"Health check error: {e!s}",
            )

    async def get_overall_health(
        self, dependency_configs: Optional[List[Dict[str, Any]]] = None
    ) -> ServiceHealth:
        """Get overall service health including dependencies."""
        dependencies = []

        # Check configured dependencies
        if dependency_configs:
            for config in dependency_configs:
                dependency = await self.check_dependency_health(**config)
                dependencies.append(dependency)

        # Check all registered health checks
        for name in self.registry.checks:
            if not any(dep.name == name for dep in dependencies):
                dependency = await self.check_dependency_health(name)
                dependencies.append(dependency)

        # Determine overall status
        overall_status = self._calculate_overall_status(dependencies)

        # Calculate uptime
        uptime = int((datetime.utcnow() - self.start_time).total_seconds())

        return ServiceHealth(
            status=overall_status,
            service=self.service_name,
            version=self.version,
            dependencies=dependencies,
            uptime=uptime,
            metadata={
                "dependencies_count": len(dependencies),
                "healthy_dependencies": len(
                    [d for d in dependencies if d.status == HealthStatus.HEALTHY]
                ),
                "degraded_dependencies": len(
                    [d for d in dependencies if d.status == HealthStatus.DEGRADED]
                ),
                "unhealthy_dependencies": len(
                    [d for d in dependencies if d.status == HealthStatus.UNHEALTHY]
                ),
            },
        )

    def get_overall_health_sync(
        self, dependency_configs: Optional[List[Dict[str, Any]]] = None
    ) -> ServiceHealth:
        """Synchronous version of get_overall_health."""
        dependencies = []

        # Check configured dependencies
        if dependency_configs:
            for config in dependency_configs:
                dependency = self.check_dependency_health_sync(**config)
                dependencies.append(dependency)

        # Determine overall status
        overall_status = self._calculate_overall_status(dependencies)

        # Calculate uptime
        uptime = int((datetime.utcnow() - self.start_time).total_seconds())

        return ServiceHealth(
            status=overall_status,
            service=self.service_name,
            version=self.version,
            dependencies=dependencies,
            uptime=uptime,
            metadata={
                "dependencies_count": len(dependencies),
                "healthy_dependencies": len(
                    [d for d in dependencies if d.status == HealthStatus.HEALTHY]
                ),
                "degraded_dependencies": len(
                    [d for d in dependencies if d.status == HealthStatus.DEGRADED]
                ),
                "unhealthy_dependencies": len(
                    [d for d in dependencies if d.status == HealthStatus.UNHEALTHY]
                ),
            },
        )

    def _calculate_overall_status(
        self, dependencies: list[DependencyHealth]
    ) -> HealthStatus:
        """Calculate overall health status from dependencies."""
        if not dependencies:
            return HealthStatus.HEALTHY

        unhealthy_count = len(
            [d for d in dependencies if d.status == HealthStatus.UNHEALTHY]
        )
        degraded_count = len(
            [d for d in dependencies if d.status == HealthStatus.DEGRADED]
        )

        # Service is unhealthy if any critical dependency is unhealthy
        # For now, treat all dependencies as critical
        if unhealthy_count > 0:
            return HealthStatus.UNHEALTHY

        # Service is degraded if any dependency is degraded
        if degraded_count > 0:
            return HealthStatus.DEGRADED

        return HealthStatus.HEALTHY

    def register_check(
        self,
        name: str,
        checker: HealthChecker,
        timeout: float = 5.0,
        description: Optional[str] = None,
    ) -> None:
        """Register a custom health check."""
        self.registry.register(name, checker, timeout, description)

    def unregister_check(self, name: str) -> None:
        """Unregister a health check."""
        self.registry.unregister(name)


# Convenience functions
def create_health_response(
    service_name: str,
    version: str = "1.0.0",
    dependencies: Optional[List[DependencyHealth]] = None,
) -> ServiceHealth:
    """Create a health response."""
    deps = dependencies or []

    # Calculate overall status
    unhealthy_count = len([d for d in deps if d.status == HealthStatus.UNHEALTHY])
    degraded_count = len([d for d in deps if d.status == HealthStatus.DEGRADED])

    if unhealthy_count > 0:
        status = HealthStatus.UNHEALTHY
    elif degraded_count > 0:
        status = HealthStatus.DEGRADED
    else:
        status = HealthStatus.HEALTHY

    return ServiceHealth(
        status=status,
        service=service_name,
        version=version,
        dependencies=deps,
        metadata={
            "dependencies_count": len(deps),
            "healthy_dependencies": len(
                [d for d in deps if d.status == HealthStatus.HEALTHY]
            ),
            "degraded_dependencies": degraded_count,
            "unhealthy_dependencies": unhealthy_count,
        },
    )


def check_dependency_health(
    name: str, url: str, timeout: float = 5.0, expected_status: int = 200
) -> DependencyHealth:
    """Quick synchronous dependency health check."""
    start_time = time.time()

    try:
        response = requests.get(url, timeout=timeout)
        response_time = int((time.time() - start_time) * 1000)

        if response.status_code == expected_status:
            return DependencyHealth(
                name=name,
                status=HealthStatus.HEALTHY,
                response_time=response_time,
                message=f"HTTP {response.status_code} OK",
            )
        else:
            return DependencyHealth(
                name=name,
                status=HealthStatus.DEGRADED,
                response_time=response_time,
                message=f"HTTP {response.status_code} (expected {expected_status})",
            )

    except requests.RequestException as e:
        response_time = int((time.time() - start_time) * 1000)
        return DependencyHealth(
            name=name,
            status=HealthStatus.UNHEALTHY,
            response_time=response_time,
            message=f"HTTP error: {e!s}",
        )

    except Exception as e:
        response_time = int((time.time() - start_time) * 1000)
        return DependencyHealth(
            name=name,
            status=HealthStatus.UNHEALTHY,
            response_time=response_time,
            message=f"Health check error: {e!s}",
        )


# Common health check functions
def check_database_connection(connection_string: str) -> bool:
    """Check database connection health."""
    # Placeholder - implement based on your database type
    try:
        # Example for SQLite
        import sqlite3

        conn = sqlite3.connect(connection_string, timeout=5)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        conn.close()
        return True
    except Exception:
        return False


def check_redis_connection(
    host: str = "localhost", port: int = 6379, timeout: float = 5.0
) -> bool:
    """Check Redis connection health."""
    try:
        import redis

        r = redis.Redis(
            host=host, port=port, socket_timeout=timeout, socket_connect_timeout=timeout
        )
        r.ping()
        return True
    except Exception:
        return False


async def check_chromadb_connection(host: str = "localhost", port: int = 8000) -> bool:
    """Check ChromaDB connection health."""
    try:
        import chromadb

        client = chromadb.HttpClient(host=host, port=port)
        client.heartbeat()
        return True
    except Exception:
        return False


def check_openai_api(api_key: str, timeout: float = 10.0) -> bool:
    """Check OpenAI API connectivity."""
    try:
        import openai

        client = openai.OpenAI(api_key=api_key, timeout=timeout)
        # Simple API call to check connectivity
        client.models.list()
        return True
    except Exception:
        return False
