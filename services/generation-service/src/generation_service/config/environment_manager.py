"""
Environment configuration manager for Generation Service
"""

import logging
import os
from enum import Enum
from pathlib import Path
from typing import Any


class Environment(str, Enum):
    """Environment types"""

    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


class EnvironmentManager:
    """Manages environment-specific configuration loading and validation"""

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)  # type: ignore[assignment]
        self.current_env = self._detect_environment()
        self.config_dir = Path(__file__).parent.parent.parent

    def _detect_environment(self) -> Environment:
        """Detect current environment from various sources"""

        # Check explicit environment variable
        env_var = os.getenv("ENVIRONMENT", os.getenv("ENV", "")).lower()
        if env_var in [e.value for e in Environment]:
            return Environment(env_var)

        # Check DEBUG flag
        if os.getenv("DEBUG", "false").lower() == "true":
            return Environment.DEVELOPMENT

        # Check for Docker environment
        if os.path.exists("/.dockerenv") or os.getenv("DOCKER_ENV"):
            return Environment.PRODUCTION

        # Check for testing frameworks
        if any(
            framework in os.environ.get("PYTEST_CURRENT_TEST", "")
            for framework in ["pytest", "test"]
        ):
            return Environment.TESTING

        # Default to development
        return Environment.DEVELOPMENT

    def load_environment_file(self) -> dict[str, str]:
        """Load environment-specific configuration file"""

        env_files = [
            f".env.{self.current_env.value}",
            f".env.{self.current_env.value}.local",
            ".env.local",
            ".env",
        ]

        loaded_vars = {}

        for env_file in env_files:
            env_path = self.config_dir / env_file
            if env_path.exists():
                self.logger.info(f"Loading environment file: {env_file}")
                env_vars = self._parse_env_file(env_path)
                loaded_vars.update(env_vars)

        # Apply loaded variables to environment (only if not already set)
        for key, value in loaded_vars.items():
            if key not in os.environ:
                os.environ[key] = value

        self.logger.info(f"Environment detected: {self.current_env.value}")
        return loaded_vars

    def _parse_env_file(self, file_path: Path) -> dict[str, str]:
        """Parse environment file and return key-value pairs"""

        env_vars = {}

        try:
            with open(file_path, encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()

                    # Skip empty lines and comments
                    if not line or line.startswith("#"):
                        continue

                    # Parse key=value pairs
                    if "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip()

                        # Remove quotes if present
                        if (value.startswith('"') and value.endswith('"')) or (
                            value.startswith("'") and value.endswith("'")
                        ):
                            value = value[1:-1]

                        env_vars[key] = value
                    else:
                        self.logger.warning(
                            f"Invalid line in {file_path}:{line_num}: {line}"
                        )

        except Exception as e:
            self.logger.error(f"Error parsing environment file {file_path}: {e}")

        return env_vars

    def validate_data_paths(self) -> dict[str, Any]:
        """Validate and ensure data paths are properly configured"""

        validation_results: dict[str, Any] = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "created_paths": [],
        }

        # Define required data paths
        data_paths = {
            "DATA_ROOT_PATH": os.getenv("DATA_ROOT_PATH", "/app/data"),
            "CHROMA_DB_PATH": os.getenv("CHROMA_DB_PATH", "/app/data/chroma"),
            "VECTOR_DATA_PATH": os.getenv("VECTOR_DATA_PATH", "/app/data/vectors"),
            "LOG_DATA_PATH": os.getenv("LOG_DATA_PATH", "/app/data/logs"),
            "CACHE_DATA_PATH": os.getenv("CACHE_DATA_PATH", "/app/data/cache"),
        }

        for path_name, path_value in data_paths.items():
            try:
                path_obj = Path(path_value)

                # Check if path is absolute (recommended for production)
                if (
                    not path_obj.is_absolute()
                    and self.current_env == Environment.PRODUCTION
                ):
                    validation_results["warnings"].append(
                        f"{path_name} should be absolute in production: {path_value}"
                    )

                # Create directory if it doesn't exist
                if not path_obj.exists():
                    try:
                        path_obj.mkdir(parents=True, exist_ok=True)
                        validation_results["created_paths"].append(str(path_obj))
                        self.logger.info(f"Created directory: {path_obj}")
                    except PermissionError:
                        validation_results["errors"].append(
                            f"Permission denied creating {path_name}: {path_value}"
                        )
                        validation_results["valid"] = False
                    except Exception as e:
                        validation_results["errors"].append(
                            f"Failed to create {path_name}: {path_value} - {e}"
                        )
                        validation_results["valid"] = False

                # Check if directory is writable
                elif not os.access(path_obj, os.W_OK):
                    validation_results["warnings"].append(
                        f"{path_name} is not writable: {path_value}"
                    )

            except Exception as e:
                validation_results["errors"].append(
                    f"Invalid path for {path_name}: {path_value} - {e}"
                )
                validation_results["valid"] = False

        return validation_results

    def get_environment_info(self) -> dict[str, Any]:
        """Get comprehensive environment information"""

        return {
            "environment": self.current_env.value,
            "is_docker": os.path.exists("/.dockerenv"),
            "is_debug": os.getenv("DEBUG", "false").lower() == "true",
            "data_paths": {
                "root": os.getenv("DATA_ROOT_PATH", "/app/data"),
                "chroma": os.getenv("CHROMA_DB_PATH", "/app/data/chroma"),
                "vectors": os.getenv("VECTOR_DATA_PATH", "/app/data/vectors"),
                "logs": os.getenv("LOG_DATA_PATH", "/app/data/logs"),
                "cache": os.getenv("CACHE_DATA_PATH", "/app/data/cache"),
            },
            "service_config": {
                "name": os.getenv("SERVICE_NAME", "generation-service"),
                "port": int(os.getenv("PORT", "8002")),
                "host": os.getenv("GENERATION_SERVICE_HOST", "0.0.0.0"),
            },
        }

    def validate_critical_settings(self) -> dict[str, Any]:
        """Validate critical settings for the current environment"""

        validation_results = {"valid": True, "errors": [], "warnings": []}

        # Critical settings by environment
        critical_settings = {
            Environment.PRODUCTION: ["DATABASE_URL", "DATA_ROOT_PATH"],
            Environment.DEVELOPMENT: ["DATA_ROOT_PATH"],
            Environment.TESTING: ["DATA_ROOT_PATH"],
        }

        # Check required settings for current environment
        required_settings = critical_settings.get(self.current_env, [])

        for setting in required_settings:
            value = os.getenv(setting)
            if not value:
                validation_results["errors"].append(
                    f"Missing required setting: {setting}"
                )
                validation_results["valid"] = False

        # Environment-specific validations
        if self.current_env == Environment.PRODUCTION:
            # Check for placeholder values in production
            ai_keys = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]
            for key in ai_keys:
                value = os.getenv(key, "")
                if not value or value.startswith("your_") or value == "placeholder":
                    validation_results["warnings"].append(
                        f"AI provider key {key} appears to be placeholder or empty"
                    )

            # Check CORS origins in production
            cors_origins = os.getenv("ALLOWED_ORIGINS", "")
            if "localhost" in cors_origins or "127.0.0.1" in cors_origins:
                validation_results["warnings"].append(
                    "CORS origins contain localhost in production environment"
                )

        return validation_results


# Global environment manager instance
env_manager = EnvironmentManager()


def get_environment_manager() -> EnvironmentManager:
    """Get the global environment manager instance"""
    return env_manager


def load_environment() -> dict[str, str]:
    """Load environment configuration (convenience function)"""
    return env_manager.load_environment_file()


def validate_environment() -> dict[str, Any]:
    """Validate environment configuration (convenience function)"""
    path_validation = env_manager.validate_data_paths()
    settings_validation = env_manager.validate_critical_settings()

    return {
        "data_paths": path_validation,
        "settings": settings_validation,
        "environment_info": env_manager.get_environment_info(),
        "overall_valid": path_validation["valid"] and settings_validation["valid"],
    }
