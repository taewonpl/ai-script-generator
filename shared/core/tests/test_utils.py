"""
Utility Functions Tests for AI Script Generator v3.0 Core

유틸리티 함수 독립성 및 기능 테스트
"""

import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

# Core 모듈에서 유틸리티 import 테스트
try:
    from ai_script_core.utils import (
        APISettings,
        BaseServiceSettings,
        ContextualLoggerAdapter,
        DatabaseSettings,
        LoggingSettings,
        SecuritySettings,
        StructuredFormatter,
        calculate_age,
        calculate_hash,
        check_multiple_services,
        clean_filename,
        configure_logging,
        create_request_logger,
        deep_merge,
        extract_emails,
        extract_urls,
        # Date/time utilities
        format_datetime,
        generate_numeric_id,
        generate_prefixed_id,
        generate_short_id,
        # UUID generation
        generate_uuid,
        generate_uuid_hex,
        get_env_var,
        # Logging
        get_service_logger,
        # Configuration
        get_settings,
        mask_sensitive_data,
        parse_datetime,
        retry_with_backoff,
        safe_json_dumps,
        # Miscellaneous
        safe_json_loads,
        # Text processing
        sanitize_text,
        to_utc,
        utc_now,
        # Service health
        validate_service_health,
    )

    IMPORT_SUCCESS = True
except ImportError as e:
    IMPORT_SUCCESS = False
    IMPORT_ERROR = str(e)


class TestUtilsImports:
    """유틸리티 임포트 테스트"""

    def test_import_success(self):
        """모든 유틸리티 함수 임포트 성공 확인"""
        assert (
            IMPORT_SUCCESS
        ), f"Utils import failed: {IMPORT_ERROR if not IMPORT_SUCCESS else ''}"

    def test_settings_classes_exist(self):
        """설정 클래스 존재 확인"""
        assert hasattr(DatabaseSettings, "__name__")
        assert hasattr(APISettings, "__name__")
        assert hasattr(LoggingSettings, "__name__")
        assert hasattr(SecuritySettings, "__name__")


class TestConfigurationSettings:
    """설정 관리 테스트"""

    def test_database_settings_creation(self):
        """DatabaseSettings 생성 테스트"""
        db_settings = DatabaseSettings()

        assert hasattr(db_settings, "database_url")
        assert hasattr(db_settings, "pool_size")
        assert hasattr(db_settings, "max_overflow")
        assert db_settings.pool_size >= 1
        assert db_settings.max_overflow >= 0

    def test_api_settings_creation(self):
        """APISettings 생성 테스트"""
        api_settings = APISettings()

        assert hasattr(api_settings, "host")
        assert hasattr(api_settings, "port")
        assert hasattr(api_settings, "workers")
        assert 1 <= api_settings.port <= 65535
        assert api_settings.workers >= 1

    def test_logging_settings_creation(self):
        """LoggingSettings 생성 테스트"""
        log_settings = LoggingSettings()

        assert hasattr(log_settings, "level")
        assert hasattr(log_settings, "format")
        assert hasattr(log_settings, "service_name")
        assert log_settings.level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        assert log_settings.format in ["json", "text"]

    def test_security_settings_creation(self):
        """SecuritySettings 생성 테스트"""
        security_settings = SecuritySettings()

        assert hasattr(security_settings, "secret_key")
        assert hasattr(security_settings, "algorithm")
        assert hasattr(security_settings, "access_token_expire_minutes")
        assert len(security_settings.secret_key) >= 32
        assert security_settings.access_token_expire_minutes > 0

    @patch.dict(
        os.environ,
        {
            "DATABASE_URL": "postgresql://test:test@localhost/testdb",  # pragma: allowlist secret
            "API_PORT": "9000",
            "LOG_LEVEL": "DEBUG",
        },
    )
    def test_settings_from_environment(self):
        """환경 변수에서 설정 로드 테스트"""
        db_settings = DatabaseSettings()
        api_settings = APISettings()
        log_settings = LoggingSettings()

        assert "postgresql" in db_settings.database_url
        assert api_settings.port == 9000
        assert log_settings.level == "DEBUG"

    def test_get_settings_function(self):
        """get_settings 함수 테스트"""
        settings = get_settings()

        assert hasattr(settings, "database")
        assert hasattr(settings, "api")
        assert hasattr(settings, "logging")
        assert hasattr(settings, "security")
        assert isinstance(settings.database, DatabaseSettings)
        assert isinstance(settings.api, APISettings)


