"""
Compatibility shim for legacy config_loader imports
Maps legacy uppercase attributes to new Settings class
"""

import warnings
from typing import Any

# Import the actual settings
from .config.settings import Settings as _ActualSettings


class _SettingsProxy:
    """
    Proxy class that provides backward compatibility for legacy config_loader imports.
    Maps uppercase attribute names to the corresponding lowercase attributes in the new Settings class.
    """

    def __init__(self):
        self._settings = _ActualSettings()

        # Attribute mapping from legacy uppercase to new lowercase
        self._attribute_mapping = {
            "PORT": "port",
            "DEBUG": "debug",
            "ALLOWED_ORIGINS": "cors_origins",
            "DATABASE_URL": "database_url",
            "OPENAI_API_KEY": "openai_api_key",  # pragma: allowlist secret
            "ANTHROPIC_API_KEY": "anthropic_api_key",  # pragma: allowlist secret
            "MAX_SCRIPT_LENGTH": "max_script_length",
            "DEFAULT_MODEL": "default_model",
            "SERVICE_NAME": "service_name",
            "ENVIRONMENT": "environment",
            "LOG_LEVEL": "log_level",
            "MAX_WORKERS": "max_workers",
            "CORS_ORIGINS": "cors_origins",
            "ENABLE_MONITORING": "enable_monitoring",
            "ENABLE_CACHING": "enable_caching",
            "REDIS_URL": "redis_url",
            "CHROMA_DB_PATH": "chroma_db_path",
            "EMBEDDING_MODEL": "embedding_model",
            "MAX_CONTEXT_LENGTH": "max_context_length",
            "SIMILARITY_THRESHOLD": "similarity_threshold",
            "DATA_ROOT_PATH": "data_root_path",
            "VECTOR_DATA_PATH": "vector_data_path",
            "LOG_DATA_PATH": "log_data_path",
            "CACHE_DATA_PATH": "cache_data_path",
        }

        # Warning tracking to avoid duplicate warnings
        self._warned_attributes = set()

    def __getattr__(self, name: str) -> Any:
        """
        Handle attribute access with backward compatibility mapping.
        Issues deprecation warnings for legacy uppercase attributes.
        """
        # Check if it's a method call (preserve method calls as-is)
        if hasattr(self._settings, name):
            return getattr(self._settings, name)

        # Check if it's a legacy uppercase attribute
        if name in self._attribute_mapping:
            new_name = self._attribute_mapping[name]

            # Issue deprecation warning (only once per attribute)
            if name not in self._warned_attributes:
                warnings.warn(
                    f"Using '{name}' is deprecated. Use '{new_name}' instead. "
                    f"Legacy config_loader import will be removed in future versions.",
                    DeprecationWarning,
                    stacklevel=2,
                )
                self._warned_attributes.add(name)

            # Return the actual value from the new settings
            if hasattr(self._settings, new_name):
                return getattr(self._settings, new_name)
            else:
                # Fallback for attributes that might not exist
                return None

        # For other attributes, try to get from the actual settings
        try:
            return getattr(self._settings, name)
        except AttributeError:
            raise AttributeError(
                f"'{self.__class__.__name__}' object has no attribute '{name}'"
            )

    def __setattr__(self, name: str, value: Any) -> None:
        """Handle attribute setting with mapping support."""
        if name.startswith("_"):
            # Internal attributes
            super().__setattr__(name, value)
        elif name in self._attribute_mapping:
            # Legacy uppercase attribute - map to new name
            new_name = self._attribute_mapping[name]
            if hasattr(self._settings, new_name):
                setattr(self._settings, new_name, value)
            else:
                super().__setattr__(name, value)
        else:
            # Try to set on the actual settings object
            try:
                setattr(self._settings, name, value)
            except AttributeError:
                super().__setattr__(name, value)

    # Explicit methods for compatibility
    def get_ai_provider_configs(self) -> dict[str, Any]:
        """Get AI provider configurations (legacy method name)."""
        if hasattr(self._settings, "get_ai_provider_config"):
            return self._settings.get_ai_provider_config()
        return {}

    def get_ai_provider_config(self) -> dict[str, Any]:
        """Get AI provider configurations (correct method name)."""
        if hasattr(self._settings, "get_ai_provider_config"):
            return self._settings.get_ai_provider_config()
        return {}

    def get_rag_configuration(self) -> dict[str, Any]:
        """Get RAG system configuration."""
        if hasattr(self._settings, "get_rag_configuration"):
            return self._settings.get_rag_configuration()
        return {}

    def get_cache_config(self) -> dict[str, Any]:
        """Get cache configuration."""
        if hasattr(self._settings, "get_cache_config"):
            return self._settings.get_cache_config()
        return {}

    def get_async_config(self) -> dict[str, Any]:
        """Get async configuration."""
        if hasattr(self._settings, "get_async_config"):
            return self._settings.get_async_config()
        return {}

    def get_resource_config(self) -> dict[str, Any]:
        """Get resource configuration."""
        if hasattr(self._settings, "get_resource_config"):
            return self._settings.get_resource_config()
        return {}

    def get_monitoring_config(self) -> dict[str, Any]:
        """Get monitoring configuration."""
        if hasattr(self._settings, "get_monitoring_config"):
            return self._settings.get_monitoring_config()
        return {}

    def get_performance_targets(self) -> dict[str, Any]:
        """Get performance targets."""
        if hasattr(self._settings, "get_performance_targets"):
            return self._settings.get_performance_targets()
        return {}

    def get_default_model(self) -> str | None:
        """Get default AI model."""
        if hasattr(self._settings, "get_default_model"):
            return self._settings.get_default_model()
        return getattr(self._settings, "default_model", None)

    def get_database_settings(self) -> dict[str, Any]:
        """Get database settings."""
        if hasattr(self._settings, "get_database_settings"):
            return self._settings.get_database_settings()
        return {
            "url": getattr(
                self._settings, "database_url", "sqlite:///./data/scripts.db"
            ),
            "echo": getattr(self._settings, "debug", False),
        }

    def get_logging_config(self) -> dict[str, Any]:
        """Get logging configuration."""
        if hasattr(self._settings, "get_logging_config"):
            return self._settings.get_logging_config()
        return {
            "level": getattr(self._settings, "log_level", "INFO"),
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        }

    def get_environment_info(self) -> dict[str, Any]:
        """Get environment information."""
        if hasattr(self._settings, "get_environment_info"):
            return self._settings.get_environment_info()
        return {
            "environment": getattr(self._settings, "environment", "development"),
            "debug": getattr(self._settings, "debug", False),
            "service_name": getattr(
                self._settings, "service_name", "generation-service"
            ),
        }


# Create the singleton settings instance
settings = _SettingsProxy()

# Additional compatibility exports
__all__ = ["settings"]


# Deprecation warning for the entire module
warnings.warn(
    "The 'config_loader' module is deprecated. "
    "Please update your imports to use 'from generation_service.config.settings import Settings' instead. "
    "This compatibility layer will be removed in future versions.",
    DeprecationWarning,
    stacklevel=2,
)
