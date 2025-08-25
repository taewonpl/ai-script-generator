"""
Exception Handling Tests for AI Script Generator v3.0 Core

예외 처리 시스템 독립성 및 기능 테스트
"""

from datetime import datetime

import pytest

# Core 모듈에서 예외 import 테스트
try:
    from ai_script_core.exceptions import (
        AIModelError,
        AuthenticationError,
        AuthorizationError,
        BaseServiceException,
        DatabaseConnectionError,
        DatabaseError,
        EpisodeNotFoundError,
        ErrorCategory,
        # Base exceptions
        ErrorSeverity,
        GatewayError,
        GenerationServiceError,
        KnowledgeBaseNotFoundError,
        NotFoundError,
        ProjectNotFoundError,
        # Service-specific exceptions
        ProjectServiceError,
        RAGServiceError,
        RateLimitExceededError,
        ServiceDiscoveryError,
        ServiceUnavailableError,
        TokenLimitExceededError,
        ValidationException,
        async_exception_handler,
        chain_exceptions,
        error_response_formatter,
        # Exception utilities
        exception_handler,
        log_exception,
        safe_execute,
    )

    IMPORT_SUCCESS = True
except ImportError as e:
    IMPORT_SUCCESS = False
    IMPORT_ERROR = str(e)


class TestExceptionImports:
    """예외 임포트 테스트"""

    def test_import_success(self):
        """모든 예외 클래스 임포트 성공 확인"""
        assert (
            IMPORT_SUCCESS
        ), f"Exception import failed: {IMPORT_ERROR if not IMPORT_SUCCESS else ''}"

    def test_enum_classes_exist(self):
        """Enum 클래스 존재 확인"""
        assert hasattr(ErrorSeverity, "__members__")
        assert hasattr(ErrorCategory, "__members__")

    def test_base_exception_exists(self):
        """기본 예외 클래스 존재 확인"""
        assert issubclass(BaseServiceException, Exception)
        assert hasattr(BaseServiceException, "__init__")


class TestErrorEnums:
    """에러 Enum 테스트"""

    def test_error_severity_values(self):
        """ErrorSeverity enum 값 테스트"""
        assert ErrorSeverity.LOW in ErrorSeverity.__members__.values()
        assert ErrorSeverity.MEDIUM in ErrorSeverity.__members__.values()
        assert ErrorSeverity.HIGH in ErrorSeverity.__members__.values()
        assert ErrorSeverity.CRITICAL in ErrorSeverity.__members__.values()

    def test_error_category_values(self):
        """ErrorCategory enum 값 테스트"""
        assert ErrorCategory.VALIDATION in ErrorCategory.__members__.values()
        assert ErrorCategory.AUTHENTICATION in ErrorCategory.__members__.values()
        assert ErrorCategory.NOT_FOUND in ErrorCategory.__members__.values()
        assert ErrorCategory.SYSTEM in ErrorCategory.__members__.values()
        assert ErrorCategory.DATABASE in ErrorCategory.__members__.values()


class TestBaseServiceException:
    """BaseServiceException 테스트"""

    def test_basic_creation(self):
        """기본 예외 생성 테스트"""
        exception = BaseServiceException("Test error message")

        assert exception.message == "Test error message"
        assert exception.error_code == "BASESERVICEEXCEPTION"
        assert exception.severity == ErrorSeverity.MEDIUM
        assert exception.category == ErrorCategory.SYSTEM
        assert isinstance(exception.timestamp, datetime)

    def test_detailed_creation(self):
        """상세 정보가 있는 예외 생성 테스트"""
        details = {"user_id": "123", "action": "create_project"}
        context = {"request_id": "req_456"}

        exception = BaseServiceException(
            message="Detailed error",
            error_code="CUSTOM_ERROR",
            details=details,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.VALIDATION,
            user_message="Something went wrong",
            context=context,
        )

        assert exception.message == "Detailed error"
        assert exception.error_code == "CUSTOM_ERROR"
        assert exception.severity == ErrorSeverity.HIGH
        assert exception.category == ErrorCategory.VALIDATION
        assert exception.user_message == "Something went wrong"
        assert exception.details == details
        assert exception.context == context

    def test_exception_methods(self):
        """예외 메서드 테스트"""
        exception = BaseServiceException("Test error")

        # add_context 메서드 테스트
        exception.add_context("new_key", "new_value")
        assert exception.context["new_key"] == "new_value"

        # add_detail 메서드 테스트
        exception.add_detail("detail_key", "detail_value")
        assert exception.details["detail_key"] == "detail_value"

        # with_cause 메서드 테스트
        cause_exception = ValueError("Cause error")
        exception.with_cause(cause_exception)
        assert exception.cause == cause_exception

        # to_dict 메서드 테스트
        dict_repr = exception.to_dict()
        assert isinstance(dict_repr, dict)
        assert dict_repr["message"] == "Test error"
        assert dict_repr["error_type"] == "BaseServiceException"


