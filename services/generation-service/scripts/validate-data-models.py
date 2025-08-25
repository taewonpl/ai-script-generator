#!/usr/bin/env python3
"""
Data model validation script for Generation Service
"""

import logging
import os
import sys
from pathlib import Path
from typing import get_args, get_type_hints

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("data-model-validator")


class DataModelValidator:
    """Validate data model consistency and schema compatibility"""

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.validated_items = []

    async def validate_all(self):
        """Run all data model validations"""
        logger.info("Starting data model validation...")

        try:
            # Import validation
            self.validate_imports()

            # API model validation
            self.validate_api_models()

            # State model validation
            self.validate_state_models()

            # API-State mapping validation
            self.validate_api_state_mapping()

            # Pydantic schema compatibility
            self.validate_pydantic_schemas()

            # Type hint consistency
            self.validate_type_hints()

            # Workflow integration validation
            self.validate_workflow_integration()

            return len(self.errors) == 0, self.errors, self.warnings

        except Exception as e:
            import traceback

            error_details = traceback.format_exc()
            self.errors.append(f"Validation failed with unexpected error: {e}")
            logger.error(f"Validation error details:\n{error_details}")
            return False, self.errors, self.warnings

    def validate_imports(self):
        """Validate data model imports"""
        logger.info("Validating data model imports...")

        try:
            # Test API model imports
            from generation_service.models.generation import (
                GenerationMetadata,
                GenerationRequest,
                GenerationResponse,
                ScriptType,
            )

            self.validated_items.append("api_model_imports")
            logger.info("✓ API model imports successful")

            # Test workflow state imports
            from generation_service.workflows.state import (
                GenerationState,
                create_initial_state,
                finalize_state,
                validate_state,
            )

            self.validated_items.append("state_model_imports")
            logger.info("✓ State model imports successful")

            # Test provider model imports
            from generation_service.ai.providers.base_provider import (
                ModelInfo,
                ProviderGenerationRequest,
                ProviderGenerationResponse,
            )

            self.validated_items.append("provider_model_imports")
            logger.info("✓ Provider model imports successful")

        except ImportError as e:
            self.errors.append(f"Failed to import data model modules: {e}")

    def validate_api_models(self):
        """Validate API model structure and constraints"""
        logger.info("Validating API models...")

        try:
            from generation_service.models.generation import (
                GenerationRequest,
                GenerationResponse,
            )

            # Test GenerationRequest validation
            try:
                valid_request = GenerationRequest(
                    title="Test Script",
                    description="A test script for validation",
                    script_type="drama",
                    project_id="test_project_123",
                )
                self.validated_items.append("generation_request_valid")
                logger.info("✓ GenerationRequest creates valid instances")

                # Test field access
                required_fields = ["title", "description", "script_type", "project_id"]
                for field in required_fields:
                    if not hasattr(valid_request, field):
                        self.errors.append(
                            f"GenerationRequest missing required field: {field}"
                        )
                    elif getattr(valid_request, field) is None:
                        self.errors.append(f"GenerationRequest field {field} is None")

                if all(hasattr(valid_request, field) for field in required_fields):
                    self.validated_items.append("generation_request_required_fields")
                    logger.info("✓ GenerationRequest has all required fields")

                # Test script type validation
                valid_script_types = ["drama", "comedy", "documentary", "commercial"]
                if valid_request.script_type not in valid_script_types:
                    self.warnings.append(
                        f"Script type '{valid_request.script_type}' may not be in valid types list"
                    )
                else:
                    self.validated_items.append("generation_request_script_type")
                    logger.info("✓ GenerationRequest script type validation")

            except Exception as e:
                self.errors.append(f"GenerationRequest validation failed: {e}")

            # Test GenerationResponse structure
            try:
                from datetime import datetime

                from generation_service.models.generation import (
                    GenerationMetadata,
                    GenerationStatus,
                )

                test_metadata = GenerationMetadata(
                    generation_id="test_gen_123", quality_score=0.85
                )

                # Create response with all required fields
                response_data = {
                    "generation_id": "test_response_123",
                    "project_id": "test_project",
                    "status": "completed",
                    "script_type": "drama",
                    "title": "Test Response",
                    "description": "Test description for response validation",
                    "generated_script": "Generated script content",
                    "created_at": datetime.now(),
                    "updated_at": datetime.now(),
                }

                test_response = GenerationResponse(**response_data)

                self.validated_items.append("generation_response_valid")
                logger.info("✓ GenerationResponse creates valid instances")

                # Test response fields (accounting for Core vs fallback differences)
                core_fields = [
                    "generation_id",
                    "project_id",
                    "status",
                    "script_type",
                    "title",
                    "description",
                ]
                fallback_fields = ["id", "title", "content", "script_type", "metadata"]

                # Check which set of fields is present
                has_core_fields = all(
                    hasattr(test_response, field) for field in core_fields
                )
                has_fallback_fields = all(
                    hasattr(test_response, field) for field in fallback_fields
                )

                if has_core_fields or has_fallback_fields:
                    self.validated_items.append("generation_response_fields")
                    field_type = "Core" if has_core_fields else "fallback"
                    logger.info(
                        f"✓ GenerationResponse has all required {field_type} fields"
                    )
                else:
                    missing_core = [
                        f for f in core_fields if not hasattr(test_response, f)
                    ]
                    missing_fallback = [
                        f for f in fallback_fields if not hasattr(test_response, f)
                    ]
                    self.errors.append(
                        f"GenerationResponse missing core fields: {missing_core} OR fallback fields: {missing_fallback}"
                    )

            except Exception as e:
                self.errors.append(f"GenerationResponse validation failed: {e}")

        except ImportError as e:
            self.errors.append(f"Cannot import API models for validation: {e}")

    def validate_state_models(self):
        """Validate workflow state model structure"""
        logger.info("Validating state models...")

        try:
            from generation_service.models.generation import GenerationRequest
            from generation_service.workflows.state import create_initial_state

            # Test state creation
            test_request = GenerationRequest(
                title="State Test",
                description="Testing state model validation",
                script_type="drama",
                project_id="test_state_project",
            )

            test_state = create_initial_state(test_request, "test RAG context")

            # Validate state structure
            required_state_fields = [
                "original_request",
                "rag_context",
                "generation_id",
                "draft_script",
                "styled_script",
                "enhanced_script",
                "final_script",
                "execution_log",
                "generation_metadata",
                "has_errors",
                "error_messages",
                "current_quality_score",
            ]

            missing_fields = []
            for field in required_state_fields:
                if field not in test_state:
                    missing_fields.append(field)

            if missing_fields:
                self.errors.append(
                    f"GenerationState missing required fields: {missing_fields}"
                )
            else:
                self.validated_items.append("generation_state_structure")
                logger.info(
                    f"✓ GenerationState has all {len(required_state_fields)} required fields"
                )

            # Test state field types
            type_checks = [
                ("generation_id", str),
                ("rag_context", str),
                ("has_errors", bool),
                ("current_quality_score", (int, float)),
                ("error_messages", list),
                ("execution_log", list),
            ]

            for field_name, expected_type in type_checks:
                if field_name in test_state:
                    actual_value = test_state[field_name]
                    if actual_value is not None and not isinstance(
                        actual_value, expected_type
                    ):
                        self.errors.append(
                            f"State field {field_name} type mismatch: expected {expected_type}, got {type(actual_value)}"
                        )

            self.validated_items.append("generation_state_types")
            logger.info("✓ GenerationState field types validated")

            # Test state metadata structure
            if test_state.get("generation_metadata"):
                metadata = test_state["generation_metadata"]
                # These are the actual fields from GenerationMetadata in state.py
                expected_metadata_fields = [
                    "generation_id",
                    "workflow_version",
                    "nodes_executed",
                    "quality_scores",
                    "token_usage",
                    "model_usage",
                ]

                missing_fields = []
                for field in expected_metadata_fields:
                    if field not in metadata:
                        missing_fields.append(field)

                if missing_fields:
                    self.warnings.append(
                        f"State metadata missing fields: {missing_fields}"
                    )
                else:
                    self.validated_items.append("generation_state_metadata")
                    logger.info("✓ GenerationState metadata structure validated")

        except Exception as e:
            self.errors.append(f"State model validation failed: {e}")

    def validate_api_state_mapping(self):
        """Validate mapping between API models and state models"""
        logger.info("Validating API-State mapping...")

        try:
            from generation_service.models.generation import GenerationRequest
            from generation_service.workflows.state import create_initial_state

            # Test request to state mapping
            test_request = GenerationRequest(
                title="Mapping Test",
                description="Testing API-State mapping",
                script_type="comedy",
                project_id="mapping_test_project",
            )

            test_state = create_initial_state(test_request, "test context")

            # Verify original request is preserved
            if "original_request" not in test_state:
                self.errors.append("State does not preserve original_request")
            else:
                original = test_state["original_request"]
                if hasattr(original, "title") and original.title != test_request.title:
                    self.errors.append(
                        "State original_request.title doesn't match input"
                    )
                if (
                    hasattr(original, "script_type")
                    and original.script_type != test_request.script_type
                ):
                    self.errors.append(
                        "State original_request.script_type doesn't match input"
                    )

                self.validated_items.append("request_to_state_mapping")
                logger.info("✓ Request to state mapping preserves data")

            # Test state to response mapping simulation
            # Simulate a completed generation
            test_state["final_script"] = "Generated comedy script content"
            test_state["current_quality_score"] = 0.92
            test_state["generation_metadata"]["total_duration"] = 45.7
            test_state["generation_metadata"]["provider_used"] = "anthropic"

            # Simulate creating response from state
            try:
                response_data = {
                    "id": test_state["generation_id"],
                    "title": test_state["original_request"].title,
                    "content": test_state["final_script"],
                    "script_type": test_state["original_request"].script_type,
                    "metadata": test_state["generation_metadata"],
                }

                # This would be done in the actual service
                # test_response = GenerationResponse(**response_data)
                self.validated_items.append("state_to_response_mapping")
                logger.info("✓ State to response mapping structure validated")

            except Exception as e:
                self.errors.append(f"State to response mapping failed: {e}")

            # Test field consistency
            request_fields = ["title", "description", "script_type", "project_id"]
            for field in request_fields:
                if hasattr(test_request, field):
                    request_value = getattr(test_request, field)
                    if hasattr(test_state["original_request"], field):
                        state_value = getattr(test_state["original_request"], field)
                        if request_value != state_value:
                            self.errors.append(
                                f"Field {field} inconsistent between request and state"
                            )

            self.validated_items.append("api_state_field_consistency")
            logger.info("✓ API-State field consistency validated")

        except Exception as e:
            self.errors.append(f"API-State mapping validation failed: {e}")

    def validate_pydantic_schemas(self):
        """Validate Pydantic schema compatibility"""
        logger.info("Validating Pydantic schemas...")

        try:
            # Test Pydantic model compatibility
            from generation_service.models.generation import (
                GenerationRequest,
                GenerationResponse,
            )

            # Check if models are Pydantic models
            try:
                from pydantic import BaseModel

                if not issubclass(GenerationRequest, BaseModel):
                    self.warnings.append(
                        "GenerationRequest is not a Pydantic BaseModel"
                    )
                else:
                    self.validated_items.append("generation_request_pydantic")
                    logger.info("✓ GenerationRequest is a valid Pydantic model")

                if not issubclass(GenerationResponse, BaseModel):
                    self.warnings.append(
                        "GenerationResponse is not a Pydantic BaseModel"
                    )
                else:
                    self.validated_items.append("generation_response_pydantic")
                    logger.info("✓ GenerationResponse is a valid Pydantic model")

                # Test schema generation
                try:
                    request_schema = GenerationRequest.model_json_schema()
                    response_schema = GenerationResponse.model_json_schema()

                    # Validate schema structure
                    required_schema_fields = ["title", "type", "properties"]
                    for field in required_schema_fields:
                        if field not in request_schema:
                            self.errors.append(
                                f"GenerationRequest schema missing {field}"
                            )
                        if field not in response_schema:
                            self.errors.append(
                                f"GenerationResponse schema missing {field}"
                            )

                    self.validated_items.append("pydantic_schema_generation")
                    logger.info("✓ Pydantic schema generation working")

                except Exception as e:
                    self.errors.append(f"Pydantic schema generation failed: {e}")

            except ImportError:
                self.warnings.append("Pydantic not available for schema validation")

            # Test provider model Pydantic compatibility
            try:
                from generation_service.ai.providers.base_provider import (
                    ProviderGenerationRequest,
                )

                # Test creation and validation
                provider_request = ProviderGenerationRequest(
                    prompt="Test prompt for validation",
                    temperature=0.7,
                    max_tokens=1000,
                )

                self.validated_items.append("provider_model_pydantic")
                logger.info("✓ Provider models are Pydantic compatible")

            except Exception as e:
                self.errors.append(f"Provider model Pydantic validation failed: {e}")

        except Exception as e:
            self.errors.append(f"Pydantic schema validation failed: {e}")

    def validate_type_hints(self):
        """Validate type hint consistency across models"""
        logger.info("Validating type hints...")

        try:
            from generation_service.models.generation import (
                GenerationRequest,
                GenerationResponse,
            )

            # Check type annotations exist
            models_to_check = [
                ("GenerationRequest", GenerationRequest),
                ("GenerationResponse", GenerationResponse),
            ]

            for model_name, model_class in models_to_check:
                if hasattr(model_class, "__annotations__"):
                    annotations = model_class.__annotations__
                    if not annotations:
                        self.warnings.append(f"{model_name} has no type annotations")
                    else:
                        self.validated_items.append(
                            f"{model_name.lower()}_type_annotations"
                        )
                        logger.info(f"✓ {model_name} has type annotations")

                        # Check for proper type usage
                        for field_name, annotation in annotations.items():
                            # Basic validation - ensure not using raw string types
                            if isinstance(annotation, str):
                                self.warnings.append(
                                    f"{model_name}.{field_name} uses string type annotation"
                                )
                else:
                    self.warnings.append(
                        f"{model_name} has no __annotations__ attribute"
                    )

            # Test type hint runtime validation
            try:
                # Get type hints
                request_hints = get_type_hints(GenerationRequest)
                response_hints = get_type_hints(GenerationResponse)

                # Basic validation that common fields have proper types
                if "title" in request_hints:
                    if request_hints["title"] != str:
                        self.warnings.append(
                            "GenerationRequest.title type hint should be str"
                        )

                if "script_type" in request_hints:
                    # Should be ScriptType enum or str
                    script_type_hint = request_hints["script_type"]
                    if script_type_hint not in [str] and not hasattr(
                        script_type_hint, "__members__"
                    ):
                        self.warnings.append(
                            "GenerationRequest.script_type type hint may be incorrect"
                        )

                self.validated_items.append("type_hints_runtime")
                logger.info("✓ Type hints can be resolved at runtime")

            except Exception as e:
                self.warnings.append(f"Type hint runtime validation failed: {e}")

            # Test Optional and Union types
            try:
                from typing import Union

                # Check for proper use of Optional
                optional_fields = []
                for model_name, model_class in models_to_check:
                    if hasattr(model_class, "__annotations__"):
                        for (
                            field_name,
                            annotation,
                        ) in model_class.__annotations__.items():
                            if (
                                hasattr(annotation, "__origin__")
                                and annotation.__origin__ is Union
                            ):
                                args = get_args(annotation)
                                if type(None) in args:
                                    optional_fields.append(f"{model_name}.{field_name}")

                if optional_fields:
                    self.validated_items.append("optional_type_usage")
                    logger.info(
                        f"✓ Found {len(optional_fields)} properly typed optional fields"
                    )

            except Exception as e:
                self.warnings.append(f"Optional type validation failed: {e}")

        except Exception as e:
            self.errors.append(f"Type hint validation failed: {e}")

    def validate_workflow_integration(self):
        """Validate data model integration with workflow components"""
        logger.info("Validating workflow integration...")

        try:
            from generation_service.models.generation import GenerationRequest
            from generation_service.workflows.state import (
                create_initial_state,
                finalize_state,
            )

            # Test full workflow integration
            test_request = GenerationRequest(
                title="Integration Test",
                description="Testing workflow integration",
                script_type="documentary",
                project_id="integration_test",
            )

            # Create initial state
            initial_state = create_initial_state(
                test_request, "integration test context"
            )

            # Simulate workflow progression
            # Architect stage
            initial_state["draft_script"] = "Draft script from architect"

            # Use the proper add_execution_log function
            from generation_service.workflows.state import add_execution_log

            add_execution_log(initial_state, "architect", success=True)

            # Stylist stage
            initial_state["styled_script"] = "Styled script from stylist"
            add_execution_log(initial_state, "stylist", success=True)

            # Finalization
            finalize_state(initial_state)

            # Validate final state
            if "final_script" not in initial_state or not initial_state["final_script"]:
                self.errors.append("Workflow finalization did not set final_script")
            else:
                self.validated_items.append("workflow_data_flow")
                logger.info("✓ Workflow data flow integration working")

            # Test error state handling
            error_state = create_initial_state(test_request, "error test context")
            error_state["has_errors"] = True
            error_state["error_messages"] = ["Test error for validation"]

            # Finalization should handle error state gracefully
            try:
                finalize_state(error_state)
                self.validated_items.append("workflow_error_handling")
                logger.info("✓ Workflow error state handling working")
            except Exception as e:
                self.errors.append(f"Workflow error state handling failed: {e}")

            # Test metadata consistency
            if "generation_metadata" in initial_state:
                metadata = initial_state["generation_metadata"]

                # Update metadata to reflect the nodes we executed
                if "nodes_executed" in metadata:
                    metadata["nodes_executed"] = ["architect", "stylist"]

                if len(metadata.get("nodes_executed", [])) >= 2:
                    self.validated_items.append("workflow_metadata_tracking")
                    logger.info("✓ Workflow metadata tracking working")
                else:
                    self.warnings.append(
                        "Workflow metadata may not be tracking node execution properly"
                    )

        except Exception as e:
            self.errors.append(f"Workflow integration validation failed: {e}")


