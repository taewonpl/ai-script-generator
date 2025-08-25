"""
AI Script Generator v3.0 Core Library

A comprehensive shared core library for AI Script Generator v3.0 microservices architecture.
Provides essential DTOs, exception handling, configuration management, logging, and utility functions.

Features:
- Pydantic-based data schemas and validation
- Comprehensive exception handling system
- Advanced configuration management with environment support
- Structured JSON logging with context tracking
- Rich utility functions for UUID generation, date formatting, text processing
- Service health monitoring capabilities
- Type-safe APIs with full type hints

Perfect for building scalable microservices with consistent data models and error handling.
"""

import sys
from typing import Any

# 버전 정보
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

# 주요 모듈 임포트
from .ai_script_core import exceptions, schemas, utils

# 주요 예외 Export
from .ai_script_core.exceptions import (
    AIModelError,
    AuthenticationError,
    AuthorizationError,
    # Base exceptions
    BaseServiceException,
    DatabaseError,
    GatewayError,
    GenerationServiceError,
    NotFoundError,
    ProjectNotFoundError,
    # Service-specific exceptions
    ProjectServiceError,
    RAGServiceError,
    ServiceUnavailableError,
    ValidationException,
    error_response_formatter,
    # Exception utilities
    exception_handler,
    log_exception,
)

# 주요 스키마 Export
from .ai_script_core.schemas import (
    AIModelConfigDTO,
    # Base schemas
    BaseSchema,
    EpisodeCreateDTO,
    EpisodeResponseDTO,
    EpisodeType,
    GenerationMetadataDTO,
    # Generation schemas
    GenerationRequestDTO,
    GenerationResponseDTO,
    GenerationStatus,
    IDMixin,
    # Project schemas
    ProjectCreateDTO,
    ProjectResponseDTO,
    # Common enums and types
    ProjectStatus,
    ProjectUpdateDTO,
    RAGConfigDTO,
    TimestampMixin,
)

# 주요 유틸리티 Export
from .ai_script_core.utils import (
    APISettings,
    DatabaseSettings,
    LoggingSettings,
    SecuritySettings,
    calculate_age,
    calculate_hash,
    check_multiple_services,
    clean_filename,
    create_request_logger,
    # Date/time utilities
    format_datetime,
    generate_prefixed_id,
    generate_short_id,
    # UUID generation
    generate_uuid,
    # Logging
    get_service_logger,
    # Configuration
    get_settings,
    safe_json_dumps,
    # Miscellaneous
    safe_json_loads,
    # Text processing
    sanitize_text,
    utc_now,
    # Service health
    validate_service_health,
)
from .ai_script_core.utils import (
    log_exception as log_exception_util,
)

# 공개 API
__all__ = [
    # Package metadata
    "__version__",
    "__author__",
    "__description__",
    "get_version",
    "get_package_info",
    "check_python_version",
    # Modules
    "schemas",
    "exceptions",
    "utils",
    # Base Schemas
    "BaseSchema",
    "IDMixin",
    "TimestampMixin",
    # Common Types
    "ProjectStatus",
    "GenerationStatus",
    "EpisodeType",
    # Project Schemas
    "ProjectCreateDTO",
    "ProjectResponseDTO",
    "ProjectUpdateDTO",
    "EpisodeCreateDTO",
    "EpisodeResponseDTO",
    # Generation Schemas
    "GenerationRequestDTO",
    "GenerationResponseDTO",
    "AIModelConfigDTO",
    "RAGConfigDTO",
    "GenerationMetadataDTO",
    # Base Exceptions
    "BaseServiceException",
    "ValidationException",
    "NotFoundError",
    "ServiceUnavailableError",
    "AuthenticationError",
    "AuthorizationError",
    # Service Exceptions
    "ProjectServiceError",
    "ProjectNotFoundError",
    "GenerationServiceError",
    "AIModelError",
    "RAGServiceError",
    "GatewayError",
    "DatabaseError",
    # Exception Utilities
    "exception_handler",
    "error_response_formatter",
    "log_exception",
    # Configuration
    "get_settings",
    "DatabaseSettings",
    "APISettings",
    "LoggingSettings",
    "SecuritySettings",
    # Logging
    "get_service_logger",
    "create_request_logger",
    "log_exception_util",
    # UUID Generation
    "generate_uuid",
    "generate_short_id",
    "generate_prefixed_id",
    # Date/Time
    "format_datetime",
    "utc_now",
    "calculate_age",
    # Text Processing
    "sanitize_text",
    "clean_filename",
    # Service Health
    "validate_service_health",
    "check_multiple_services",
    # Utilities
    "safe_json_loads",
    "safe_json_dumps",
    "calculate_hash",
]
