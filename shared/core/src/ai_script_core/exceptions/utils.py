"""
Exception Handling Utilities for AI Script Generator v3.0

예외 처리 관련 데코레이터, 포매터 및 로그 자동 기록 기능을 제공합니다.
"""

import functools
import logging
import sys
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from .base import BaseServiceException, ErrorCategory, ErrorSeverity
from .service_errors import *

# 제네릭 타입 정의
F = TypeVar("F", bound=Callable[..., Any])


class ExceptionLogger:
    """예외 로깅 관리자"""

    def __init__(self, logger_name: str = "ai_script_exceptions"):
        self.logger = logging.getLogger(logger_name)
        self._configure_logger()

    def _configure_logger(self) -> None:
        """로거 기본 설정"""
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def log_exception(
        self,
        exception: BaseServiceException,
        context: dict[str, Any] | None = None,
        include_traceback: bool = True,
    ) -> None:
        """예외 로그 기록"""
        log_data = {
            "exception_type": exception.__class__.__name__,
            "error_code": exception.error_code,
            "message": exception.message,
            "severity": exception.severity.value,
            "category": exception.category.value,
            "timestamp": exception.timestamp.isoformat(),
            "context": exception.context,
        }

        if context:
            log_data["additional_context"] = context

        # 심각도에 따른 로그 레벨 결정
        if exception.severity == ErrorSeverity.CRITICAL:
            log_level = logging.CRITICAL
        elif exception.severity == ErrorSeverity.HIGH:
            log_level = logging.ERROR
        elif exception.severity == ErrorSeverity.MEDIUM:
            log_level = logging.WARNING
        else:
            log_level = logging.INFO

        # 로그 메시지 생성
        log_message = f"{exception.error_code}: {exception.message}"
        if exception.details:
            log_message += f" | Details: {exception.details}"

        if include_traceback and exception.traceback_str:
            log_message += f"\nTraceback: {exception.traceback_str}"

        self.logger.log(log_level, log_message, extra=log_data)


# 전역 예외 로거 인스턴스
_exception_logger = ExceptionLogger()


def log_exception(
    exception: BaseServiceException,
    context: dict[str, Any] | None = None,
    include_traceback: bool = True,
    logger: ExceptionLogger | None = None,
) -> None:
    """예외 로그 기록 함수"""
    if logger is None:
        logger = _exception_logger

    logger.log_exception(exception, context, include_traceback)


