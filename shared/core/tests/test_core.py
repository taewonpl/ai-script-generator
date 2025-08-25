"""
Core Test Suite for AI Script Core

Comprehensive tests covering all major DTOs, validation, and functionality.
"""

from datetime import datetime

import pytest

from ai_script_core import (
    AIModelConfigDTO,
    # Schemas
    BaseSchema,
    # Exceptions
    BaseServiceException,
    EpisodeCreateDTO,
    GenerationRequestDTO,
    GenerationStatus,
    ProjectCreateDTO,
    ProjectNotFoundError,
    ProjectStatus,
    # Enums
    ProjectType,
    RAGConfigDTO,
    ValidationException,
    format_datetime,
    # Utilities
    generate_uuid,
    safe_json_dumps,
    safe_json_loads,
    sanitize_text,
)


class TestSchemas:
    """Test schema functionality"""

    def test_base_schema_creation(self):
        """Test BaseSchema instantiation"""
        schema = BaseSchema()
        assert schema is not None

    def test_project_create_dto_valid(self):
        """Test valid ProjectCreateDTO creation"""
        project = ProjectCreateDTO(
            name="Test Project",
            type=ProjectType.DRAMA,
            description="A test project for validation",
        )

        assert project.name == "Test Project"
        assert project.type == ProjectType.DRAMA
        assert project.description == "A test project for validation"

    def test_project_create_dto_invalid_name(self):
        """Test ProjectCreateDTO with invalid name"""
        with pytest.raises(ValueError):
            ProjectCreateDTO(
                name="",  # Empty name should fail
                type=ProjectType.DRAMA,
            )

    def test_project_create_dto_invalid_type(self):
        """Test ProjectCreateDTO with invalid type"""
        with pytest.raises(ValueError):
            ProjectCreateDTO(
                name="Test Project",
                type="invalid_type",  # Invalid enum value
            )

    def test_episode_create_dto_valid(self):
        """Test valid EpisodeCreateDTO creation"""
        episode = EpisodeCreateDTO(
            project_id="test-project-123",
            episode_number=1,
            title="Episode 1: Beginning",
        )

        assert episode.project_id == "test-project-123"
        assert episode.episode_number == 1
        assert episode.title == "Episode 1: Beginning"

    def test_episode_create_dto_invalid_number(self):
        """Test EpisodeCreateDTO with invalid episode number"""
        with pytest.raises(ValueError):
            EpisodeCreateDTO(
                project_id="test-project-123",
                episode_number=0,  # Should be >= 1
                title="Invalid Episode",
            )

    def test_ai_model_config_dto_valid(self):
        """Test valid AIModelConfigDTO creation"""
        config = AIModelConfigDTO(
            model_name="gpt-4", provider="openai", temperature=0.7, max_tokens=2000
        )

        assert config.model_name == "gpt-4"
        assert config.provider == "openai"
        assert config.temperature == 0.7
        assert config.max_tokens == 2000

    def test_ai_model_config_dto_invalid_model(self):
        """Test AIModelConfigDTO with invalid model name"""
        with pytest.raises(ValueError, match="Model must be one of"):
            AIModelConfigDTO(model_name="invalid-model", provider="openai")

    def test_ai_model_config_dto_temperature_bounds(self):
        """Test AIModelConfigDTO temperature validation"""
        # Valid temperature
        config = AIModelConfigDTO(
            model_name="gpt-4", provider="openai", temperature=0.5
        )
        assert config.temperature == 0.5

        # Invalid temperature (too high)
        with pytest.raises(ValueError):
            AIModelConfigDTO(
                model_name="gpt-4",
                provider="openai",
                temperature=3.0,  # Should be <= 2.0
            )

    def test_rag_config_dto_valid(self):
        """Test valid RAGConfigDTO creation"""
        config = RAGConfigDTO(
            enabled=True,
            search_top_k=10,
            similarity_threshold=0.8,
            embedding_model="text-embedding-ada-002",
        )

        assert config.enabled is True
        assert config.search_top_k == 10
        assert config.similarity_threshold == 0.8
        assert config.embedding_model == "text-embedding-ada-002"

    def test_rag_config_dto_bounds(self):
        """Test RAGConfigDTO validation bounds"""
        # Valid configuration
        config = RAGConfigDTO(search_top_k=5, similarity_threshold=0.7)
        assert config.search_top_k == 5

        # Invalid search_top_k (too high)
        with pytest.raises(ValueError):
            RAGConfigDTO(search_top_k=25)  # Should be <= 20

        # Invalid similarity_threshold (too high)
        with pytest.raises(ValueError):
            RAGConfigDTO(similarity_threshold=1.5)  # Should be <= 1.0

    def test_generation_request_dto_valid(self):
        """Test valid GenerationRequestDTO creation"""
        ai_config = AIModelConfigDTO(model_name="gpt-4", provider="openai")

        request = GenerationRequestDTO(
            id=generate_uuid(),
            project_id="test-project",
            generation_type="script",
            purpose="Generate test script",
            prompt="Create a dialogue between two characters",
            ai_config=ai_config,
        )

        assert request.generation_type == "script"
        assert request.purpose == "Generate test script"
        assert len(request.prompt) >= 10
        assert request.ai_config.model_name == "gpt-4"

    def test_generation_request_dto_invalid_type(self):
        """Test GenerationRequestDTO with invalid generation type"""
        ai_config = AIModelConfigDTO(model_name="gpt-4", provider="openai")

        with pytest.raises(ValueError, match="Generation type must be one of"):
            GenerationRequestDTO(
                id=generate_uuid(),
                project_id="test-project",
                generation_type="invalid_type",
                purpose="Test purpose",
                prompt="Test prompt that is long enough",
                ai_config=ai_config,
            )

    def test_generation_request_dto_short_prompt(self):
        """Test GenerationRequestDTO with too short prompt"""
        ai_config = AIModelConfigDTO(model_name="gpt-4", provider="openai")

        with pytest.raises(ValueError):
            GenerationRequestDTO(
                id=generate_uuid(),
                project_id="test-project",
                generation_type="script",
                purpose="Test purpose",
                prompt="short",  # Should be >= 10 characters
                ai_config=ai_config,
            )


