#!/usr/bin/env python3
"""
Pydantic v2 compatibility test script
"""

import logging
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("pydantic-v2-test")


class PydanticV2Tester:
    """Test Pydantic v2 compatibility across the Generation Service"""

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.validated_items = []

    def test_all(self):
        """Run all Pydantic v2 compatibility tests"""
        logger.info("Starting Pydantic v2 compatibility testing...")

        try:
            # Test pydantic version
            self.test_pydantic_version()

            # Test settings import and creation
            self.test_settings_import()

            # Test model imports
            self.test_model_imports()

            # Test model validation
            self.test_model_validation()

            # Test field validators
            self.test_field_validators()

            # Test model serialization
            self.test_model_serialization()

            return len(self.errors) == 0, self.errors, self.warnings

        except Exception as e:
            import traceback

            error_details = traceback.format_exc()
            self.errors.append(f"Testing failed with unexpected error: {e}")
            logger.error(f"Testing error details:\n{error_details}")
            return False, self.errors, self.warnings

    def test_pydantic_version(self):
        """Test Pydantic version"""
        logger.info("Testing Pydantic version...")

        try:
            import pydantic

            version = pydantic.VERSION

            if version.startswith("2."):
                self.validated_items.append("pydantic_v2_version")
                logger.info(f"✓ Pydantic v2 detected: {version}")
            else:
                self.errors.append(f"Pydantic v1 detected: {version}, expected v2")

            # Test pydantic-settings import
            from pydantic_settings import BaseSettings

            self.validated_items.append("pydantic_settings_import")
            logger.info("✓ pydantic-settings import successful")

        except ImportError as e:
            self.errors.append(f"Failed to import Pydantic components: {e}")

    def test_settings_import(self):
        """Test settings import and instantiation"""
        logger.info("Testing settings import...")

        try:
            from generation_service.config.settings import Settings, get_settings

            # Test basic instantiation
            settings = Settings()
            self.validated_items.append("settings_instantiation")
            logger.info("✓ Settings class instantiation successful")

            # Test get_settings function
            global_settings = get_settings()
            self.validated_items.append("settings_global_function")
            logger.info("✓ get_settings() function working")

            # Test field access
            test_fields = ["app_name", "version", "environment", "host", "port"]
            for field in test_fields:
                if hasattr(settings, field):
                    value = getattr(settings, field)
                    logger.debug(f"  {field}: {value}")
                else:
                    self.errors.append(f"Settings missing field: {field}")

            if all(hasattr(settings, field) for field in test_fields):
                self.validated_items.append("settings_field_access")
                logger.info("✓ Settings field access working")

        except Exception as e:
            self.errors.append(f"Settings import/instantiation failed: {e}")

    def test_model_imports(self):
        """Test model imports"""
        logger.info("Testing model imports...")

        try:
            # Test generation models
            from generation_service.models.generation import (
                GenerationMetadata,
                GenerationRequest,
                GenerationResponse,
                ScriptType,
            )

            self.validated_items.append("generation_models_import")
            logger.info("✓ Generation models import successful")

            # Test RAG models
            from generation_service.models.rag_models import (
                RAGSearchRequestDTO,
                RAGSearchResultDTO,
                SearchStrategy,
            )

            self.validated_items.append("rag_models_import")
            logger.info("✓ RAG models import successful")

            # Test vector document models
            from generation_service.models.vector_document import (
                DocumentSearchFilter,
                DocumentType,
                VectorDocumentDTO,
            )

            self.validated_items.append("vector_models_import")
            logger.info("✓ Vector document models import successful")

        except ImportError as e:
            self.errors.append(f"Model import failed: {e}")

    def test_model_validation(self):
        """Test model validation with Pydantic v2"""
        logger.info("Testing model validation...")

        try:
            from generation_service.models.generation import (
                GenerationRequest,
                ScriptType,
            )

            # Test valid request creation
            valid_request = GenerationRequest(
                title="Test Script",
                description="A test script for Pydantic v2 validation",
                script_type=ScriptType.DRAMA,
                project_id="test_project_v2",
            )

            self.validated_items.append("generation_request_validation")
            logger.info("✓ GenerationRequest validation successful")

            # Test invalid request (should raise validation error)
            try:
                invalid_request = GenerationRequest(
                    title="",  # Invalid: too short
                    description="Short",  # Invalid: too short
                    script_type="invalid_type",  # Invalid enum
                    project_id="",  # Invalid: empty
                )
                self.warnings.append(
                    "Expected validation error for invalid GenerationRequest was not raised"
                )
            except Exception:
                # This is expected - validation should fail
                self.validated_items.append("generation_request_validation_errors")
                logger.info("✓ GenerationRequest validation errors work correctly")

        except Exception as e:
            self.errors.append(f"Model validation testing failed: {e}")

    def test_field_validators(self):
        """Test field validators work with Pydantic v2"""
        logger.info("Testing field validators...")

        try:
            from generation_service.models.rag_models import RAGSearchRequestDTO

            # Test query validation (should strip whitespace)
            query = RAGSearchRequestDTO(
                query="  test query with whitespace  ", max_results=10
            )

            if query.query == "test query with whitespace":
                self.validated_items.append("field_validator_query_strip")
                logger.info("✓ Query field validator (strip) working")
            else:
                self.errors.append(
                    f"Query field validator not working: got '{query.query}'"
                )

            # Test empty query validation (should raise error)
            try:
                empty_query = RAGSearchRequestDTO(
                    query="",  # Should be invalid
                    max_results=10,
                )
                self.warnings.append(
                    "Expected validation error for empty query was not raised"
                )
            except Exception:
                self.validated_items.append("field_validator_query_empty_check")
                logger.info("✓ Empty query validation working")

        except Exception as e:
            self.errors.append(f"Field validator testing failed: {e}")

    def test_model_serialization(self):
        """Test model serialization with Pydantic v2"""
        logger.info("Testing model serialization...")

        try:
            from generation_service.models.generation import (
                GenerationRequest,
                ScriptType,
            )

            # Create test request
            request = GenerationRequest(
                title="Serialization Test",
                description="Testing Pydantic v2 serialization capabilities",
                script_type=ScriptType.COMEDY,
                project_id="serialize_test_123",
            )

            # Test model_dump (v2 method)
            try:
                data = request.model_dump()
                self.validated_items.append("model_dump_method")
                logger.info("✓ model_dump() method working")
            except AttributeError:
                # Try v1 method as fallback
                data = request.dict()
                self.warnings.append(
                    "Using v1 dict() method instead of v2 model_dump()"
                )

            # Verify serialized data
            required_fields = ["title", "description", "script_type", "project_id"]
            for field in required_fields:
                if field not in data:
                    self.errors.append(f"Serialized data missing field: {field}")

            if all(field in data for field in required_fields):
                self.validated_items.append("model_serialization_fields")
                logger.info("✓ Model serialization includes all required fields")

            # Test JSON schema generation (v2 method)
            try:
                schema = request.model_json_schema()
                if "properties" in schema and "title" in schema:
                    self.validated_items.append("model_json_schema")
                    logger.info("✓ model_json_schema() method working")
                else:
                    self.warnings.append(
                        "JSON schema generation may not be working correctly"
                    )
            except AttributeError:
                self.warnings.append("model_json_schema() method not available")

        except Exception as e:
            self.errors.append(f"Model serialization testing failed: {e}")