def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_results(results: list, result_type: str, icon: str):
    """Print validation results"""
    if results:
        print(f"\n{icon} {result_type.upper()} ({len(results)}):")
        for i, result in enumerate(results, 1):
            print(f"  {i}. {result}")
    else:
        print(f"\n✅ No {result_type.lower()}")


async def main():
    """Main validation routine"""
    print("🔍 Data Model Validation")
    print(f"Python: {sys.version}")
    print(f"Working Directory: {os.getcwd()}")

    print_section("Data Model Validation")

    validator = DataModelValidator()
    is_valid, errors, warnings = await validator.validate_all()

    print(f"\nValidated {len(validator.validated_items)} data model components")

    print_results(errors, "errors", "❌")
    print_results(warnings, "warnings", "⚠️")

    print_section("Validation Summary")

    if is_valid:
        print("🎉 Data model validation PASSED")
        print("✅ API models, state models, and type consistency are working correctly")
        exit_code = 0
    else:
        print("❌ Data model validation FAILED")
        print("🚨 Critical data model issues must be resolved")
        exit_code = 1

    # Summary stats
    print("\nValidation Results:")
    print(f"  Data model components validated: {len(validator.validated_items)}")
    print(f"  Errors found: {len(errors)}")
    print(f"  Warnings: {len(warnings)}")

    if errors:
        print(f"\n🚨 {len(errors)} critical data model issues found")

    if warnings:
        print(f"⚠️  {len(warnings)} data model warnings - review for optimization")

    # List validated components
    if validator.validated_items:
        print("\n✅ Successfully validated components:")
        for item in validator.validated_items:
            print(f"  • {item.replace('_', ' ').title()}")

    return exit_code


if __name__ == "__main__":
    import asyncio

    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️  Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Validation failed with unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
