"""
Configuration validation utilities for Generation Service
"""

import logging
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Configuration validation error"""

    pass


class ConfigValidator:
    """Comprehensive configuration validator"""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.validated_keys: list[str] = []

    def validate_all(self, settings: Any) -> tuple[bool, list[str], list[str]]:
        """
        Validate all configuration aspects

        Returns:
            (is_valid, errors, warnings)
        """
        self.errors.clear()
        self.warnings.clear()
        self.validated_keys.clear()

        # Environment file validation
        self._validate_env_file_loading()

        # Required environment variables
        self._validate_required_variables(settings)

        # API key validation
        self._validate_api_keys(settings)

        # Database configuration
        self._validate_database_config(settings)

        # ChromaDB configuration
        self._validate_chroma_config(settings)

        # AI model configurations
        self._validate_ai_model_configs(settings)

        # Service dependencies
        self._validate_service_dependencies(settings)

        # Performance settings
        self._validate_performance_settings(settings)

        is_valid = len(self.errors) == 0

        logger.info(
            f"Configuration validation completed: {len(self.validated_keys)} keys validated"
        )
        if self.errors:
            logger.error(
                f"Configuration validation failed with {len(self.errors)} errors"
            )
        if self.warnings:
            logger.warning(
                f"Configuration validation completed with {len(self.warnings)} warnings"
            )

        return is_valid, self.errors.copy(), self.warnings.copy()

    def _validate_env_file_loading(self) -> None:
        """Validate .env file loading"""
        env_files = [".env", ".env.local", ".env.production"]
        found_env_file = False

        for env_file in env_files:
            if os.path.exists(env_file):
                found_env_file = True
                self.validated_keys.append(f"env_file:{env_file}")

                # Check file readability
                try:
                    with open(env_file) as f:
                        content = f.read()

                    # Validate .env format
                    lines = content.split("\n")
                    for i, line in enumerate(lines, 1):
                        line = line.strip()
                        if line and not line.startswith("#"):
                            if "=" not in line:
                                self.errors.append(
                                    f"Invalid .env format in {env_file}:{i}: {line}"
                                )
                            else:
                                key, value = line.split("=", 1)
                                if not key.strip():
                                    self.errors.append(f"Empty key in {env_file}:{i}")
                                if any(char in key for char in [" ", "\t"]):
                                    self.warnings.append(
                                        f"Whitespace in key '{key}' in {env_file}:{i}"
                                    )

                except Exception as e:
                    self.errors.append(f"Cannot read .env file {env_file}: {e}")
                break

        if not found_env_file:
            self.warnings.append(
                "No .env file found - using defaults and environment variables"
            )

    def _validate_required_variables(self, settings: Any) -> None:
        """Validate required environment variables"""
        required_vars = [
            "SERVICE_NAME",
            "PORT",
            "DATABASE_URL",
        ]

        optional_but_recommended = [
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "CHROMA_DB_PATH",
            "PROJECT_SERVICE_URL",
        ]

        for var in required_vars:
            value = getattr(settings, var, None)
            if not value:
                self.errors.append(
                    f"Required environment variable {var} is missing or empty"
                )
            else:
                self.validated_keys.append(f"required_var:{var}")

        for var in optional_but_recommended:
            value = getattr(settings, var, None)
            if not value:
                self.warnings.append(
                    f"Recommended environment variable {var} is missing"
                )
            else:
                self.validated_keys.append(f"optional_var:{var}")

    def _validate_api_keys(self, settings: Any) -> None:
        """Validate API key formats and patterns"""
        api_key_configs = [
            ("OPENAI_API_KEY", r"^sk-[A-Za-z0-9]{20,}$", "OpenAI API key"),
            ("ANTHROPIC_API_KEY", r"^sk-ant-[A-Za-z0-9-_]{20,}$", "Anthropic API key"),
        ]

        for var_name, pattern, description in api_key_configs:
            api_key = getattr(settings, var_name, "")

            if api_key and api_key not in [
                "",
                "your_openai_api_key_here",
                "your_anthropic_api_key_here",
            ]:
                if not re.match(pattern, api_key):
                    self.errors.append(f"Invalid {description} format: {var_name}")
                else:
                    self.validated_keys.append(f"api_key:{var_name}")

                # Check for common mistakes
                if api_key.startswith(" ") or api_key.endswith(" "):
                    self.errors.append(f"{description} has leading/trailing whitespace")

                if len(api_key) < 20:
                    self.errors.append(f"{description} appears too short")
            else:
                self.warnings.append(
                    f"{description} not configured or using placeholder"
                )

    def _validate_database_config(self, settings: Any) -> None:
        """Validate database configuration"""
        database_url = getattr(settings, "DATABASE_URL", "")

        if not database_url:
            self.errors.append("DATABASE_URL is required")
            return

        try:
            parsed = urlparse(database_url)

            # Validate scheme
            if parsed.scheme not in ["sqlite"]:
                self.errors.append(
                    f"Unsupported database scheme: {parsed.scheme}. Only SQLite is supported."
                )

            # Validate SQLite path
            if parsed.scheme == "sqlite":
                db_path = parsed.path.lstrip("/")
                if db_path and db_path != ":memory:":
                    db_dir = os.path.dirname(db_path)
                    if db_dir and not os.path.exists(db_dir):
                        self.warnings.append(
                            f"SQLite database directory does not exist: {db_dir}"
                        )

            self.validated_keys.append("database_config")

        except Exception as e:
            self.errors.append(f"Invalid DATABASE_URL format: {e}")

    def _validate_chroma_config(self, settings: Any) -> None:
        """Validate ChromaDB configuration"""
        chroma_path = getattr(settings, "CHROMA_DB_PATH", "")

        if not chroma_path:
            self.warnings.append("CHROMA_DB_PATH not configured")
            return

        # Validate path format
        try:
            path_obj = Path(chroma_path)

            # Check if path is absolute
            if not path_obj.is_absolute():
                self.warnings.append(f"ChromaDB path is relative: {chroma_path}")

            # Check parent directory exists and is writable
            parent_dir = path_obj.parent
            if not parent_dir.exists():
                try:
                    parent_dir.mkdir(parents=True, exist_ok=True)
                    self.validated_keys.append("chroma_path_created")
                except Exception as e:
                    self.errors.append(
                        f"Cannot create ChromaDB directory {parent_dir}: {e}"
                    )
            else:
                # Check write permissions
                if not os.access(parent_dir, os.W_OK):
                    self.errors.append(
                        f"No write permission for ChromaDB directory: {parent_dir}"
                    )
                else:
                    self.validated_keys.append("chroma_path_writable")

            # Validate collection name
            collection_name = getattr(settings, "CHROMA_COLLECTION_NAME", "")
            if collection_name:
                if not re.match(r"^[a-zA-Z0-9_-]+$", collection_name):
                    self.errors.append(
                        f"Invalid ChromaDB collection name: {collection_name}"
                    )
                else:
                    self.validated_keys.append("chroma_collection_name")

        except Exception as e:
            self.errors.append(f"Invalid ChromaDB path: {e}")

    def _validate_ai_model_configs(self, settings: Any) -> None:
        """Validate AI model configurations"""
        try:
            ai_configs = getattr(settings, "AI_MODEL_CONFIGS", {})

            if not isinstance(ai_configs, dict):
                self.errors.append("AI_MODEL_CONFIGS must be a dictionary")
                return

            required_fields = ["type", "model"]

            for provider, config in ai_configs.items():
                if not isinstance(config, dict):
                    self.errors.append(f"Invalid config for provider {provider}")
                    continue

                # Check required fields
                for field in required_fields:
                    if field not in config:
                        self.errors.append(f"Missing {field} in {provider} config")

                # Validate provider-specific configurations
                provider_type = config.get("type", "")

                if provider_type == "openai":
                    self._validate_openai_config(provider, config)
                elif provider_type == "anthropic":
                    self._validate_anthropic_config(provider, config)
                elif provider_type == "local":
                    self._validate_local_model_config(provider, config)
                else:
                    self.warnings.append(f"Unknown provider type: {provider_type}")

                self.validated_keys.append(f"ai_config:{provider}")

        except Exception as e:
            self.errors.append(f"Error validating AI model configs: {e}")

    def _validate_openai_config(self, provider: str, config: dict[str, Any]) -> None:
        """Validate OpenAI-specific configuration"""
        model = config.get("model", "")
        valid_models = [
            "gpt-4",
            "gpt-4-turbo",
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-3.5-turbo",
        ]

        if model not in valid_models:
            self.warnings.append(f"Unknown OpenAI model in {provider}: {model}")

        # Validate rate limits
        rate_limit = config.get("rate_limit", {})
        if isinstance(rate_limit, dict):
            rpm = rate_limit.get("requests_per_minute", 0)
            tpm = rate_limit.get("tokens_per_minute", 0)

            if rpm <= 0:
                self.warnings.append(
                    f"Invalid requests_per_minute in {provider}: {rpm}"
                )
            if tpm <= 0:
                self.warnings.append(f"Invalid tokens_per_minute in {provider}: {tpm}")

    def _validate_anthropic_config(self, provider: str, config: dict[str, Any]) -> None:
        """Validate Anthropic-specific configuration"""
        model = config.get("model", "")
        valid_models = [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
        ]

        if model and not any(valid in model for valid in ["claude-3", "claude-2"]):
            self.warnings.append(f"Unknown Anthropic model in {provider}: {model}")

    def _validate_local_model_config(
        self, provider: str, config: dict[str, Any]
    ) -> None:
        """Validate local model configuration"""
        endpoint_url = config.get("endpoint_url", "")

        if endpoint_url:
            try:
                parsed = urlparse(endpoint_url)
                if not parsed.scheme or not parsed.netloc:
                    self.errors.append(
                        f"Invalid endpoint URL in {provider}: {endpoint_url}"
                    )

                if parsed.scheme not in ["http", "https"]:
                    self.warnings.append(
                        f"Non-HTTP endpoint in {provider}: {parsed.scheme}"
                    )

            except Exception as e:
                self.errors.append(f"Invalid endpoint URL format in {provider}: {e}")

    def _validate_service_dependencies(self, settings: Any) -> None:
        """Validate external service dependencies"""
        project_service_url = getattr(settings, "PROJECT_SERVICE_URL", "")

        if project_service_url:
            try:
                parsed = urlparse(project_service_url)
                if not parsed.scheme or not parsed.netloc:
                    self.errors.append(
                        f"Invalid PROJECT_SERVICE_URL: {project_service_url}"
                    )
                else:
                    self.validated_keys.append("project_service_url")
            except Exception as e:
                self.errors.append(f"Invalid PROJECT_SERVICE_URL format: {e}")

    def _validate_performance_settings(self, settings: Any) -> None:
        """Validate performance-related settings"""
        # Validate numeric settings
        numeric_settings = [
            ("MAX_SCRIPT_LENGTH", 1, 100000),
            ("MAX_CONTEXT_LENGTH", 1000, 32000),
            ("EMBEDDING_BATCH_SIZE", 1, 1000),
            ("MAX_SEARCH_RESULTS", 1, 100),
            ("MAX_CONCURRENT_RAG_REQUESTS", 1, 50),
        ]

        for setting_name, min_val, max_val in numeric_settings:
            value = getattr(settings, setting_name, None)
            if value is not None:
                try:
                    numeric_value = int(value)
                    if not (min_val <= numeric_value <= max_val):
                        self.warnings.append(
                            f"{setting_name} ({numeric_value}) outside recommended range {min_val}-{max_val}"
                        )
                    else:
                        self.validated_keys.append(f"numeric_setting:{setting_name}")
                except (ValueError, TypeError):
                    self.errors.append(
                        f"Invalid numeric value for {setting_name}: {value}"
                    )

        # Validate float settings
        similarity_threshold = getattr(settings, "SIMILARITY_THRESHOLD", None)
        if similarity_threshold is not None:
            try:
                float_value = float(similarity_threshold)
                if not (0.0 <= float_value <= 1.0):
                    self.errors.append(
                        f"SIMILARITY_THRESHOLD must be between 0.0 and 1.0: {float_value}"
                    )
                else:
                    self.validated_keys.append("similarity_threshold")
            except (ValueError, TypeError):
                self.errors.append(
                    f"Invalid float value for SIMILARITY_THRESHOLD: {similarity_threshold}"
                )


async def validate_external_connections(
    settings: Any,
) -> tuple[bool, list[str], list[str]]:
    """
    Validate external service connections

    Returns:
        (all_healthy, errors, warnings)
    """
    errors = []
    warnings = []

    # Test project service connection
    project_service_url = getattr(settings, "PROJECT_SERVICE_URL", "")
    if project_service_url:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{project_service_url}/health")
                if response.status_code != 200:
                    warnings.append(
                        f"Project service unhealthy: {response.status_code}"
                    )
                else:
                    logger.info("Project service connection validated")
        except Exception as e:
            warnings.append(f"Cannot connect to project service: {e}")

    # Test database connection
    database_url = getattr(settings, "DATABASE_URL", "")
    if database_url:
        try:
            # Basic connection test would go here
            # For now, we just validate the URL format was already checked
            logger.info("Database configuration validated")
        except Exception as e:
            errors.append(f"Database connection failed: {e}")

    all_healthy = len(errors) == 0
    return all_healthy, errors, warnings


def validate_environment_compatibility() -> tuple[bool, list[str]]:
    """Validate environment compatibility"""
    import platform
    import sys

    issues = []

    # Python version check
    if sys.version_info < (3, 8):
        issues.append(f"Python 3.8+ required, found {sys.version}")

    # Platform-specific checks
    if platform.system() == "Windows":
        # Windows-specific validations
        pass
    elif platform.system() == "Darwin":
        # macOS-specific validations
        pass
    elif platform.system() == "Linux":
        # Linux-specific validations
        pass

    return issues


def get_config_summary(settings: Any) -> dict[str, Any]:
    """Get configuration summary for debugging"""

    def safe_get(attr: str, default: str = "<not set>") -> str:
        value = getattr(settings, attr, default)
        # Mask sensitive information
        if "key" in attr.lower() or "password" in attr.lower():
            if value and value != default:
                return f"{'*' * (len(str(value)) - 4)}{str(value)[-4:]}"
        return value

    return {
        "service": {
            "name": safe_get("SERVICE_NAME"),
            "port": safe_get("PORT"),
            "debug": safe_get("DEBUG"),
        },
        "database": {
            "url": safe_get("DATABASE_URL"),
        },
        "ai_providers": {
            "openai_key": safe_get("OPENAI_API_KEY"),
            "anthropic_key": safe_get("ANTHROPIC_API_KEY"),
            "default_model": safe_get("DEFAULT_MODEL"),
        },
        "rag_system": {
            "chroma_path": safe_get("CHROMA_DB_PATH"),
            "collection": safe_get("CHROMA_COLLECTION_NAME"),
            "embedding_model": safe_get("EMBEDDING_MODEL"),
        },
        "external_services": {
            "project_service": safe_get("PROJECT_SERVICE_URL"),
        },
    }
