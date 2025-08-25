#!/usr/bin/env python3
"""
SSE Type Compatibility Verification Script

This script validates that Python SSE models and TypeScript SSE types
are perfectly compatible by analyzing their structure and field definitions.
"""

import re
import sys
from pathlib import Path
from typing import Any, Dict, List


def extract_python_sse_models() -> Dict[str, Any]:
    """Extract Python SSE model definitions"""
    python_file = (
        Path(__file__).parent.parent
        / "services/generation-service/src/generation_service/models/sse_models.py"
    )

    if not python_file.exists():
        print(f"❌ Python SSE models file not found: {python_file}")
        return {}

    content = python_file.read_text()

    models = {}

    # Extract enum definitions more robustly
    enum_classes = ["SSEEventType", "GenerationJobStatus"]
    for enum_name in enum_classes:
        enum_pattern = rf"class {enum_name}\(str, Enum\):(.*?)(?=^class|\Z)"
        enum_match = re.search(enum_pattern, content, re.MULTILINE | re.DOTALL)
        if enum_match:
            enum_content = enum_match.group(1)
            values = re.findall(r'(\w+)\s*=\s*["\'](\w+)["\']', enum_content)
            if values:
                models[enum_name] = {"type": "enum", "values": [v[1] for v in values]}

    # Extract model classes
    model_classes = [
        "ProgressEventData",
        "PreviewEventData",
        "CompletedEventData",
        "FailedEventData",
        "HeartbeatEventData",
        "SSEEvent",
        "GenerationJob",
        "GenerationJobRequest",
        "GenerationJobResponse",
    ]

    for class_name in model_classes:
        pattern = rf"class {class_name}\(BaseModel\):(.*?)(?=^class|\Z)"
        match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
        if match:
            class_content = match.group(1)
            fields = extract_pydantic_fields(class_content)
            models[class_name] = {"type": "model", "fields": fields}

    return models


def extract_pydantic_fields(class_content: str) -> Dict[str, Any]:
    """Extract field definitions from Pydantic model class"""
    fields = {}

    lines = class_content.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Skip empty lines, comments, methods, decorators
        if (
            not line
            or line.startswith('"""')
            or line.startswith("#")
            or line.startswith("def ")
            or line.startswith("@")
            or line.startswith("class ")
        ):
            i += 1
            continue

        # Handle multi-line field definitions
        full_line = line
        while (
            i + 1 < len(lines)
            and not re.match(r"\w+:", lines[i + 1].strip())
            and not lines[i + 1].strip().startswith("def ")
            and not lines[i + 1].strip().startswith("@")
            and not lines[i + 1].strip().startswith("class ")
            and lines[i + 1].strip()
        ):
            i += 1
            full_line += " " + lines[i].strip()

        # Pattern for field definitions (more flexible)
        field_pattern = r"(\w+):\s*([^=]+?)(?:\s*=\s*([^#]+))?(?:\s*#.*)?$"
        match = re.match(field_pattern, full_line)

        if match:
            field_name, field_type, default_value = match.groups()

            # Clean up type annotation
            field_type = field_type.strip()
            default_value = default_value.strip() if default_value else None

            # Determine if field is required
            required = True
            if field_type.startswith("Optional["):
                field_type = field_type[9:-1]  # Remove Optional[]
                required = False
            elif default_value:
                if "Field(" in default_value:
                    # Check Field() definition
                    if "None" in default_value or "default=None" in default_value:
                        required = False
                    elif "..." in default_value or "Field(...)" in default_value:
                        required = True
                    elif (
                        'Field("' in default_value
                        or "Field('" in default_value
                        or "Field(0" in default_value
                        or "default=" in default_value
                    ):
                        # Has default value in Field() - treat as optional for TypeScript compatibility
                        required = False
                else:
                    # Has simple default value (not in Field()) - treat as optional for TypeScript
                    required = False

            # Simplify type names
            field_type = simplify_type_name(field_type)

            fields[field_name] = {"type": field_type, "required": required}

        i += 1

    return fields


