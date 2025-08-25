"""
Fallback configuration base class for Generation Service
"""

import json
import os
from typing import Any


class ConfigField:
    """Simple field descriptor for configuration"""

    def __init__(self, default: Any = None, env: str | None = None) -> None:
        self.default = default
        self.env = env

    def __set_name__(self, owner: Any, name: str) -> None:
        self.name = name
        if not self.env:
            self.env = name


class BaseConfiguration:
    """Fallback base configuration class"""

    def __init__(self, **kwargs: Any) -> None:
        # Load environment variables
        self._load_env_file()

        # Set defaults and environment overrides
        for attr_name in dir(self):
            attr_value = getattr(self.__class__, attr_name, None)
            if isinstance(attr_value, ConfigField):
                # Get value from environment or use default
                env_value = os.getenv(attr_value.env)
                if env_value is not None:
                    # Convert string values to appropriate types
                    value = self._convert_env_value(env_value)
                else:
                    value = attr_value.default

                setattr(self, attr_name, value)

        # Override with any provided kwargs
        for key, value in kwargs.items():
            setattr(self, key, value)

    def _load_env_file(self) -> None:
        """Load .env file if it exists"""
        env_files = [".env", ".env.local"]

        for env_file in env_files:
            if os.path.exists(env_file):
                with open(env_file) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            key = key.strip()
                            value = value.strip().strip("\"'")
                            if key and key not in os.environ:
                                os.environ[key] = value
                break

    def _convert_env_value(self, value: str) -> Any:
        """Convert string environment value to appropriate type"""
        # Boolean conversion
        if value.lower() in ("true", "false"):
            return value.lower() == "true"

        # Integer conversion
        try:
            return int(value)
        except ValueError:
            pass

        # Float conversion
        try:
            return float(value)
        except ValueError:
            pass

        # JSON conversion for complex types
        if value.startswith(("[", "{")):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, ValueError):
                pass

        # List conversion (comma-separated)
        if "," in value:
            return [item.strip() for item in value.split(",")]

        # Return as string
        return value


def Field(default: Any = None, env: str | None = None) -> ConfigField:
    """Create a configuration field"""
    return ConfigField(default=default, env=env)


# Use our fallback implementation by default
ConfigBase = BaseConfiguration


class GenerationServiceSettings(ConfigBase):
    """Generation Service specific settings"""

    # Service Configuration
    SERVICE_NAME: str = Field(default="generation-service", env="SERVICE_NAME")
    PORT: int = Field(default=8002, env="PORT")
    DEBUG: bool = Field(default=False, env="DEBUG")
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")

    # CORS Configuration
    ALLOWED_ORIGINS: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        env="ALLOWED_ORIGINS",
    )

    # Database Configuration
    # No default value - will be determined by environment in config_loader.py
    DATABASE_URL: str = Field(default=None, env="DATABASE_URL")

    # AI Service Configuration
    OPENAI_API_KEY: str = Field(default="", env="OPENAI_API_KEY")
    ANTHROPIC_API_KEY: str = Field(default="", env="ANTHROPIC_API_KEY")
    LOCAL_MODEL_ENDPOINT: str = Field(
        default="http://localhost:8080", env="LOCAL_MODEL_ENDPOINT"
    )
    LOCAL_MODEL_API_KEY: str = Field(default="", env="LOCAL_MODEL_API_KEY")

    # Generation Settings
    MAX_SCRIPT_LENGTH: int = Field(default=10000, env="MAX_SCRIPT_LENGTH")
    DEFAULT_MODEL: str = Field(default="gpt-4o", env="DEFAULT_MODEL")

    # Data Paths Configuration - Environment specific defaults
    DATA_ROOT_PATH: str = Field(default="./data", env="DATA_ROOT_PATH")
    CHROMA_DB_PATH: str = Field(default="./data/chroma", env="CHROMA_DB_PATH")
    VECTOR_DATA_PATH: str = Field(default="./data/vectors", env="VECTOR_DATA_PATH")
    LOG_DATA_PATH: str = Field(default="./data/logs", env="LOG_DATA_PATH")
    CACHE_DATA_PATH: str = Field(default="./data/cache", env="CACHE_DATA_PATH")

    # RAG System Configuration
    CHROMA_COLLECTION_NAME: str = Field(
        default="script_knowledge", env="CHROMA_COLLECTION_NAME"
    )
    EMBEDDING_MODEL: str = Field(
        default="text-embedding-ada-002", env="EMBEDDING_MODEL"
    )
    MAX_CONTEXT_LENGTH: int = Field(default=8000, env="MAX_CONTEXT_LENGTH")
    EMBEDDING_BATCH_SIZE: int = Field(default=100, env="EMBEDDING_BATCH_SIZE")

    # External Services
    PROJECT_SERVICE_URL: str = Field(
        default="http://localhost:8001", env="PROJECT_SERVICE_URL"
    )

    # Performance Settings
    MAX_SEARCH_RESULTS: int = Field(default=10, env="MAX_SEARCH_RESULTS")
    SIMILARITY_THRESHOLD: float = Field(default=0.7, env="SIMILARITY_THRESHOLD")
    CONTEXT_OVERLAP_RATIO: float = Field(default=0.1, env="CONTEXT_OVERLAP_RATIO")
    CHUNKING_STRATEGY: str = Field(default="sentence", env="CHUNKING_STRATEGY")

    # Cache Settings
    RAG_CACHE_ENABLED: bool = Field(default=True, env="RAG_CACHE_ENABLED")
    RAG_CACHE_TTL_HOURS: int = Field(default=24, env="RAG_CACHE_TTL_HOURS")
    MAX_CONCURRENT_RAG_REQUESTS: int = Field(
        default=10, env="MAX_CONCURRENT_RAG_REQUESTS"
    )

    def get_ai_provider_config(self) -> dict[str, Any]:
        """Get AI provider configurations"""
        return {
            "openai": {
                "type": "openai",
                "api_key": self.OPENAI_API_KEY,
                "model": "gpt-4o",
                "max_retries": 3,
                "timeout": 60,
            },
            "anthropic": {
                "type": "anthropic",
                "api_key": self.ANTHROPIC_API_KEY,
                "model": "claude-3-5-sonnet-20241022",
                "max_retries": 3,
                "timeout": 120,
            },
            "local": {
                "type": "local",
                "endpoint_url": self.LOCAL_MODEL_ENDPOINT,
                "api_key": self.LOCAL_MODEL_API_KEY,
                "timeout": 300,
            },
        }

    def get_rag_configuration(self) -> dict[str, Any]:
        """Get RAG system configuration"""
        return {
            "chroma_db_path": self.CHROMA_DB_PATH,
            "collection_name": self.CHROMA_COLLECTION_NAME,
            "embedding_model": self.EMBEDDING_MODEL,
            "max_context_length": self.MAX_CONTEXT_LENGTH,
            "embedding_batch_size": self.EMBEDDING_BATCH_SIZE,
            "max_search_results": self.MAX_SEARCH_RESULTS,
            "similarity_threshold": self.SIMILARITY_THRESHOLD,
            "context_overlap_ratio": self.CONTEXT_OVERLAP_RATIO,
            "chunking_strategy": self.CHUNKING_STRATEGY,
            "cache_enabled": self.RAG_CACHE_ENABLED,
            "cache_ttl_hours": self.RAG_CACHE_TTL_HOURS,
            "max_concurrent_requests": self.MAX_CONCURRENT_RAG_REQUESTS,
        }

    # Add Config class for pydantic compatibility
    if hasattr(ConfigBase, "__annotations__"):

        class Config:
            env_file = ".env"
            case_sensitive = True
