#!/usr/bin/env python3
"""
Debug script to check async method status
"""

import inspect
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from generation_service.ai.providers.anthropic_provider import AnthropicProvider
    from generation_service.ai.providers.openai_provider import OpenAIProvider

    print("🔍 Checking async method status...\n")

    # Check OpenAI provider
    print("OpenAI Provider:")
    methods = ["generate", "generate_stream", "validate_connection"]
    for method_name in methods:
        if hasattr(OpenAIProvider, method_name):
            method = getattr(OpenAIProvider, method_name)
            if method_name == "generate_stream":
                is_async = inspect.isasyncgenfunction(method)
                print(
                    f"  {method_name}: {'✓ async generator' if is_async else '❌ not async generator'}"
                )
            else:
                is_async = inspect.iscoroutinefunction(method)
                print(f"  {method_name}: {'✓ async' if is_async else '❌ not async'}")
        else:
            print(f"  {method_name}: ❌ method not found")

    print()

    # Check Anthropic provider
    print("Anthropic Provider:")
    for method_name in methods:
        if hasattr(AnthropicProvider, method_name):
            method = getattr(AnthropicProvider, method_name)
            if method_name == "generate_stream":
                is_async = inspect.isasyncgenfunction(method)
                print(
                    f"  {method_name}: {'✓ async generator' if is_async else '❌ not async generator'}"
                )
            else:
                is_async = inspect.iscoroutinefunction(method)
                print(f"  {method_name}: {'✓ async' if is_async else '❌ not async'}")
        else:
            print(f"  {method_name}: ❌ method not found")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