class TestValidationException:
    """ValidationException 테스트"""

    def test_validation_exception_creation(self):
        """ValidationException 생성 테스트"""
        exception = ValidationException(
            message="Invalid field value",
            field="email",
            value="invalid-email",
            validation_rule="email_format",
        )

        assert exception.message == "Invalid field value"
        assert exception.field == "email"
        assert exception.value == "invalid-email"
        assert exception.validation_rule == "email_format"
        assert exception.category == ErrorCategory.VALIDATION
        assert exception.severity == ErrorSeverity.LOW

    def test_default_user_message(self):
        """기본 사용자 메시지 테스트"""
        exception = ValidationException("Test", field="name")
        assert "name" in exception.user_message

        exception_no_field = ValidationException("Test")
        assert "입력된 데이터가 올바르지 않습니다" in exception_no_field.user_message


class TestNotFoundError:
    """NotFoundError 테스트"""

    def test_not_found_with_string_id(self):
        """문자열 ID로 NotFoundError 테스트"""
        exception = NotFoundError("User", "user_123")

        assert exception.resource_type == "User"
        assert exception.identifier == "user_123"
        assert "User not found with id: user_123" in exception.message
        assert exception.category == ErrorCategory.NOT_FOUND
        assert exception.severity == ErrorSeverity.LOW

    def test_not_found_with_dict_criteria(self):
        """딕셔너리 조건으로 NotFoundError 테스트"""
        criteria = {"email": "test@example.com", "status": "active"}
        exception = NotFoundError("User", criteria)

        assert exception.resource_type == "User"
        assert exception.identifier == criteria
        assert "email=test@example.com" in exception.message
        assert "status=active" in exception.message


class TestServiceSpecificExceptions:
    """서비스별 예외 테스트"""

    def test_project_not_found_error(self):
        """ProjectNotFoundError 테스트"""
        exception = ProjectNotFoundError("proj_123")

        assert exception.project_id == "proj_123"
        assert exception.resource_type == "Project"
        assert exception.identifier == "proj_123"
        assert "요청하신 프로젝트를 찾을 수 없습니다" in exception.user_message

    def test_episode_not_found_error(self):
        """EpisodeNotFoundError 테스트"""
        exception = EpisodeNotFoundError("ep_456", project_id="proj_123")

        assert exception.episode_id == "ep_456"
        assert exception.project_id == "proj_123"
        assert "요청하신 에피소드를 찾을 수 없습니다" in exception.user_message

    def test_ai_model_error(self):
        """AIModelError 테스트"""
        exception = AIModelError(
            model_name="gpt-4",
            operation="text_generation",
            error_message="Rate limit exceeded",
        )

        assert exception.model_name == "gpt-4"
        assert exception.operation == "text_generation"
        assert exception.error_message == "Rate limit exceeded"
        assert exception.category == ErrorCategory.EXTERNAL_SERVICE
        assert exception.severity == ErrorSeverity.HIGH

    def test_token_limit_exceeded_error(self):
        """TokenLimitExceededError 테스트"""
        exception = TokenLimitExceededError(
            model_name="gpt-4", token_count=5000, max_tokens=4000
        )

        assert exception.model_name == "gpt-4"
        assert exception.token_count == 5000
        assert exception.max_tokens == 4000
        assert f"최대 {exception.max_tokens} 토큰까지" in exception.user_message

    def test_database_connection_error(self):
        """DatabaseConnectionError 테스트"""
        exception = DatabaseConnectionError(
            database_url="postgresql://user:pass@localhost:5432/db",  # pragma: allowlist secret
            error_message="Connection timeout",
        )

        assert "postgresql://user:***@localhost:5432/db" in exception.database_url
        assert exception.error_message == "Connection timeout"
        assert exception.severity == ErrorSeverity.CRITICAL

    def test_rate_limit_exceeded_error(self):
        """RateLimitExceededError 테스트"""
        exception = RateLimitExceededError(
            client_id="client_123", limit=100, window_seconds=60, retry_after=30
        )

        assert exception.client_id == "client_123"
        assert exception.limit == 100
        assert exception.window_seconds == 60
        assert exception.retry_after == 30
        assert "30초 후 다시 시도해주세요" in exception.user_message


class TestExceptionHandlerDecorator:
    """exception_handler 데코레이터 테스트"""

    def test_exception_handler_basic(self):
        """기본 exception_handler 테스트"""

        @exception_handler()
        def test_function():
            raise ValueError("Test error")

        with pytest.raises(BaseServiceException) as exc_info:
            test_function()

        assert "Unexpected error in test_function" in str(exc_info.value)
        assert exc_info.value.cause.__class__ == ValueError

    def test_exception_handler_with_custom_exception(self):
        """사용자 정의 예외 타입으로 exception_handler 테스트"""

        @exception_handler(default_exception_type=ProjectServiceError)
        def test_function():
            raise ValueError("Test error")

        with pytest.raises(ProjectServiceError):
            test_function()

    def test_exception_handler_with_suppression(self):
        """예외 억제로 exception_handler 테스트"""

        @exception_handler(suppress_exceptions=True, fallback_return="fallback")
        def test_function():
            raise ValueError("Test error")

        result = test_function()
        assert result == "fallback"

    def test_exception_handler_preserves_service_exceptions(self):
        """서비스 예외 보존 테스트"""

        @exception_handler()
        def test_function():
            raise ProjectNotFoundError("proj_123")

        with pytest.raises(ProjectNotFoundError) as exc_info:
            test_function()

        assert exc_info.value.project_id == "proj_123"