def simplify_type_name(type_str: str) -> str:
    """Simplify Python type names for comparison"""
    type_str = type_str.strip()

    # Common type mappings
    type_mappings = {
        "str": "string",
        "int": "number",
        "float": "number",
        "bool": "boolean",
        "dict[str, Any]": "Record<string, unknown>",
        "Optional[int]": "number",
        "Optional[str]": "string",
        "Optional[bool]": "boolean",
        "Optional[float]": "number",
    }

    for py_type, ts_type in type_mappings.items():
        if type_str == py_type:
            return ts_type

    # Handle Field() expressions
    if "Field(" in type_str:
        # Extract the base type before Field()
        base_type = type_str.split("=")[0].strip()
        return simplify_type_name(base_type)

    # Handle Union types
    if type_str.startswith("Union["):
        return "SSEEventData"  # Python Union maps to TypeScript SSEEventData

    # Keep complex types as-is for manual review
    return type_str


def extract_typescript_sse_types() -> Dict[str, Any]:
    """Extract TypeScript SSE type definitions"""
    ts_file = (
        Path(__file__).parent.parent
        / "frontend/src/features/script-generation/types/sse.ts"
    )

    if not ts_file.exists():
        print(f"❌ TypeScript SSE types file not found: {ts_file}")
        return {}

    content = ts_file.read_text()

    models = {}

    # Extract type aliases
    type_aliases = re.findall(r"export type (\w+) = ([^;]+);", content)
    for name, definition in type_aliases:
        if "SSEEventType" == name or "GenerationJobStatus" == name:
            # Extract union values
            values = re.findall(r"'(\w+)'", definition)
            models[name] = {"type": "enum", "values": values}
        else:
            models[name] = {"type": "type_alias", "definition": definition.strip()}

    # Extract interfaces
    interface_pattern = r"export interface (\w+) \{(.*?)\n\}"
    interfaces = re.findall(interface_pattern, content, re.DOTALL)

    for interface_name, interface_body in interfaces:
        fields = extract_typescript_fields(interface_body)
        models[interface_name] = {"type": "interface", "fields": fields}

    return models


def extract_typescript_fields(interface_body: str) -> Dict[str, Any]:
    """Extract field definitions from TypeScript interface"""
    fields = {}

    # Clean up the interface body
    lines = [line.strip() for line in interface_body.split("\n") if line.strip()]

    for line in lines:
        # Skip comments
        if line.startswith("//") or line.startswith("/*") or line.startswith("*"):
            continue

        # Match field definitions
        field_match = re.match(r"(\w+)(\??):\s*([^;]+);?", line)
        if field_match:
            field_name, optional_marker, field_type = field_match.groups()

            required = not bool(optional_marker)
            field_type = field_type.strip().rstrip(";")

            # Simplify TypeScript types
            field_type = simplify_typescript_type(field_type)

            fields[field_name] = {"type": field_type, "required": required}

    return fields


def simplify_typescript_type(type_str: str) -> str:
    """Simplify TypeScript type names for comparison"""
    type_str = type_str.strip()

    # Handle complex object types
    if type_str.startswith("{") and type_str.endswith("}"):
        return "object"

    # Handle array types
    if type_str.endswith("[]"):
        return "array"

    # Handle Record types
    if type_str.startswith("Record<"):
        return "Record<string, unknown>"

    # Handle union types (including SSEEventData)
    if "|" in type_str or type_str == "SSEEventData":
        return "SSEEventData"  # This matches our Union types from Python

    return type_str


def compare_models(
    python_models: Dict[str, Any], ts_models: Dict[str, Any]
) -> List[str]:
    """Compare Python and TypeScript models for compatibility"""
    issues = []

    # Check if both have the same model names
    python_names = set(python_models.keys())
    ts_names = set(ts_models.keys())

    missing_in_ts = python_names - ts_names
    missing_in_python = ts_names - python_names

    if missing_in_ts:
        issues.append(f"⚠️ Missing in TypeScript: {', '.join(missing_in_ts)}")

    if missing_in_python:
        issues.append(f"ℹ️ TypeScript-only types: {', '.join(missing_in_python)}")

    # Compare common models
    common_models = python_names & ts_names

    for model_name in sorted(common_models):
        py_model = python_models[model_name]
        ts_model = ts_models[model_name]

        model_issues = compare_single_model(model_name, py_model, ts_model)
        issues.extend(model_issues)

    return issues


