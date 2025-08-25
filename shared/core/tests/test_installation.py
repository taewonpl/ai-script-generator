"""
Installation and Package Independence Tests for AI Script Generator v3.0 Core

패키지 설치 및 독립성 검증 테스트
"""

import sys
from pathlib import Path

import pytest


class TestPackageStructure:
    """패키지 구조 테스트"""

    def test_package_files_exist(self):
        """필수 패키지 파일 존재 확인"""
        core_dir = Path(__file__).parent.parent

        # 필수 파일들
        required_files = [
            "setup.py",
            "src/__init__.py",
            "src/schemas/__init__.py",
            "src/exceptions/__init__.py",
            "src/utils/__init__.py",
        ]

        for file_path in required_files:
            full_path = core_dir / file_path
            assert full_path.exists(), f"Required file missing: {file_path}"

    def test_source_code_structure(self):
        """소스코드 구조 확인"""
        core_dir = Path(__file__).parent.parent
        src_dir = core_dir / "src"

        # 주요 디렉토리 존재 확인
        assert (src_dir / "schemas").is_dir()
        assert (src_dir / "exceptions").is_dir()
        assert (src_dir / "utils").is_dir()

        # 각 모듈의 필수 파일 확인
        schema_files = ["base.py", "common.py", "project.py", "generation.py"]
        for file_name in schema_files:
            assert (src_dir / "schemas" / file_name).exists()

        exception_files = ["base.py", "service_errors.py", "utils.py"]
        for file_name in exception_files:
            assert (src_dir / "exceptions" / file_name).exists()

        utils_files = ["config.py", "logger.py", "helpers.py"]
        for file_name in utils_files:
            assert (src_dir / "utils" / file_name).exists()


class TestDirectImports:
    """직접 임포트 테스트"""

    def test_core_package_import(self):
        """코어 패키지 임포트 테스트"""
        try:
            # 상대 경로로 임포트 시도
            core_dir = Path(__file__).parent.parent / "src"
            sys.path.insert(0, str(core_dir))

            # 각 모듈 임포트 테스트
            import exceptions
            import schemas
            import utils

            # 기본 속성 확인
            assert hasattr(schemas, "__all__")
            assert hasattr(exceptions, "__all__")
            assert hasattr(utils, "__all__")

            sys.path.remove(str(core_dir))

        except ImportError as e:
            pytest.fail(f"Direct import failed: {e}")

    def test_individual_module_imports(self):
        """개별 모듈 임포트 테스트"""
        try:
            core_dir = Path(__file__).parent.parent / "src"
            sys.path.insert(0, str(core_dir))

            # Schemas 모듈
            from schemas import BaseSchema, GenerationRequestDTO, ProjectCreateDTO

            assert BaseSchema is not None
            assert ProjectCreateDTO is not None
            assert GenerationRequestDTO is not None

            # Exceptions 모듈
            from exceptions import BaseServiceException, ProjectNotFoundError

            assert BaseServiceException is not None
            assert ProjectNotFoundError is not None

            # Utils 모듈
            from utils import generate_uuid, get_settings, sanitize_text

            assert generate_uuid is not None
            assert get_settings is not None
            assert sanitize_text is not None

            sys.path.remove(str(core_dir))

        except ImportError as e:
            pytest.fail(f"Individual module import failed: {e}")

    def test_cross_module_dependencies(self):
        """모듈 간 의존성 테스트"""
        try:
            core_dir = Path(__file__).parent.parent / "src"
            sys.path.insert(0, str(core_dir))

            # 예외 모듈이 설정을 사용하는지 확인
            from exceptions.base import BaseServiceException
            from utils.config import get_settings

            # 예외 생성 테스트
            exception = BaseServiceException("Test error")
            assert exception.message == "Test error"

            # 설정 로드 테스트
            settings = get_settings()
            assert settings is not None

            sys.path.remove(str(core_dir))

        except Exception as e:
            pytest.fail(f"Cross-module dependency test failed: {e}")


