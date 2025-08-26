"""
Performance configuration management system
"""

import json
import os
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

try:
    from ai_script_core import get_service_logger, utc_now

    CORE_AVAILABLE = True
    logger = get_service_logger("generation-service.config.performance")
except (ImportError, RuntimeError):
    CORE_AVAILABLE = False
    import logging

    logger = logging.getLogger(__name__)  # type: ignore[assignment]


class Environment(str, Enum):
    """Deployment environments"""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class CacheConfig:
    """Cache configuration settings"""

    enabled: bool = True
    redis_url: str | None = None
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str | None = None
    memory_fallback: bool = True
    memory_cache_size: int = 1000
    default_ttl: int = 3600

    # Cache strategy settings
    prompt_cache_ttl: int = 3600  # 1 hour
    rag_cache_ttl: int = 86400  # 24 hours
    embedding_cache_ttl: int = 604800  # 1 week
    api_response_cache_ttl: int = 1800  # 30 minutes


@dataclass
class AsyncConfig:
    """Async optimization configuration"""

    enabled: bool = True

    # AI API pool settings
    ai_api_max_concurrent: int = 5
    ai_api_timeout: float = 60.0
    ai_api_rate_limit: int = 10

    # General processing pool
    general_max_concurrent: int = 10
    general_timeout: float = 30.0

    # Priority pool
    priority_max_concurrent: int = 3
    priority_timeout: float = 120.0

    # Connection pooling
    connection_pool_min: int = 2
    connection_pool_max: int = 10
    connection_timeout: float = 30.0
    health_check_interval: float = 60.0


@dataclass
class ResourceConfig:
    """Resource management configuration"""

    enabled: bool = True

    # Memory limits
    memory_limit_mb: int = 2048
    memory_warning_percent: float = 80.0
    memory_critical_percent: float = 90.0
    auto_gc_enabled: bool = True
    gc_threshold_mb: float = 100.0

    # CPU limits
    cpu_warning_percent: float = 80.0
    cpu_critical_percent: float = 95.0

    # Disk limits
    disk_warning_percent: float = 80.0
    disk_critical_percent: float = 90.0

    # Connection limits
    max_connections: int = 1000
    max_open_files: int = 1024

    # Monitoring intervals
    monitoring_interval: float = 30.0
    cleanup_interval: float = 300.0


@dataclass
class MonitoringConfig:
    """Monitoring and metrics configuration"""

    enabled: bool = True

    # Metrics collection
    metrics_collection_interval: float = 5.0
    max_metric_history: int = 10000
    metric_retention_hours: int = 24

    # Health monitoring
    health_check_interval: float = 60.0
    health_retention_hours: int = 24

    # Alerting
    alerting_enabled: bool = True
    alert_cooldown_seconds: int = 300
    alert_channels: list[str] = field(default_factory=lambda: ["log", "console"])

    # Dashboard
    dashboard_enabled: bool = True
    dashboard_refresh_interval: float = 5.0
    dashboard_max_data_points: int = 100


@dataclass
class LoggingConfig:
    """Logging configuration"""

    enabled: bool = True

    # Log levels
    log_level: str = "info"
    debug_mode: bool = False

    # File logging
    log_file: str | None = None
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    backup_count: int = 5

    # Structured logging
    max_log_entries: int = 10000

    # Performance tracing
    tracing_enabled: bool = True
    trace_sample_rate: float = 1.0
    max_traces: int = 1000
    trace_retention_hours: int = 24


@dataclass
class PerformanceTargets:
    """Performance targets and thresholds"""

    # Workflow performance
    workflow_execution_time_target: float = 30.0  # seconds
    workflow_execution_time_warning: float = 45.0
    workflow_execution_time_critical: float = 60.0

    # Concurrency targets
    max_concurrent_workflows: int = 20
    concurrent_workflows_warning: int = 15
    concurrent_workflows_critical: int = 18

    # API performance
    api_response_time_cached_target: float = 0.1  # 100ms
    api_response_time_warning: float = 1.0
    api_response_time_critical: float = 5.0

    # Cache performance
    cache_hit_ratio_target: float = 0.7  # 70%
    cache_hit_ratio_warning: float = 0.6
    cache_hit_ratio_critical: float = 0.5

    # AI API performance
    ai_api_success_rate_target: float = 0.95  # 95%
    ai_api_error_rate_warning: float = 0.05  # 5%
    ai_api_error_rate_critical: float = 0.1  # 10%