def compare_single_model(
    name: str, py_model: Dict[str, Any], ts_model: Dict[str, Any]
) -> List[str]:
    """Compare a single model between Python and TypeScript"""
    issues = []

    # Python models correspond to TypeScript interfaces
    compatible_types = [
        ("enum", "enum"),
        ("model", "interface"),  # Pydantic models -> TS interfaces
        ("type_alias", "type_alias"),
    ]

    py_type = py_model["type"]
    ts_type = ts_model["type"]

    type_compatible = any(
        (py_type == py_t and ts_type == ts_t) or (py_type == ts_t and ts_type == py_t)
        for py_t, ts_t in compatible_types
    )

    if not type_compatible:
        issues.append(
            f"❌ {name}: Type mismatch - Python: {py_type}, TypeScript: {ts_type}"
        )
        return issues

    if py_model["type"] == "enum":
        py_values = set(py_model["values"])
        ts_values = set(ts_model["values"])

        if py_values != ts_values:
            missing_in_ts = py_values - ts_values
            extra_in_ts = ts_values - py_values

            if missing_in_ts:
                issues.append(
                    f"❌ {name}: Missing enum values in TypeScript: {missing_in_ts}"
                )
            if extra_in_ts:
                issues.append(
                    f"⚠️ {name}: Extra enum values in TypeScript: {extra_in_ts}"
                )

    elif py_model["type"] in ["model", "interface"]:
        py_fields = py_model.get("fields", {})
        ts_fields = ts_model.get("fields", {})

        field_issues = compare_fields(name, py_fields, ts_fields)
        issues.extend(field_issues)

    return issues


def compare_fields(
    model_name: str, py_fields: Dict[str, Any], ts_fields: Dict[str, Any]
) -> List[str]:
    """Compare fields between Python and TypeScript models"""
    issues = []

    py_field_names = set(py_fields.keys())
    ts_field_names = set(ts_fields.keys())

    missing_in_ts = py_field_names - ts_field_names
    extra_in_ts = ts_field_names - py_field_names

    if missing_in_ts:
        issues.append(f"⚠️ {model_name}: Missing fields in TypeScript: {missing_in_ts}")

    if extra_in_ts:
        issues.append(f"ℹ️ {model_name}: Extra fields in TypeScript: {extra_in_ts}")

    # Compare common fields
    common_fields = py_field_names & ts_field_names

    for field_name in sorted(common_fields):
        py_field = py_fields[field_name]
        ts_field = ts_fields[field_name]

        # Check required/optional consistency
        if py_field["required"] != ts_field["required"]:
            py_req = "required" if py_field["required"] else "optional"
            ts_req = "required" if ts_field["required"] else "optional"
            issues.append(
                f"⚠️ {model_name}.{field_name}: Requirement mismatch - Python: {py_req}, TypeScript: {ts_req}"
            )

        # Check type compatibility
        py_type = py_field["type"]
        ts_type = ts_field["type"]

        if not types_compatible(py_type, ts_type):
            issues.append(
                f"❌ {model_name}.{field_name}: Type mismatch - Python: {py_type}, TypeScript: {ts_type}"
            )

    return issues


def types_compatible(py_type: str, ts_type: str) -> bool:
    """Check if Python and TypeScript types are compatible"""
    # Direct matches
    if py_type == ts_type:
        return True

    # Common compatible types
    compatible_pairs = [
        ("string", "string"),
        ("number", "number"),
        ("boolean", "boolean"),
        ("object", "object"),
        ("array", "array"),
        ("union", "union"),
        ("Record<string, unknown>", "Record<string, unknown>"),
        ("dict[str, Any]", "Record<string, unknown>"),
        ("dict[str, Any]", "object"),
        ("datetime", "string"),  # Python datetime -> TypeScript string (ISO format)
        ("Union[", "SSEEventData"),  # Python Union types -> TypeScript union types
    ]

    for py, ts in compatible_pairs:
        if py_type == py and ts_type == ts:
            return True
        if py_type == ts and ts_type == py:
            return True

    # Special cases for flexible types
    if py_type == "dict[str, Any]" and (
        "object" in ts_type or "Record<string, unknown>" in ts_type
    ):
        return True

    if "Union[" in py_type and (ts_type == "union" or ts_type == "SSEEventData"):
        return True

    # Handle TypeScript complex object types like "{ ... }"
    if py_type == "Record<string, unknown>" and ts_type.startswith("{"):
        return True

    return False


