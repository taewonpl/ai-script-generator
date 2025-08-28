"""
Base Exception Classes for AI Script Generator v3.0

모든 서비스에서 공통으로 사용하는 기본 예외 클래스들을 정의합니다.
"""

from __future__ import annotations

import traceback
from datetime import datetime
from enum import Enum
from typing import Any


class ErrorSeverity(str, Enum):
    """에러 심각도"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(str, Enum):
    """에러 카테고리"""

    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    NOT_FOUND = "not_found"
    BUSINESS_LOGIC = "business_logic"
    EXTERNAL_SERVICE = "external_service"
    SYSTEM = "system"
    NETWORK = "network"
    DATABASE = "database"


class BaseServiceException(Exception):
    """모든 서비스 예외의 기본 클래스"""

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        user_message: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        self.message = message
        self.error_code = error_code or self.__class__.__name__.upper()
        self.details = details or {}
        self.cause = cause
        self.severity = severity
        self.category = category
        self.user_message = user_message or self._get_default_user_message()
        self.context = context or {}

        # 메타데이터
        self.timestamp = datetime.now()
        self.traceback_str = "".join(traceback.format_stack()[:-1])

        super().__init__(self.message)

    def _get_default_user_message(self) -> str:
        """사용자에게 보여줄 기본 메시지"""
        return "처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."

    def to_dict(self) -> dict[str, Any]:
        """예외를 딕셔너리로 변환"""
        result = {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "user_message": self.user_message,
            "severity": self.severity.value,
            "category": self.category.value,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
            "context": self.context,
        }

        if self.cause:
            result["cause"] = str(self.cause)

        return result

    def add_context(self, key: str, value: Any) -> BaseServiceException:
        """컨텍스트 정보 추가"""
        self.context[key] = value
        return self

    def add_detail(self, key: str, value: Any) -> BaseServiceException:
        """상세 정보 추가"""
        self.details[key] = value
        return self

    def with_cause(self, cause: Exception) -> BaseServiceException:
        """원인 예외 설정"""
        self.cause = cause
        return self

    def __str__(self) -> str:
        return f"{self.__class__.__name__}: {self.message}"

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"message='{self.message}', "
            f"error_code='{self.error_code}', "
            f"severity='{self.severity.value}', "
            f"category='{self.category.value}')"
        )


class ValidationException(BaseServiceException):
    """데이터 검증 실패 예외"""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: Any = None,
        validation_rule: str | None = None,
        **kwargs: Any,
    ) -> None:
        self.field = field
        self.value = value
        self.validation_rule = validation_rule

        details = kwargs.get("details", {})
        if field:
            details["field"] = field
        if value is not None:
            details["invalid_value"] = str(value)
        if validation_rule:
            details["validation_rule"] = validation_rule

        kwargs["details"] = details
        kwargs["category"] = ErrorCategory.VALIDATION
        kwargs["severity"] = ErrorSeverity.LOW

        super().__init__(message, **kwargs)

    def _get_default_user_message(self) -> str:
        if self.field:
            return f"'{self.field}' 필드의 값이 올바르지 않습니다."
        return "입력된 데이터가 올바르지 않습니다."


class NotFoundError(BaseServiceException):
    """리소스를 찾을 수 없는 예외"""

    def __init__(
        self,
        resource_type: str,
        identifier: str | int | dict[str, Any],
        message: str | None = None,
        **kwargs: Any,
    ) -> None:
        self.resource_type = resource_type
        self.identifier = identifier

        if message is None:
            if isinstance(identifier, dict):
                id_str = ", ".join(f"{k}={v}" for k, v in identifier.items())
                message = f"{resource_type} not found with criteria: {id_str}"
            else:
                message = f"{resource_type} not found with id: {identifier}"

        details = kwargs.get("details", {})
        details.update(
            {
                "resource_type": resource_type,
                "identifier": (
                    identifier if not isinstance(identifier, dict) else str(identifier)
                ),
            }
        )

        kwargs["details"] = details
        kwargs["category"] = ErrorCategory.NOT_FOUND
        kwargs["severity"] = ErrorSeverity.LOW

        super().__init__(message, **kwargs)

    def _get_default_user_message(self) -> str:
        return f"요청하신 {self.resource_type}을(를) 찾을 수 없습니다."


class ServiceUnavailableError(BaseServiceException):
    """서비스 이용 불가 예외"""

    def __init__(
        self,
        service_name: str,
        reason: str | None = None,
        retry_after: int | None = None,
        **kwargs: Any,
    ) -> None:
        self.service_name = service_name
        self.reason = reason
        self.retry_after = retry_after

        message = f"Service '{service_name}' is currently unavailable"
        if reason:
            message += f": {reason}"

        details = kwargs.get("details", {})
        details.update(
            {
                "service_name": service_name,
                "reason": reason,
                "retry_after_seconds": retry_after,
            }
        )

        kwargs["details"] = details
        kwargs["category"] = ErrorCategory.EXTERNAL_SERVICE
        kwargs["severity"] = ErrorSeverity.HIGH

        super().__init__(message, **kwargs)

    def _get_default_user_message(self) -> str:
        if self.retry_after:
            return f"{self.service_name} 서비스가 일시적으로 이용할 수 없습니다. {self.retry_after}초 후 다시 시도해주세요."
        return f"{self.service_name} 서비스가 일시적으로 이용할 수 없습니다."


class AuthenticationError(BaseServiceException):
    """인증 실패 예외"""

    def __init__(
        self,
        message: str = "Authentication failed",
        auth_method: str | None = None,
        **kwargs: Any,
    ) -> None:
        self.auth_method = auth_method

        details = kwargs.get("details", {})
        if auth_method:
            details["auth_method"] = auth_method

        kwargs["details"] = details
        kwargs["category"] = ErrorCategory.AUTHENTICATION
        kwargs["severity"] = ErrorSeverity.MEDIUM

        super().__init__(message, **kwargs)

    def _get_default_user_message(self) -> str:
        return "인증이 필요합니다. 로그인 후 다시 시도해주세요."


class AuthorizationError(BaseServiceException):
    """권한 부족 예외"""

    def __init__(
        self,
        action: str,
        resource: str | None = None,
        required_permission: str | None = None,
        **kwargs: Any,
    ) -> None:
        self.action = action
        self.resource = resource
        self.required_permission = required_permission

        if resource:
            message = f"Not authorized to {action} {resource}"
        else:
            message = f"Not authorized to {action}"

        details = kwargs.get("details", {})
        details.update(
            {
                "action": action,
                "resource": resource,
                "required_permission": required_permission,
            }
        )

        kwargs["details"] = details
        kwargs["category"] = ErrorCategory.AUTHORIZATION
        kwargs["severity"] = ErrorSeverity.MEDIUM

        super().__init__(message, **kwargs)

    def _get_default_user_message(self) -> str:
        return "이 작업을 수행할 권한이 없습니다."


class BusinessLogicError(BaseServiceException):
    """비즈니스 로직 오류 예외"""

    def __init__(
        self, message: str, business_rule: str | None = None, **kwargs: Any
    ) -> None:
        self.business_rule = business_rule

        details = kwargs.get("details", {})
        if business_rule:
            details["business_rule"] = business_rule

        kwargs["details"] = details
        kwargs["category"] = ErrorCategory.BUSINESS_LOGIC
        kwargs["severity"] = ErrorSeverity.MEDIUM

        super().__init__(message, **kwargs)

    def _get_default_user_message(self) -> str:
        return "요청하신 작업을 처리할 수 없습니다."


class ExternalServiceError(BaseServiceException):
    """외부 서비스 오류 예외"""

    def __init__(
        self,
        service_name: str,
        operation: str,
        status_code: int | None = None,
        response_body: str | None = None,
        **kwargs: Any,
    ) -> None:
        self.service_name = service_name
        self.operation = operation
        self.status_code = status_code
        self.response_body = response_body

        message = f"External service '{service_name}' error during '{operation}'"
        if status_code:
            message += f" (status: {status_code})"

        details = kwargs.get("details", {})
        details.update(
            {
                "service_name": service_name,
                "operation": operation,
                "status_code": status_code,
                "response_body": (
                    response_body[:1000] if response_body else None
                ),  # 응답 크기 제한
            }
        )

        kwargs["details"] = details
        kwargs["category"] = ErrorCategory.EXTERNAL_SERVICE
        kwargs["severity"] = ErrorSeverity.HIGH

        super().__init__(message, **kwargs)

    def _get_default_user_message(self) -> str:
        return "외부 서비스 연동 중 오류가 발생했습니다."


class ConfigurationError(BaseServiceException):
    """설정 오류 예외"""

    def __init__(
        self,
        config_key: str,
        message: str | None = None,
        expected_type: str | None = None,
        actual_value: Any = None,
        **kwargs: Any,
    ) -> None:
        self.config_key = config_key
        self.expected_type = expected_type
        self.actual_value = actual_value

        if message is None:
            message = f"Configuration error for key '{config_key}'"
            if expected_type:
                message += f": expected {expected_type}"
            if actual_value is not None:
                message += f", got {type(actual_value).__name__}: {actual_value}"

        details = kwargs.get("details", {})
        details.update(
            {
                "config_key": config_key,
                "expected_type": expected_type,
                "actual_value": str(actual_value) if actual_value is not None else None,
            }
        )

        kwargs["details"] = details
        kwargs["category"] = ErrorCategory.SYSTEM
        kwargs["severity"] = ErrorSeverity.CRITICAL

        super().__init__(message, **kwargs)

    def _get_default_user_message(self) -> str:
        return "시스템 설정 오류가 발생했습니다. 관리자에게 문의하세요."