def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_results(results: list, result_type: str, icon: str):
    """Print test results"""
    if results:
        print(f"\n{icon} {result_type.upper()} ({len(results)}):")
        for i, result in enumerate(results, 1):
            print(f"  {i}. {result}")
    else:
        print(f"\n✅ No {result_type.lower()}")


def main():
    """Main testing routine"""
    print("🔍 Pydantic v2 Compatibility Testing")
    print(f"Python: {sys.version}")
    print(f"Working Directory: {os.getcwd()}")

    print_section("Pydantic v2 Compatibility Testing")

    tester = PydanticV2Tester()
    is_compatible, errors, warnings = tester.test_all()

    print(f"\nTested {len(tester.validated_items)} Pydantic v2 components")

    print_results(errors, "errors", "❌")
    print_results(warnings, "warnings", "⚠️")

    print_section("Testing Summary")

    if is_compatible:
        print("🎉 Pydantic v2 compatibility testing PASSED")
        print("✅ All models and validators are compatible with Pydantic v2")
        exit_code = 0
    else:
        print("❌ Pydantic v2 compatibility testing FAILED")
        print("🚨 Critical compatibility issues must be resolved")
        exit_code = 1

    # Summary stats
    print("\nTesting Results:")
    print(f"  Pydantic v2 components tested: {len(tester.validated_items)}")
    print(f"  Errors found: {len(errors)}")
    print(f"  Warnings: {len(warnings)}")

    if errors:
        print(f"\n🚨 {len(errors)} critical compatibility issues found")

    if warnings:
        print(f"⚠️  {len(warnings)} compatibility warnings - review for optimization")

    # List validated components
    if tester.validated_items:
        print("\n✅ Successfully tested components:")
        for item in tester.validated_items:
            print(f"  • {item.replace('_', ' ').title()}")

    return exit_code


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️  Testing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Testing failed with unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
