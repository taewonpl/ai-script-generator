"""
AI Script Generator v3.0 Core Library

A comprehensive shared core library for AI Script Generator v3.0 microservices architecture.
Provides essential DTOs, exception handling, configuration management, logging, and utility functions.
"""

import sys
from typing import Any

# Version information
__version__ = "0.1.0"
__author__ = "AI Script Generator Team"
__description__ = "Core library for AI Script Generator v3.0 microservices - schemas, exceptions, and utilities"


def get_version() -> str:
    """패키지 버전 반환"""
    return __version__


def get_package_info() -> dict[str, Any]:
    """패키지 정보 반환"""
    return {
        "name": "ai-script-core",
        "version": __version__,
        "author": __author__,
        "description": __description__,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "supported_python": ">=3.10",
    }


def check_python_version() -> bool:
    """Python 버전 호환성 확인"""
    return sys.version_info >= (3, 9)


# Python 버전 체크
if not check_python_version():
    raise RuntimeError(
        f"AI Script Core requires Python 3.9 or higher. "
        f"Current version: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )

# Core module imports
from . import exceptions, schemas, utils

# Essential Exception Exports
from .exceptions import (
    BaseServiceException,
    GenerationServiceError,
    NotFoundError,
    ProjectNotFoundError,
    # Service-specific exceptions
    ValidationException,
)

# Essential Schema Exports
from .schemas import (
    # Generation schemas
    AIModelConfigDTO,
    BaseSchema,
    CommonResponseDTO,
    EpisodeCreateDTO,
    EpisodeDTO,
    EpisodeType,
    EpisodeUpdateDTO,
    ErrorResponseDTO,
    GenerationRequestDTO,
    GenerationResponseDTO,
    GenerationStatus,
    ProjectCreateDTO,
    ProjectDTO,
    # Backward compatibility aliases
    ProjectStatus,
    ProjectType,
    ProjectUpdateDTO,
    RAGConfigDTO,
    SuccessResponseDTO,
)

# Essential Utility Exports
from .utils import (
    calculate_hash,
    format_datetime,
    generate_prefixed_id,
    generate_uuid,
    # Logging
    get_service_logger,
    # Configuration
    get_settings,
    safe_json_dumps,
    # Utilities
    safe_json_loads,
    # Text processing
    sanitize_text,
    # Time utilities
    utc_now,
)

# Public API - Only essential items for clean imports
__all__ = [
    # Package metadata
    "__version__",
    "__author__",
    "__description__",
    "get_version",
    "get_package_info",
    "check_python_version",
    # Core modules (for advanced usage)
    "schemas",
    "exceptions",
    "utils",
    # Essential schemas - most commonly used
    "BaseSchema",
    "ProjectDTO",
    "ProjectCreateDTO",
    "ProjectUpdateDTO",
    "EpisodeDTO",
    "EpisodeCreateDTO",
    "EpisodeUpdateDTO",
    "GenerationRequestDTO",
    "GenerationResponseDTO",
    "AIModelConfigDTO",
    "RAGConfigDTO",
    # Common types
    "ProjectStatus",
    "ProjectType",
    "EpisodeType",
    "GenerationStatus",
    # Response types
    "CommonResponseDTO",
    "SuccessResponseDTO",
    "ErrorResponseDTO",
    # Essential exceptions
    "BaseServiceException",
    "ValidationException",
    "NotFoundError",
    "ProjectNotFoundError",
    "GenerationServiceError",
    # Essential utilities
    "get_settings",
    "get_service_logger",
    "calculate_hash",
    "generate_prefixed_id",
    "generate_uuid",
    "format_datetime",
    "sanitize_text",
    "safe_json_loads",
    "safe_json_dumps",
    "utc_now",
]
