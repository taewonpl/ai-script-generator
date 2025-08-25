#!/usr/bin/env python3
"""
Simple integration test for LangGraph workflow system
"""

import asyncio
import os
import sys

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


async def test_workflow_structure():
    """Test workflow structure and compilation without AI providers"""

    print("🔄 Testing LangGraph workflow structure...")

    try:
        from generation_service.workflows.generation_workflow import GenerationWorkflow

        # Test with None provider factory for structure validation
        workflow = GenerationWorkflow(provider_factory=None, rag_service=None)

        # Get workflow info
        info = workflow.get_workflow_info()

        print("✅ Workflow structure test successful!")
        print(f"   LangGraph Available: {info['langgraph_available']}")
        print(f"   Workflow Compiled: {info['workflow_compiled']}")
        print(f"   Expected Nodes: {info['nodes']}")
        print(f"   Provider Mapping: {info['providers']}")

        return info["langgraph_available"]

    except Exception as e:
        print(f"❌ Workflow structure test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_state_management():
    """Test state management functionality"""

    print("\n🔄 Testing state management...")

    try:
        from generation_service.models.generation import GenerationRequest
        from generation_service.workflows.state import (
            add_execution_log,
            add_token_usage,
            create_initial_state,
            finalize_state,
        )

        # Create test request
        request = GenerationRequest(
            project_id="test_proj",
            title="State Test",
            description="Testing state management",
            script_type="drama",
        )

        # Test initial state creation
        state = create_initial_state(request, "test rag context", "state_test_001")

        print("✅ Initial state creation successful!")
        print(f"   Generation ID: {state['generation_id']}")
        print(f"   Has RAG Context: {bool(state['rag_context'])}")
        print(f"   Quality Score: {state['current_quality_score']}")

        # Test state modifications
        add_execution_log(state, "test_node", success=True)
        add_token_usage(state, "test_node", 100, "test-model")

        state["draft_script"] = "This is a test draft script."
        state["styled_script"] = "This is a styled version of the script."

        # Test finalization
        finalize_state(state)

        print("✅ State management test successful!")
        print(f"   Execution Log Entries: {len(state['execution_log'])}")
        print(
            f"   Token Usage Tracked: {bool(state['generation_metadata']['token_usage'])}"
        )
        print(
            f"   Total Execution Time: {state['generation_metadata']['total_execution_time']}"
        )

        return True

    except Exception as e:
        print(f"❌ State management test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_conditional_routing():
    """Test conditional routing logic"""

    print("\n🔄 Testing conditional routing...")

    try:
        from generation_service.models.generation import GenerationRequest
        from generation_service.workflows.edges import (
            route_after_stylist,
            should_add_details,
            should_enhance_plot,
            should_improve_dialogue,
        )
        from generation_service.workflows.state import create_initial_state

        # Test different routing scenarios
        test_cases = [
            {
                "name": "Comedy Script",
                "request": GenerationRequest(
                    project_id="test",
                    title="Funny Story",
                    description="A comedy script with humor",
                    script_type="comedy",
                ),
                "styled_script": "A short comedy script with some dialogue.",
            },
            {
                "name": "Documentary Script",
                "request": GenerationRequest(
                    project_id="test",
                    title="Mystery Tale",
                    description="A documentary with twists and surprises",
                    script_type="documentary",
                ),
                "styled_script": "A basic documentary script without much tension.",
            },
            {
                "name": "Drama Script",
                "request": GenerationRequest(
                    project_id="test",
                    title="Emotional Journey",
                    description="A drama with deep emotions and conflict",
                    script_type="drama",
                ),
                "styled_script": "A very short drama script.",
            },
        ]

        results = {}

        for test_case in test_cases:
            state = create_initial_state(
                test_case["request"],
                "",
                f"route_test_{test_case['name'].lower().replace(' ', '_')}",
            )
            state["styled_script"] = test_case["styled_script"]

            # Test individual checks
            needs_plot = should_enhance_plot(state)
            needs_dialogue = should_improve_dialogue(state)
            needs_details = should_add_details(state)

            # Test routing decision
            route = route_after_stylist(state)

            results[test_case["name"]] = {
                "needs_plot": needs_plot,
                "needs_dialogue": needs_dialogue,
                "needs_details": needs_details,
                "route": route,
            }

        print("✅ Conditional routing test successful!")
        for name, result in results.items():
            print(f"   {name}:")
            print(f"     Route: {result['route']}")
            print(
                f"     Needs Enhancement: {any([result['needs_plot'], result['needs_dialogue'], result['needs_details']])}"
            )

        return True

    except Exception as e:
        print(f"❌ Conditional routing test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_service_integration():
    """Test GenerationService integration"""

    print("\n🔄 Testing GenerationService integration...")

    try:
        from generation_service.services.generation_service import GenerationService

        # Initialize service (will fail on AI providers but structure should work)
        service = GenerationService()

        # Test workflow info access
        workflow_info = await service.get_workflow_info()
        langgraph_available = await service.is_langgraph_available()

        print("✅ GenerationService integration successful!")
        print("   Service Initialized: True")
        print(f"   LangGraph Available: {langgraph_available}")
        print(f"   Workflow Info Available: {bool(workflow_info)}")
        print(f"   Core Available: {workflow_info.get('core_module_available', False)}")

        return True

    except Exception as e:
        print(f"❌ GenerationService integration test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Main test function"""

    print("🚀 Starting LangGraph Integration Tests")
    print("=" * 60)

    # Run all tests
    tests = [
        ("Workflow Structure", test_workflow_structure),
        ("State Management", test_state_management),
        ("Conditional Routing", test_conditional_routing),
        ("Service Integration", test_service_integration),
    ]

    results = {}

    for test_name, test_func in tests:
        try:
            results[test_name] = await test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results[test_name] = False

    # Summary
    print("\n" + "=" * 60)
    print("📊 Integration Test Summary:")

    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {test_name}: {status}")

    passed = sum(1 for success in results.values() if success)
    total = len(results)

    print(f"\n🎯 Overall Result: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All integration tests PASSED!")
        return True
    else:
        print("⚠️  Some integration tests FAILED!")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
