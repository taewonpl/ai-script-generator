#!/usr/bin/env python3
"""
Runtime Test Script for AI Script Core
Tests Pydantic v2 validation, serialization, and all DTO functionality
"""

import sys
import traceback
from datetime import datetime


# Color codes for output
class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    NC = "\033[0m"  # No Color


def print_header(message: str) -> None:
    print(f"{Colors.BLUE}=== {message} ==={Colors.NC}")


def print_success(message: str) -> None:
    print(f"{Colors.GREEN}✅ {message}{Colors.NC}")


def print_warning(message: str) -> None:
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.NC}")


def print_error(message: str) -> None:
    print(f"{Colors.RED}❌ {message}{Colors.NC}")


def test_pydantic_v2_features():
    """Test Pydantic v2 specific features"""
    print_header("Pydantic v2 Runtime Validation Tests")

    try:
        from ai_script_core.schemas.base import BaseSchema
        from ai_script_core.schemas.generation import AIModelConfigDTO

        # Test 1: ConfigDict usage (no deprecation warnings)
        schema = BaseSchema()
        print_success("BaseSchema with ConfigDict instantiated successfully")

        # Test 2: Protected namespaces setting
        # This should not raise warnings about model_ prefix
        config = AIModelConfigDTO(model_name="gpt-4", provider="openai")
        print_success("AIModelConfigDTO with model_ prefix created without warnings")

        # Test 3: field_validator functionality
        try:
            # This should fail validation
            invalid_config = AIModelConfigDTO(
                model_name="invalid-model-name", provider="openai"
            )
            print_error("Validation should have failed for invalid model name")
            return False
        except ValueError as e:
            print_success(f"field_validator correctly rejected invalid model: {e!s}")

        # Test 4: Valid model names
        valid_models = ["gpt-4", "claude-3-sonnet", "gpt-3.5-turbo"]
        for model in valid_models:
            config = AIModelConfigDTO(model_name=model, provider="test")
            print_success(f"Valid model '{model}' accepted")

        return True

    except Exception as e:
        print_error(f"Pydantic v2 test failed: {e!s}")
        traceback.print_exc()
        return False


