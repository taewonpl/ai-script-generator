"""
Utils Package for AI Script Generator v3.0

공통 유틸리티 패키지 - 설정 관리, 로깅, 헬퍼 함수를 제공합니다.
"""

# Configuration Management
from .config import (
    AIServiceSettings,
    APISettings,
    BaseServiceSettings,
    DatabaseSettings,
    LoggingSettings,
    SecuritySettings,
    Settings,
    create_service_settings,
    get_settings,
    validate_all_settings,
)

# Helper Functions
from .helpers import (
    calculate_age,
    # 기타 유틸리티
    calculate_hash,
    check_multiple_services,
    clean_filename,
    deep_merge,
    extract_emails,
    extract_urls,
    # 날짜/시간 처리
    format_datetime,
    generate_numeric_id,
    generate_prefixed_id,
    generate_short_id,
    # UUID 생성
    generate_uuid,
    generate_uuid_hex,
    get_env_var,
    mask_sensitive_data,
    parse_datetime,
    retry_with_backoff,
    safe_json_dumps,
    safe_json_loads,
    # 텍스트 정제
    sanitize_text,
    to_utc,
    utc_now,
    # 서비스 상태 확인
    validate_service_health,
    validate_service_health_async,
)

# Logging System
from .logger import (
    ContextualLoggerAdapter,
    LoggerManager,
    StructuredFormatter,
    TextFormatter,
    configure_logging,
    create_request_logger,
    get_logger,
    get_logger_manager,
    get_service_logger,
    health_check_logs,
    log_exception,
    set_log_level,
)

# 공개 API
__all__ = [
    # Configuration Management
    "BaseServiceSettings",
    "DatabaseSettings",
    "APISettings",
    "LoggingSettings",
    "SecuritySettings",
    "AIServiceSettings",
    "Settings",
    "get_settings",
    "create_service_settings",
    "validate_all_settings",
    # Logging System
    "StructuredFormatter",
    "TextFormatter",
    "ContextualLoggerAdapter",
    "LoggerManager",
    "get_logger_manager",
    "get_service_logger",
    "get_logger",
    "set_log_level",
    "configure_logging",
    "log_exception",
    "create_request_logger",
    "health_check_logs",
    # UUID Generation
    "generate_uuid",
    "generate_uuid_hex",
    "generate_prefixed_id",
    "generate_short_id",
    "generate_numeric_id",
    # Date/Time Utilities
    "format_datetime",
    "parse_datetime",
    "utc_now",
    "to_utc",
    "calculate_age",
    # Text Processing
    "sanitize_text",
    "clean_filename",
    "extract_emails",
    "extract_urls",
    "mask_sensitive_data",
    # Service Health Check
    "validate_service_health",
    "validate_service_health_async",
    "check_multiple_services",
    # Miscellaneous Utilities
    "calculate_hash",
    "safe_json_loads",
    "safe_json_dumps",
    "deep_merge",
    "get_env_var",
    "retry_with_backoff",
]