class TestSerialization:
    """Test JSON serialization and deserialization"""

    def test_project_dto_json_roundtrip(self):
        """Test ProjectCreateDTO JSON round-trip"""
        original = ProjectCreateDTO(
            name="JSON Test Project",
            type=ProjectType.COMEDY,
            description="Testing JSON serialization",
            deadline=datetime(2024, 12, 31, 23, 59, 59),
        )

        # Serialize to JSON
        json_str = original.model_dump_json()
        assert isinstance(json_str, str)

        # Deserialize from JSON
        restored = ProjectCreateDTO.model_validate_json(json_str)

        # Verify data integrity
        assert restored.name == original.name
        assert restored.type == original.type
        assert restored.description == original.description
        assert restored.deadline == original.deadline

    def test_ai_config_dict_conversion(self):
        """Test AIModelConfigDTO dict conversion"""
        config = AIModelConfigDTO(
            model_name="claude-3-sonnet",
            provider="anthropic",
            temperature=0.8,
            extra_params={"custom_setting": "test_value"},
        )

        # Convert to dict
        config_dict = config.model_dump()

        assert isinstance(config_dict, dict)
        assert config_dict["model_name"] == "claude-3-sonnet"
        assert config_dict["provider"] == "anthropic"
        assert config_dict["temperature"] == 0.8
        assert config_dict["extra_params"]["custom_setting"] == "test_value"

    def test_complex_object_serialization(self):
        """Test serialization of complex nested objects"""
        ai_config = AIModelConfigDTO(
            model_name="gpt-4", provider="openai", temperature=0.7
        )

        rag_config = RAGConfigDTO(
            enabled=True, search_top_k=5, knowledge_base_ids=["kb1", "kb2"]
        )

        request = GenerationRequestDTO(
            id=generate_uuid(),
            project_id="complex-test",
            generation_type="script",
            purpose="Complex serialization test",
            prompt="Generate a complex script with multiple characters",
            ai_config=ai_config,
            rag_config=rag_config,
            genre_hints=["drama", "romance"],
        )

        # Serialize
        json_str = request.model_dump_json()

        # Deserialize
        restored = GenerationRequestDTO.model_validate_json(json_str)

        # Verify nested objects
        assert restored.ai_config.model_name == ai_config.model_name
        assert restored.rag_config.enabled == rag_config.enabled
        assert restored.rag_config.knowledge_base_ids == rag_config.knowledge_base_ids
        assert restored.genre_hints == ["drama", "romance"]