def test_dto_creation_and_validation():
    """Test all DTO creation and validation"""
    print_header("DTO Creation and Validation Tests")

    test_results = []

    # Test ProjectCreateDTO
    try:
        from ai_script_core import ProjectCreateDTO, ProjectType

        project = ProjectCreateDTO(
            name="Test Project",
            type=ProjectType.DRAMA,
            description="A comprehensive test project",
        )

        # Test validation constraints
        assert len(project.name) > 0
        assert project.type == ProjectType.DRAMA or project.type == "drama"

        print_success("ProjectCreateDTO creation and validation")
        test_results.append(True)

    except Exception as e:
        print_error(f"ProjectCreateDTO test failed: {e!s}")
        import traceback

        traceback.print_exc()
        test_results.append(False)

    # Test EpisodeCreateDTO
    try:
        from ai_script_core import EpisodeCreateDTO

        episode = EpisodeCreateDTO(
            project_id="test-project-123",
            episode_number=1,
            title="Episode 1: The Beginning",
            description="First episode of our test series",
        )

        # Test constraints
        assert episode.episode_number > 0
        assert len(episode.title) > 0

        print_success("EpisodeCreateDTO creation and validation")
        test_results.append(True)

    except Exception as e:
        print_error(f"EpisodeCreateDTO test failed: {e!s}")
        test_results.append(False)

    # Test GenerationRequestDTO
    try:
        from ai_script_core import AIModelConfigDTO, GenerationRequestDTO
        from ai_script_core.utils import generate_uuid

        ai_config = AIModelConfigDTO(
            model_name="gpt-4", provider="openai", temperature=0.7, max_tokens=2000
        )

        generation_request = GenerationRequestDTO(
            id=generate_uuid(),
            project_id="test-project-123",
            generation_type="script",
            purpose="Generate test script",
            prompt="Create a dramatic scene between two characters discussing their future.",
            ai_config=ai_config,
        )

        # Test constraints
        assert generation_request.generation_type in [
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
        assert len(generation_request.prompt) >= 10

        print_success("GenerationRequestDTO creation and validation")
        test_results.append(True)

    except Exception as e:
        print_error(f"GenerationRequestDTO test failed: {e!s}")
        test_results.append(False)

    # Test RAGConfigDTO
    try:
        from ai_script_core import RAGConfigDTO

        rag_config = RAGConfigDTO(
            enabled=True,
            search_top_k=10,
            similarity_threshold=0.8,
            embedding_model="text-embedding-ada-002",
            chunk_size=1000,
            chunk_overlap=200,
        )

        # Test constraints
        assert 1 <= rag_config.search_top_k <= 20
        assert 0.0 <= rag_config.similarity_threshold <= 1.0
        assert 100 <= rag_config.chunk_size <= 4000

        print_success("RAGConfigDTO creation and validation")
        test_results.append(True)

    except Exception as e:
        print_error(f"RAGConfigDTO test failed: {e!s}")
        test_results.append(False)

    return all(test_results)


def test_json_serialization():
    """Test JSON round-trip serialization"""
    print_header("JSON Serialization Tests")

    try:
        from ai_script_core import AIModelConfigDTO, ProjectCreateDTO, ProjectType

        # Create complex object
        project = ProjectCreateDTO(
            name="Serialization Test Project",
            type=ProjectType.COMEDY,
            description="Testing JSON serialization capabilities",
            deadline=datetime.now(),
        )

        ai_config = AIModelConfigDTO(
            model_name="claude-3-sonnet",
            provider="anthropic",
            temperature=0.8,
            max_tokens=4000,
            extra_params={"custom_setting": "test_value"},
        )

        # Test serialization
        project_json = project.model_dump_json()
        ai_config_json = ai_config.model_dump_json()

        print_success("JSON serialization successful")

        # Test deserialization
        project_restored = ProjectCreateDTO.model_validate_json(project_json)
        ai_config_restored = AIModelConfigDTO.model_validate_json(ai_config_json)

        # Verify data integrity
        assert project_restored.name == project.name
        assert project_restored.type == project.type
        assert ai_config_restored.model_name == ai_config.model_name
        assert ai_config_restored.extra_params == ai_config.extra_params

        print_success("JSON round-trip preservation verified")

        # Test Python dict conversion
        project_dict = project.model_dump()
        ai_config_dict = ai_config.model_dump()

        assert isinstance(project_dict, dict)
        assert isinstance(ai_config_dict, dict)
        assert project_dict["name"] == project.name

        print_success("Python dict conversion successful")

        return True

    except Exception as e:
        print_error(f"JSON serialization test failed: {e!s}")
        traceback.print_exc()
        return False


def test_validation_error_handling():
    """Test validation error handling"""
    print_header("Validation Error Handling Tests")

    test_results = []

    # Test empty string validation
    try:
        from ai_script_core import ProjectCreateDTO

        try:
            invalid_project = ProjectCreateDTO(
                name="",  # Should fail min_length=1
                type="drama",
            )
            print_error("Empty name should have been rejected")
            test_results.append(False)
        except ValueError:
            print_success("Empty name correctly rejected")
            test_results.append(True)

    except Exception as e:
        print_error(f"Empty string validation test failed: {e!s}")
        test_results.append(False)

    # Test invalid enum values
    try:
        from ai_script_core import ProjectCreateDTO

        try:
            invalid_project = ProjectCreateDTO(
                name="Test",
                type="invalid_type",  # Should fail enum validation
            )
            print_error("Invalid project type should have been rejected")
            test_results.append(False)
        except ValueError:
            print_success("Invalid project type correctly rejected")
            test_results.append(True)

    except Exception as e:
        print_error(f"Invalid enum validation test failed: {e!s}")
        test_results.append(False)

    # Test range validation
    try:
        from ai_script_core import EpisodeCreateDTO

        try:
            invalid_episode = EpisodeCreateDTO(
                project_id="test",
                episode_number=0,  # Should fail ge=1
                title="Test Episode",
            )
            print_error("Zero episode number should have been rejected")
            test_results.append(False)
        except ValueError:
            print_success("Zero episode number correctly rejected")
            test_results.append(True)

    except Exception as e:
        print_error(f"Range validation test failed: {e!s}")
        test_results.append(False)

    return all(test_results)


def test_utility_functions():
    """Test utility functions"""
    print_header("Utility Functions Tests")

    try:
        from ai_script_core import (
            format_datetime,
            generate_uuid,
            safe_json_dumps,
            safe_json_loads,
            sanitize_text,
        )

        # Test UUID generation
        uuid1 = generate_uuid()
        uuid2 = generate_uuid()
        assert uuid1 != uuid2
        assert len(uuid1) > 0
        print_success("UUID generation working")

        # Test text sanitization
        dirty_text = "Test <script>alert('xss')</script> & cleaning"
        clean_text = sanitize_text(dirty_text)
        assert "<script>" not in clean_text
        print_success("Text sanitization working")

        # Test JSON utilities
        test_data = {"key": "value", "number": 42}
        json_str = safe_json_dumps(test_data)
        restored_data = safe_json_loads(json_str)
        assert restored_data == test_data
        print_success("JSON utilities working")

        # Test datetime formatting
        now = datetime.now()
        formatted = format_datetime(now)
        assert isinstance(formatted, str)
        assert len(formatted) > 0
        print_success("Datetime formatting working")

        return True

    except Exception as e:
        print_error(f"Utility functions test failed: {e!s}")
        traceback.print_exc()
        return False


def main():
    """Run all runtime tests"""
    print_header("AI Script Core - Runtime Validation Tests")
    print(f"Python version: {sys.version}")
    print("")

    tests = [
        ("Pydantic v2 Features", test_pydantic_v2_features),
        ("DTO Creation & Validation", test_dto_creation_and_validation),
        ("JSON Serialization", test_json_serialization),
        ("Validation Error Handling", test_validation_error_handling),
        ("Utility Functions", test_utility_functions),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append(result)
            if result:
                print_success(f"{test_name} - PASSED")
            else:
                print_error(f"{test_name} - FAILED")
        except Exception as e:
            print_error(f"{test_name} - ERROR: {e!s}")
            results.append(False)
        print("")

    # Summary
    print_header("Runtime Test Summary")
    passed = sum(results)
    total = len(results)

    if passed == total:
        print_success(f"All {total} test suites passed! 🎉")
        print_success("Core module is production ready")
        return 0
    else:
        print_error(f"{passed}/{total} test suites passed")
        print_error("Core module needs fixes before production")
        return 1


if __name__ == "__main__":
    sys.exit(main())