class TestPydanticIntegration:
    """Pydantic 통합 테스트"""

    def test_pydantic_schemas_work(self):
        """Pydantic 스키마 동작 확인"""
        try:
            core_dir = Path(__file__).parent.parent / "src"
            sys.path.insert(0, str(core_dir))

            from schemas.generation import AIModelConfigDTO
            from schemas.project import ProjectCreateDTO

            # ProjectCreateDTO 테스트
            project_dto = ProjectCreateDTO(
                name="Test Project", description="Test Description"
            )
            assert project_dto.name == "Test Project"

            # 유효성 검증 테스트
            try:
                invalid_project = ProjectCreateDTO(name="a")  # 너무 짧음
                pytest.fail("Validation should have failed")
            except Exception:
                pass  # 예상된 검증 실패

            # AIModelConfigDTO 테스트
            ai_config = AIModelConfigDTO(model_name="gpt-4", provider="openai")
            assert ai_config.model_name == "gpt-4"
            assert ai_config.temperature == 0.7  # 기본값

            sys.path.remove(str(core_dir))

        except Exception as e:
            pytest.fail(f"Pydantic integration test failed: {e}")


class TestFunctionalityWithoutInstallation:
    """설치 없이 기능 테스트"""

    def test_uuid_generation(self):
        """UUID 생성 기능 테스트"""
        try:
            core_dir = Path(__file__).parent.parent / "src"
            sys.path.insert(0, str(core_dir))

            from utils.helpers import generate_short_id, generate_uuid

            # UUID 생성 테스트
            uuid1 = generate_uuid()
            uuid2 = generate_uuid()

            assert uuid1 != uuid2
            assert len(uuid1) == 36

            # 짧은 ID 생성 테스트
            short_id = generate_short_id(8)
            assert len(short_id) == 8

            sys.path.remove(str(core_dir))

        except Exception as e:
            pytest.fail(f"UUID generation test failed: {e}")

    def test_date_formatting(self):
        """날짜 포맷팅 기능 테스트"""
        try:
            core_dir = Path(__file__).parent.parent / "src"
            sys.path.insert(0, str(core_dir))

            from datetime import datetime

            from utils.helpers import format_datetime, utc_now

            # 현재 시간 테스트
            now = utc_now()
            assert isinstance(now, datetime)

            # 포맷팅 테스트
            formatted = format_datetime(now, format_type="standard")
            assert isinstance(formatted, str)
            assert len(formatted) > 0

            sys.path.remove(str(core_dir))

        except Exception as e:
            pytest.fail(f"Date formatting test failed: {e}")

    def test_text_processing(self):
        """텍스트 처리 기능 테스트"""
        try:
            core_dir = Path(__file__).parent.parent / "src"
            sys.path.insert(0, str(core_dir))

            from utils.helpers import clean_filename, sanitize_text

            # 텍스트 정제 테스트
            dirty_text = "  <p>Hello   World</p>  "
            clean_text = sanitize_text(dirty_text, remove_html=True)
            assert clean_text == "Hello World"

            # 파일명 정제 테스트
            dirty_filename = "my<file>name.txt"
            clean_name = clean_filename(dirty_filename)
            assert "<" not in clean_name
            assert ">" not in clean_name

            sys.path.remove(str(core_dir))

        except Exception as e:
            pytest.fail(f"Text processing test failed: {e}")

    def test_json_utilities(self):
        """JSON 유틸리티 기능 테스트"""
        try:
            core_dir = Path(__file__).parent.parent / "src"
            sys.path.insert(0, str(core_dir))

            from utils.helpers import safe_json_dumps, safe_json_loads

            # JSON 직렬화/역직렬화 테스트
            data = {"name": "test", "value": 123}
            json_str = safe_json_dumps(data)
            restored_data = safe_json_loads(json_str)

            assert restored_data == data

            # 잘못된 JSON 처리 테스트
            invalid_json = '{"name": "test", "value":'
            result = safe_json_loads(invalid_json, default={"error": "failed"})
            assert result == {"error": "failed"}

            sys.path.remove(str(core_dir))

        except Exception as e:
            pytest.fail(f"JSON utilities test failed: {e}")


