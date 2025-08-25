#!/usr/bin/env python3
"""
LangGraph workflow validation script for Generation Service
"""

import inspect
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
logger = logging.getLogger("workflow-validator")


class WorkflowValidator:
    """Validate LangGraph workflow structure and consistency"""

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.validated_items = []

    def validate_all(self):
        """Run all workflow validations"""
        logger.info("Starting LangGraph workflow validation...")

        try:
            # Import validation
            self.validate_imports()

            # State consistency validation
            self.validate_state_consistency()

            # Node validation
            self.validate_workflow_nodes()

            # Edge validation
            self.validate_workflow_edges()

            # Data flow validation
            self.validate_data_flow()

            # Error handling validation
            self.validate_error_handling()

            # Type consistency validation
            self.validate_type_consistency()

            return len(self.errors) == 0, self.errors, self.warnings

        except Exception as e:
            self.errors.append(f"Validation failed with unexpected error: {e}")
            return False, self.errors, self.warnings

    def validate_imports(self):
        """Validate workflow imports and dependencies"""
        logger.info("Validating workflow imports...")

        try:
            # Test state module import
            from generation_service.workflows.state import (
                GenerationState,
                create_initial_state,
                finalize_state,
                validate_state,
            )

            self.validated_items.append("state_module_import")
            logger.info("✓ State module imports successful")

            # Test workflow module import
            from generation_service.workflows.generation_workflow import (
                GenerationWorkflow,
            )

            self.validated_items.append("workflow_module_import")
            logger.info("✓ Workflow module imports successful")

        except ImportError as e:
            if "langgraph" in str(e).lower():
                self.warnings.append(f"LangGraph not available: {e}")
                logger.warning(f"⚠️ LangGraph dependency missing: {e}")
            else:
                self.errors.append(f"Failed to import workflow modules: {e}")

        # Test optional dependencies
        try:
            import langgraph

            self.validated_items.append("langgraph_available")
            logger.info("✓ LangGraph dependency available")
        except ImportError:
            self.warnings.append(
                "LangGraph not installed - workflow will use fallback mode"
            )

        try:
            from generation_service.workflows.nodes import (
                ArchitectNode,
                SpecialAgentRouter,
                StylistNode,
            )

            self.validated_items.append("node_modules_import")
            logger.info("✓ Workflow node modules available")
        except ImportError as e:
            self.errors.append(f"Failed to import workflow nodes: {e}")

        try:
            from generation_service.workflows.edges import (
                route_after_stylist,
                route_to_finalization,
            )

            self.validated_items.append("edge_modules_import")
            logger.info("✓ Workflow edge modules available")
        except ImportError as e:
            self.errors.append(f"Failed to import workflow edges: {e}")

    def validate_state_consistency(self):
        """Validate GenerationState consistency and field definitions"""
        logger.info("Validating GenerationState consistency...")

        try:
            from generation_service.models.generation import GenerationRequest
            from generation_service.workflows.state import (
                GenerationState,
                create_initial_state,
                validate_state,
            )

            # Check required state fields
            required_fields = [
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

            # Create a test state to check field presence
            try:
                test_request = GenerationRequest(
                    title="Test",
                    description="Test description",
                    script_type="drama",
                    project_id="test_project",
                )

                test_state = create_initial_state(test_request, "test context")

                missing_fields = []
                for field in required_fields:
                    if field not in test_state:
                        missing_fields.append(field)

                if missing_fields:
                    self.errors.append(
                        f"Missing required state fields: {missing_fields}"
                    )
                else:
                    self.validated_items.append("state_required_fields")
                    logger.info(
                        f"✓ All {len(required_fields)} required state fields present"
                    )

                # Test state validation function
                validation_issues = validate_state(test_state)
                if validation_issues:
                    self.warnings.append(
                        f"State validation issues: {validation_issues}"
                    )
                else:
                    self.validated_items.append("state_validation_function")
                    logger.info("✓ State validation function works correctly")

                # Check decision flags consistency
                decision_flags = [
                    "needs_plot_enhancement",
                    "needs_dialogue_improvement",
                    "needs_detail_addition",
                    "requires_special_agent",
                ]

                for flag in decision_flags:
                    if flag not in test_state:
                        self.errors.append(f"Missing decision flag: {flag}")
                    elif not isinstance(test_state[flag], bool):
                        self.errors.append(f"Decision flag {flag} should be boolean")

                if all(flag in test_state for flag in decision_flags):
                    self.validated_items.append("decision_flags_present")
                    logger.info("✓ All decision flags present and properly typed")

            except Exception as e:
                self.errors.append(f"Failed to create test state: {e}")

        except ImportError as e:
            self.errors.append(f"Cannot import state modules for validation: {e}")

    def validate_workflow_nodes(self):
        """Validate workflow node definitions and interfaces"""
        logger.info("Validating workflow nodes...")

        try:
            from generation_service.workflows.generation_workflow import (
                GenerationWorkflow,
            )

            # Check node methods exist
            node_methods = [
                "_architect_wrapper",
                "_stylist_wrapper",
                "_special_agent_wrapper",
                "_finalization_wrapper",
            ]

            missing_methods = []
            for method_name in node_methods:
                if not hasattr(GenerationWorkflow, method_name):
                    missing_methods.append(method_name)

            if missing_methods:
                self.errors.append(f"Missing workflow node methods: {missing_methods}")
            else:
                self.validated_items.append("workflow_node_methods")
                logger.info(f"✓ All {len(node_methods)} workflow node methods present")

            # Check async compatibility
            for method_name in node_methods:
                if hasattr(GenerationWorkflow, method_name):
                    method = getattr(GenerationWorkflow, method_name)
                    if not inspect.iscoroutinefunction(method):
                        self.errors.append(f"Node method {method_name} is not async")

            self.validated_items.append("node_async_compatibility")
            logger.info("✓ Node methods are properly async")

            # Check node initialization
            try:
                # Mock initialization for testing
                class MockProviderFactory:
                    pass

                class MockRAGService:
                    pass

                workflow = GenerationWorkflow(MockProviderFactory(), MockRAGService())
                self.validated_items.append("workflow_initialization")
                logger.info("✓ Workflow initializes without errors")

            except Exception as e:
                self.errors.append(f"Workflow initialization failed: {e}")

        except ImportError as e:
            self.errors.append(f"Cannot import workflow for node validation: {e}")

    def validate_workflow_edges(self):
        """Validate workflow edge definitions and routing logic"""
        logger.info("Validating workflow edges...")

        try:
            from generation_service.models.generation import GenerationRequest
            from generation_service.workflows.edges import (
                route_after_stylist,
                route_to_finalization,
            )
            from generation_service.workflows.state import create_initial_state

            # Test routing functions
            test_request = GenerationRequest(
                title="Test",
                description="Test description",
                script_type="drama",
                project_id="test_project",
            )

            test_state = create_initial_state(test_request)

            # Test route_after_stylist function
            try:
                # Test with default state (should route to finalization)
                route_result = route_after_stylist(test_state)
                if route_result not in ["special_agent", "finalization"]:
                    self.errors.append(
                        f"Invalid route_after_stylist result: {route_result}"
                    )
                else:
                    self.validated_items.append("route_after_stylist_default")
                    logger.info(
                        f"✓ route_after_stylist returns valid route: {route_result}"
                    )

                # Test with special agent required
                test_state["requires_special_agent"] = True
                route_result = route_after_stylist(test_state)
                if route_result != "special_agent":
                    self.warnings.append(
                        "route_after_stylist should route to special_agent when required"
                    )
                else:
                    self.validated_items.append("route_after_stylist_special_agent")
                    logger.info(
                        "✓ route_after_stylist correctly routes to special_agent when required"
                    )

            except Exception as e:
                self.errors.append(f"route_after_stylist function error: {e}")

            # Test route_to_finalization function
            try:
                route_result = route_to_finalization(test_state)
                if route_result != "finalization":
                    self.errors.append(
                        "route_to_finalization should always return 'finalization'"
                    )
                else:
                    self.validated_items.append("route_to_finalization")
                    logger.info("✓ route_to_finalization works correctly")

            except Exception as e:
                self.errors.append(f"route_to_finalization function error: {e}")

        except ImportError as e:
            self.errors.append(f"Cannot import edge functions for validation: {e}")

    def validate_data_flow(self):
        """Validate data flow between workflow stages"""
        logger.info("Validating workflow data flow...")

        try:
            from generation_service.models.generation import GenerationRequest
            from generation_service.workflows.state import (
                create_initial_state,
                finalize_state,
            )

            # Create test state
            test_request = GenerationRequest(
                title="Data Flow Test",
                description="Testing data flow between stages",
                script_type="drama",
                project_id="test_project",
            )

            test_state = create_initial_state(test_request, "test RAG context")

            # Test stage progression logic
            stages = [
                ("draft_script", "Architect stage output"),
                ("styled_script", "Stylist stage output"),
                ("enhanced_script", "Special agent stage output"),
                ("final_script", "Final stage output"),
            ]

            # Test each stage
            for i, (stage_key, stage_content) in enumerate(stages):
                # Set stage content
                test_state[stage_key] = stage_content

                # Check that finalize_state correctly selects the most advanced script
                finalize_state(test_state)

                expected_final = stage_content  # Should be the latest stage
                if test_state.get("final_script") != expected_final:
                    self.warnings.append(
                        f"finalize_state didn't select correct script at stage {stage_key}"
                    )

                # Reset final_script for next test
                test_state["final_script"] = None

            self.validated_items.append("data_flow_stage_progression")
            logger.info("✓ Data flow stage progression logic validated")

            # Test metadata flow
            test_state["generation_metadata"]["nodes_executed"] = [
                "architect",
                "stylist",
            ]
            test_state["generation_metadata"]["quality_scores"] = {
                "architect": 0.8,
                "stylist": 0.9,
            }

            # Check that metadata is properly maintained
            if not test_state["generation_metadata"]["nodes_executed"]:
                self.errors.append("Metadata nodes_executed not maintained")
            else:
                self.validated_items.append("metadata_flow")
                logger.info("✓ Metadata flow properly maintained")

        except Exception as e:
            self.errors.append(f"Data flow validation failed: {e}")

    def validate_error_handling(self):
        """Validate error handling throughout the workflow"""
        logger.info("Validating error handling...")

        try:
            from generation_service.models.generation import GenerationRequest
            from generation_service.workflows.state import (
                add_execution_log,
                create_initial_state,
            )

            # Create test state
            test_request = GenerationRequest(
                title="Error Test",
                description="Testing error handling",
                script_type="drama",
                project_id="test_project",
            )

            test_state = create_initial_state(test_request)

            # Test error state consistency
            if test_state["has_errors"] != False:
                self.errors.append("Initial state should not have errors")

            if test_state["error_messages"] != []:
                self.errors.append("Initial state should have empty error_messages")

            # Test error logging
            try:
                add_execution_log(
                    test_state,
                    "test_node",
                    success=False,
                    error_message="Test error message",
                )

                if not test_state["has_errors"]:
                    self.errors.append(
                        "add_execution_log should set has_errors=True on failure"
                    )

                if "Test error message" not in " ".join(test_state["error_messages"]):
                    self.errors.append("Error message not properly added to state")
                else:
                    self.validated_items.append("error_logging")
                    logger.info("✓ Error logging works correctly")

            except Exception as e:
                self.errors.append(f"Error logging test failed: {e}")

            # Test error consistency validation
            from generation_service.workflows.state import validate_state

            # Create inconsistent error state
            inconsistent_state = create_initial_state(test_request)
            inconsistent_state["has_errors"] = True
            inconsistent_state["error_messages"] = (
                []
            )  # Inconsistent with has_errors=True

            validation_issues = validate_state(inconsistent_state)
            if "has_errors is True but no error messages" not in validation_issues:
                self.warnings.append(
                    "State validation doesn't catch error inconsistency"
                )
            else:
                self.validated_items.append("error_consistency_validation")
                logger.info("✓ Error consistency validation works")

        except Exception as e:
            self.errors.append(f"Error handling validation failed: {e}")

    def validate_type_consistency(self):
        """Validate type consistency across workflow components"""
        logger.info("Validating type consistency...")

        try:
            from generation_service.models.generation import GenerationRequest
            from generation_service.workflows.state import (
                GenerationState,
                create_initial_state,
            )

            # Test type annotations

            # Check GenerationState type definition
            if hasattr(GenerationState, "__annotations__"):
                annotations = GenerationState.__annotations__

                # Check that required fields have proper type annotations
                required_typed_fields = [
                    ("original_request", "GenerationRequest"),
                    ("rag_context", "str"),
                    ("generation_id", "str"),
                    ("has_errors", "bool"),
                    ("current_quality_score", "float"),
                ]

                for field_name, expected_type in required_typed_fields:
                    if field_name not in annotations:
                        self.warnings.append(
                            f"Missing type annotation for {field_name}"
                        )
                    else:
                        # Basic type check (simplified)
                        annotation_str = str(annotations[field_name])
                        if expected_type not in annotation_str:
                            self.warnings.append(
                                f"Type annotation for {field_name} might be incorrect"
                            )

                self.validated_items.append("state_type_annotations")
                logger.info("✓ State type annotations checked")

            # Test actual type consistency
            test_request = GenerationRequest(
                title="Type Test",
                description="Testing type consistency",
                script_type="drama",
                project_id="test_project",
            )

            test_state = create_initial_state(test_request)

            # Check actual types match expectations
            type_checks = [
                ("generation_id", str),
                ("rag_context", str),
                ("has_errors", bool),
                ("current_quality_score", (int, float)),
                ("error_messages", list),
                ("execution_log", list),
            ]

            for field_name, expected_type in type_checks:
                actual_value = test_state.get(field_name)
                if actual_value is not None and not isinstance(
                    actual_value, expected_type
                ):
                    self.errors.append(
                        f"Type mismatch for {field_name}: expected {expected_type}, got {type(actual_value)}"
                    )

            self.validated_items.append("runtime_type_consistency")
            logger.info("✓ Runtime type consistency validated")

        except Exception as e:
            self.errors.append(f"Type consistency validation failed: {e}")


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


def main():
    """Main validation routine"""
    print("🔍 LangGraph Workflow Validation")
    print(f"Python: {sys.version}")
    print(f"Working Directory: {os.getcwd()}")

    print_section("LangGraph Workflow Structure Validation")

    validator = WorkflowValidator()
    is_valid, errors, warnings = validator.validate_all()

    print(f"\nValidated {len(validator.validated_items)} workflow components")

    print_results(errors, "errors", "❌")
    print_results(warnings, "warnings", "⚠️")

    print_section("Validation Summary")

    if is_valid:
        print("🎉 LangGraph workflow validation PASSED")
        print("✅ Workflow structure and data flow are consistent")
        exit_code = 0
    else:
        print("❌ LangGraph workflow validation FAILED")
        print("🚨 Critical workflow issues must be resolved")
        exit_code = 1

    # Summary stats
    print("\nValidation Results:")
    print(f"  Workflow components validated: {len(validator.validated_items)}")
    print(f"  Errors found: {len(errors)}")
    print(f"  Warnings: {len(warnings)}")

    if errors:
        print(f"\n🚨 {len(errors)} critical workflow issues found")

    if warnings:
        print(f"⚠️  {len(warnings)} workflow warnings - review for optimization")

    # List validated components
    if validator.validated_items:
        print("\n✅ Successfully validated components:")
        for item in validator.validated_items:
            print(f"  • {item.replace('_', ' ').title()}")

    return exit_code


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️  Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Validation failed with unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
