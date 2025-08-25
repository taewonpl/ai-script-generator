#!/usr/bin/env python3
"""
Strengthen import fallback logic for ai_script_core across Generation Service
"""

import os
import sys

# Files that need import fallback strengthening
TARGET_FILES = [
    "src/generation_service/models/vector_document.py",
    "src/generation_service/models/rag_models.py",
    "src/generation_service/models/generation.py",
    "src/generation_service/config/settings.py",
    "src/generation_service/optimization/resource_manager.py",
    "src/generation_service/optimization/async_manager.py",
    "src/generation_service/config.py",
    "src/generation_service/api/performance_endpoints.py",
    "src/generation_service/api/cache_endpoints.py",
    "src/generation_service/api/monitoring_endpoints.py",
    "src/generation_service/config/performance_config.py",
    "src/generation_service/logging/debug_tools.py",
    "src/generation_service/logging/performance_tracer.py",
    "src/generation_service/logging/structured_logger.py",
    "src/generation_service/monitoring/dashboard.py",
    "src/generation_service/monitoring/alerting.py",
    "src/generation_service/monitoring/health_monitor.py",
    "src/generation_service/monitoring/metrics_collector.py",
    "src/generation_service/optimization/connection_pool.py",
    "src/generation_service/workflows/feedback/feedback_system.py",
    "src/generation_service/workflows/quality/quality_assessor.py",
    "src/generation_service/workflows/agents/agent_coordinator.py",
    "src/generation_service/workflows/agents/tension_builder_agent.py",
    "src/generation_service/workflows/agents/scene_visualizer_agent.py",
    "src/generation_service/workflows/agents/dialogue_enhancer_agent.py",
    "src/generation_service/workflows/agents/flaw_generator_agent.py",
    "src/generation_service/workflows/agents/plot_twister_agent.py",
    "src/generation_service/workflows/agents/base_agent.py",
    "src/generation_service/main.py",
    "src/generation_service/api/generate.py",
    "src/generation_service/services/generation_service.py",
    "src/generation_service/workflows/generation_workflow.py",
    "src/generation_service/workflows/edges/conditional_edges.py",
    "src/generation_service/workflows/nodes/special_agent_nodes.py",
    "src/generation_service/workflows/nodes/stylist_node.py",
    "src/generation_service/workflows/nodes/architect_node.py",
    "src/generation_service/workflows/nodes/base_node.py",
    "src/generation_service/workflows/state.py",
    "src/generation_service/ai/prompts/base_prompt.py",
    "src/generation_service/api/rag.py",
    "src/generation_service/rag/rag_service.py",
    "src/generation_service/rag/context_builder.py",
    "src/generation_service/rag/retriever.py",
    "src/generation_service/rag/embeddings.py",
    "src/generation_service/rag/chroma_store.py",
    "src/generation_service/ai/providers/base_provider.py",
    "src/generation_service/ai/providers/anthropic_provider.py",
    "src/generation_service/ai/providers/openai_provider.py",
]


def analyze_import_patterns(file_path: str) -> dict:
    """Analyze ai_script_core import patterns in a file"""

    if not os.path.exists(file_path):
        return {"status": "file_not_found", "patterns": []}

    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        patterns = []
        lines = content.split("\n")

        for i, line in enumerate(lines, 1):
            if "from ai_script_core import" in line or "import ai_script_core" in line:
                patterns.append(
                    {"line_number": i, "line": line.strip(), "type": "direct_import"}
                )
            elif "ai_script_core" in line:
                patterns.append(
                    {"line_number": i, "line": line.strip(), "type": "usage"}
                )

        # Check if try-except pattern already exists
        has_fallback = (
            "except (ImportError, RuntimeError):" in content
            or "CORE_AVAILABLE" in content
        )

        return {
            "status": "analyzed",
            "file": file_path,
            "patterns": patterns,
            "has_fallback": has_fallback,
            "content": content,
        }

    except Exception as e:
        return {"status": "error", "error": str(e), "patterns": []}


