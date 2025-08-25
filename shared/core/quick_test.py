#!/usr/bin/env python3
"""
Quick Test Script for AI Script Generator v3.0 Core

패키지 독립성 및 기본 기능을 빠르게 검증하는 스크립트
"""

import sys
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import Any


def print_status(message: str, status: str = "INFO") -> None:
    """상태 메시지 출력"""
    colors = {
        "INFO": "\033[0;34m",  # Blue
        "SUCCESS": "\033[0;32m",  # Green
        "WARNING": "\033[1;33m",  # Yellow
        "ERROR": "\033[0;31m",  # Red
        "RESET": "\033[0m",  # Reset
    }

    symbols = {"INFO": "ℹ", "SUCCESS": "✓", "WARNING": "⚠", "ERROR": "✗"}

    color = colors.get(status, colors["INFO"])
    symbol = symbols.get(status, "•")
    reset = colors["RESET"]

    print(f"{color}{symbol}{reset} {message}")


def run_test(test_name: str, test_function: Callable[[], Any]) -> tuple[bool, Any]:
    """테스트 실행 및 결과 출력"""
    try:
        print_status(f"Running {test_name}...")
        result = test_function()
        print_status(f"{test_name} - PASSED", "SUCCESS")
        return True, result
    except Exception as e:
        print_status(f"{test_name} - FAILED: {e!s}", "ERROR")
        if "--verbose" in sys.argv:
            traceback.print_exc()
        return False, None


def test_python_version() -> str:
    """Python 버전 테스트"""
    if sys.version_info < (3, 9):
        raise ValueError(f"Python 3.9+ required, got {sys.version_info}")
    return f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def test_package_structure() -> str:
    """패키지 구조 테스트"""
    current_dir = Path(__file__).parent
    required_files = [
        "setup.py",
        "src/__init__.py",
        "src/schemas/__init__.py",
        "src/exceptions/__init__.py",
        "src/utils/__init__.py",
    ]

    missing_files = []
    for file_path in required_files:
        if not (current_dir / file_path).exists():
            missing_files.append(file_path)

    if missing_files:
        raise FileNotFoundError(f"Missing required files: {missing_files}")

    return f"All {len(required_files)} required files found"


def test_direct_imports() -> str:
    """직접 임포트 테스트"""
    # Add src to path for direct import
    current_dir = Path(__file__).parent
    src_dir = current_dir / "src"
    sys.path.insert(0, str(src_dir))

    try:
        # Test core modules

        # Test key classes/functions
        from ai_script_core.exceptions import BaseServiceException
        from ai_script_core.schemas import ProjectCreateDTO
        from ai_script_core.schemas.common import ProjectType
        from ai_script_core.utils import generate_uuid, get_settings

        # Test basic instantiation
        uuid_val = generate_uuid()
        assert len(uuid_val) == 36

        project = ProjectCreateDTO(
            name="Test Project",
            type=ProjectType.DRAMA,
            description="Test Description",
            logline="Test logline",
            deadline=None,
        )
        assert project.name == "Test Project"

        exception = BaseServiceException("Test error")
        assert exception.message == "Test error"

        settings = get_settings()
        assert hasattr(settings, "service_name")

        return "All core modules imported and functional"

    finally:
        sys.path.remove(str(src_dir))


def test_pydantic_integration() -> str:
    """Pydantic 통합 테스트"""
    current_dir = Path(__file__).parent
    src_dir = current_dir / "src"
    sys.path.insert(0, str(src_dir))

    try:
        from pydantic import ValidationError

        from ai_script_core.schemas.common import ProjectType
        from ai_script_core.schemas.generation import AIModelConfigDTO
        from ai_script_core.schemas.project import ProjectCreateDTO

        # Valid creation
        project = ProjectCreateDTO(
            name="Test Project",
            type=ProjectType.DRAMA,
            description="Test Description",
            logline="Test logline",
            deadline=None,
        )
        assert project.name == "Test Project"

        # Validation error test
        try:
            ProjectCreateDTO(
                name="a",
                type=ProjectType.DRAMA,
                description="Test Description",
                logline="Test logline",
                deadline=None,
            )  # Too short
            raise AssertionError("Validation should have failed")
        except ValidationError:
            pass  # Expected

        # AI Config test
        ai_config = AIModelConfigDTO(model_name="gpt-4", provider="openai")
        assert ai_config.model_name == "gpt-4"
        assert ai_config.temperature == 0.7  # Default value

        return "Pydantic validation working correctly"

    finally:
        sys.path.remove(str(src_dir))


def test_utility_functions() -> str:
    """유틸리티 함수 테스트"""
    current_dir = Path(__file__).parent
    src_dir = current_dir / "src"
    sys.path.insert(0, str(src_dir))

    try:
        from ai_script_core.utils.helpers import (
            calculate_hash,
            format_datetime,
            generate_short_id,
            generate_uuid,
            safe_json_dumps,
            safe_json_loads,
            sanitize_text,
            utc_now,
        )

        # UUID tests
        uuid1 = generate_uuid()
        uuid2 = generate_uuid()
        assert uuid1 != uuid2
        assert len(uuid1) == 36

        short_id = generate_short_id(8)
        assert len(short_id) == 8

        # Date/time tests
        now = utc_now()
        formatted = format_datetime(now, format_type="standard")
        assert len(formatted) > 0

        # Text processing
        dirty_text = "  <p>Hello   World</p>  "
        clean_text = sanitize_text(dirty_text, remove_html=True)
        assert clean_text == "Hello World"

        # JSON utilities
        data = {"name": "test", "value": 123}
        json_str = safe_json_dumps(data)
        restored = safe_json_loads(json_str)
        assert restored == data

        # Hash calculation
        hash1 = calculate_hash("test")
        hash2 = calculate_hash("test")
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256

        return "All utility functions working correctly"

    finally:
        sys.path.remove(str(src_dir))