class TestLoggingSystem:
    """로깅 시스템 테스트"""

    def test_get_service_logger(self):
        """get_service_logger 테스트"""
        logger = get_service_logger("test-service")

        assert hasattr(logger, "info")
        assert hasattr(logger, "error")
        assert hasattr(logger, "warning")
        assert isinstance(logger, ContextualLoggerAdapter)

    def test_create_request_logger(self):
        """create_request_logger 테스트"""
        logger = create_request_logger("test-service", "req_123", user_id="user_456")

        assert isinstance(logger, ContextualLoggerAdapter)
        assert logger.extra.get("request_id") == "req_123"
        assert logger.extra.get("user_id") == "user_456"

    def test_structured_formatter(self):
        """StructuredFormatter 테스트"""
        formatter = StructuredFormatter(
            service_name="test-service", service_version="1.0.0"
        )

        assert formatter.service_name == "test-service"
        assert formatter.service_version == "1.0.0"

    def test_configure_logging(self):
        """configure_logging 함수 테스트"""
        # 에러 없이 실행되는지 확인
        configure_logging(level="INFO", format_type="json", service_name="test-service")


class TestUUIDGeneration:
    """UUID 생성 테스트"""

    def test_generate_uuid(self):
        """generate_uuid 테스트"""
        uuid1 = generate_uuid()
        uuid2 = generate_uuid()

        assert isinstance(uuid1, str)
        assert isinstance(uuid2, str)
        assert uuid1 != uuid2
        assert len(uuid1) == 36  # UUID4 길이 (하이픈 포함)
        assert "-" in uuid1

    def test_generate_uuid_hex(self):
        """generate_uuid_hex 테스트"""
        uuid_hex = generate_uuid_hex()

        assert isinstance(uuid_hex, str)
        assert len(uuid_hex) == 32  # UUID4 길이 (하이픈 제외)
        assert "-" not in uuid_hex

    def test_generate_prefixed_id(self):
        """generate_prefixed_id 테스트"""
        prefixed_id = generate_prefixed_id("test")

        assert isinstance(prefixed_id, str)
        assert prefixed_id.startswith("test_")
        assert len(prefixed_id) > 5  # "test_" + UUID

    def test_generate_short_id(self):
        """generate_short_id 테스트"""
        short_id = generate_short_id(8)

        assert isinstance(short_id, str)
        assert len(short_id) == 8

        # 다양한 길이 테스트
        for length in [4, 6, 10, 16]:
            sid = generate_short_id(length)
            assert len(sid) == length

    def test_generate_numeric_id(self):
        """generate_numeric_id 테스트"""
        numeric_id = generate_numeric_id(10)

        assert isinstance(numeric_id, str)
        assert len(numeric_id) == 10
        assert numeric_id.isdigit()


