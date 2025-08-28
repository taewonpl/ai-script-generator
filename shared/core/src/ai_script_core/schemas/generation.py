"""
Generation Schemas for AI Script Generator v3.0

AI 생성 및 RAG 관련 서비스 간 통신용 DTO를 정의합니다.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field, field_validator

from .base import BaseSchema, IDMixin, TimestampMixin
from .common import GenerationStatus


class AIModelConfigDTO(BaseSchema):
    """AI 모델 설정 DTO"""

    model_name: str = Field(..., description="AI 모델명 (예: gpt-4, claude-3)")
    provider: str = Field(..., description="AI 서비스 제공업체")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="창의성 온도")
    max_tokens: int = Field(default=2000, ge=100, le=8000, description="최대 토큰 수")
    top_p: float = Field(default=1.0, ge=0.0, le=1.0, description="Top-p 샘플링")
    frequency_penalty: float = Field(
        default=0.0, ge=-2.0, le=2.0, description="빈도 패널티"
    )
    presence_penalty: float = Field(
        default=0.0, ge=-2.0, le=2.0, description="존재 패널티"
    )

    # 추가 설정 (모델별로 다를 수 있음)
    extra_params: dict[str, Any] = Field(
        default_factory=dict, description="추가 매개변수"
    )

    @field_validator("model_name")
    @classmethod
    def validate_model_name(cls, v: Any) -> Any:
        allowed_models = [
            "gpt-3.5-turbo",
            "gpt-4",
            "gpt-4-turbo",
            "gpt-4o",
            "claude-3-haiku",
            "claude-3-sonnet",
            "claude-3-opus",
            "claude-3-5-sonnet",
        ]
        if v not in allowed_models:
            raise ValueError(f"Model must be one of: {allowed_models}")
        return v


class RAGConfigDTO(BaseSchema):
    """RAG (Retrieval-Augmented Generation) 설정 DTO"""

    enabled: bool = Field(default=True, description="RAG 활성화 여부")

    # 검색 설정
    search_top_k: int = Field(default=5, ge=1, le=20, description="검색할 상위 문서 수")
    similarity_threshold: float = Field(
        default=0.7, ge=0.0, le=1.0, description="유사도 임계값"
    )

    # 임베딩 설정
    embedding_model: str = Field(
        default="text-embedding-ada-002", description="임베딩 모델"
    )
    chunk_size: int = Field(default=1000, ge=100, le=4000, description="문서 청크 크기")
    chunk_overlap: int = Field(
        default=200, ge=0, le=1000, description="청크 간 겹침 크기"
    )

    # 지식베이스 설정
    knowledge_base_ids: list[str] = Field(
        default_factory=list, description="사용할 지식베이스 ID 목록"
    )
    include_metadata: bool = Field(default=True, description="메타데이터 포함 여부")

    # 필터링
    document_types: list[str] | None = Field(None, description="문서 타입 필터")
    date_range: dict[str, datetime] | None = Field(None, description="날짜 범위 필터")
    tags: list[str] | None = Field(None, description="태그 필터")


class GenerationRequestDTO(BaseSchema, IDMixin):
    """생성 요청 DTO"""

    project_id: str = Field(..., description="프로젝트 ID")
    episode_id: str | None = Field(None, description="에피소드 ID (선택적)")

    # 생성 타입 및 목적
    generation_type: str = Field(
        ..., description="생성 타입 (script, character, scene, dialogue 등)"
    )
    purpose: str = Field(..., description="생성 목적 설명")

    # 프롬프트 및 컨텍스트
    prompt: str = Field(
        ..., min_length=10, max_length=10000, description="메인 프롬프트"
    )
    system_prompt: str | None = Field(
        None, max_length=2000, description="시스템 프롬프트"
    )
    context: str | None = Field(None, max_length=5000, description="추가 컨텍스트")

    # 스타일 및 톤
    style_guide: str | None = Field(None, description="스타일 가이드")
    tone: str | None = Field(None, description="톤 (formal, casual, dramatic 등)")
    genre_hints: list[str] = Field(default_factory=list, description="장르 힌트")

    # AI 및 RAG 설정
    ai_config: AIModelConfigDTO = Field(..., description="AI 모델 설정")
    rag_config: RAGConfigDTO | None = Field(None, description="RAG 설정")

    # 메타데이터
    priority: int = Field(
        default=0, ge=0, le=10, description="우선순위 (0=낮음, 10=높음)"
    )
    deadline: datetime | None = Field(None, description="완료 기한")
    callback_url: str | None = Field(None, description="완료 시 호출할 콜백 URL")

    @field_validator("generation_type")
    @classmethod
    def validate_generation_type(cls, v: Any) -> str:
        allowed_types = [
            "script",
            "character",
            "scene",
            "dialogue",
            "synopsis",
            "treatment",
            "outline",
            "logline",
            "pitch",
            "revision",
        ]
        if v not in allowed_types:
            raise ValueError(f"Generation type must be one of: {allowed_types}")
        return str(v)


class GenerationMetadataDTO(BaseSchema):
    """생성 메타데이터 DTO"""

    # AI 모델 정보
    model_used: str = Field(..., description="사용된 AI 모델")
    model_version: str | None = Field(None, description="모델 버전")

    # 성능 메트릭
    generation_time_ms: int = Field(..., description="생성 시간(밀리초)")
    token_usage: dict[str, int] = Field(
        ..., description="토큰 사용량 (prompt_tokens, completion_tokens, total_tokens)"
    )
    cost_estimate: float | None = Field(None, description="예상 비용 (USD)")

    # RAG 정보 (사용된 경우)
    rag_used: bool = Field(default=False, description="RAG 사용 여부")
    retrieved_docs_count: int = Field(default=0, description="검색된 문서 수")
    avg_similarity_score: float | None = Field(None, description="평균 유사도 점수")

    # 품질 메트릭
    content_length: int = Field(default=0, description="생성된 내용 길이")
    readability_score: float | None = Field(None, description="가독성 점수")
    coherence_score: float | None = Field(None, description="일관성 점수")

    # 처리 정보
    retry_count: int = Field(default=0, description="재시도 횟수")
    processing_node: str | None = Field(None, description="처리 노드 ID")

    # 추가 메타데이터
    extra_metadata: dict[str, Any] = Field(
        default_factory=dict, description="추가 메타데이터"
    )


class GenerationResponseDTO(BaseSchema, IDMixin, TimestampMixin):
    """생성 응답 DTO"""

    request_id: str = Field(..., description="원본 요청 ID")
    project_id: str = Field(..., description="프로젝트 ID")
    episode_id: str | None = Field(None, description="에피소드 ID")

    # 상태 및 결과
    status: GenerationStatus = Field(..., description="생성 상태")
    progress_percentage: float = Field(
        default=0.0, ge=0.0, le=100.0, description="진행률"
    )

    # 생성된 내용
    content: str | None = Field(None, description="생성된 주요 내용")
    title: str | None = Field(None, description="생성된 제목")
    summary: str | None = Field(None, description="내용 요약")

    # 구조화된 결과 (타입에 따라 다름)
    structured_result: dict[str, Any] | None = Field(
        None, description="구조화된 생성 결과"
    )

    # 메타데이터
    metadata: GenerationMetadataDTO = Field(..., description="생성 메타데이터")

    # 오류 정보
    error_message: str | None = Field(None, description="오류 메시지")
    error_code: str | None = Field(None, description="오류 코드")

    # 피드백 및 평가
    quality_score: float | None = Field(None, ge=0.0, le=1.0, description="품질 점수")
    feedback: str | None = Field(None, description="피드백")
