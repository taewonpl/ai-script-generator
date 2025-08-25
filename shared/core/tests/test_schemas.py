"""
Schema Validation Tests for AI Script Generator v3.0 Core

스키마 독립성 및 검증 테스트
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

# Core 모듈에서 스키마 import 테스트
try:
    from ai_script_core.schemas import (
        AIModelConfigDTO,
        BaseResponseSchema,
        # Base schemas
        BaseSchema,
        EpisodeCreateDTO,
        EpisodeResponseDTO,
        EpisodeType,
        ErrorResponseDTO,
        # Generation schemas
        GenerationRequestDTO,
        GenerationResponseDTO,
        GenerationStatus,
        IDMixin,
        PaginatedResponse,
        PaginationSchema,
        # Project schemas
        ProjectCreateDTO,
        ProjectResponseDTO,
        # Common types
        ProjectStatus,
        ProjectUpdateDTO,
        RAGConfigDTO,
        SuccessResponseDTO,
        TimestampMixin,
    )

    IMPORT_SUCCESS = True
except ImportError as e:
    IMPORT_SUCCESS = False
    IMPORT_ERROR = str(e)


class TestSchemaImports:
    """스키마 임포트 테스트"""

    def test_import_success(self):
        """모든 스키마 임포트 성공 확인"""
        assert (
            IMPORT_SUCCESS
        ), f"Schema import failed: {IMPORT_ERROR if not IMPORT_SUCCESS else ''}"

    def test_base_schema_classes_exist(self):
        """기본 스키마 클래스 존재 확인"""
        assert hasattr(BaseSchema, "__name__")
        assert hasattr(IDMixin, "__name__")
        assert hasattr(TimestampMixin, "__name__")

    def test_enum_classes_exist(self):
        """Enum 클래스 존재 확인"""
        assert hasattr(ProjectStatus, "__members__")
        assert hasattr(GenerationStatus, "__members__")
        assert hasattr(EpisodeType, "__members__")


class TestBaseSchemas:
    """기본 스키마 테스트"""

    def test_base_schema_creation(self):
        """BaseSchema 인스턴스 생성 테스트"""

        class TestDTO(BaseSchema):
            name: str
            value: int

        dto = TestDTO(name="test", value=42)
        assert dto.name == "test"
        assert dto.value == 42

    def test_id_mixin(self):
        """IDMixin 기능 테스트"""

        class TestWithID(BaseSchema, IDMixin):
            name: str

        dto = TestWithID(id="test-id", name="test")
        assert dto.id == "test-id"
        assert dto.name == "test"

    def test_timestamp_mixin(self):
        """TimestampMixin 기능 테스트"""

        class TestWithTimestamp(BaseSchema, TimestampMixin):
            name: str

        now = datetime.now()
        dto = TestWithTimestamp(name="test", created_at=now, updated_at=now)
        assert dto.created_at == now
        assert dto.updated_at == now

    def test_pagination_schema(self):
        """PaginationSchema 테스트"""
        pagination = PaginationSchema(page=1, size=10, total=100)
        assert pagination.page == 1
        assert pagination.size == 10
        assert pagination.total == 100


class TestCommonSchemas:
    """공통 스키마 테스트"""

    def test_project_status_enum(self):
        """ProjectStatus enum 테스트"""
        assert ProjectStatus.ACTIVE in ProjectStatus.__members__.values()
        assert ProjectStatus.DRAFT in ProjectStatus.__members__.values()
        assert ProjectStatus.COMPLETED in ProjectStatus.__members__.values()

    def test_generation_status_enum(self):
        """GenerationStatus enum 테스트"""
        assert GenerationStatus.PENDING in GenerationStatus.__members__.values()
        assert GenerationStatus.PROCESSING in GenerationStatus.__members__.values()
        assert GenerationStatus.COMPLETED in GenerationStatus.__members__.values()
        assert GenerationStatus.FAILED in GenerationStatus.__members__.values()

    def test_error_response_dto(self):
        """ErrorResponseDTO 테스트"""
        error_dto = ErrorResponseDTO(
            error=True, message="Test error", error_code="TEST_ERROR"
        )
        assert error_dto.error is True
        assert error_dto.message == "Test error"
        assert error_dto.error_code == "TEST_ERROR"

    def test_success_response_dto(self):
        """SuccessResponseDTO 테스트"""
        success_dto = SuccessResponseDTO(success=True, message="Operation successful")
        assert success_dto.success is True
        assert success_dto.message == "Operation successful"


class TestProjectSchemas:
    """프로젝트 스키마 테스트"""

    def test_project_create_dto(self):
        """ProjectCreateDTO 생성 및 검증 테스트"""
        project_dto = ProjectCreateDTO(
            name="Test Project",
            description="Test Description",
            genre="drama",
            target_audience="adults",
        )

        assert project_dto.name == "Test Project"
        assert project_dto.description == "Test Description"
        assert project_dto.genre == "drama"
        assert project_dto.target_audience == "adults"

    def test_project_create_dto_validation(self):
        """ProjectCreateDTO 유효성 검증 테스트"""
        # 필수 필드 누락 테스트
        with pytest.raises(ValidationError):
            ProjectCreateDTO()

        # 이름 길이 제한 테스트 (너무 짧은 경우)
        with pytest.raises(ValidationError):
            ProjectCreateDTO(name="a")

    def test_project_response_dto(self):
        """ProjectResponseDTO 테스트"""
        now = datetime.now()
        project_dto = ProjectResponseDTO(
            id="proj_123",
            name="Test Project",
            description="Test Description",
            status=ProjectStatus.ACTIVE,
            genre="drama",
            target_audience="adults",
            created_at=now,
            updated_at=now,
        )

        assert project_dto.id == "proj_123"
        assert project_dto.name == "Test Project"
        assert project_dto.status == ProjectStatus.ACTIVE
        assert project_dto.created_at == now

    def test_episode_create_dto(self):
        """EpisodeCreateDTO 테스트"""
        episode_dto = EpisodeCreateDTO(
            title="Episode 1",
            description="First episode",
            episode_number=1,
            project_id="proj_123",
        )

        assert episode_dto.title == "Episode 1"
        assert episode_dto.episode_number == 1
        assert episode_dto.project_id == "proj_123"


class TestGenerationSchemas:
    """생성 스키마 테스트"""

    def test_ai_model_config_dto(self):
        """AIModelConfigDTO 테스트"""
        config_dto = AIModelConfigDTO(
            model_name="gpt-4", provider="openai", temperature=0.7, max_tokens=2000
        )

        assert config_dto.model_name == "gpt-4"
        assert config_dto.provider == "openai"
        assert config_dto.temperature == 0.7
        assert config_dto.max_tokens == 2000

    def test_ai_model_config_validation(self):
        """AIModelConfigDTO 유효성 검증 테스트"""
        # 잘못된 모델명 테스트
        with pytest.raises(ValidationError):
            AIModelConfigDTO(model_name="invalid-model", provider="openai")

        # 온도 범위 초과 테스트
        with pytest.raises(ValidationError):
            AIModelConfigDTO(
                model_name="gpt-4",
                provider="openai",
                temperature=3.0,  # 2.0을 초과
            )

    def test_rag_config_dto(self):
        """RAGConfigDTO 테스트"""
        rag_config = RAGConfigDTO(
            enabled=True,
            search_top_k=5,
            similarity_threshold=0.7,
            embedding_model="text-embedding-ada-002",
        )

        assert rag_config.enabled is True
        assert rag_config.search_top_k == 5
        assert rag_config.similarity_threshold == 0.7
        assert rag_config.embedding_model == "text-embedding-ada-002"

    def test_generation_request_dto(self):
        """GenerationRequestDTO 테스트"""
        ai_config = AIModelConfigDTO(model_name="gpt-4", provider="openai")

        generation_dto = GenerationRequestDTO(
            id="gen_123",
            project_id="proj_123",
            generation_type="script",
            purpose="Generate script for episode 1",
            prompt="Write a dramatic scene",
            ai_config=ai_config,
        )

        assert generation_dto.id == "gen_123"
        assert generation_dto.project_id == "proj_123"
        assert generation_dto.generation_type == "script"
        assert generation_dto.ai_config.model_name == "gpt-4"

    def test_generation_response_dto(self):
        """GenerationResponseDTO 테스트"""
        now = datetime.now()

        metadata = {
            "model_used": "gpt-4",
            "generation_time_ms": 1500,
            "token_usage": {
                "prompt_tokens": 100,
                "completion_tokens": 500,
                "total_tokens": 600,
            },
        }

        response_dto = GenerationResponseDTO(
            id="gen_123",
            request_id="req_456",
            project_id="proj_123",
            status=GenerationStatus.COMPLETED,
            content="Generated script content here...",
            metadata=metadata,
            created_at=now,
            updated_at=now,
        )

        assert response_dto.id == "gen_123"
        assert response_dto.status == GenerationStatus.COMPLETED
        assert response_dto.content == "Generated script content here..."
        assert response_dto.metadata["model_used"] == "gpt-4"


class TestSchemaValidation:
    """스키마 유효성 검증 테스트"""

    def test_pydantic_validation_works(self):
        """Pydantic 유효성 검증 동작 확인"""
        # 타입 불일치 테스트
        with pytest.raises(ValidationError):
            ProjectCreateDTO(
                name=123,  # 문자열이어야 함
                description="Test",
            )

    def test_optional_fields(self):
        """선택적 필드 테스트"""
        # 최소 필수 필드만으로 객체 생성
        project_dto = ProjectCreateDTO(name="Minimal Project")
        assert project_dto.name == "Minimal Project"
        assert project_dto.description is None

    def test_default_values(self):
        """기본값 테스트"""
        ai_config = AIModelConfigDTO(model_name="gpt-4", provider="openai")

        # 기본값 확인
        assert ai_config.temperature == 0.7
        assert ai_config.max_tokens == 2000
        assert ai_config.top_p == 1.0


class TestSchemaIntegration:
    """스키마 통합 테스트"""

    def test_nested_schema_validation(self):
        """중첩 스키마 유효성 검증"""
        ai_config = AIModelConfigDTO(model_name="gpt-4", provider="openai")

        rag_config = RAGConfigDTO(enabled=True, search_top_k=3)

        generation_request = GenerationRequestDTO(
            id="gen_123",
            project_id="proj_123",
            generation_type="script",
            purpose="Test generation",
            prompt="Test prompt",
            ai_config=ai_config,
            rag_config=rag_config,
        )

        assert generation_request.ai_config.model_name == "gpt-4"
        assert generation_request.rag_config.enabled is True

    def test_json_serialization(self):
        """JSON 직렬화 테스트"""
        project_dto = ProjectCreateDTO(
            name="Test Project", description="Test Description"
        )

        # JSON 직렬화
        json_data = project_dto.model_dump()
        assert isinstance(json_data, dict)
        assert json_data["name"] == "Test Project"

        # JSON에서 복원
        restored_dto = ProjectCreateDTO.model_validate(json_data)
        assert restored_dto.name == "Test Project"
        assert restored_dto.description == "Test Description"

    def test_schema_inheritance(self):
        """스키마 상속 테스트"""

        # IDMixin과 TimestampMixin을 함께 사용
        class CompleteDTO(BaseSchema, IDMixin, TimestampMixin):
            name: str

        now = datetime.now()
        dto = CompleteDTO(id="test_id", name="test", created_at=now, updated_at=now)

        assert dto.id == "test_id"
        assert dto.name == "test"
        assert dto.created_at == now
        assert dto.updated_at == now


if __name__ == "__main__":
    pytest.main([__file__])