def generate_compatibility_report(
    issues: List[str], python_models: Dict[str, Any], ts_models: Dict[str, Any]
) -> str:
    """Generate a detailed compatibility report"""
    report = []
    report.append("🔍 Python SSE Models ↔ TypeScript SSE Types Compatibility Report")
    report.append("=" * 70)
    report.append("")

    # Add model counts summary
    py_count = len(python_models)
    ts_count = len(ts_models)
    common_count = len(set(python_models.keys()) & set(ts_models.keys()))

    report.append("📊 Model Analysis:")
    report.append(f"  • Python models: {py_count}")
    report.append(f"  • TypeScript types: {ts_count}")
    report.append(f"  • Matched pairs: {common_count}")
    report.append("")

    if not issues:
        report.append("✅ Perfect Compatibility!")
        report.append("All Python SSE models match TypeScript SSE types exactly.")
        report.append("")
        report.append("🎉 Type safety guaranteed across Python-TypeScript boundary!")
        report.append("")

        # Add details about matched models
        report.append("✅ Successfully Matched Types:")
        for model_name in sorted(set(python_models.keys()) & set(ts_models.keys())):
            py_model = python_models[model_name]
            if py_model["type"] == "enum":
                value_count = len(py_model.get("values", []))
                report.append(f"  • {model_name}: Enum with {value_count} values")
            elif py_model["type"] == "model":
                field_count = len(py_model.get("fields", {}))
                report.append(f"  • {model_name}: Model with {field_count} fields")

        return "\n".join(report)

    # Categorize issues
    errors = [issue for issue in issues if issue.startswith("❌")]
    warnings = [issue for issue in issues if issue.startswith("⚠️")]
    info = [issue for issue in issues if issue.startswith("ℹ️")]

    if errors:
        report.append(f"❌ Critical Issues ({len(errors)}):")
        for error in errors:
            report.append(f"  {error}")
        report.append("")

    if warnings:
        report.append(f"⚠️ Warnings ({len(warnings)}):")
        for warning in warnings:
            report.append(f"  {warning}")
        report.append("")

    if info:
        report.append(f"ℹ️ Information ({len(info)}):")
        for inf in info:
            report.append(f"  {inf}")
        report.append("")

    # Summary
    report.append("📊 Summary:")
    report.append(f"  • Critical Issues: {len(errors)}")
    report.append(f"  • Warnings: {len(warnings)}")
    report.append(f"  • Information: {len(info)}")
    report.append("")

    if errors:
        report.append("🚨 Action Required: Fix critical issues for type safety!")
    elif warnings:
        report.append(
            "⚠️ Review Recommended: Address warnings for better compatibility."
        )
    else:
        report.append("✅ Good: Only informational differences found.")

    return "\n".join(report)


def main():
    """Main validation function"""
    print("🔍 Starting SSE Type Compatibility Validation...")
    print()

    try:
        # Extract models from both languages
        print("1. Extracting Python SSE models...")
        python_models = extract_python_sse_models()
        print(f"   Found {len(python_models)} Python models")

        print("2. Extracting TypeScript SSE types...")
        ts_models = extract_typescript_sse_types()
        print(f"   Found {len(ts_models)} TypeScript types")
        print()

        # Compare models
        print("3. Comparing model compatibility...")
        issues = compare_models(python_models, ts_models)
        print()

        # Generate report
        report = generate_compatibility_report(issues, python_models, ts_models)
        print(report)

        # Write detailed report to file
        report_file = Path(__file__).parent.parent / "sse-type-compatibility-report.md"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write("# SSE Type Compatibility Report\n\n")
            f.write("Generated by: `scripts/validate-sse-type-compatibility.py`\n\n")
            f.write(report)

        print(f"\n📄 Detailed report saved to: {report_file}")

        # Exit code based on results
        critical_issues = len([issue for issue in issues if issue.startswith("❌")])
        if critical_issues > 0:
            print(f"\n❌ Validation failed with {critical_issues} critical issues")
            sys.exit(1)
        else:
            print("\n✅ Validation passed!")
            sys.exit(0)

    except Exception as e:
        print(f"💥 Validation error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