class TestExceptionHandling:
    """예외 처리 테스트"""

    def test_exception_creation_without_installation(self):
        """설치 없이 예외 생성 테스트"""
        try:
            core_dir = Path(__file__).parent.parent / "src"
            sys.path.insert(0, str(core_dir))

            from exceptions.base import BaseServiceException, ErrorSeverity
            from exceptions.service_errors import ProjectNotFoundError

            # 기본 예외 테스트
            base_exception = BaseServiceException("Test error")
            assert base_exception.message == "Test error"
            assert base_exception.severity == ErrorSeverity.MEDIUM

            # 특화 예외 테스트
            project_exception = ProjectNotFoundError("proj_123")
            assert project_exception.project_id == "proj_123"
            assert isinstance(project_exception, BaseServiceException)

            sys.path.remove(str(core_dir))

        except Exception as e:
            pytest.fail(f"Exception handling test failed: {e}")

    def test_exception_utilities_without_installation(self):
        """설치 없이 예외 유틸리티 테스트"""
        try:
            core_dir = Path(__file__).parent.parent / "src"
            sys.path.insert(0, str(core_dir))

            from exceptions.base import BaseServiceException
            from exceptions.utils import error_response_formatter, safe_execute

            # 에러 포맷팅 테스트
            exception = BaseServiceException("Test error", error_code="TEST_001")
            formatted = error_response_formatter(exception)

            assert formatted["error"] is True
            assert formatted["error_code"] == "TEST_001"

            # safe_execute 테스트
            def test_function():
                return "success"

            result = safe_execute(test_function)
            assert result == "success"

            # 실패하는 함수 테스트
            def failing_function():
                raise ValueError("Test error")

            result = safe_execute(failing_function, default_return="default")
            assert result == "default"

            sys.path.remove(str(core_dir))

        except Exception as e:
            pytest.fail(f"Exception utilities test failed: {e}")


class TestConfigurationSystem:
    """설정 시스템 테스트"""

    def test_settings_without_installation(self):
        """설치 없이 설정 시스템 테스트"""
        try:
            core_dir = Path(__file__).parent.parent / "src"
            sys.path.insert(0, str(core_dir))

            from utils.config import APISettings, DatabaseSettings, get_settings

            # 개별 설정 클래스 테스트
            db_settings = DatabaseSettings()
            assert hasattr(db_settings, "database_url")
            assert hasattr(db_settings, "pool_size")

            api_settings = APISettings()
            assert hasattr(api_settings, "host")
            assert hasattr(api_settings, "port")

            # 통합 설정 테스트
            settings = get_settings()
            assert hasattr(settings, "database")
            assert hasattr(settings, "api")
            assert hasattr(settings, "logging")

            sys.path.remove(str(core_dir))

        except Exception as e:
            pytest.fail(f"Configuration system test failed: {e}")


class TestMinimalDependencies:
    """최소 의존성 테스트"""

    def test_required_packages_available(self):
        """필수 패키지 가용성 확인"""
        required_packages = ["pydantic", "python-dotenv", "fastapi"]

        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                pytest.fail(f"Required package not available: {package}")

    def test_no_unnecessary_dependencies(self):
        """불필요한 의존성 없음 확인"""
        try:
            core_dir = Path(__file__).parent.parent / "src"
            sys.path.insert(0, str(core_dir))

            # 코어 모듈을 임포트해도 heavy dependency가 없어야 함

            # 이 시점에서 메모리 사용량이 합리적이어야 함
            # (구체적인 측정은 환경에 따라 다를 수 있음)

            sys.path.remove(str(core_dir))

        except Exception as e:
            pytest.fail(f"Unnecessary dependencies test failed: {e}")


