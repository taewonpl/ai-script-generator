"""
API Surface Tests - Verify public API integrity and stability
"""

import inspect

import ai_script_core


class TestPublicAPI:
    """Test public API surface"""

    def test_package_exports_only_intended_symbols(self):
        """Verify that only intended symbols are exported from main package"""
        # Get all symbols exported by the package
        exported_symbols = set(ai_script_core.__all__)

        # Define expected core symbols (essential for users)
        expected_core_symbols = {
            # Package metadata
            "__version__",
            "__author__",
            "__description__",
            "get_version",
            "get_package_info",
            "check_python_version",
            # Core modules
            "schemas",
            "exceptions",
            "utils",
            # Essential schemas
            "BaseSchema",
            "ProjectDTO",
            "ProjectCreateDTO",
            "ProjectUpdateDTO",
            "EpisodeDTO",
            "EpisodeCreateDTO",
            "EpisodeUpdateDTO",
            "GenerationRequestDTO",
            "GenerationResponseDTO",
            "AIModelConfigDTO",
            "RAGConfigDTO",
            # Common types
            "ProjectStatus",
            "ProjectType",
            "EpisodeType",
            "GenerationStatus",
            # Response types
            "CommonResponseDTO",
            "SuccessResponseDTO",
            "ErrorResponseDTO",
            # Essential exceptions
            "BaseServiceException",
            "ValidationException",
            "NotFoundError",
            "ProjectNotFoundError",
            "GenerationServiceError",
            # Essential utilities
            "get_settings",
            "get_service_logger",
            "generate_uuid",
            "format_datetime",
            "sanitize_text",
            "safe_json_loads",
            "safe_json_dumps",
        }

        # Verify no unexpected symbols are exported
        unexpected_symbols = exported_symbols - expected_core_symbols
        assert (
            not unexpected_symbols
        ), f"Unexpected symbols in __all__: {unexpected_symbols}"

        # Verify all expected symbols are exported
        missing_symbols = expected_core_symbols - exported_symbols
        assert (
            not missing_symbols
        ), f"Missing expected symbols from __all__: {missing_symbols}"

    def test_no_private_symbols_exported(self):
        """Verify no private symbols (starting with _) are exported"""
        exported_symbols = ai_script_core.__all__

        private_symbols = [
            symbol for symbol in exported_symbols if symbol.startswith("_")
        ]
        assert (
            not private_symbols
        ), f"Private symbols found in __all__: {private_symbols}"

    def test_all_exported_symbols_importable(self):
        """Verify all symbols in __all__ can actually be imported"""
        for symbol in ai_script_core.__all__:
            try:
                getattr(ai_script_core, symbol)
            except AttributeError:
                pytest.fail(f"Symbol '{symbol}' in __all__ but not available in module")

    def test_essential_classes_have_stable_interfaces(self):
        """Test that essential classes have expected methods and attributes"""
        # Test ProjectCreateDTO
        from ai_script_core import ProjectCreateDTO, ProjectType

        project = ProjectCreateDTO(name="Test", type=ProjectType.DRAMA)

        # Should have Pydantic methods
        assert hasattr(project, "model_dump")
        assert hasattr(project, "model_dump_json")
        assert hasattr(project, "model_validate")
        assert hasattr(project, "model_validate_json")

        # Should have expected fields
        assert hasattr(project, "name")
        assert hasattr(project, "type")
        assert hasattr(project, "description")

    def test_module_structure_stability(self):
        """Test that core module structure is stable"""
        # Core modules should be available
        assert hasattr(ai_script_core, "schemas")
        assert hasattr(ai_script_core, "exceptions")
        assert hasattr(ai_script_core, "utils")

        # Submodules should be importable

    def test_backward_compatibility_aliases(self):
        """Test that backward compatibility aliases are available"""
        from ai_script_core import (
            EpisodeResponseDTO,  # Alias for EpisodeDTO
            ProjectResponseDTO,  # Alias for ProjectDTO
        )

        # These should be available for backward compatibility
        assert ProjectResponseDTO is not None
        assert EpisodeResponseDTO is not None


class TestAPIStability:
    """Test API stability and breaking change detection"""

    def test_dto_fields_stability(self):
        """Test that DTO fields haven't changed unexpectedly"""
        from ai_script_core import ProjectCreateDTO

        # Get model fields
        fields = ProjectCreateDTO.model_fields

        # Core fields that should always be present
        required_fields = {"name", "type"}
        assert all(field in fields for field in required_fields)

        # Optional fields that should be present
        optional_fields = {"description", "logline", "deadline", "settings"}
        assert all(field in fields for field in optional_fields)

    def test_enum_values_stability(self):
        """Test that enum values are stable"""
        from ai_script_core import GenerationStatus, ProjectStatus, ProjectType

        # ProjectType values should be stable
        expected_project_types = {
            "drama",
            "comedy",
            "romance",
            "thriller",
            "documentary",
            "web_series",
            "short_film",
            "advertisement",
            "education",
        }
        actual_project_types = {pt.value for pt in ProjectType}
        assert expected_project_types.issubset(actual_project_types)

        # ProjectStatus values should be stable
        expected_project_statuses = {
            "planning",
            "in_progress",
            "completed",
            "on_hold",
            "cancelled",
        }
        actual_project_statuses = {ps.value for ps in ProjectStatus}
        assert expected_project_statuses.issubset(actual_project_statuses)

        # GenerationStatus values should be stable
        expected_generation_statuses = {
            "pending",
            "processing",
            "completed",
            "failed",
            "cancelled",
        }
        actual_generation_statuses = {gs.value for gs in GenerationStatus}
        assert expected_generation_statuses.issubset(actual_generation_statuses)

    def test_exception_hierarchy_stability(self):
        """Test exception hierarchy is stable"""
        from ai_script_core import (
            BaseServiceException,
            GenerationServiceError,
            ProjectNotFoundError,
            ValidationException,
        )

        # Check inheritance relationships
        assert issubclass(ValidationException, BaseServiceException)
        assert issubclass(ProjectNotFoundError, BaseServiceException)
        assert issubclass(GenerationServiceError, BaseServiceException)

    def test_utility_function_signatures(self):
        """Test that utility function signatures are stable"""
        from ai_script_core import format_datetime, generate_uuid, sanitize_text

        # Check function signatures haven't changed
        uuid_sig = inspect.signature(generate_uuid)
        assert len(uuid_sig.parameters) == 0  # No parameters

        sanitize_sig = inspect.signature(sanitize_text)
        assert "text" in sanitize_sig.parameters  # Should have text parameter

        format_dt_sig = inspect.signature(format_datetime)
        assert "dt" in format_dt_sig.parameters  # Should have dt parameter
