"""
Common Response Schemas for AI Script Generator v3.0

공통 응답 스키마와 서비스 상태 관련 DTO를 정의합니다.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import Field

from .base import BaseResponseSchema, BaseSchema


class ProjectStatus(str, Enum):
    """프로젝트 상태"""

    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"
    CANCELLED = "cancelled"


class ProjectType(str, Enum):
    """프로젝트 타입"""

    DRAMA = "drama"
    COMEDY = "comedy"
    ROMANCE = "romance"
    THRILLER = "thriller"
    DOCUMENTARY = "documentary"
    WEB_SERIES = "web_series"
    SHORT_FILM = "short_film"
    ADVERTISEMENT = "advertisement"
    EDUCATION = "education"


class EpisodeType(str, Enum):
    """에피소드 타입"""

    MAIN = "main"
    SPECIAL = "special"
    PILOT = "pilot"
    FINALE = "finale"
    FLASHBACK = "flashback"
    BONUS = "bonus"


class GenerationStatus(str, Enum):
    """생성 상태"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    COMPLETED_PENDING_SAVE = "completed_pending_save"  # 생성 완료, 저장 대기 중
    FAILED = "failed"
    CANCELLED = "cancelled"
    SAVE_FAILED = "save_failed"  # 저장 실패


class ServiceStatus(str, Enum):
    """서비스 상태"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    MAINTENANCE = "maintenance"


class ErrorCode(str, Enum):
    """표준 에러 코드"""

    # 일반 오류
    INTERNAL_ERROR = "INTERNAL_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"

    # 비즈니스 로직 오류
    PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"
    EPISODE_NOT_FOUND = "EPISODE_NOT_FOUND"
    GENERATION_FAILED = "GENERATION_FAILED"
    DUPLICATE_RESOURCE = "DUPLICATE_RESOURCE"

    # 서비스 오류
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    TIMEOUT = "TIMEOUT"

    # 외부 서비스 오류
    AI_SERVICE_ERROR = "AI_SERVICE_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    EXTERNAL_API_ERROR = "EXTERNAL_API_ERROR"


class ErrorResponseDTO(BaseSchema):
    """표준 에러 응답 DTO"""

    error: bool = Field(True, description="에러 여부")
    error_code: ErrorCode = Field(..., description="에러 코드")
    message: str = Field(..., description="에러 메시지")
    details: dict[str, Any] | None = Field(None, description="에러 상세 정보")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="에러 발생 시간"
    )

    # 디버깅 정보 (개발 환경에서만 포함)
    trace_id: str | None = Field(None, description="추적 ID")
    request_id: str | None = Field(None, description="요청 ID")

    @classmethod
    def create(
        cls,
        error_code: ErrorCode,
        message: str,
        details: dict[str, Any] | None = None,
        trace_id: str | None = None,
        request_id: str | None = None,
    ) -> ErrorResponseDTO:
        """에러 응답 생성"""
        return cls(
            error=True,
            error_code=error_code,
            message=message,
            details=details,
            trace_id=trace_id,
            request_id=request_id,
        )


class SuccessResponseDTO(BaseResponseSchema[Any]):
    """표준 성공 응답 DTO"""

    error: bool = Field(False, description="에러 여부")

    @classmethod
    def create(cls, data: Any = None, message: str = "Success") -> SuccessResponseDTO:
        """성공 응답 생성"""
        return cls(success=True, error=False, message=message, data=data)


class ServiceStatusDTO(BaseSchema):
    """서비스 상태 DTO"""

    service_name: str = Field(..., description="서비스 이름")
    version: str = Field(..., description="서비스 버전")
    status: ServiceStatus = Field(..., description="서비스 상태")
    uptime_seconds: int = Field(..., description="가동 시간(초)")

    # 성능 지표
    cpu_usage_percent: float | None = Field(None, description="CPU 사용률")
    memory_usage_percent: float | None = Field(None, description="메모리 사용률")
    disk_usage_percent: float | None = Field(None, description="디스크 사용률")

    # 연결 상태
    database_connected: bool = Field(..., description="데이터베이스 연결 상태")
    external_services: dict[str, bool] = Field(
        default_factory=dict, description="외부 서비스 연결 상태"
    )

    # 처리 통계
    requests_per_minute: int | None = Field(None, description="분당 요청 수")
    average_response_time_ms: float | None = Field(
        None, description="평균 응답 시간(밀리초)"
    )
    error_rate_percent: float | None = Field(None, description="에러율")

    # 추가 정보
    environment: str = Field(default="production", description="실행 환경")
    deployment_time: datetime = Field(..., description="배포 시간")
    health_check_time: datetime = Field(
        default_factory=datetime.now, description="헬스체크 시간"
    )

    # 상세 정보 (디버깅용)
    details: dict[str, Any] = Field(default_factory=dict, description="상세 상태 정보")


class CommonResponseDTO(BaseResponseSchema[Any]):
    """공통 응답 DTO"""

    pass