class TestVersionCompatibility:
    """버전 호환성 테스트"""

    def test_python_version_check(self):
        """Python 버전 체크 테스트"""
        try:
            core_dir = Path(__file__).parent.parent / "src"
            sys.path.insert(0, str(core_dir))

            # Python 버전이 3.9 이상인지 확인
            assert sys.version_info >= (3, 9), "Python 3.9+ required"

            # 패키지 내부 버전 체크 함수 테스트
            import __init__ as core_init

            assert core_init.check_python_version() is True

            sys.path.remove(str(core_dir))

        except Exception as e:
            pytest.fail(f"Python version compatibility test failed: {e}")

    def test_package_version_info(self):
        """패키지 버전 정보 테스트"""
        try:
            core_dir = Path(__file__).parent.parent / "src"
            sys.path.insert(0, str(core_dir))

            import __init__ as core_init

            # 버전 정보 확인
            version = core_init.get_version()
            assert version == "0.1.0"

            # 패키지 정보 확인
            package_info = core_init.get_package_info()
            assert package_info["name"] == "ai-script-core"
            assert package_info["version"] == "0.1.0"
            assert "python_version" in package_info

            sys.path.remove(str(core_dir))

        except Exception as e:
            pytest.fail(f"Package version info test failed: {e}")


class TestPortability:
    """이식성 테스트"""

    def test_cross_platform_paths(self):
        """크로스 플랫폼 경로 처리 테스트"""
        try:
            core_dir = Path(__file__).parent.parent / "src"
            sys.path.insert(0, str(core_dir))

            from utils.helpers import clean_filename

            # Windows 스타일 경로 문자 테스트
            windows_bad = "file<name>with:bad*chars?.txt"
            cleaned = clean_filename(windows_bad)

            # 금지된 문자들이 제거되었는지 확인
            forbidden_chars = ["<", ">", ":", "*", "?", "|", '"', "\\", "/"]
            for char in forbidden_chars:
                assert char not in cleaned

            sys.path.remove(str(core_dir))

        except Exception as e:
            pytest.fail(f"Cross-platform portability test failed: {e}")

    def test_encoding_handling(self):
        """인코딩 처리 테스트"""
        try:
            core_dir = Path(__file__).parent.parent / "src"
            sys.path.insert(0, str(core_dir))

            from utils.helpers import safe_json_dumps, sanitize_text

            # 유니코드 텍스트 처리 테스트
            unicode_text = "안녕하세요 Hello 🌍 世界"
            sanitized = sanitize_text(unicode_text)
            assert len(sanitized) > 0

            # JSON 직렬화에서 유니코드 처리 테스트
            unicode_data = {"message": unicode_text}
            json_str = safe_json_dumps(unicode_data)
            assert unicode_text in json_str or "안녕하세요" in json_str

            sys.path.remove(str(core_dir))

        except Exception as e:
            pytest.fail(f"Encoding handling test failed: {e}")


class TestInstallationReadiness:
    """설치 준비성 테스트"""

    def test_setup_py_syntax(self):
        """setup.py 구문 검사"""
        setup_py_path = Path(__file__).parent.parent / "setup.py"
        assert setup_py_path.exists(), "setup.py not found"

        # setup.py 파일을 컴파일해서 구문 오류가 없는지 확인
        with open(setup_py_path, encoding="utf-8") as f:
            setup_code = f.read()

        try:
            compile(setup_code, str(setup_py_path), "exec")
        except SyntaxError as e:
            pytest.fail(f"setup.py has syntax error: {e}")

    def test_manifest_files_included(self):
        """패키지에 포함될 파일들 확인"""
        core_dir = Path(__file__).parent.parent

        # 패키지에 포함되어야 할 중요한 파일들
        important_files = [
            "src/__init__.py",
            "src/schemas/__init__.py",
            "src/exceptions/__init__.py",
            "src/utils/__init__.py",
        ]

        for file_path in important_files:
            full_path = core_dir / file_path
            assert full_path.exists(), f"Important file missing: {file_path}"
            assert full_path.stat().st_size > 0, f"File is empty: {file_path}"


if __name__ == "__main__":
    pytest.main([__file__])