@dataclass
class EnvironmentConfig:
    """Environment-specific configuration"""

    environment: Environment
    debug: bool = False

    # Service configuration
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1

    # External services
    ai_providers: dict[str, dict[str, Any]] = field(default_factory=dict)
    database_url: str | None = None

    # Security
    cors_origins: list[str] = field(default_factory=list)
    api_keys: dict[str, str] = field(default_factory=dict)


@dataclass
class PerformanceConfig:
    """Complete performance configuration"""

    environment: EnvironmentConfig
    cache: CacheConfig = field(default_factory=CacheConfig)
    async_config: AsyncConfig = field(default_factory=AsyncConfig)
    resources: ResourceConfig = field(default_factory=ResourceConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    targets: PerformanceTargets = field(default_factory=PerformanceTargets)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PerformanceConfig":
        """Create from dictionary"""

        # Extract nested configs
        env_data = data.get("environment", {})
        environment = EnvironmentConfig(**env_data)

        cache_data = data.get("cache", {})
        cache = CacheConfig(**cache_data)

        async_data = data.get("async_config", {})
        async_config = AsyncConfig(**async_data)

        resources_data = data.get("resources", {})
        resources = ResourceConfig(**resources_data)

        monitoring_data = data.get("monitoring", {})
        monitoring = MonitoringConfig(**monitoring_data)

        logging_data = data.get("logging", {})
        logging = LoggingConfig(**logging_data)

        targets_data = data.get("targets", {})
        targets = PerformanceTargets(**targets_data)

        return cls(
            environment=environment,
            cache=cache,
            async_config=async_config,
            resources=resources,
            monitoring=monitoring,
            logging=logging,
            targets=targets,
        )

    def validate(self) -> list[str]:
        """Validate configuration and return list of issues"""

        issues = []

        # Validate cache configuration
        if (
            self.cache.enabled
            and not self.cache.redis_url
            and not self.cache.memory_fallback
        ):
            issues.append("Cache enabled but no Redis URL and memory fallback disabled")

        # Validate async configuration
        if self.async_config.ai_api_max_concurrent <= 0:
            issues.append("AI API max concurrent must be greater than 0")

        # Validate resource limits
        if self.resources.memory_limit_mb <= 0:
            issues.append("Memory limit must be greater than 0")

        if (
            self.resources.memory_warning_percent
            >= self.resources.memory_critical_percent
        ):
            issues.append("Memory warning percent must be less than critical percent")

        # Validate performance targets
        if self.targets.workflow_execution_time_target <= 0:
            issues.append("Workflow execution time target must be greater than 0")

        if (
            self.targets.cache_hit_ratio_target < 0
            or self.targets.cache_hit_ratio_target > 1
        ):
            issues.append("Cache hit ratio target must be between 0 and 1")

        return issues

    def get_environment_overrides(self) -> dict[str, Any]:
        """Get configuration overrides based on environment"""

        overrides = {}

        if self.environment.environment == Environment.DEVELOPMENT:
            overrides.update(
                {
                    "logging.debug_mode": True,
                    "logging.log_level": "debug",
                    "monitoring.dashboard_enabled": True,
                    "resources.memory_limit_mb": 1024,  # Lower limit for dev
                    "async_config.ai_api_max_concurrent": 3,  # Reduced for dev
                }
            )

        elif self.environment.environment == Environment.TESTING:
            overrides.update(
                {
                    "logging.log_level": "debug",
                    "monitoring.alerting_enabled": False,  # No alerts in testing
                    "cache.enabled": False,  # Disable cache for testing
                    "resources.monitoring_interval": 10.0,  # More frequent monitoring
                }
            )

        elif self.environment.environment == Environment.STAGING:
            overrides.update(
                {
                    "logging.log_level": "info",
                    "monitoring.dashboard_enabled": True,
                    "resources.memory_limit_mb": 1536,  # Mid-tier limit
                }
            )

        elif self.environment.environment == Environment.PRODUCTION:
            overrides.update(
                {
                    "logging.log_level": "warning",
                    "logging.debug_mode": False,
                    "monitoring.alerting_enabled": True,
                    "resources.auto_gc_enabled": True,
                    "async_config.ai_api_max_concurrent": 5,  # Full capacity
                }
            )

        return overrides

    def apply_environment_overrides(self) -> None:
        """Apply environment-specific overrides"""

        overrides = self.get_environment_overrides()

        for key, value in overrides.items():
            keys = key.split(".")
            target = self

            # Navigate to the target object
            for k in keys[:-1]:
                target = getattr(target, k)

            # Set the final value
            setattr(target, keys[-1], value)


class ConfigManager:
    """
    Configuration management system for performance settings

    Features:
    - Environment-based configuration
    - File-based configuration loading
    - Environment variable overrides
    - Configuration validation
    - Hot reloading support
    - Configuration templates
    """

    def __init__(self, config_dir: str | None = None):
        self.config_dir = Path(config_dir) if config_dir else Path("config")
        self.current_config: PerformanceConfig | None = None
        self._config_watchers: list[Callable[[Any], None]] = []

    def load_config(
        self,
        environment: str | Environment = Environment.DEVELOPMENT,
        config_file: str | None = None,
    ) -> PerformanceConfig:
        """Load configuration for specified environment"""

        if isinstance(environment, str):
            environment = Environment(environment)

        # Load base configuration
        base_config = self._load_base_config()

        # Load environment-specific configuration
        env_config = self._load_environment_config(environment)

        # Load from specific file if provided
        file_config = {}
        if config_file:
            file_config = self._load_config_file(config_file)

        # Load from environment variables
        env_var_config = self._load_from_environment_variables()

        # Merge configurations (priority: env vars > file > environment > base)
        merged_config = self._merge_configs(
            [base_config, env_config, file_config, env_var_config]
        )

        # Create performance config
        performance_config = PerformanceConfig.from_dict(merged_config)

        # Apply environment-specific overrides
        performance_config.apply_environment_overrides()

        # Validate configuration
        issues = performance_config.validate()
        if issues:
            logger.warning(f"Configuration validation issues: {issues}")

        self.current_config = performance_config
        logger.info(f"Configuration loaded for environment: {environment.value}")

        return performance_config

    def _load_base_config(self) -> dict[str, Any]:
        """Load base configuration"""

        return {
            "environment": {
                "environment": Environment.DEVELOPMENT,
                "debug": False,
                "host": "0.0.0.0",
                "port": 8000,
                "workers": 1,
            }
        }

    def _load_environment_config(self, environment: Environment) -> dict[str, Any]:
        """Load environment-specific configuration"""

        config_file = self.config_dir / f"{environment.value}.yaml"

        if config_file.exists():
            return self._load_config_file(str(config_file))

        # Return default environment config
        return {
            "environment": {
                "environment": environment,
                "debug": environment == Environment.DEVELOPMENT,
            }
        }

    def _load_config_file(self, file_path: str) -> dict[str, Any]:
        """Load configuration from file"""

        config_path = Path(file_path)

        if not config_path.exists():
            logger.warning(f"Configuration file not found: {file_path}")
            return {}

        try:
            with open(config_path) as f:
                if config_path.suffix.lower() == ".json":
                    result: dict[str, Any] = json.load(f)
                    return result
                elif config_path.suffix.lower() in [".yaml", ".yml"]:
                    yaml_result: dict[str, Any] = yaml.safe_load(f) or {}
                    return yaml_result
                else:
                    logger.error(f"Unsupported configuration file format: {file_path}")
                    return {}

        except Exception as e:
            logger.error(f"Failed to load configuration file {file_path}: {e}")
            return {}

    def _load_from_environment_variables(self) -> dict[str, Any]:
        """Load configuration from environment variables"""

        config: dict[str, Any] = {}

        # Map environment variables to config keys
        env_mappings = {
            "GEN_SERVICE_DEBUG": ("environment.debug", bool),
            "GEN_SERVICE_HOST": ("environment.host", str),
            "GEN_SERVICE_PORT": ("environment.port", int),
            "GEN_SERVICE_WORKERS": ("environment.workers", int),
            # Cache settings
            "GEN_SERVICE_CACHE_ENABLED": ("cache.enabled", bool),
            "GEN_SERVICE_REDIS_URL": ("cache.redis_url", str),
            "GEN_SERVICE_REDIS_HOST": ("cache.redis_host", str),
            "GEN_SERVICE_REDIS_PORT": ("cache.redis_port", int),
            "GEN_SERVICE_REDIS_PASSWORD": ("cache.redis_password", str),
            # Resource settings
            "GEN_SERVICE_MEMORY_LIMIT_MB": ("resources.memory_limit_mb", int),
            "GEN_SERVICE_MAX_CONCURRENT": ("async_config.ai_api_max_concurrent", int),
            # Monitoring settings
            "GEN_SERVICE_MONITORING_ENABLED": ("monitoring.enabled", bool),
            "GEN_SERVICE_DASHBOARD_ENABLED": ("monitoring.dashboard_enabled", bool),
            # Logging settings
            "GEN_SERVICE_LOG_LEVEL": ("logging.log_level", str),
            "GEN_SERVICE_LOG_FILE": ("logging.log_file", str),
        }

        for env_var, (config_key, value_type) in env_mappings.items():
            env_value = os.getenv(env_var)

            if env_value is not None:
                # Convert value to appropriate type
                try:
                    converted_value: bool | int | float | str
                    if value_type == bool:
                        converted_value = env_value.lower() in (
                            "true",
                            "1",
                            "yes",
                            "on",
                        )
                    elif value_type == int:
                        converted_value = int(env_value)
                    elif value_type == float:
                        converted_value = float(env_value)
                    else:
                        converted_value = env_value

                    # Set nested configuration value
                    self._set_nested_config(config, config_key, converted_value)

                except (ValueError, TypeError) as e:
                    logger.warning(
                        f"Invalid environment variable value {env_var}={env_value}: {e}"
                    )

        return config

    def _set_nested_config(self, config: dict[str, Any], key: str, value: Any) -> None:
        """Set nested configuration value using dot notation"""

        keys = key.split(".")
        target = config

        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]

        target[keys[-1]] = value

    def _merge_configs(self, configs: list[dict[str, Any]]) -> dict[str, Any]:
        """Merge multiple configuration dictionaries"""

        merged: dict[str, Any] = {}

        for config in configs:
            merged = self._deep_merge(merged, config)

        return merged

    def _deep_merge(
        self, base: dict[str, Any], override: dict[str, Any]
    ) -> dict[str, Any]:
        """Deep merge two dictionaries"""

        result = base.copy()

        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def save_config(self, config: PerformanceConfig, file_path: str) -> None:
        """Save configuration to file"""

        config_path = Path(file_path)
        config_data = config.to_dict()

        try:
            with open(config_path, "w") as f:
                if config_path.suffix.lower() == ".json":
                    json.dump(config_data, f, indent=2)
                elif config_path.suffix.lower() in [".yaml", ".yml"]:
                    yaml.dump(config_data, f, default_flow_style=False, indent=2)
                else:
                    raise ValueError(f"Unsupported file format: {config_path.suffix}")

            logger.info(f"Configuration saved to {file_path}")

        except Exception as e:
            logger.error(f"Failed to save configuration to {file_path}: {e}")
            raise

    def create_config_template(
        self, file_path: str, environment: Environment = Environment.DEVELOPMENT
    ) -> None:
        """Create configuration template file"""

        # Create default configuration
        env_config = EnvironmentConfig(environment=environment)
        template_config = PerformanceConfig(environment=env_config)

        # Save as template
        self.save_config(template_config, file_path)
        logger.info(f"Configuration template created: {file_path}")

    def validate_config_file(self, file_path: str) -> list[str]:
        """Validate configuration file"""

        try:
            config_data = self._load_config_file(file_path)
            config = PerformanceConfig.from_dict(config_data)
            return config.validate()

        except Exception as e:
            return [f"Failed to load/parse configuration: {e}"]

    def add_config_watcher(self, callback: Callable[[Any], None]) -> None:
        """Add callback for configuration changes"""
        self._config_watchers.append(callback)

    def reload_config(self) -> PerformanceConfig | None:
        """Reload current configuration"""

        if self.current_config:
            environment = self.current_config.environment.environment
            new_config = self.load_config(environment)

            # Notify watchers
            for watcher in self._config_watchers:
                try:
                    watcher(new_config)
                except Exception as e:
                    logger.error(f"Config watcher failed: {e}")

            return new_config

        return None

    def get_current_config(self) -> PerformanceConfig | None:
        """Get current configuration"""
        return self.current_config


# Global configuration manager
_config_manager: ConfigManager | None = None


def get_config_manager() -> ConfigManager | None:
    """Get global configuration manager"""
    global _config_manager
    return _config_manager


def initialize_config_manager(config_dir: str | None = None) -> ConfigManager:
    """Initialize global configuration manager"""
    global _config_manager

    _config_manager = ConfigManager(config_dir)
    return _config_manager


def get_current_config() -> PerformanceConfig | None:
    """Get current performance configuration"""
    manager = get_config_manager()
    return manager.get_current_config() if manager else None
