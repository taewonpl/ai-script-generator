"""
Base Schemas for AI Script Generator v3.0

서비스 간 통신용 공통 기본 스키마를 정의합니다.
"""

from datetime import datetime
from typing import Generic, TypeVar, Optional, List

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class BaseSchema(BaseModel):
    """모든 스키마의 기본 클래스"""

    model_config = ConfigDict(
        use_enum_values=True,
        from_attributes=True,
        protected_namespaces=(),
        json_encoders={datetime: lambda v: v.isoformat() if v else None},
    )


class IDMixin(BaseModel):
    """ID 필드를 포함하는 믹스인"""

    id: str = Field(..., description="고유 식별자")


class TimestampMixin(BaseModel):
    """타임스탬프 필드를 포함하는 믹스인"""

    created_at: datetime = Field(..., description="생성 시간")
    updated_at: datetime = Field(..., description="수정 시간")


class BaseResponseSchema(BaseSchema, Generic[T]):
    """기본 응답 스키마"""

    success: bool = Field(..., description="성공 여부")
    message: str = Field(..., description="응답 메시지")
    data: Optional[T] = Field(None, description="응답 데이터")
    timestamp: datetime = Field(default_factory=datetime.now, description="응답 시간")

    @classmethod
    def success_response(
        cls, data: Optional[T] = None, message: str = "Success"
    ) -> "BaseResponseSchema[T]":
        """성공 응답 생성"""
        return cls(success=True, message=message, data=data)

    @classmethod
    def error_response(
        cls, message: str = "Error occurred", data: Optional[T] = None
    ) -> "BaseResponseSchema[T]":
        """오류 응답 생성"""
        return cls(success=False, message=message, data=data)


class PaginationSchema(BaseSchema):
    """페이지네이션 스키마"""

    page: int = Field(default=1, ge=1, description="현재 페이지 번호")
    size: int = Field(default=20, ge=1, le=100, description="페이지당 항목 수")
    total: int = Field(..., ge=0, description="전체 항목 수")
    total_pages: int = Field(..., ge=0, description="전체 페이지 수")
    has_next: bool = Field(..., description="다음 페이지 존재 여부")
    has_prev: bool = Field(..., description="이전 페이지 존재 여부")

    @classmethod
    def calculate(cls, page: int, size: int, total: int) -> "PaginationSchema":
        """페이지네이션 정보 계산"""
        total_pages = (total + size - 1) // size if total > 0 else 0
        return cls(
            page=page,
            size=size,
            total=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )


class PaginatedResponse(BaseSchema, Generic[T]):
    """페이지네이션된 응답 스키마"""

    items: List[T] = Field(..., description="데이터 목록")
    pagination: PaginationSchema = Field(..., description="페이지네이션 정보")

    @classmethod
    def create(
        cls, items: List[T], page: int, size: int, total: int
    ) -> "PaginatedResponse[T]":
        """페이지네이션된 응답 생성"""
        pagination = PaginationSchema.calculate(page, size, total)
        return cls(items=items, pagination=pagination)


class RequestMetadata(BaseSchema):
    """요청 메타데이터"""

    request_id: Optional[str] = Field(None, description="요청 ID")
    user_id: Optional[str] = Field(None, description="사용자 ID")
    service_name: Optional[str] = Field(None, description="요청한 서비스명")
    timestamp: datetime = Field(default_factory=datetime.now, description="요청 시간")


class ResponseMetadata(BaseSchema):
    """응답 메타데이터"""

    request_id: Optional[str] = Field(None, description="요청 ID")
    service_name: str = Field(..., description="응답한 서비스명")
    version: str = Field(..., description="서비스 버전")
    timestamp: datetime = Field(default_factory=datetime.now, description="응답 시간")
    processing_time_ms: Optional[int] = Field(None, description="처리 시간(밀리초)")