class TestExceptions:
    """Test exception handling"""

    def test_base_service_exception(self):
        """Test BaseServiceException creation"""
        exc = BaseServiceException("Test error message")
        assert str(exc) == "Test error message"
        assert exc.message == "Test error message"

    def test_project_not_found_error(self):
        """Test ProjectNotFoundError"""
        exc = ProjectNotFoundError("Project with ID 'test-123' not found")
        assert "test-123" in str(exc)
        assert isinstance(exc, BaseServiceException)

    def test_validation_exception(self):
        """Test ValidationException"""
        exc = ValidationException("Validation failed for field 'name'")
        assert "Validation failed" in str(exc)
        assert isinstance(exc, BaseServiceException)


class TestUtilities:
    """Test utility functions"""

    def test_generate_uuid(self):
        """Test UUID generation"""
        uuid1 = generate_uuid()
        uuid2 = generate_uuid()

        assert isinstance(uuid1, str)
        assert isinstance(uuid2, str)
        assert uuid1 != uuid2
        assert len(uuid1) > 0
        assert len(uuid2) > 0

    def test_sanitize_text(self):
        """Test text sanitization"""
        dirty_text = "Test <script>alert('xss')</script> & cleaning"
        clean_text = sanitize_text(dirty_text)

        assert isinstance(clean_text, str)
        assert "<script>" not in clean_text
        assert "alert" not in clean_text
        assert "Test" in clean_text
        assert "cleaning" in clean_text

    def test_safe_json_operations(self):
        """Test safe JSON operations"""
        test_data = {
            "string": "test value",
            "number": 42,
            "boolean": True,
            "list": [1, 2, 3],
            "nested": {"key": "value"},
        }

        # Test safe dumps
        json_str = safe_json_dumps(test_data)
        assert isinstance(json_str, str)

        # Test safe loads
        restored_data = safe_json_loads(json_str)
        assert restored_data == test_data

    def test_safe_json_loads_invalid(self):
        """Test safe_json_loads with invalid JSON"""
        invalid_json = "{'invalid': json}"
        result = safe_json_loads(invalid_json)
        assert result is None

    def test_format_datetime(self):
        """Test datetime formatting"""
        test_datetime = datetime(2024, 1, 15, 10, 30, 45)
        formatted = format_datetime(test_datetime)

        assert isinstance(formatted, str)
        assert "2024" in formatted
        assert "01" in formatted or "1" in formatted
        assert "15" in formatted

    def test_format_datetime_none(self):
        """Test datetime formatting with None"""
        formatted = format_datetime(None)
        assert formatted is None


