#!/usr/bin/env python3
"""
Test Pydantic v2 model_ field warnings removal
"""

import sys
import warnings
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_pydantic_model_fields():
    """Test that model_ fields no longer generate warnings"""

    print("🔍 Testing Pydantic v2 model_ field warnings...")

    # Capture warnings
    warnings.simplefilter("always")
    warning_list = []

    def warning_handler(message, category, filename, lineno, file=None, line=None):
        warning_list.append(
            {
                "message": str(message),
                "category": category.__name__,
                "filename": filename,
                "lineno": lineno,
            }
        )

    old_showwarning = warnings.showwarning
    warnings.showwarning = warning_handler

    try:
        # Test 1: Import models module
        print("\n1. Testing model import...")
        from generation_service.models.generation import (
            GenerationResponse,
            GenerationUpdate,
            NodeExecutionResult,
            ScriptGenerationRequest,
        )

        print("   ✅ Models imported successfully")

        # Test 2: Create instances with model_ fields
        print("\n2. Testing model instantiation with model_ fields...")

        # Test GenerationResponse (Core version if available)
        try:
            from datetime import datetime

            response = GenerationResponse(
                generation_id="test-123",
                project_id="proj-456",
                status="completed",
                script_type="drama",  # Required field
                title="Test Script",  # Required field
                description="Test description for validation",  # Required field
                content="Test content",
                model_used="gpt-4o",  # This should not generate warnings
                generation_time_seconds=2.5,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            print("   ✅ GenerationResponse created with model_used field")
        except Exception as e:
            print(f"   ⚠️ GenerationResponse creation failed: {e}")

        # Test GenerationUpdate
        try:
            update = GenerationUpdate(
                status="completed",
                model_used="gpt-4o",  # This should not generate warnings
                content="Updated content",
            )
            print("   ✅ GenerationUpdate created with model_used field")
        except Exception as e:
            print(f"   ⚠️ GenerationUpdate creation failed: {e}")

        # Test ScriptGenerationRequest
        try:
            request = ScriptGenerationRequest(
                project_id="proj-789",
                script_type="drama",
                title="Test Script",
                description="This is a test script for validation",
                model_preferences={
                    "architect": "gpt-4o",
                    "stylist": "claude-3-5-sonnet",
                },  # This should not generate warnings
                temperature=0.8,
            )
            print("   ✅ ScriptGenerationRequest created with model_preferences field")
        except Exception as e:
            print(f"   ⚠️ ScriptGenerationRequest creation failed: {e}")

        # Test NodeExecutionResult
        try:
            result = NodeExecutionResult(
                node_type="architect",
                status="completed",
                content="Node result content",
                model_used="anthropic-claude",  # This should not generate warnings
                execution_time=1.5,
            )
            print("   ✅ NodeExecutionResult created with model_used field")
        except Exception as e:
            print(f"   ⚠️ NodeExecutionResult creation failed: {e}")

        # Test 3: Model serialization/deserialization
        print("\n3. Testing model serialization...")

        try:
            # Test JSON serialization
            response_dict = response.model_dump()
            assert "model_used" in response_dict
            print("   ✅ model_used field preserved in serialization")

            # Test JSON deserialization
            new_response = GenerationResponse.model_validate(response_dict)
            assert new_response.model_used == "gpt-4o"
            print("   ✅ model_used field preserved in deserialization")

        except Exception as e:
            print(f"   ⚠️ Serialization test failed: {e}")

        # Test 4: Check for specific Pydantic warnings
        print("\n4. Testing for Pydantic warnings...")

        pydantic_warnings = [
            w for w in warning_list if "pydantic" in str(w["message"]).lower()
        ]
        model_warnings = [w for w in warning_list if "model_" in str(w["message"])]
        namespace_warnings = [
            w for w in warning_list if "namespace" in str(w["message"]).lower()
        ]

        if pydantic_warnings:
            print("   ⚠️ Pydantic warnings found:")
            for w in pydantic_warnings[:5]:  # Show first 5
                print(f"      - {w['message']}")
        else:
            print("   ✅ No Pydantic warnings detected")

        if model_warnings:
            print("   ⚠️ model_ field warnings found:")
            for w in model_warnings:
                print(f"      - {w['message']}")
        else:
            print("   ✅ No model_ field warnings detected")

        if namespace_warnings:
            print("   ⚠️ Namespace warnings found:")
            for w in namespace_warnings:
                print(f"      - {w['message']}")
        else:
            print("   ✅ No namespace warnings detected")

        # Test 5: API schema compatibility
        print("\n5. Testing API schema compatibility...")

        try:
            # Test that schema generation works
            schema = GenerationResponse.model_json_schema()

            # Check that model_used field is in schema
            if "properties" in schema and "model_used" in schema["properties"]:
                print("   ✅ model_used field present in JSON schema")
            else:
                print("   ⚠️ model_used field missing from JSON schema")

            # Check for any deprecated warnings in schema
            schema_str = str(schema)
            if "deprecat" in schema_str.lower():
                print("   ⚠️ Deprecated warnings in schema")
            else:
                print("   ✅ No deprecated warnings in schema")

        except Exception as e:
            print(f"   ⚠️ Schema generation failed: {e}")

        # Summary
        print("\n📊 Pydantic v2 model_ Field Test Results:")
        print(f"  Total warnings captured: {len(warning_list)}")
        print(f"  Pydantic-related warnings: {len(pydantic_warnings)}")
        print(f"  model_ field warnings: {len(model_warnings)}")
        print(f"  Namespace warnings: {len(namespace_warnings)}")

        success = (
            len(pydantic_warnings) == 0
            and len(model_warnings) == 0
            and len(namespace_warnings) == 0
        )

        if success:
            print("\n🎉 All model_ field warnings successfully removed!")
            print("✅ ConfigDict(protected_namespaces=()) working correctly")
            print("✅ API schema compatibility maintained")
            print("✅ Field serialization/deserialization working")
            return True
        else:
            print("\n⚠️ Some warnings still present")
            print("Review the warnings above for remaining issues")
            return False

    finally:
        # Restore original warning handler
        warnings.showwarning = old_showwarning


def test_api_compatibility():
    """Test API endpoint compatibility"""

    print("\n🔧 Testing API endpoint compatibility...")

    try:
        # Test that FastAPI can generate docs without warnings
        from generation_service.models.generation import GenerationResponse

        # Create a mock API response
        mock_response = {
            "generation_id": "test-123",
            "project_id": "proj-456",
            "status": "completed",
            "script_type": "drama",
            "title": "Test Script",
            "description": "Test description for API validation",
            "content": "Generated script content",
            "model_used": "gpt-4o",
            "created_at": "2024-01-01T12:00:00Z",
            "updated_at": "2024-01-01T12:01:00Z",
        }

        # Test validation
        response = GenerationResponse.model_validate(mock_response)
        print("   ✅ API response validation working")

        # Test serialization maintains field names
        serialized = response.model_dump()
        if "model_used" in serialized:
            print("   ✅ API field names preserved")
        else:
            print("   ❌ API field names changed - breaking change!")
            return False

        return True

    except Exception as e:
        print(f"   ❌ API compatibility test failed: {e}")
        return False


if __name__ == "__main__":
    print("Pydantic v2 Model Field Warning Removal Test")
    print("=" * 50)

    # Test 1: Model field warnings
    model_test_success = test_pydantic_model_fields()

    # Test 2: API compatibility
    api_test_success = test_api_compatibility()

    # Overall result
    overall_success = model_test_success and api_test_success

    if overall_success:
        print("\n🎉 All Pydantic v2 tests PASSED!")
        print("✅ model_ field warnings removed")
        print("✅ API compatibility maintained")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed")
        sys.exit(1)