def exception_handler(
    *,
    default_exception_type: type[BaseServiceException] = BaseServiceException,
    log_exceptions: bool = True,
    include_traceback: bool = True,
    context_extractor: Callable[..., dict[str, Any]] | None = None,
    suppress_exceptions: bool = False,
    fallback_return: Any = None,
) -> Callable[[F], F]:
    """
    함수나 메서드에 예외 처리 로직을 추가하는 데코레이터

    Args:
        default_exception_type: 기본 예외 타입
        log_exceptions: 예외 로깅 여부
        include_traceback: 트레이스백 포함 여부
        context_extractor: 컨텍스트 추출 함수
        suppress_exceptions: 예외 억제 여부 (True시 예외를 발생시키지 않음)
        fallback_return: 예외 억제시 반환할 기본값
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except BaseServiceException as e:
                # 이미 BaseServiceException인 경우
                context = {}
                if context_extractor:
                    try:
                        context = context_extractor(*args, **kwargs)
                    except Exception:
                        context = {"context_extraction_failed": True}

                # 함수 정보 추가
                context.update(
                    {
                        "function_name": func.__name__,
                        "module_name": func.__module__,
                        "args_count": len(args),
                        "kwargs_count": len(kwargs),
                    }
                )

                e.add_context("handler_context", context)

                if log_exceptions:
                    log_exception(e, context, include_traceback)

                if suppress_exceptions:
                    return fallback_return
                raise

            except Exception as e:
                # 다른 예외를 BaseServiceException으로 변환
                context = {"original_exception": str(e)}
                if context_extractor:
                    try:
                        extracted_context = context_extractor(*args, **kwargs)
                        context.update(extracted_context)
                    except Exception:
                        context["context_extraction_failed"] = True

                # 함수 정보 추가
                context.update(
                    {
                        "function_name": func.__name__,
                        "module_name": func.__module__,
                        "args_count": len(args),
                        "kwargs_count": len(kwargs),
                    }
                )

                wrapped_exception = default_exception_type(
                    message=f"Unexpected error in {func.__name__}: {e!s}",
                    cause=e,
                    context=context,
                )

                if log_exceptions:
                    log_exception(wrapped_exception, context, include_traceback)

                if suppress_exceptions:
                    return fallback_return
                raise wrapped_exception

        return wrapper  # type: ignore[return-value]

    return decorator


def async_exception_handler(
    *,
    default_exception_type: type[BaseServiceException] = BaseServiceException,
    log_exceptions: bool = True,
    include_traceback: bool = True,
    context_extractor: Callable[..., dict[str, Any]] | None = None,
    suppress_exceptions: bool = False,
    fallback_return: Any = None,
) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    """비동기 함수용 예외 처리 데코레이터"""

    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except BaseServiceException as e:
                context = {}
                if context_extractor:
                    try:
                        context = context_extractor(*args, **kwargs)
                    except Exception:
                        context = {"context_extraction_failed": True}

                context.update(
                    {
                        "function_name": func.__name__,
                        "module_name": func.__module__,
                        "is_async": True,
                    }
                )

                e.add_context("handler_context", context)

                if log_exceptions:
                    log_exception(e, context, include_traceback)

                if suppress_exceptions:
                    return fallback_return
                raise

            except Exception as e:
                context = {"original_exception": str(e)}
                if context_extractor:
                    try:
                        extracted_context = context_extractor(*args, **kwargs)
                        context.update(extracted_context)
                    except Exception:
                        context["context_extraction_failed"] = True

                context.update(
                    {
                        "function_name": func.__name__,
                        "module_name": func.__module__,
                        "is_async": True,
                    }
                )

                wrapped_exception = default_exception_type(
                    message=f"Unexpected error in async {func.__name__}: {e!s}",
                    cause=e,
                    context=context,
                )

                if log_exceptions:
                    log_exception(wrapped_exception, context, include_traceback)

                if suppress_exceptions:
                    return fallback_return
                raise wrapped_exception

        return wrapper

    return decorator


def error_response_formatter(
    exception: BaseServiceException,
    include_debug_info: bool = False,
    include_context: bool = False,
) -> dict[str, Any]:
    """
    예외를 API 응답용 딕셔너리로 포맷

    Args:
        exception: 변환할 예외
        include_debug_info: 디버그 정보 포함 여부
        include_context: 컨텍스트 정보 포함 여부
    """
    response = {
        "error": True,
        "error_code": exception.error_code,
        "message": exception.user_message,
        "severity": exception.severity.value,
        "category": exception.category.value,
        "timestamp": exception.timestamp.isoformat(),
    }

    # 기본 상세 정보 (민감하지 않은 정보만)
    if exception.details:
        safe_details = {}
        for key, value in exception.details.items():
            # 민감한 키 제외
            if not any(
                sensitive in key.lower()
                for sensitive in ["password", "token", "secret", "key"]
            ):
                safe_details[key] = value

        if safe_details:
            response["details"] = safe_details

    # 디버그 정보 (개발 환경에서만)
    if include_debug_info:
        debug_info: dict[str, Any] = {
            "exception_type": exception.__class__.__name__,
            "internal_message": exception.message,
            "traceback": exception.traceback_str,
        }

        if exception.cause:
            debug_info["cause"] = str(exception.cause)

        response["debug"] = debug_info

    # 컨텍스트 정보
    if include_context and exception.context:
        response["context"] = exception.context

    return response


def format_error_for_api(
    exception: BaseServiceException | Exception,
    include_debug_info: bool = False,
    include_context: bool = False,
) -> dict[str, Any]:
    """
    일반 예외를 포함하여 API 응답용으로 포맷
    """
    if isinstance(exception, BaseServiceException):
        return error_response_formatter(exception, include_debug_info, include_context)

    # 일반 예외를 BaseServiceException으로 변환
    wrapped = BaseServiceException(
        message=str(exception),
        error_code="INTERNAL_ERROR",
        severity=ErrorSeverity.HIGH,
        category=ErrorCategory.SYSTEM,
    )

    return error_response_formatter(wrapped, include_debug_info, include_context)


class ExceptionAnalyzer:
    """예외 분석 및 통계 수집기"""

    def __init__(self) -> None:
        self.exception_stats: dict[str, int] = {}
        self.severity_stats: dict[str, int] = {}
        self.category_stats: dict[str, int] = {}
        self.hourly_stats: dict[str, int] = {}

    def record_exception(self, exception: BaseServiceException) -> None:
        """예외 통계 기록"""
        # 예외 타입별 통계
        exception_type = exception.__class__.__name__
        self.exception_stats[exception_type] = (
            self.exception_stats.get(exception_type, 0) + 1
        )

        # 심각도별 통계
        severity = exception.severity.value
        self.severity_stats[severity] = self.severity_stats.get(severity, 0) + 1

        # 카테고리별 통계
        category = exception.category.value
        self.category_stats[category] = self.category_stats.get(category, 0) + 1

        # 시간별 통계 (시간대별)
        hour_key = exception.timestamp.strftime("%Y-%m-%d_%H")
        self.hourly_stats[hour_key] = self.hourly_stats.get(hour_key, 0) + 1

    def get_statistics(self) -> dict[str, Any]:
        """예외 통계 반환"""
        return {
            "exception_types": dict(
                sorted(self.exception_stats.items(), key=lambda x: x[1], reverse=True)
            ),
            "severity_distribution": self.severity_stats,
            "category_distribution": self.category_stats,
            "hourly_distribution": dict(sorted(self.hourly_stats.items())),
            "total_exceptions": sum(self.exception_stats.values()),
        }

    def get_top_exceptions(self, limit: int = 10) -> list[dict[str, Any]]:
        """가장 빈번한 예외 반환"""
        sorted_exceptions = sorted(
            self.exception_stats.items(), key=lambda x: x[1], reverse=True
        )[:limit]

        return [
            {"exception_type": exc_type, "count": count}
            for exc_type, count in sorted_exceptions
        ]


# 전역 예외 분석기 인스턴스
_exception_analyzer = ExceptionAnalyzer()


def record_exception_stats(exception: BaseServiceException) -> None:
    """예외 통계 기록"""
    _exception_analyzer.record_exception(exception)


def get_exception_statistics() -> dict[str, Any]:
    """전역 예외 통계 반환"""
    return _exception_analyzer.get_statistics()


def safe_execute(
    func: Callable[..., Any],
    *args: Any,
    default_return: Any = None,
    exception_types: tuple[type, ...] = (Exception,),
    log_errors: bool = True,
    **kwargs: Any,
) -> Any:
    """
    안전한 함수 실행 (예외 발생시 기본값 반환)
    """
    try:
        return func(*args, **kwargs)
    except exception_types as e:  # type: ignore[misc]
        if log_errors:
            if isinstance(e, BaseServiceException):
                log_exception(e)
            else:
                logging.error(f"Error in safe_execute: {e!s}")
        return default_return


def chain_exceptions(*exceptions: BaseServiceException) -> BaseServiceException:
    """
    여러 예외를 연결하여 하나의 예외로 만듦
    """
    if not exceptions:
        raise ValueError("At least one exception is required")

    if len(exceptions) == 1:
        return exceptions[0]

    main_exception = exceptions[0]

    # 다른 예외들을 컨텍스트로 추가
    chained_info = []
    for i, exc in enumerate(exceptions[1:], 1):
        chained_info.append(
            {
                f"chained_exception_{i}": {
                    "type": exc.__class__.__name__,
                    "message": exc.message,
                    "error_code": exc.error_code,
                    "severity": exc.severity.value,
                }
            }
        )

    main_exception.add_context("chained_exceptions", chained_info)
    return main_exception
