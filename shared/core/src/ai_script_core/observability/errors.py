"""
Standardized error handling and response format for all services.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class HttpStatusCode(int, Enum):
    """Standardized HTTP status codes across all services."""

    # Success
    SUCCESS = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204

    # Client Errors
    BAD_REQUEST = 400  # Validation failures
    UNAUTHORIZED = 401  # Authentication required
    FORBIDDEN = 403  # Authorization failed
    NOT_FOUND = 404  # Resource not found (project/episode)
    METHOD_NOT_ALLOWED = 405
    CONFLICT = 409  # Episode number conflicts
    UNPROCESSABLE_ENTITY = 422  # Business rule violations
    TOO_MANY_REQUESTS = 429  # Rate limiting

    # Server Errors
    INTERNAL_SERVER_ERROR = 500  # Internal server errors
    BAD_GATEWAY = 502  # Upstream service errors
    SERVICE_UNAVAILABLE = 503  # External service outages (OpenAI, ChromaDB)
    GATEWAY_TIMEOUT = 504  # Service timeout


class ErrorCode(str, Enum):
    """Standardized error codes across all services."""

    # Validation Errors (400)
    VALIDATION_FAILED = "VALIDATION_FAILED"
    INVALID_REQUEST_FORMAT = "INVALID_REQUEST_FORMAT"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_FIELD_VALUE = "INVALID_FIELD_VALUE"

    # Authentication/Authorization Errors (401/403)
    AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
    INVALID_TOKEN = "INVALID_TOKEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"

    # Resource Not Found Errors (404)
    PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"
    EPISODE_NOT_FOUND = "EPISODE_NOT_FOUND"
    GENERATION_JOB_NOT_FOUND = "GENERATION_JOB_NOT_FOUND"
    USER_NOT_FOUND = "USER_NOT_FOUND"

    # Conflict Errors (409)
    EPISODE_NUMBER_CONFLICT = "EPISODE_NUMBER_CONFLICT"
    PROJECT_NAME_CONFLICT = "PROJECT_NAME_CONFLICT"
    RESOURCE_ALREADY_EXISTS = "RESOURCE_ALREADY_EXISTS"

    # Business Rule Violations (422)
    INVALID_GENERATION_PROMPT = "INVALID_GENERATION_PROMPT"
    EPISODE_LIMIT_EXCEEDED = "EPISODE_LIMIT_EXCEEDED"
    PROJECT_ARCHIVED = "PROJECT_ARCHIVED"
    GENERATION_IN_PROGRESS = "GENERATION_IN_PROGRESS"

    # Rate Limiting (429)
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    DAILY_QUOTA_EXCEEDED = "DAILY_QUOTA_EXCEEDED"
    CONCURRENT_LIMIT_EXCEEDED = "CONCURRENT_LIMIT_EXCEEDED"

    # Internal Server Errors (500)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    EPISODE_SAVE_FAILED = "EPISODE_SAVE_FAILED"
    GENERATION_FAILED = "GENERATION_FAILED"

    # External Service Errors (503)
    OPENAI_SERVICE_UNAVAILABLE = "OPENAI_SERVICE_UNAVAILABLE"
    CHROMADB_CONNECTION_FAILED = "CHROMADB_CONNECTION_FAILED"
    EXTERNAL_API_ERROR = "EXTERNAL_API_ERROR"
    SERVICE_DEGRADED = "SERVICE_DEGRADED"

    # Network/Timeout Errors (504)
    REQUEST_TIMEOUT = "REQUEST_TIMEOUT"
    GENERATION_TIMEOUT = "GENERATION_TIMEOUT"
    DATABASE_TIMEOUT = "DATABASE_TIMEOUT"


class ErrorDetail(BaseModel):
    """Detailed error information."""

    code: ErrorCode = Field(..., description="Standardized error code")
    message: str = Field(..., description="Human-readable error message")
    details: dict[str, Any] | None = Field(
        default=None, description="Additional error context and debugging information"
    )
    trace_id: str | None = Field(
        default=None, description="Unique trace ID for request tracking"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Error occurrence timestamp"
    )


class StandardErrorResponse(BaseModel):
    """Standardized error response format for all services."""

    success: bool = Field(default=False, description="Always false for error responses")
    error: ErrorDetail = Field(..., description="Error details")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() + "Z"}


class StandardSuccessResponse(BaseModel):
    """Standardized success response format."""

    success: bool = Field(default=True, description="Always true for success responses")
    data: Any | None = Field(default=None, description="Response data payload")
    message: str | None = Field(default=None, description="Optional success message")

    # Response metadata
    trace_id: str | None = Field(default=None, description="Request trace ID")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() + "Z"}


def create_error_response(
    code: ErrorCode,
    message: str,
    details: dict[str, Any] | None = None,
    trace_id: str | None = None,
    timestamp: datetime | None = None,
) -> StandardErrorResponse:
    """Create a standardized error response."""

    error_detail = ErrorDetail(
        code=code,
        message=message,
        details=details or {},
        trace_id=trace_id,
        timestamp=timestamp or datetime.utcnow(),
    )

    return StandardErrorResponse(error=error_detail)


def create_success_response(
    data: Any = None,
    message: str | None = None,
    trace_id: str | None = None,
    timestamp: datetime | None = None,
) -> StandardSuccessResponse:
    """Create a standardized success response."""

    return StandardSuccessResponse(
        data=data,
        message=message,
        trace_id=trace_id,
        timestamp=timestamp or datetime.utcnow(),
    )


# Common error response mappings
COMMON_ERROR_MESSAGES = {
    ErrorCode.PROJECT_NOT_FOUND: "요청한 프로젝트를 찾을 수 없습니다.",
    ErrorCode.EPISODE_NOT_FOUND: "요청한 에피소드를 찾을 수 없습니다.",
    ErrorCode.GENERATION_JOB_NOT_FOUND: "요청한 생성 작업을 찾을 수 없습니다.",
    ErrorCode.EPISODE_NUMBER_CONFLICT: "해당 에피소드 번호가 이미 존재합니다.",
    ErrorCode.EPISODE_SAVE_FAILED: "에피소드 저장 중 오류가 발생했습니다.",
    ErrorCode.GENERATION_FAILED: "콘텐츠 생성 중 오류가 발생했습니다.",
    ErrorCode.CHROMADB_CONNECTION_FAILED: "벡터 데이터베이스 연결에 실패했습니다.",
    ErrorCode.OPENAI_SERVICE_UNAVAILABLE: "AI 서비스가 일시적으로 이용할 수 없습니다.",
    ErrorCode.VALIDATION_FAILED: "입력 데이터 검증에 실패했습니다.",
    ErrorCode.RATE_LIMIT_EXCEEDED: "요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요.",
    ErrorCode.INTERNAL_ERROR: "내부 서버 오류가 발생했습니다.",
}


def get_error_message(code: ErrorCode, custom_message: str | None = None) -> str:
    """Get localized error message for error code."""
    return custom_message or COMMON_ERROR_MESSAGES.get(
        code, "알 수 없는 오류가 발생했습니다."
    )


def get_http_status_for_error(code: ErrorCode) -> HttpStatusCode:
    """Map error codes to appropriate HTTP status codes."""

    status_mapping = {
        # 400 - Bad Request
        ErrorCode.VALIDATION_FAILED: HttpStatusCode.BAD_REQUEST,
        ErrorCode.INVALID_REQUEST_FORMAT: HttpStatusCode.BAD_REQUEST,
        ErrorCode.MISSING_REQUIRED_FIELD: HttpStatusCode.BAD_REQUEST,
        ErrorCode.INVALID_FIELD_VALUE: HttpStatusCode.BAD_REQUEST,
        # 401 - Unauthorized
        ErrorCode.AUTHENTICATION_REQUIRED: HttpStatusCode.UNAUTHORIZED,
        ErrorCode.INVALID_TOKEN: HttpStatusCode.UNAUTHORIZED,
        ErrorCode.TOKEN_EXPIRED: HttpStatusCode.UNAUTHORIZED,
        # 403 - Forbidden
        ErrorCode.INSUFFICIENT_PERMISSIONS: HttpStatusCode.FORBIDDEN,
        # 404 - Not Found
        ErrorCode.PROJECT_NOT_FOUND: HttpStatusCode.NOT_FOUND,
        ErrorCode.EPISODE_NOT_FOUND: HttpStatusCode.NOT_FOUND,
        ErrorCode.GENERATION_JOB_NOT_FOUND: HttpStatusCode.NOT_FOUND,
        ErrorCode.USER_NOT_FOUND: HttpStatusCode.NOT_FOUND,
        # 409 - Conflict
        ErrorCode.EPISODE_NUMBER_CONFLICT: HttpStatusCode.CONFLICT,
        ErrorCode.PROJECT_NAME_CONFLICT: HttpStatusCode.CONFLICT,
        ErrorCode.RESOURCE_ALREADY_EXISTS: HttpStatusCode.CONFLICT,
        # 422 - Unprocessable Entity
        ErrorCode.INVALID_GENERATION_PROMPT: HttpStatusCode.UNPROCESSABLE_ENTITY,
        ErrorCode.EPISODE_LIMIT_EXCEEDED: HttpStatusCode.UNPROCESSABLE_ENTITY,
        ErrorCode.PROJECT_ARCHIVED: HttpStatusCode.UNPROCESSABLE_ENTITY,
        ErrorCode.GENERATION_IN_PROGRESS: HttpStatusCode.UNPROCESSABLE_ENTITY,
        # 429 - Too Many Requests
        ErrorCode.RATE_LIMIT_EXCEEDED: HttpStatusCode.TOO_MANY_REQUESTS,
        ErrorCode.DAILY_QUOTA_EXCEEDED: HttpStatusCode.TOO_MANY_REQUESTS,
        ErrorCode.CONCURRENT_LIMIT_EXCEEDED: HttpStatusCode.TOO_MANY_REQUESTS,
        # 503 - Service Unavailable
        ErrorCode.OPENAI_SERVICE_UNAVAILABLE: HttpStatusCode.SERVICE_UNAVAILABLE,
        ErrorCode.CHROMADB_CONNECTION_FAILED: HttpStatusCode.SERVICE_UNAVAILABLE,
        ErrorCode.EXTERNAL_API_ERROR: HttpStatusCode.SERVICE_UNAVAILABLE,
        ErrorCode.SERVICE_DEGRADED: HttpStatusCode.SERVICE_UNAVAILABLE,
        # 504 - Gateway Timeout
        ErrorCode.REQUEST_TIMEOUT: HttpStatusCode.GATEWAY_TIMEOUT,
        ErrorCode.GENERATION_TIMEOUT: HttpStatusCode.GATEWAY_TIMEOUT,
        ErrorCode.DATABASE_TIMEOUT: HttpStatusCode.GATEWAY_TIMEOUT,
    }

    return status_mapping.get(code, HttpStatusCode.INTERNAL_SERVER_ERROR)