def check_existing_fallback_quality(analysis: dict) -> dict:
    """Check quality of existing fallback implementation"""

    if not analysis.get("has_fallback", False):
        return {"quality": "none", "issues": ["No fallback logic found"]}

    content = analysis.get("content", "")
    issues = []

    # Check for proper exception handling
    if (
        "except ImportError:" in content
        and "except (ImportError, RuntimeError):" not in content
    ):
        issues.append("Should catch both ImportError and RuntimeError")

    # Check for CORE_AVAILABLE flag
    if "CORE_AVAILABLE" not in content:
        issues.append("Missing CORE_AVAILABLE flag for conditional logic")

    # Check for proper logging setup
    if "import logging" not in content and "get_service_logger" in content:
        issues.append("Missing logging fallback when Core logger not available")

    # Check for utility function fallbacks
    core_utils = ["utc_now", "generate_uuid", "generate_id"]
    for util in core_utils:
        if util in content and f"def {util}(" not in content:
            issues.append(f"Missing fallback implementation for {util}")

    quality = (
        "good"
        if len(issues) == 0
        else "needs_improvement" if len(issues) <= 2 else "poor"
    )

    return {"quality": quality, "issues": issues}


def generate_fallback_template(imports: list[str]) -> str:
    """Generate fallback template based on imported items"""

    template_parts = []

    # Base template
    template_parts.append(
        """# Import Core Module components
try:
    from ai_script_core import ("""
    )

    # Add imports
    for imp in sorted(imports):
        template_parts.append(f"        {imp},")

    template_parts.append(
        """    )
    CORE_AVAILABLE = True
    logger = get_service_logger("generation-service")
except (ImportError, RuntimeError):
    CORE_AVAILABLE = False
    import logging
    logger = logging.getLogger(__name__)

    # Fallback implementations"""
    )

    # Add fallback implementations for common utilities
    common_fallbacks = {
        "utc_now": '''
    def utc_now():
        """Fallback UTC timestamp"""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc)''',
        "generate_uuid": '''
    def generate_uuid():
        """Fallback UUID generation"""
        import uuid
        return str(uuid.uuid4())''',
        "generate_id": '''
    def generate_id():
        """Fallback ID generation"""
        import uuid
        return str(uuid.uuid4())[:8]''',
    }

    for imp in imports:
        if imp in common_fallbacks:
            template_parts.append(common_fallbacks[imp])

    return "\n".join(template_parts)


def main():
    """Main execution"""

    print("🔍 Analyzing ai_script_core import fallback patterns...")

    analyses = {}
    files_needing_improvement = []
    files_with_good_fallbacks = []
    files_with_errors = []

    # Analyze all target files
    for file_path in TARGET_FILES:
        full_path = os.path.join(os.getcwd(), file_path)
        analysis = analyze_import_patterns(full_path)
        analyses[file_path] = analysis

        if analysis["status"] == "error":
            files_with_errors.append(file_path)
            continue
        elif analysis["status"] == "file_not_found":
            continue

        if not analysis["patterns"]:
            continue  # No ai_script_core imports

        # Check fallback quality
        fallback_quality = check_existing_fallback_quality(analysis)
        analysis["fallback_quality"] = fallback_quality

        if fallback_quality["quality"] in ["none", "poor"]:
            files_needing_improvement.append(file_path)
        elif fallback_quality["quality"] == "needs_improvement":
            files_needing_improvement.append(file_path)
        else:
            files_with_good_fallbacks.append(file_path)

    # Print results
    print("\n📊 Analysis Results:")
    print(f"  Files with good fallbacks: {len(files_with_good_fallbacks)}")
    print(f"  Files needing improvement: {len(files_needing_improvement)}")
    print(f"  Files with errors: {len(files_with_errors)}")

    if files_with_good_fallbacks:
        print("\n✅ Files with good fallbacks:")
        for file_path in files_with_good_fallbacks:
            print(f"  • {file_path}")

    if files_needing_improvement:
        print("\n⚠️ Files needing fallback improvement:")
        for file_path in files_needing_improvement:
            analysis = analyses[file_path]
            quality = analysis.get("fallback_quality", {})
            print(f"  • {file_path}")
            for issue in quality.get("issues", []):
                print(f"    - {issue}")

    if files_with_errors:
        print("\n❌ Files with analysis errors:")
        for file_path in files_with_errors:
            analysis = analyses[file_path]
            print(f"  • {file_path}: {analysis.get('error', 'Unknown error')}")

    # Summary recommendations
    print("\n🎯 Recommendations:")

    if files_needing_improvement:
        print(f"  1. Improve fallback logic in {len(files_needing_improvement)} files")
        print(
            "  2. Ensure all files use try-except (ImportError, RuntimeError) pattern"
        )
        print("  3. Add CORE_AVAILABLE flags for conditional logic")
        print("  4. Implement proper logging fallbacks")
        print("  5. Add utility function fallbacks where needed")
    else:
        print("  ✅ All files have adequate fallback logic")

    return len(files_needing_improvement) == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