class TestValidationEdgeCases:
    """Test edge cases in validation"""

    def test_project_name_length_limits(self):
        """Test project name length validation"""
        # Minimum length (1 character)
        project = ProjectCreateDTO(name="A", type=ProjectType.DRAMA)
        assert project.name == "A"

        # Maximum length (200 characters)
        long_name = "A" * 200
        project = ProjectCreateDTO(name=long_name, type=ProjectType.DRAMA)
        assert len(project.name) == 200

        # Too long (201 characters)
        with pytest.raises(ValueError):
            ProjectCreateDTO(name="A" * 201, type=ProjectType.DRAMA)

    def test_episode_duration_validation(self):
        """Test episode duration validation"""
        # Valid duration
        episode = EpisodeCreateDTO(
            project_id="test",
            episode_number=1,
            title="Test Episode",
            duration_minutes=60,
        )
        assert episode.duration_minutes == 60

        # Maximum duration (1440 minutes = 24 hours)
        episode = EpisodeCreateDTO(
            project_id="test",
            episode_number=1,
            title="Test Episode",
            duration_minutes=1440,
        )
        assert episode.duration_minutes == 1440

        # Too long duration
        with pytest.raises(ValueError):
            EpisodeCreateDTO(
                project_id="test",
                episode_number=1,
                title="Test Episode",
                duration_minutes=1441,
            )

    def test_ai_config_parameter_bounds(self):
        """Test AI configuration parameter bounds"""
        # Test all valid bounds
        config = AIModelConfigDTO(
            model_name="gpt-4",
            provider="openai",
            temperature=2.0,  # Maximum
            max_tokens=8000,  # Maximum
            top_p=1.0,  # Maximum
            frequency_penalty=2.0,  # Maximum
            presence_penalty=-2.0,  # Minimum
        )

        assert config.temperature == 2.0
        assert config.max_tokens == 8000
        assert config.top_p == 1.0
        assert config.frequency_penalty == 2.0
        assert config.presence_penalty == -2.0

    def test_generation_prompt_length(self):
        """Test generation prompt length validation"""
        ai_config = AIModelConfigDTO(model_name="gpt-4", provider="openai")

        # Minimum length (10 characters)
        request = GenerationRequestDTO(
            id=generate_uuid(),
            project_id="test",
            generation_type="script",
            purpose="Test",
            prompt="1234567890",  # Exactly 10 characters
            ai_config=ai_config,
        )
        assert len(request.prompt) == 10

        # Maximum length (10000 characters)
        long_prompt = "A" * 10000
        request = GenerationRequestDTO(
            id=generate_uuid(),
            project_id="test",
            generation_type="script",
            purpose="Test",
            prompt=long_prompt,
            ai_config=ai_config,
        )
        assert len(request.prompt) == 10000

        # Too long prompt
        with pytest.raises(ValueError):
            GenerationRequestDTO(
                id=generate_uuid(),
                project_id="test",
                generation_type="script",
                purpose="Test",
                prompt="A" * 10001,
                ai_config=ai_config,
            )


class TestEnumValues:
    """Test enum value handling"""

    def test_project_type_values(self):
        """Test ProjectType enum values"""
        assert ProjectType.DRAMA == "drama"
        assert ProjectType.COMEDY == "comedy"
        assert ProjectType.ROMANCE == "romance"
        assert ProjectType.THRILLER == "thriller"
        assert ProjectType.DOCUMENTARY == "documentary"

    def test_project_status_values(self):
        """Test ProjectStatus enum values"""
        assert ProjectStatus.PLANNING == "planning"
        assert ProjectStatus.IN_PROGRESS == "in_progress"
        assert ProjectStatus.COMPLETED == "completed"
        assert ProjectStatus.ON_HOLD == "on_hold"
        assert ProjectStatus.CANCELLED == "cancelled"

    def test_generation_status_values(self):
        """Test GenerationStatus enum values"""
        assert GenerationStatus.PENDING == "pending"
        assert GenerationStatus.PROCESSING == "processing"
        assert GenerationStatus.COMPLETED == "completed"
        assert GenerationStatus.FAILED == "failed"
        assert GenerationStatus.CANCELLED == "cancelled"
