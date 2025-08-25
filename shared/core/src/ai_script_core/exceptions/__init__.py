"""
Exceptions Package for AI Script Generator v3.0

마이크로서비스 아키텍처를 위한 완전한 예외 처리 시스템
"""

# Base Exception Classes and Enums
from .base import (
    AuthenticationError,
    AuthorizationError,
    BaseServiceException,
    BusinessLogicError,
    ConfigurationError,
    ErrorCategory,
    ErrorSeverity,
    ExternalServiceError,
    NotFoundError,
    ServiceUnavailableError,
    ValidationException,
)

# Service-specific Exceptions
from .service_errors import (
    AIModelError,
    ContentFilterError,
    DatabaseConnectionError,
    # Database
    DatabaseError,
    DatabaseIntegrityError,
    DatabaseTransactionError,
    EmbeddingError,
    EpisodeNotFoundError,
    # Gateway
    GatewayError,
    # Generation Service
    GenerationServiceError,
    GenerationTimeoutError,
    KnowledgeBaseNotFoundError,
    LoadBalancingError,
    ProjectNotFoundError,
    ProjectQuotaExceededError,
    # Project Service
    ProjectServiceError,
    ProjectStatusError,
    # RAG Service
    RAGServiceError,
    RateLimitExceededError,
    ServiceDiscoveryError,
    TokenLimitExceededError,
    VectorSearchError,
)

# Exception Handling Utilities
from .utils import (
    ExceptionAnalyzer,
    ExceptionLogger,
    async_exception_handler,
    chain_exceptions,
    error_response_formatter,
    exception_handler,
    format_error_for_api,
    get_exception_statistics,
    log_exception,
    record_exception_stats,
    safe_execute,
)

# 공개 API
__all__ = [
    # Enums
    "ErrorSeverity",
    "ErrorCategory",
    # Base Exception Classes
    "BaseServiceException",
    "ValidationException",
    "NotFoundError",
    "ServiceUnavailableError",
    "AuthenticationError",
    "AuthorizationError",
    "BusinessLogicError",
    "ExternalServiceError",
    "ConfigurationError",
    # Project Service Exceptions
    "ProjectServiceError",
    "ProjectNotFoundError",
    "EpisodeNotFoundError",
    "ProjectStatusError",
    "ProjectQuotaExceededError",
    # Generation Service Exceptions
    "GenerationServiceError",
    "AIModelError",
    "TokenLimitExceededError",
    "GenerationTimeoutError",
    "ContentFilterError",
    # RAG Service Exceptions
    "RAGServiceError",
    "KnowledgeBaseNotFoundError",
    "EmbeddingError",
    "VectorSearchError",
    # Gateway Exceptions
    "GatewayError",
    "ServiceDiscoveryError",
    "LoadBalancingError",
    "RateLimitExceededError",
    # Database Exceptions
    "DatabaseError",
    "DatabaseConnectionError",
    "DatabaseTransactionError",
    "DatabaseIntegrityError",
    # Utilities
    "ExceptionLogger",
    "ExceptionAnalyzer",
    "exception_handler",
    "async_exception_handler",
    "error_response_formatter",
    "format_error_for_api",
    "log_exception",
    "record_exception_stats",
    "get_exception_statistics",
    "safe_execute",
    "chain_exceptions",
]
