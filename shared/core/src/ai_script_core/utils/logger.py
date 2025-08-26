"""
Advanced Logging System for AI Script Generator v3.0

구조화된 JSON 로깅과 서비스별 로거 관리 시스템을 제공합니다.
"""

import json
import logging
import logging.handlers
import os
import sys
from collections.abc import MutableMapping
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional, Dict, Union

from .config import LoggingSettings, get_settings


class StructuredFormatter(logging.Formatter):
    """구조화된 JSON 로그 포맷터"""

    def __init__(
        self,
        service_name: str = "ai-script-generator",
        service_version: str = "3.0.0",
        include_trace: bool = False,
    ):
        super().__init__()
        self.service_name = service_name
        self.service_version = service_version
        self.include_trace = include_trace

    def format(self, record: logging.LogRecord) -> str:
        """로그 레코드를 JSON 형태로 포맷"""

        # 기본 로그 데이터
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": {"name": self.service_name, "version": self.service_version},
            "process": {
                "pid": os.getpid(),
                "thread_id": record.thread,
                "thread_name": (
                    record.threadName if hasattr(record, "threadName") else None
                ),
            },
            "location": {
                "file": record.filename,
                "function": record.funcName,
                "line": record.lineno,
                "module": record.module,
            },
        }

        # 추가 필드가 있으면 포함
        if hasattr(record, "extra_fields") and record.extra_fields:
            log_data.update(record.extra_fields)

        # 예외 정보가 있으면 포함
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": (
                    self.formatException(record.exc_info)
                    if self.include_trace
                    else None
                ),
            }

        # 스택 정보 포함 (옵션)
        if self.include_trace and record.stack_info:
            log_data["stack_info"] = record.stack_info

        # 요청 ID나 상관 ID가 있으면 포함 (컨텍스트에서)
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "correlation_id"):
            log_data["correlation_id"] = record.correlation_id
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id

        return json.dumps(log_data, ensure_ascii=False, default=str)


class TextFormatter(logging.Formatter):
    """읽기 쉬운 텍스트 형태 포맷터"""

    def __init__(self) -> None:
        format_string = (
            "%(asctime)s | %(levelname)-8s | %(name)-20s | "
            "%(filename)s:%(lineno)d:%(funcName)s | %(message)s"
        )
        super().__init__(format_string, datefmt="%Y-%m-%d %H:%M:%S")


class ContextualLoggerAdapter(logging.LoggerAdapter[logging.Logger]):
    """컨텍스트 정보를 자동으로 추가하는 로거 어댑터"""

    def __init__(self, logger: logging.Logger, extra: Optional[Dict[str, Any]] = None):
        super().__init__(logger, extra or {})

    def process(
        self, msg: Any, kwargs: MutableMapping[str, Any]
    ) -> tuple[Any, MutableMapping[str, Any]]:
        """로그 메시지 처리 시 컨텍스트 정보 추가"""
        # extra 필드에 컨텍스트 정보 추가
        if "extra" not in kwargs:
            kwargs["extra"] = {}

        kwargs["extra"].update(self.extra)

        # 사용자 정의 필드를 extra_fields로 그룹화
        extra_fields = kwargs["extra"].copy()
        kwargs["extra"]["extra_fields"] = extra_fields

        return msg, kwargs

    def add_context(self, **kwargs: Any) -> "ContextualLoggerAdapter":
        """컨텍스트 정보 추가"""
        new_extra = dict(self.extra) if self.extra else {}
        new_extra.update(kwargs)
        return ContextualLoggerAdapter(self.logger, new_extra)


