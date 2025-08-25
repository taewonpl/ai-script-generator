#!/usr/bin/env python3
"""
Test script for LangGraph workflow integration
"""

import asyncio
import os
import sys

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from generation_service.ai.providers.provider_factory import ProviderFactory
from generation_service.config import settings
from generation_service.models.generation import GenerationRequest
from generation_service.workflows.generation_workflow import GenerationWorkflow


async def test_workflow_compilation():
    """Test LangGraph workflow compilation"""

    print("🔄 Testing LangGraph workflow compilation...")

    try:
        # Initialize provider factory
        provider_configs = settings.get_ai_provider_configs()
        provider_factory = ProviderFactory(provider_configs)

        # Initialize workflow
        workflow = GenerationWorkflow(
            provider_factory=provider_factory,
            rag_service=None,  # Skip RAG for basic test
        )

        # Get workflow info
        workflow_info = workflow.get_workflow_info()

        print("✅ Workflow initialization successful!")
        print(f"   LangGraph Available: {workflow_info['langgraph_available']}")
        print(f"   Workflow Compiled: {workflow_info['workflow_compiled']}")
        print(f"   Nodes: {workflow_info['nodes']}")
        print(f"   Providers: {workflow_info['providers']}")

        return (
            workflow_info["langgraph_available"] and workflow_info["workflow_compiled"]
        )

    except Exception as e:
        print(f"❌ Workflow compilation failed: {e}")
        return False


async def test_workflow_execution():
    """Test basic workflow execution"""

    print("\n🔄 Testing workflow execution...")

    try:
        # Initialize provider factory
        provider_configs = settings.get_ai_provider_configs()
        provider_factory = ProviderFactory(provider_configs)

        # Initialize workflow
        workflow = GenerationWorkflow(
            provider_factory=provider_factory, rag_service=None
        )

        # Create test request
        test_request = GenerationRequest(
            project_id="test_project",
            title="Test Script",
            description="A simple test script for comedy genre",
            script_type="comedy",
        )

        print(f"   Test Request: {test_request.title}")
        print(f"   Project ID: {test_request.project_id}")
        print(f"   Script Type: {test_request.script_type}")

        # Execute workflow
        print("   Executing workflow...")
        response = await workflow.execute(test_request, "test_gen_001")

        print("✅ Workflow execution successful!")
        print(f"   Generation ID: {response.generation_id}")
        print(f"   Status: {response.status}")
        print(f"   Word Count: {response.word_count}")
        print(
            f"   Script Length: {len(response.generated_script) if response.generated_script else 0} characters"
        )

        if hasattr(response, "quality_score"):
            print(f"   Quality Score: {response.quality_score}")

        if hasattr(response, "workflow_metadata"):
            metadata = response.workflow_metadata
            print(f"   LangGraph Used: {metadata.get('langgraph_used', False)}")
            print(f"   Nodes Executed: {metadata.get('nodes_executed', [])}")

        return True

    except Exception as e:
        print(f"❌ Workflow execution failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_workflow_nodes():
    """Test individual workflow nodes"""

    print("\n🔄 Testing workflow nodes...")

    try:
        # Test state creation
        from generation_service.workflows.state import create_initial_state

        test_request = GenerationRequest(
            project_id="test_project",
            title="Node Test Script",
            description="Testing individual nodes",
            script_type="drama",
        )

        initial_state = create_initial_state(
            test_request, "test rag context", "node_test_001"
        )

        print("✅ State creation successful!")
        print(f"   Generation ID: {initial_state['generation_id']}")
        print(f"   Request Title: {initial_state['original_request'].title}")
        print(f"   RAG Context Available: {bool(initial_state['rag_context'])}")

        # Test conditional edges
        from generation_service.workflows.edges import route_after_stylist

        # Simulate stylist completion
        test_state = initial_state.copy()
        test_state["styled_script"] = (
            "This is a test styled script with dialogue and scenes."
        )

        routing_decision = route_after_stylist(test_state)
        print(f"   Routing Decision: {routing_decision}")

        return True

    except Exception as e:
        print(f"❌ Node testing failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Main test function"""

    print("🚀 Starting LangGraph Workflow Tests")
    print("=" * 50)

    # Test 1: Workflow compilation
    compilation_success = await test_workflow_compilation()

    # Test 2: Workflow nodes
    nodes_success = await test_workflow_nodes()

    # Test 3: Workflow execution (only if compilation succeeded)
    execution_success = False
    if compilation_success:
        execution_success = await test_workflow_execution()
    else:
        print("\n⚠️  Skipping execution test due to compilation failure")

    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    print(f"   Workflow Compilation: {'✅' if compilation_success else '❌'}")
    print(f"   Node Testing: {'✅' if nodes_success else '❌'}")
    print(f"   Workflow Execution: {'✅' if execution_success else '❌'}")

    overall_success = compilation_success and nodes_success and execution_success
    print(f"\n🎯 Overall Result: {'SUCCESS' if overall_success else 'FAILED'}")

    return overall_success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