class TestDateTimeUtilities:
    """날짜/시간 유틸리티 테스트"""

    def test_utc_now(self):
        """utc_now 테스트"""
        now = utc_now()

        assert isinstance(now, datetime)
        assert now.tzinfo == timezone.utc

    def test_format_datetime_iso(self):
        """format_datetime ISO 포맷 테스트"""
        dt = datetime(2024, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
        formatted = format_datetime(dt, format_type="iso")

        assert "2024-01-15T10:30:45" in formatted

    def test_format_datetime_standard(self):
        """format_datetime 표준 포맷 테스트"""
        dt = datetime(2024, 1, 15, 10, 30, 45)
        formatted = format_datetime(dt, format_type="standard")

        assert formatted == "2024-01-15 10:30:45"

    def test_format_datetime_compact(self):
        """format_datetime 압축 포맷 테스트"""
        dt = datetime(2024, 1, 15, 10, 30, 45)
        formatted = format_datetime(dt, format_type="compact")

        assert formatted == "20240115_103045"

    def test_format_datetime_human(self):
        """format_datetime 한국어 포맷 테스트"""
        dt = datetime(2024, 1, 15, 10, 30, 45)
        formatted = format_datetime(dt, format_type="human")

        assert "2024년 01월 15일" in formatted

    def test_parse_datetime(self):
        """parse_datetime 테스트"""
        # ISO 포맷
        dt1 = parse_datetime("2024-01-15T10:30:45")
        assert dt1 == datetime(2024, 1, 15, 10, 30, 45)

        # 표준 포맷
        dt2 = parse_datetime("2024-01-15 10:30:45")
        assert dt2 == datetime(2024, 1, 15, 10, 30, 45)

        # 날짜만
        dt3 = parse_datetime("2024-01-15")
        assert dt3 == datetime(2024, 1, 15)

        # 잘못된 포맷
        dt_invalid = parse_datetime("invalid-date")
        assert dt_invalid is None

    def test_calculate_age(self):
        """calculate_age 테스트"""
        from_date = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        to_date = datetime(2024, 1, 2, 14, 30, 45, tzinfo=timezone.utc)

        age = calculate_age(from_date, to_date)

        assert age["days"] == 1
        assert age["hours"] == 2
        assert age["minutes"] == 30
        assert age["seconds"] == 45
        assert age["total_seconds"] > 0

    def test_to_utc(self):
        """to_utc 테스트"""
        # timezone이 없는 datetime
        dt_naive = datetime(2024, 1, 15, 10, 30, 45)
        dt_utc = to_utc(dt_naive)
        assert dt_utc.tzinfo == timezone.utc

        # 이미 UTC인 datetime
        dt_already_utc = datetime(2024, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
        dt_converted = to_utc(dt_already_utc)
        assert dt_converted.tzinfo == timezone.utc


class TestTextProcessing:
    """텍스트 처리 테스트"""

    def test_sanitize_text_basic(self):
        """기본 텍스트 정제 테스트"""
        text = "  Hello   World  "
        sanitized = sanitize_text(text)

        assert sanitized == "Hello World"

    def test_sanitize_text_html_removal(self):
        """HTML 태그 제거 테스트"""
        text = "<p>Hello <strong>World</strong></p>"
        sanitized = sanitize_text(text, remove_html=True)

        assert sanitized == "Hello World"
        assert "<" not in sanitized
        assert ">" not in sanitized

    def test_sanitize_text_special_chars(self):
        """특수 문자 제거 테스트"""
        text = "Hello@#$%World!"
        sanitized = sanitize_text(text, remove_special_chars=True)

        assert "Hello" in sanitized
        assert "World" in sanitized
        assert "@#$%" not in sanitized

    def test_sanitize_text_length_limit(self):
        """길이 제한 테스트"""
        text = "This is a very long text that should be truncated"
        sanitized = sanitize_text(text, max_length=20)

        assert len(sanitized) <= 23  # 20 + "..."
        assert sanitized.endswith("...")

    def test_clean_filename(self):
        """파일명 정제 테스트"""
        filename = "my<file>name:with?special*chars.txt"
        cleaned = clean_filename(filename)

        assert "<" not in cleaned
        assert ">" not in cleaned
        assert ":" not in cleaned
        assert "?" not in cleaned
        assert "*" not in cleaned
        assert ".txt" in cleaned or cleaned.endswith("_txt")

    def test_extract_emails(self):
        """이메일 추출 테스트"""
        text = "Contact us at support@example.com or admin@test.org"
        emails = extract_emails(text)

        assert "support@example.com" in emails
        assert "admin@test.org" in emails
        assert len(emails) == 2

    def test_extract_urls(self):
        """URL 추출 테스트"""
        text = "Visit https://example.com or http://test.org for more info"
        urls = extract_urls(text)

        assert "https://example.com" in urls
        assert "http://test.org" in urls
        assert len(urls) == 2

    def test_mask_sensitive_data(self):
        """민감한 데이터 마스킹 테스트"""
        text = "Email: user@example.com Phone: 010-1234-5678"
        masked = mask_sensitive_data(text)

        assert "us***@example.com" in masked
        assert "010-****-5678" in masked
        assert "user@example.com" not in masked
        assert "1234" not in masked


class TestServiceHealthCheck:
    """서비스 헬스체크 테스트"""

    @patch("requests.get")
    def test_validate_service_health_success(self, mock_get):
        """서비스 헬스체크 성공 테스트"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "healthy", "version": "1.0.0"}
        mock_get.return_value = mock_response

        result = validate_service_health("http://test-service:8000")

        assert result["is_healthy"] is True
        assert result["status_code"] == 200
        assert result["service_info"]["status"] == "healthy"
        assert result["service_info"]["version"] == "1.0.0"

    @patch("requests.get")
    def test_validate_service_health_failure(self, mock_get):
        """서비스 헬스체크 실패 테스트"""
        mock_get.side_effect = Exception("Connection error")

        result = validate_service_health("http://invalid-service:8000")

        assert result["is_healthy"] is False
        assert result["error"] == "Unexpected error: Connection error"

    @patch("requests.get")
    def test_check_multiple_services(self, mock_get):
        """여러 서비스 헬스체크 테스트"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "healthy"}
        mock_get.return_value = mock_response

        services = ["http://service1:8001", "http://service2:8002"]
        results = check_multiple_services(services)

        assert len(results) == 2
        assert "http://service1:8001" in results
        assert "http://service2:8002" in results
        assert results["http://service1:8001"]["is_healthy"] is True
        assert results["http://service2:8002"]["is_healthy"] is True


class TestMiscellaneousUtils:
    """기타 유틸리티 테스트"""

    def test_safe_json_loads_success(self):
        """safe_json_loads 성공 테스트"""
        json_str = '{"name": "test", "value": 123}'
        result = safe_json_loads(json_str)

        assert result == {"name": "test", "value": 123}

    def test_safe_json_loads_failure(self):
        """safe_json_loads 실패 테스트"""
        invalid_json = '{"name": "test", "value":'  # 잘못된 JSON
        result = safe_json_loads(invalid_json, default={"error": "parsing_failed"})

        assert result == {"error": "parsing_failed"}

    def test_safe_json_dumps_success(self):
        """safe_json_dumps 성공 테스트"""
        data = {"name": "test", "value": 123}
        result = safe_json_dumps(data)

        assert '"name": "test"' in result
        assert '"value": 123' in result

    def test_safe_json_dumps_with_datetime(self):
        """safe_json_dumps datetime 처리 테스트"""
        data = {"timestamp": datetime.now()}
        result = safe_json_dumps(data)

        # datetime이 문자열로 변환되어야 함
        assert isinstance(result, str)
        assert "timestamp" in result

    def test_calculate_hash(self):
        """calculate_hash 테스트"""
        text = "Hello World"
        hash1 = calculate_hash(text)
        hash2 = calculate_hash(text)

        assert hash1 == hash2  # 같은 입력은 같은 해시
        assert len(hash1) == 64  # SHA256은 64자리 hex

        # 다른 입력은 다른 해시
        hash3 = calculate_hash("Different text")
        assert hash1 != hash3

    def test_deep_merge(self):
        """deep_merge 테스트"""
        dict1 = {"a": 1, "b": {"x": 10, "y": 20}, "c": [1, 2, 3]}

        dict2 = {"b": {"y": 30, "z": 40}, "d": 4}

        result = deep_merge(dict1, dict2)

        assert result["a"] == 1
        assert result["b"]["x"] == 10
        assert result["b"]["y"] == 30  # dict2로 덮어씀
        assert result["b"]["z"] == 40  # dict2에서 추가
        assert result["c"] == [1, 2, 3]
        assert result["d"] == 4

    @patch.dict(os.environ, {"TEST_VAR": "test_value"})
    def test_get_env_var_string(self):
        """get_env_var 문자열 테스트"""
        value = get_env_var("TEST_VAR")
        assert value == "test_value"

    @patch.dict(os.environ, {"TEST_INT": "42"})
    def test_get_env_var_int(self):
        """get_env_var 정수 테스트"""
        value = get_env_var("TEST_INT", var_type=int)
        assert value == 42
        assert isinstance(value, int)

    @patch.dict(os.environ, {"TEST_BOOL": "true"})
    def test_get_env_var_bool(self):
        """get_env_var 불린 테스트"""
        value = get_env_var("TEST_BOOL", var_type=bool)
        assert value is True

        # 다양한 true 값 테스트
        for true_val in ["1", "yes", "on", "TRUE"]:
            with patch.dict(os.environ, {"TEST_BOOL": true_val}):
                assert get_env_var("TEST_BOOL", var_type=bool) is True

    @patch.dict(os.environ, {"TEST_LIST": "a,b,c,d"})
    def test_get_env_var_list(self):
        """get_env_var 리스트 테스트"""
        value = get_env_var("TEST_LIST", var_type=list)
        assert value == ["a", "b", "c", "d"]
        assert isinstance(value, list)

    def test_get_env_var_default(self):
        """get_env_var 기본값 테스트"""
        value = get_env_var("NON_EXISTENT_VAR", default="default_value")
        assert value == "default_value"

    def test_retry_with_backoff(self):
        """retry_with_backoff 테스트"""
        call_count = 0

        @retry_with_backoff(max_retries=2, base_delay=0.01)
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "success"

        result = flaky_function()
        assert result == "success"
        assert call_count == 3  # 2번 재시도 후 성공

    def test_retry_with_backoff_failure(self):
        """retry_with_backoff 최종 실패 테스트"""
        call_count = 0

        @retry_with_backoff(max_retries=1, base_delay=0.01)
        def always_failing_function():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")

        with pytest.raises(ValueError):
            always_failing_function()

        assert call_count == 2  # 초기 시도 + 1번 재시도


class TestIntegration:
    """통합 테스트"""

    def test_full_workflow_integration(self):
        """전체 워크플로우 통합 테스트"""
        # 1. 설정 로드
        settings = get_settings()
        assert settings is not None

        # 2. 로거 생성
        request_id = generate_uuid()
        logger = create_request_logger("test-service", request_id)
        assert logger is not None

        # 3. 데이터 처리
        timestamp = format_datetime(utc_now(), format_type="iso")
        assert timestamp is not None

        # 4. 텍스트 처리
        clean_text = sanitize_text("<p>Test message</p>", remove_html=True)
        assert clean_text == "Test message"

        # 5. JSON 처리
        data = {"request_id": request_id, "message": clean_text, "timestamp": timestamp}
        json_str = safe_json_dumps(data)
        restored_data = safe_json_loads(json_str)

        assert restored_data["request_id"] == request_id
        assert restored_data["message"] == clean_text


if __name__ == "__main__":
    pytest.main([__file__])