class TestAsyncExceptionHandler:
    """async_exception_handler 데코레이터 테스트"""

    @pytest.mark.asyncio
    async def test_async_exception_handler_basic(self):
        """기본 async_exception_handler 테스트"""

        @async_exception_handler()
        async def test_async_function():
            raise ValueError("Async test error")

        with pytest.raises(BaseServiceException) as exc_info:
            await test_async_function()

        assert "Unexpected error in async test_async_function" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_async_exception_handler_suppression(self):
        """비동기 예외 억제 테스트"""

        @async_exception_handler(
            suppress_exceptions=True, fallback_return="async_fallback"
        )
        async def test_async_function():
            raise ValueError("Async test error")

        result = await test_async_function()
        assert result == "async_fallback"


class TestErrorResponseFormatter:
    """error_response_formatter 테스트"""

    def test_basic_error_formatting(self):
        """기본 에러 포맷팅 테스트"""
        exception = BaseServiceException(
            message="Internal error",
            error_code="TEST_ERROR",
            user_message="Something went wrong",
        )

        response = error_response_formatter(exception)

        assert response["error"] is True
        assert response["error_code"] == "TEST_ERROR"
        assert response["message"] == "Something went wrong"
        assert response["severity"] == ErrorSeverity.MEDIUM.value
        assert "timestamp" in response

    def test_error_formatting_with_debug_info(self):
        """디버그 정보 포함 에러 포맷팅 테스트"""
        exception = BaseServiceException("Debug test")

        response = error_response_formatter(exception, include_debug_info=True)

        assert "debug" in response
        assert response["debug"]["exception_type"] == "BaseServiceException"
        assert response["debug"]["internal_message"] == "Debug test"

    def test_error_formatting_filters_sensitive_data(self):
        """민감한 데이터 필터링 테스트"""
        exception = BaseServiceException(
            "Test error",
            details={
                "user_id": "123",
                "password": "secret123",  # pragma: allowlist secret
                "api_key": "key123",  # pragma: allowlist secret
                "safe_data": "public",
            },
        )

        response = error_response_formatter(exception)

        assert "details" in response
        assert "user_id" in response["details"]
        assert "safe_data" in response["details"]
        assert "password" not in response["details"]
        assert "api_key" not in response["details"]


class TestUtilityFunctions:
    """유틸리티 함수 테스트"""

    def test_safe_execute_success(self):
        """safe_execute 성공 케이스 테스트"""

        def success_function():
            return "success"

        result = safe_execute(success_function)
        assert result == "success"

    def test_safe_execute_with_exception(self):
        """safe_execute 예외 발생 케이스 테스트"""

        def failing_function():
            raise ValueError("Test error")

        result = safe_execute(failing_function, default_return="default")
        assert result == "default"

    def test_chain_exceptions(self):
        """chain_exceptions 테스트"""
        exc1 = BaseServiceException("First error")
        exc2 = BaseServiceException("Second error")
        exc3 = BaseServiceException("Third error")

        chained = chain_exceptions(exc1, exc2, exc3)

        assert chained == exc1
        assert "chained_exceptions" in chained.context
        assert len(chained.context["chained_exceptions"]) == 2

    def test_chain_exceptions_single(self):
        """단일 예외 chain_exceptions 테스트"""
        exc = BaseServiceException("Single error")
        chained = chain_exceptions(exc)

        assert chained == exc

    def test_chain_exceptions_empty(self):
        """빈 예외 리스트 chain_exceptions 테스트"""
        with pytest.raises(ValueError):
            chain_exceptions()


class TestExceptionInheritance:
    """예외 상속 구조 테스트"""

    def test_service_exception_inheritance(self):
        """서비스 예외 상속 구조 테스트"""
        # 모든 서비스 예외가 BaseServiceException을 상속받는지 확인
        assert issubclass(ProjectServiceError, BaseServiceException)
        assert issubclass(GenerationServiceError, BaseServiceException)
        assert issubclass(RAGServiceError, BaseServiceException)
        assert issubclass(GatewayError, BaseServiceException)
        assert issubclass(DatabaseError, BaseServiceException)

    def test_specific_exception_inheritance(self):
        """특정 예외 상속 구조 테스트"""
        assert issubclass(ProjectNotFoundError, NotFoundError)
        assert issubclass(NotFoundError, BaseServiceException)

        assert issubclass(ValidationException, BaseServiceException)
        assert issubclass(AuthenticationError, BaseServiceException)


if __name__ == "__main__":
    pytest.main([__file__])