class LoggerManager:
    """로거 관리자 클래스"""

    def __init__(self, settings: Optional[LoggingSettings] = None):
        self.settings = settings or get_settings().logging
        self._loggers: Dict[str, logging.Logger] = {}
        self._setup_root_logger()

    def _setup_root_logger(self) -> None:
        """루트 로거 설정"""
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.settings.level.upper()))

        # 기존 핸들러 제거
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

    def _create_console_handler(self) -> logging.Handler:
        """콘솔 핸들러 생성"""
        handler = logging.StreamHandler(sys.stdout)

        formatter: Union[StructuredFormatter, TextFormatter]
        if self.settings.format == "json":
            formatter = StructuredFormatter(
                service_name=self.settings.service_name,
                service_version=self.settings.service_version,
                include_trace=self.settings.include_trace,
            )
        else:
            formatter = TextFormatter()

        handler.setFormatter(formatter)
        handler.setLevel(getattr(logging, self.settings.level.upper()))

        return handler

    def _create_file_handler(self) -> Optional[logging.Handler]:
        """파일 핸들러 생성"""
        if not self.settings.file_enabled or not self.settings.file_path:
            return None

        try:
            # 로그 디렉토리 생성
            log_path = Path(self.settings.file_path)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            # 로테이팅 파일 핸들러 사용
            handler = logging.handlers.RotatingFileHandler(
                filename=self.settings.file_path,
                maxBytes=self.settings.file_max_size,
                backupCount=self.settings.file_backup_count,
                encoding="utf-8",
            )

            if self.settings.format == "json":
                formatter = StructuredFormatter(
                    service_name=self.settings.service_name,
                    service_version=self.settings.service_version,
                    include_trace=self.settings.include_trace,
                )
            else:
                formatter = TextFormatter()  # type: ignore[assignment]

            handler.setFormatter(formatter)
            handler.setLevel(getattr(logging, self.settings.level.upper()))

            return handler
        except (OSError, PermissionError):
            # 컨테이너 환경에서 파일 생성 권한 에러 시 None 반환
            # 로거는 콘솔 출력만 사용하도록 폴백
            return None

    def get_logger(
        self,
        name: str,
        add_console: bool = True,
        add_file: bool = True,
        context: Optional[Dict[str, Any]] = None,
    ) -> ContextualLoggerAdapter:
        """서비스별 로거 생성 및 반환"""

        if name in self._loggers:
            logger = self._loggers[name]
        else:
            logger = logging.getLogger(name)
            logger.setLevel(getattr(logging, self.settings.level.upper()))

            # 핸들러 제거 (중복 방지)
            for handler in logger.handlers[:]:
                logger.removeHandler(handler)

            # 콘솔 핸들러 추가
            if add_console and self.settings.console_enabled:
                console_handler = self._create_console_handler()
                logger.addHandler(console_handler)

            # 파일 핸들러 추가
            if add_file and self.settings.file_enabled:
                file_handler = self._create_file_handler()
                if file_handler:
                    logger.addHandler(file_handler)

            # 상위 로거로의 전파 방지 (중복 로그 방지)
            logger.propagate = False

            self._loggers[name] = logger

        # 컨텍스트 로거 어댑터로 감싸서 반환
        return ContextualLoggerAdapter(logger, context or {})

    def set_level(self, name: str, level: Union[str, int]) -> None:
        """특정 로거의 레벨 동적 조정"""
        if isinstance(level, str):
            level = getattr(logging, level.upper())

        if name in self._loggers:
            self._loggers[name].setLevel(level)

            # 핸들러 레벨도 조정
            for handler in self._loggers[name].handlers:
                handler.setLevel(level)

    def get_all_loggers(self) -> Dict[str, logging.Logger]:
        """모든 등록된 로거 반환"""
        return self._loggers.copy()


# 전역 로거 매니저 인스턴스
_logger_manager = None


@lru_cache
def get_logger_manager() -> LoggerManager:
    """로거 매니저 싱글톤 인스턴스 반환"""
    global _logger_manager
    if _logger_manager is None:
        _logger_manager = LoggerManager()
    return _logger_manager


def get_service_logger(
    service_name: str,
    context: Optional[Dict[str, Any]] = None,
    add_console: bool = True,
    add_file: bool = False,
) -> ContextualLoggerAdapter:
    """서비스별 로거 생성"""
    manager = get_logger_manager()
    return manager.get_logger(
        name=service_name, add_console=add_console, add_file=add_file, context=context
    )


def get_logger(name: str) -> ContextualLoggerAdapter:
    """기본 로거 획득 (호환성 유지)"""
    return get_service_logger(name)


def set_log_level(logger_name: str, level: Union[str, int]) -> None:
    """로그 레벨 동적 조정"""
    manager = get_logger_manager()
    manager.set_level(logger_name, level)


def configure_logging(
    level: str = "INFO",
    format_type: str = "json",
    service_name: str = "ai-script-generator",
    enable_file: bool = True,
    log_file: Optional[str] = None,
) -> None:
    """전역 로깅 설정"""
    settings = LoggingSettings(
        level=level,
        format=format_type,
        service_name=service_name,
        file_enabled=enable_file,
        file_path=log_file,
    )

    global _logger_manager
    _logger_manager = LoggerManager(settings)


def log_exception(
    logger: ContextualLoggerAdapter,
    exception: Exception,
    message: str = "An exception occurred",
    extra_context: Optional[Dict[str, Any]] = None,
) -> None:
    """예외 정보와 함께 로그 기록"""
    context = {"exception_type": type(exception).__name__}
    if extra_context:
        context.update(extra_context)

    logger_with_context = logger.add_context(**context)
    logger_with_context.error(message, exc_info=True)


def create_request_logger(
    service_name: str,
    request_id: str,
    user_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> ContextualLoggerAdapter:
    """요청별 컨텍스트 로거 생성"""
    context = {"request_id": request_id}

    if user_id:
        context["user_id"] = user_id
    if correlation_id:
        context["correlation_id"] = correlation_id

    return get_service_logger(service_name, context=context)


def health_check_logs() -> Dict[str, Any]:
    """로깅 시스템 상태 확인"""
    manager = get_logger_manager()

    return {
        "status": "healthy",
        "settings": {
            "level": manager.settings.level,
            "format": manager.settings.format,
            "console_enabled": manager.settings.console_enabled,
            "file_enabled": manager.settings.file_enabled,
            "file_path": manager.settings.file_path,
        },
        "active_loggers": list(manager.get_all_loggers().keys()),
        "handlers_count": {
            name: len(logger.handlers)
            for name, logger in manager.get_all_loggers().items()
        },
    }