def test_exception_system() -> str:
    """예외 시스템 테스트"""
    current_dir = Path(__file__).parent
    src_dir = current_dir / "src"
    sys.path.insert(0, str(src_dir))

    try:
        from ai_script_core.exceptions.base import (
            BaseServiceException,
            ErrorSeverity,
        )
        from ai_script_core.exceptions.service_errors import ProjectNotFoundError
        from ai_script_core.exceptions.utils import (
            error_response_formatter,
            exception_handler,
        )

        # Base exception test
        base_exc = BaseServiceException("Test error", error_code="TEST_001")
        assert base_exc.message == "Test error"
        assert base_exc.error_code == "TEST_001"
        assert base_exc.severity == ErrorSeverity.MEDIUM

        # Specialized exception test
        project_exc = ProjectNotFoundError("proj_123")
        assert project_exc.project_id == "proj_123"
        assert isinstance(project_exc, BaseServiceException)

        # Error formatter test
        formatted = error_response_formatter(base_exc)
        assert formatted["error"] is True
        assert formatted["error_code"] == "TEST_001"

        # Decorator test
        @exception_handler()
        def test_function() -> str:
            return "success"

        result = test_function()
        assert result == "success"

        return "Exception system working correctly"

    finally:
        sys.path.remove(str(src_dir))


def test_configuration_system() -> str:
    """설정 시스템 테스트"""
    current_dir = Path(__file__).parent
    src_dir = current_dir / "src"
    sys.path.insert(0, str(src_dir))

    try:
        from ai_script_core.utils.config import (
            APISettings,
            DatabaseSettings,
            get_settings,
        )

        # Individual settings
        db_settings = DatabaseSettings()
        assert hasattr(db_settings, "database_url")
        assert db_settings.pool_size > 0

        api_settings = APISettings()
        assert hasattr(api_settings, "host")
        assert 1 <= api_settings.port <= 65535

        # Integrated settings
        settings = get_settings()
        assert hasattr(settings, "database")
        assert hasattr(settings, "api")
        assert hasattr(settings, "logging")
        assert isinstance(settings.database, DatabaseSettings)

        return "Configuration system working correctly"

    finally:
        sys.path.remove(str(src_dir))


def test_logging_system() -> str:
    """로깅 시스템 테스트"""
    current_dir = Path(__file__).parent
    src_dir = current_dir / "src"
    sys.path.insert(0, str(src_dir))

    try:
        from ai_script_core.utils.logger import (
            StructuredFormatter,
            create_request_logger,
            get_service_logger,
        )

        # Service logger
        logger = get_service_logger("test-service")
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")

        # Request logger with context
        req_logger = create_request_logger(
            "test-service", "req_123", user_id="user_456"
        )
        assert req_logger.extra is not None
        assert req_logger.extra.get("request_id") == "req_123"
        assert req_logger.extra.get("user_id") == "user_456"

        # Structured formatter
        formatter = StructuredFormatter("test-service", "1.0.0")
        assert formatter.service_name == "test-service"

        return "Logging system working correctly"

    finally:
        sys.path.remove(str(src_dir))


def main() -> int:
    """메인 테스트 실행"""
    print("🚀 AI Script Generator v3.0 Core - Quick Test")
    print("=" * 50)

    tests = [
        ("Python Version Check", test_python_version),
        ("Package Structure", test_package_structure),
        ("Direct Imports", test_direct_imports),
        ("Pydantic Integration", test_pydantic_integration),
        ("Utility Functions", test_utility_functions),
        ("Exception System", test_exception_system),
        ("Configuration System", test_configuration_system),
        ("Logging System", test_logging_system),
    ]

    results = []
    total_tests = len(tests)
    passed_tests = 0

    print(f"\nRunning {total_tests} test categories...\n")

    for test_name, test_function in tests:
        success, result = run_test(test_name, test_function)
        results.append((test_name, success, result))
        if success:
            passed_tests += 1
            if result:
                print_status(f"  → {result}", "INFO")
        print()

    # Summary
    print("=" * 50)
    print(f"📊 Test Summary: {passed_tests}/{total_tests} tests passed")

    if passed_tests == total_tests:
        print_status("🎉 ALL TESTS PASSED!", "SUCCESS")
        print_status("Core package is ready for use!", "SUCCESS")

        print("\n📦 Package Information:")
        print("  - Name: ai-script-core")
        print("  - Version: 0.1.0")
        print("  - Python: 3.9+")
        print("  - Status: ✅ Ready for production")

        print("\n🚀 Next Steps:")
        print("  1. Run full test suite: python -m pytest tests/")
        print("  2. Install package: pip install -e .")
        print("  3. Use in microservices: from ai_script_core import ...")

        return 0
    else:
        print_status(f"❌ {total_tests - passed_tests} tests failed", "ERROR")
        print_status("Please fix issues before using the package", "WARNING")

        print("\n🔧 Failed Tests:")
        for test_name, success, result in results:
            if not success:
                print(f"  - {test_name}")

        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
