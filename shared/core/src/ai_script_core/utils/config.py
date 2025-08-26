"""
Configuration Management for AI Script Generator v3.0

pydantic BaseSettings를 사용한 고급 설정 관리 시스템을 제공합니다.
"""

from functools import lru_cache
from pathlib import Path
from typing import Any, Optional, Dict, List, Union

# Import pydantic v2 components
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from ..exceptions import ConfigurationError


class BaseServiceSettings(BaseSettings):
    """모든 서비스 설정의 기본 클래스"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        validate_assignment=True,
    )

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.validate_configuration()

    def validate_configuration(self) -> None:
        """설정 검증 로직"""
        pass

    def to_dict(self) -> Dict[str, Any]:
        """설정을 딕셔너리로 변환"""
        return self.model_dump()

    def to_json(self, **kwargs: Any) -> str:
        """설정을 JSON 문자열로 변환"""
        return self.model_dump_json(**kwargs)


class DatabaseSettings(BaseServiceSettings):
    """데이터베이스 설정"""

    # 기본 연결 설정
    database_url: str = Field(
        default="sqlite:///./ai_script_generator.db",
        description="데이터베이스 연결 URL",
    )

    # 커넥션 풀 설정
    pool_size: int = Field(default=5, ge=1, le=50, description="커넥션 풀 크기")
    max_overflow: int = Field(
        default=10,
        ge=0,
        le=100,
        description="최대 오버플로우 커넥션 수",
    )
    pool_timeout: int = Field(default=30, ge=1, description="커넥션 획득 타임아웃(초)")
    pool_recycle: int = Field(
        default=3600,
        ge=300,
        description="커넥션 재활용 시간(초)",
    )

    # 디버깅 및 로깅
    echo: bool = Field(default=False, description="SQL 쿼리 에코 여부")
    echo_pool: bool = Field(default=False, description="커넥션 풀 로깅 여부")

    # 성능 최적화
    isolation_level: Optional[str] = Field(default=None, description="트랜쟭션 격리 수준")

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError("Database URL cannot be empty")
        return v

    def validate_configuration(self) -> None:
        """데이터베이스 설정 검증"""
        if self.pool_size <= 0:
            raise ConfigurationError("pool_size", "Pool size must be positive")

        if self.max_overflow < 0:
            raise ConfigurationError("max_overflow", "Max overflow cannot be negative")


class APISettings(BaseServiceSettings):
    """API 서버 설정"""

    # 서버 설정
    host: str = Field(default="127.0.0.1", description="서버 호스트")
    port: int = Field(default=8000, ge=1, le=65535, description="서버 포트")

    # 개발 설정
    debug: bool = Field(default=False, description="디버그 모드")
    reload: bool = Field(default=False, description="자동 리로드")

    # 워커 설정
    workers: int = Field(default=1, ge=1, le=32, description="워커 프로세스 수")

    # 보안 설정
    allowed_hosts: List[str] = Field(default=["*"], description="허용된 호스트 목록")

    # 요청 제한
    max_request_size: int = Field(
        default=16777216,  # 16MB
        ge=1024,  # 1KB
        description="최대 요청 크기(바이트)",
    )
    request_timeout: int = Field(
        default=300,  # 5분
        ge=1,
        description="요청 타임아웃(초)",
    )

    @field_validator("allowed_hosts", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [host.strip() for host in v.split(",") if host.strip()]
        return v


class LoggingSettings(BaseServiceSettings):
    """로깅 설정"""

    # 기본 로그 레벨
    level: str = Field(
        default="INFO",
        pattern=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
        description="로그 레벨",
    )

    # 로그 포맷
    format: str = Field(
        default="json",
        pattern=r"^(json|text)$",
        description="로그 포맷 (json 또는 text)",
    )

    # 파일 로그 설정
    file_enabled: bool = Field(default=False, description="파일 로깅 활성화")
    file_path: Optional[str] = Field(
        default="logs/ai_script_generator.log",
        description="로그 파일 경로",
    )
    file_max_size: int = Field(
        default=10485760,  # 10MB
        ge=1024,  # 1KB
        description="로그 파일 최대 크기(바이트)",
    )
    file_backup_count: int = Field(
        default=5,
        ge=1,
        le=50,
        description="백업 파일 개수",
    )

    # 콘솔 로그 설정
    console_enabled: bool = Field(default=True, description="콘솔 로깅 활성화")

    # 구조화된 로그 메타데이터
    include_trace: bool = Field(default=False, description="트레이스 정보 포함")
    service_name: str = Field(default="ai-script-generator", description="서비스 이름")
    service_version: str = Field(default="3.0.0", description="서비스 버전")

    def validate_configuration(self) -> None:
        """로깅 설정 검증"""
        if self.file_enabled and self.file_path:
            # 로그 디렉토리 생성
            log_dir = Path(self.file_path).parent
            log_dir.mkdir(parents=True, exist_ok=True)


class SecuritySettings(BaseServiceSettings):
    """보안 설정"""

    # JWT 설정
    secret_key: str = Field(
        default="your-secret-key-change-this-in-production",  # pragma: allowlist secret
        min_length=32,
        description="JWT 서명 키",
    )
    algorithm: str = Field(
        default="HS256",
        pattern=r"^(HS256|HS384|HS512|RS256|RS384|RS512)$",
        description="JWT 알고리즘",
    )
    access_token_expire_minutes: int = Field(
        default=30,
        ge=1,
        le=10080,  # 1주일
        description="액세스 토큰 만료 시간(분)",
    )
    refresh_token_expire_days: int = Field(
        default=7,
        ge=1,
        le=365,
        description="리프레시 토큰 만료 시간(일)",
    )

    # CORS 설정
    cors_origins: List[str] = Field(default=["*"], description="CORS 허용 오리진")
    cors_methods: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "PATCH"],
        description="CORS 허용 메서드",
    )
    cors_headers: List[str] = Field(default=["*"], description="CORS 허용 헤더")
    cors_credentials: bool = Field(default=True, description="CORS 자격 증명 허용")

    # 레이트 리미팅
    rate_limit_enabled: bool = Field(default=True, description="레이트 리미팅 활성화")
    rate_limit_requests: int = Field(
        default=100,
        ge=1,
        description="시간 창당 허용 요청 수",
    )
    rate_limit_window: int = Field(
        default=60,  # 1분
        ge=1,
        description="레이트 리미트 시간 창(초)",
    )

    @field_validator("cors_origins", "cors_methods", "cors_headers", mode="before")
    @classmethod
    def parse_cors_lists(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    def validate_configuration(self) -> None:
        """보안 설정 검증"""
        import os

        if (
            self.secret_key == "your-secret-key-change-this-in-production"
        ):  # pragma: allowlist secret
            if os.getenv("ENV") in {"prod", "production"}:
                raise ConfigurationError(
                    "secret_key",
                    "Default secret key detected. Please change it for production.",
                )
            else:
                # Development environment - log warning instead of raising error
                import logging

                logger = logging.getLogger(__name__)
                logger.warning("SECRET_KEY not set - using default (development only)")


class AIServiceSettings(BaseServiceSettings):
    """AI 서비스 설정"""

    # OpenAI 설정
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API 키")
    openai_organization: Optional[str] = Field(default=None, description="OpenAI 조직 ID")

    # Claude 설정 (Anthropic)
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API 키")

    # 기본 모델 설정
    default_model: str = Field(default="gpt-3.5-turbo", description="기본 AI 모델")
    max_tokens: int = Field(default=2000, ge=100, le=8000, description="최대 토큰 수")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="생성 온도")

    # 타임아웃 및 재시도
    request_timeout: int = Field(
        default=60,
        ge=5,
        le=300,
        description="AI API 요청 타임아웃(초)",
    )
    max_retries: int = Field(default=3, ge=0, le=10, description="최대 재시도 횟수")


class Settings(BaseServiceSettings):
    """전체 애플리케이션 설정"""

    # 환경
    environment: str = Field(
        default="development",
        pattern=r"^(development|staging|production)$",
        description="실행 환경",
    )

    # 서비스 정보
    service_name: str = Field(default="ai-script-generator", description="서비스 이름")
    service_version: str = Field(default="3.0.0", description="서비스 버전")

    # 개별 설정
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    api: APISettings = Field(default_factory=APISettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    ai_service: AIServiceSettings = Field(default_factory=AIServiceSettings)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        validate_assignment=True,
    )

    @model_validator(mode="before")
    @classmethod
    def validate_environment_consistency(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """환경별 설정 일관성 검증"""
        env = values.get("environment", "development")

        if env == "production":
            # 프로덕션 환경 필수 검증
            database = values.get("database", {})
            if hasattr(database, "database_url") and "sqlite" in database.database_url:
                raise ValueError("SQLite is not recommended for production")

            api = values.get("api", {})
            if hasattr(api, "debug") and api.debug:
                raise ValueError("Debug mode should be disabled in production")

        return values

    def is_production(self) -> bool:
        """프로덕션 환경 여부"""
        return self.environment == "production"

    def is_development(self) -> bool:
        """개발 환경 여부"""
        return self.environment == "development"


@lru_cache
def get_settings() -> Settings:
    """설정 싱글톤 인스턴스 반환"""
    return Settings()


def create_service_settings(
    service_name: str, additional_settings: Optional[Dict[str, Any]] = None
) -> BaseServiceSettings:
    """서비스별 설정 생성"""

    class ServiceSpecificSettings(BaseServiceSettings):
        """서비스별 동적 설정 클래스"""

        def __init__(self, **kwargs: Any) -> None:
            if additional_settings:
                kwargs.update(additional_settings)
            super().__init__(**kwargs)

        class Config:
            env_prefix = f"{service_name.upper()}_"
            env_file = f".{service_name}.env"

    return ServiceSpecificSettings()


def validate_all_settings() -> Dict[str, bool]:
    """모든 설정 검증 결과 반환"""
    validation_results = {}

    try:
        settings = get_settings()

        # 각 설정 모듈 검증
        for setting_name in ["database", "api", "logging", "security", "ai_service"]:
            try:
                setting_obj = getattr(settings, setting_name)
                setting_obj.validate_configuration()
                validation_results[setting_name] = True
            except Exception as e:
                validation_results[setting_name] = False
                print(f"Validation failed for {setting_name}: {e}")

    except Exception as e:
        print(f"Settings validation error: {e}")
        validation_results["global"] = False

    return validation_results
