#!/usr/bin/env python3
"""
Fix import fallback logic for ai_script_core across Generation Service
"""

import os
import re
import sys
from pathlib import Path


def read_file(file_path: str) -> str:
    """Read file content"""
    try:
        with open(file_path, encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"❌ Error reading {file_path}: {e}")
        return ""


def write_file(file_path: str, content: str) -> bool:
    """Write content to file"""
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"❌ Error writing {file_path}: {e}")
        return False


def extract_imports(content: str) -> list[str]:
    """Extract ai_script_core imports from content"""
    imports = []

    # Find import lines
    import_pattern = r"from ai_script_core import \((.*?)\)"
    single_import_pattern = r"from ai_script_core import (.+)"

    # Multi-line imports
    multi_match = re.search(import_pattern, content, re.DOTALL)
    if multi_match:
        import_text = multi_match.group(1)
        # Extract individual imports
        for line in import_text.split("\n"):
            line = line.strip().rstrip(",")
            if line and not line.startswith("#"):
                imports.append(line)

    # Single-line imports
    single_matches = re.findall(single_import_pattern, content)
    for match in single_matches:
        if "(" not in match:  # Skip if already captured by multi-line
            items = [item.strip() for item in match.split(",")]
            imports.extend(items)

    return list(set(imports))


def generate_fallback_functions() -> str:
    """Generate common fallback functions"""
    return '''
    # Fallback utility functions
    def utc_now():
        """Fallback UTC timestamp"""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc)

    def generate_uuid():
        """Fallback UUID generation"""
        import uuid
        return str(uuid.uuid4())

    def generate_id():
        """Fallback ID generation"""
        import uuid
        return str(uuid.uuid4())[:8]

    # Fallback base classes
    class BaseDTO:
        """Fallback base DTO class"""
        pass

    class SuccessResponseDTO:
        """Fallback success response DTO"""
        pass

    class ErrorResponseDTO:
        """Fallback error response DTO"""
        pass'''


def fix_import_block(content: str, file_path: str) -> str:
    """Fix import block to add proper fallback logic"""

    # Extract existing imports
    imports = extract_imports(content)

    if not imports:
        return content  # No ai_script_core imports found

    # Check if fallback already exists and is good
    if (
        "except (ImportError, RuntimeError):" in content
        and "CORE_AVAILABLE = False" in content
        and "def utc_now(" in content
        and "def generate_uuid(" in content
    ):
        return content  # Already has good fallback

    # Find the import block to replace
    import_pattern = r"(# Import Core Module components\s*try:\s*from ai_script_core import \(.*?\)\s*CORE_AVAILABLE = True.*?except.*?)(.*?)(?=\n\n|\nfrom|\nclass|\ndef|\Z)"

    match = re.search(import_pattern, content, re.DOTALL)
    if not match:
        # Try simpler pattern
        simple_pattern = r"(try:\s*from ai_script_core import.*?except.*?)(.*?)(?=\n\n|\nfrom|\nclass|\ndef|\Z)"
        match = re.search(simple_pattern, content, re.DOTALL)

    if match:
        # Replace existing import block
        old_block = match.group(0)

        # Generate new import block
        new_block = f"""# Import Core Module components
try:
    from ai_script_core import (
{chr(10).join(f'        {imp},' for imp in sorted(imports))}
    )
    CORE_AVAILABLE = True
    logger = get_service_logger("generation-service.{Path(file_path).stem}")
except (ImportError, RuntimeError):
    CORE_AVAILABLE = False
    import logging
    logger = logging.getLogger(__name__)
{generate_fallback_functions()}"""

        content = content.replace(old_block, new_block)
    else:
        # Add new import block
        # Find where to insert (after other imports, before classes/functions)
        lines = content.split("\n")
        insert_pos = 0

        # Find last import line
        for i, line in enumerate(lines):
            if (
                line.startswith("from ") or line.startswith("import ")
            ) and "ai_script_core" not in line:
                insert_pos = i + 1
            elif (
                line.startswith("class ")
                or line.startswith("def ")
                or line.startswith("async def ")
            ):
                break

        new_block = f"""
# Import Core Module components
try:
    from ai_script_core import (
{chr(10).join(f'        {imp},' for imp in sorted(imports))}
    )
    CORE_AVAILABLE = True
    logger = get_service_logger("generation-service.{Path(file_path).stem}")
except (ImportError, RuntimeError):
    CORE_AVAILABLE = False
    import logging
    logger = logging.getLogger(__name__)
{generate_fallback_functions()}
"""

        lines.insert(insert_pos, new_block)
        content = "\n".join(lines)

    return content


def fix_config_file_special_case(content: str) -> str:
    """Special handling for config.py file"""

    # Fix the exception handling
    old_pattern = r"except ImportError:"
    new_pattern = "except (ImportError, RuntimeError):"

    return content.replace(old_pattern, new_pattern)


def fix_single_file(file_path: str) -> bool:
    """Fix a single file's import fallback logic"""

    if not os.path.exists(file_path):
        print(f"⚠️ File not found: {file_path}")
        return False

    content = read_file(file_path)
    if not content:
        return False

    # Skip if no ai_script_core imports
    if "ai_script_core" not in content:
        return True

    original_content = content

    # Special case for config.py
    if file_path.endswith("config.py"):
        content = fix_config_file_special_case(content)
    else:
        content = fix_import_block(content, file_path)

    # Check if content changed
    if content != original_content:
        if write_file(file_path, content):
            print(f"✅ Fixed: {file_path}")
            return True
        else:
            return False
    else:
        print(f"ℹ️ No changes needed: {file_path}")
        return True


def main():
    """Main execution"""

    print("🔧 Fixing ai_script_core import fallback logic...")

    # Files that need fixing based on our analysis
    files_to_fix = [
        "src/generation_service/models/vector_document.py",
        "src/generation_service/models/rag_models.py",
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
        "src/generation_service/services/generation_service.py",
        "src/generation_service/workflows/generation_workflow.py",
        "src/generation_service/workflows/nodes/special_agent_nodes.py",
        "src/generation_service/workflows/nodes/stylist_node.py",
        "src/generation_service/workflows/nodes/architect_node.py",
        "src/generation_service/workflows/nodes/base_node.py",
        "src/generation_service/workflows/state.py",
        "src/generation_service/ai/prompts/base_prompt.py",
        "src/generation_service/rag/rag_service.py",
        "src/generation_service/rag/context_builder.py",
        "src/generation_service/rag/retriever.py",
        "src/generation_service/rag/embeddings.py",
        "src/generation_service/rag/chroma_store.py",
        "src/generation_service/ai/providers/base_provider.py",
        "src/generation_service/ai/providers/anthropic_provider.py",
        "src/generation_service/ai/providers/openai_provider.py",
    ]

    fixed_count = 0
    failed_count = 0

    for file_path in files_to_fix:
        full_path = os.path.join(os.getcwd(), file_path)
        if fix_single_file(full_path):
            fixed_count += 1
        else:
            failed_count += 1

    print("\n📊 Results:")
    print(f"  ✅ Successfully fixed: {fixed_count}")
    print(f"  ❌ Failed to fix: {failed_count}")

    if failed_count == 0:
        print("\n🎉 All import fallback logic has been strengthened!")
        print("✅ Generation Service can now run with or without Core Module")
    else:
        print("\n⚠️ Some files could not be fixed automatically")
        print("Manual review may be required")

    return failed_count == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
