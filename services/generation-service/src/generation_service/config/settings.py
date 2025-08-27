"""
Application settings management with validation and type safety
"""

import json
from enum import Enum
from typing import Any, Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

try:
    from ai_script_core import get_service_logger

    CORE_AVAILABLE = True
    logger = get_service_logger("generation-service.config.settings")
except (ImportError, RuntimeError):
    CORE_AVAILABLE = False
    import logging

    logger = logging.getLogger(__name__)  # type: ignore[assignment]


class LogLevel(str, Enum):
    """Available log levels"""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class Environment(str, Enum):
    """Deployment environments"""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """
    Application settings with validation and environment variable support

    Uses Pydantic for type validation and automatic environment variable loading
    """

    # Application settings
    app_name: str = Field(default="Generation Service", description="Application name")
    version: str = Field(default="1.0.0", description="Application version")
    environment: Environment = Field(
        default=Environment.DEVELOPMENT, description="Deployment environment"
    )
    debug: bool = Field(default=False, description="Enable debug mode")

    # Server settings
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, ge=1, le=65535, description="Server port")
    workers: int = Field(
        default=1, ge=1, le=32, description="Number of worker processes"
    )

    # Performance settings
    enable_performance_optimization: bool = Field(
        default=True, description="Enable performance optimizations"
    )
    enable_caching: bool = Field(default=True, description="Enable caching")
    enable_monitoring: bool = Field(default=True, description="Enable monitoring")
    enable_async_optimization: bool = Field(
        default=True, description="Enable async optimizations"
    )

    # Cache settings
    redis_url: Optional[str] = Field(default=None, description="Redis connection URL")
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, ge=1, le=65535, description="Redis port")
    redis_db: int = Field(default=0, ge=0, le=15, description="Redis database number")
    redis_password: Optional[str] = Field(default=None, description="Redis password")
    cache_ttl_default: int = Field(
        default=3600, ge=1, description="Default cache TTL in seconds"
    )

    # Memory and resource limits
    memory_limit_mb: int = Field(default=2048, ge=128, description="Memory limit in MB")
    max_concurrent_workflows: int = Field(
        default=20, ge=1, le=100, description="Maximum concurrent workflows"
    )
    ai_api_max_concurrent: int = Field(
        default=5, ge=1, le=20, description="Maximum concurrent AI API calls"
    )
    ai_api_timeout: float = Field(
        default=60.0, ge=1.0, le=300.0, description="AI API timeout in seconds"
    )

    # Monitoring and alerting
    monitoring_interval: float = Field(
        default=30.0, ge=1.0, description="Monitoring interval in seconds"
    )
    alert_cooldown: int = Field(
        default=300, ge=60, description="Alert cooldown in seconds"
    )
    dashboard_enabled: bool = Field(
        default=True, description="Enable monitoring dashboard"
    )
    metrics_retention_hours: int = Field(
        default=24, ge=1, le=168, description="Metrics retention in hours"
    )

    # Logging settings
    log_level: LogLevel = Field(default=LogLevel.INFO, description="Logging level")
    log_file: Optional[str] = Field(default=None, description="Log file path")
    log_max_file_size: int = Field(
        default=100 * 1024 * 1024,
        ge=1024 * 1024,
        description="Max log file size in bytes",
    )
    log_backup_count: int = Field(
        default=5, ge=1, le=20, description="Number of log backup files"
    )
    structured_logging: bool = Field(
        default=True, description="Enable structured logging"
    )

    # Performance tracing
    tracing_enabled: bool = Field(
        default=True, description="Enable performance tracing"
    )
    trace_sample_rate: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Trace sampling rate"
    )
    trace_retention_hours: int = Field(
        default=24, ge=1, le=168, description="Trace retention in hours"
    )

    # AI Provider settings
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    anthropic_api_key: Optional[str] = Field(
        default=None, description="Anthropic API key"
    )
    claude_api_key: Optional[str] = Field(
        default=None, description="Claude API key (alias for Anthropic)"
    )
    gemini_api_key: Optional[str] = Field(default=None, description="Gemini API key")
    google_api_key: Optional[str] = Field(
        default=None, description="Google API key (alias for Gemini)"
    )
    ai_provider_timeout: float = Field(
        default=30.0, ge=1.0, le=300.0, description="AI provider timeout"
    )
    ai_provider_retries: int = Field(
        default=3, ge=0, le=10, description="AI provider retry attempts"
    )

    # Security settings
    cors_origins: list[str] = Field(
        default_factory=list, description="CORS allowed origins"
    )
    api_key: Optional[str] = Field(
        default=None, description="API key for authentication"
    )
    rate_limit_requests: int = Field(
        default=1000, ge=10, description="Rate limit requests per hour"
    )

    # Database settings (if needed)
    database_url: Optional[str] = Field(
        default=None, description="Database connection URL"
    )
    database_pool_size: int = Field(
        default=5, ge=1, le=20, description="Database connection pool size"
    )

    # External service URLs
    project_service_url: str = Field(
        default="http://localhost:8001", description="Project service URL"
    )

    model_config = SettingsConfigDict(
        env_prefix="GEN_SERVICE_",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
    )

    @field_validator("environment", mode="before")
    @classmethod
    def validate_environment(cls, v: Any) -> Environment:
        """Validate environment value"""
        if isinstance(v, str):
            return Environment(v.lower())
        if isinstance(v, Environment):
            return v
        raise ValueError(f"Invalid environment value: {v}")

    @field_validator("log_level", mode="before")
    @classmethod
    def validate_log_level(cls, v: Any) -> LogLevel:
        """Validate log level value"""
        if isinstance(v, str):
            return LogLevel(v.lower())
        if isinstance(v, LogLevel):
            return v
        raise ValueError(f"Invalid log level value: {v}")

    @model_validator(mode="after")
    def validate_redis_url(self) -> "Settings":
        """Build Redis URL if not provided"""
        if self.redis_url is None:
            host = self.redis_host
            port = self.redis_port
            db = self.redis_db
            password = self.redis_password

            if password:
                self.redis_url = f"redis://:{password}@{host}:{port}/{db}"
            else:
                self.redis_url = f"redis://{host}:{port}/{db}"

        return self

    @field_validator("cors_origins", mode="before")
    @classmethod
    def validate_cors_origins(cls, v: Any) -> list[str]:
        """Parse CORS origins from string (JSON/CSV) or list"""
        if isinstance(v, str):
            # Try JSON parsing first
            if v.strip().startswith("[") and v.strip().endswith("]"):
                try:
                    parsed: list[str] = json.loads(v)
                    return parsed
                except json.JSONDecodeError:
                    pass
            # Fall back to CSV parsing
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        if isinstance(v, list):
            return v
        raise ValueError(f"Invalid CORS origins value: {v}")

    @property
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.environment == Environment.DEVELOPMENT

    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment == Environment.PRODUCTION

    @property
    def is_testing(self) -> bool:
        """Check if running in testing environment"""
        return self.environment == Environment.TESTING

    def get_cache_config(self) -> dict[str, Any]:
        """Get cache configuration"""
        return {
            "enabled": self.enable_caching,
            "redis_url": self.redis_url,
            "redis_host": self.redis_host,
            "redis_port": self.redis_port,
            "redis_db": self.redis_db,
            "redis_password": self.redis_password,
            "default_ttl": self.cache_ttl_default,
            "memory_fallback": True,
            "memory_cache_size": 1000,
        }

    def get_async_config(self) -> dict[str, Any]:
        """Get async optimization configuration"""
        return {
            "enabled": self.enable_async_optimization,
            "ai_api_max_concurrent": self.ai_api_max_concurrent,
            "ai_api_timeout": self.ai_api_timeout,
            "general_max_concurrent": 10,
            "general_timeout": 30.0,
            "priority_max_concurrent": 3,
            "priority_timeout": 120.0,
        }

    def get_resource_config(self) -> dict[str, Any]:
        """Get resource management configuration"""
        return {
            "enabled": True,
            "memory_limit_mb": self.memory_limit_mb,
            "memory_warning_percent": 80.0,
            "memory_critical_percent": 90.0,
            "auto_gc_enabled": True,
            "monitoring_interval": self.monitoring_interval,
        }

    def get_monitoring_config(self) -> dict[str, Any]:
        """Get monitoring configuration"""
        return {
            "enabled": self.enable_monitoring,
            "metrics_collection_interval": 5.0,
            "max_metric_history": 10000,
            "metric_retention_hours": self.metrics_retention_hours,
            "health_check_interval": 60.0,
            "alerting_enabled": not self.is_testing,
            "alert_cooldown_seconds": self.alert_cooldown,
            "dashboard_enabled": self.dashboard_enabled,
        }

    def get_logging_config(self) -> dict[str, Any]:
        """Get logging configuration"""
        return {
            "enabled": True,
            "log_level": self.log_level.value,
            "debug_mode": self.debug,
            "log_file": self.log_file,
            "max_file_size": self.log_max_file_size,
            "backup_count": self.log_backup_count,
            "max_log_entries": 10000,
            "tracing_enabled": self.tracing_enabled,
            "trace_sample_rate": self.trace_sample_rate,
            "trace_retention_hours": self.trace_retention_hours,
        }

    def get_ai_provider_config(self) -> dict[str, dict[str, Any]]:
        """Get AI provider configuration"""
        providers = {}

        if self.openai_api_key:
            providers["openai"] = {
                "type": "openai",
                "model": "gpt-4o",
                "api_key": self.openai_api_key,
                "timeout": self.ai_provider_timeout,
                "retries": self.ai_provider_retries,
                "rate_limit": 10,
                "max_connections": 5,
            }

        # Anthropic provider with fallback API key support
        anthropic_key = self.anthropic_api_key or self.claude_api_key
        if anthropic_key:
            providers["anthropic"] = {
                "type": "anthropic",
                "model": "claude-3-5-sonnet-20241022",
                "api_key": anthropic_key,
                "timeout": self.ai_provider_timeout,
                "retries": self.ai_provider_retries,
                "rate_limit": 5,
                "max_connections": 3,
            }

        # Gemini provider with fallback API key support
        gemini_key = self.gemini_api_key or self.google_api_key
        if gemini_key:
            providers["gemini"] = {
                "type": "gemini",
                "model": "gemini-pro",
                "api_key": gemini_key,
                "timeout": self.ai_provider_timeout,
                "retries": self.ai_provider_retries,
                "rate_limit": 10,
                "max_connections": 5,
            }

        return providers

    def get_performance_targets(self) -> dict[str, Any]:
        """Get performance targets"""
        return {
            "workflow_execution_time_target": 30.0,
            "max_concurrent_workflows": self.max_concurrent_workflows,
            "api_response_time_cached_target": 0.1,
            "cache_hit_ratio_target": 0.7,
            "ai_api_success_rate_target": 0.95,
        }

    def apply_environment_defaults(self) -> None:
        """Apply environment-specific defaults"""

        if self.environment == Environment.DEVELOPMENT:
            self.debug = True
            self.log_level = LogLevel.DEBUG
            self.dashboard_enabled = True
            self.memory_limit_mb = min(
                self.memory_limit_mb, 1024
            )  # Lower limit for dev

        elif self.environment == Environment.TESTING:
            self.debug = True
            self.log_level = LogLevel.DEBUG
            self.enable_caching = False  # Disable cache for testing
            self.enable_monitoring = False  # Simplified monitoring
            self.dashboard_enabled = False

        elif self.environment == Environment.STAGING:
            self.debug = False
            self.log_level = LogLevel.INFO
            self.dashboard_enabled = True

        elif self.environment == Environment.PRODUCTION:
            self.debug = False
            self.log_level = LogLevel.WARNING
            self.dashboard_enabled = (
                False  # Disable dashboard in prod unless explicitly enabled
            )
            self.trace_sample_rate = 0.1  # Reduced sampling in production

    def validate_settings(self) -> list[str]:
        """Validate settings and return list of issues"""

        issues = []

        # Check required AI provider keys (with fallback support)
        anthropic_key = self.anthropic_api_key or self.claude_api_key
        gemini_key = self.gemini_api_key or self.google_api_key
        if not self.openai_api_key and not anthropic_key and not gemini_key:
            issues.append(
                "At least one AI provider API key must be configured (OpenAI, Anthropic/Claude, or Gemini/Google)"
            )

        # Check memory limits
        if self.memory_limit_mb < 256:
            issues.append("Memory limit too low (minimum 256MB)")

        # Check performance settings
        if self.max_concurrent_workflows > 50:
            issues.append("Max concurrent workflows is very high (>50)")

        if self.ai_api_max_concurrent > self.max_concurrent_workflows:
            issues.append(
                "AI API max concurrent should not exceed max concurrent workflows"
            )

        # Environment-specific checks
        if self.environment == Environment.PRODUCTION:
            if self.debug:
                issues.append("Debug mode should be disabled in production")

            if self.log_level == LogLevel.DEBUG:
                issues.append("Debug log level should not be used in production")

        return issues

    def get_summary(self) -> dict[str, Any]:
        """Get configuration summary"""

        return {
            "app_name": self.app_name,
            "version": self.version,
            "environment": self.environment.value,
            "debug": self.debug,
            "server": {"host": self.host, "port": self.port, "workers": self.workers},
            "performance": {
                "caching_enabled": self.enable_caching,
                "monitoring_enabled": self.enable_monitoring,
                "async_optimization_enabled": self.enable_async_optimization,
                "memory_limit_mb": self.memory_limit_mb,
                "max_concurrent_workflows": self.max_concurrent_workflows,
            },
            "logging": {
                "level": self.log_level.value,
                "structured": self.structured_logging,
                "tracing_enabled": self.tracing_enabled,
            },
        }


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get global settings instance"""
    global _settings

    if _settings is None:
        _settings = Settings()
        _settings.apply_environment_defaults()

        # Validate settings
        issues = _settings.validate_settings()
        if issues:
            logger.warning(f"Settings validation issues: {issues}")

    return _settings


def initialize_settings(env_file: Optional[str] = None, **overrides: Any) -> Settings:
    """Initialize settings with optional overrides"""
    global _settings

    # Load base settings
    # In Pydantic v2, env_file is handled via model_config, not constructor
    _settings = Settings()

    # Apply overrides
    for key, value in overrides.items():
        if hasattr(_settings, key):
            setattr(_settings, key, value)

    # Apply environment defaults
    _settings.apply_environment_defaults()

    # Validate settings
    issues = _settings.validate_settings()
    if issues:
        logger.warning(f"Settings validation issues: {issues}")

    logger.info(f"Settings initialized for environment: {_settings.environment.value}")

    return _settings


def reload_settings() -> Settings:
    """Reload settings from environment"""
    global _settings
    _settings = None
    return get_settings()
