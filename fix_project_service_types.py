#!/usr/bin/env python3
"""
Script to fix Python 3.9 type union compatibility issues in project-service
Converts `Type | None` to `Optional[Type]` and adds necessary imports
"""

import re
from pathlib import Path

# Map of type unions to Optional equivalents
TYPE_PATTERNS = [
    (r"\bstr \| None\b", "Optional[str]"),
    (r"\bint \| None\b", "Optional[int]"),
    (r"\bbool \| None\b", "Optional[bool]"),
    (r"\bfloat \| None\b", "Optional[float]"),
    (r"\bdict\[([^\]]+)\] \| None\b", r"Optional[dict[\1]]"),
    (r"\blist\[([^\]]+)\] \| None\b", r"Optional[list[\1]]"),
    (r"\btuple\[([^\]]+)\] \| None\b", r"Optional[tuple[\1]]"),
    (r"\bAny \| None\b", "Optional[Any]"),
    # Model types
    (r"\bSession \| None\b", "Optional[Session]"),
    (r"\bProject \| None\b", "Optional[Project]"),
    (r"\bEpisode \| None\b", "Optional[Episode]"),
]


def fix_type_unions_in_file(file_path: Path):
    """Fix type union syntax in a single file"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # Apply type pattern replacements
        for pattern, replacement in TYPE_PATTERNS:
            content = re.sub(pattern, replacement, content)

        # Check if we need to add Optional import
        if (
            "Optional[" in content
            and "Optional"
            not in re.findall(r"from typing import ([^\\n]+)", content)[0]
            if re.findall(r"from typing import ([^\\n]+)", content)
            else True
        ):
            # Add Optional to existing typing import
            typing_import_match = re.search(r"from typing import ([^\\n]+)", content)
            if typing_import_match:
                existing_imports = typing_import_match.group(1)
                if "Optional" not in existing_imports:
                    new_imports = existing_imports.rstrip() + ", Optional"
                    content = content.replace(
                        f"from typing import {existing_imports}",
                        f"from typing import {new_imports}",
                    )
            else:
                # Add new typing import at the top
                if "from typing import" not in content and "Optional[" in content:
                    # Find the right place to insert the import
                    lines = content.split("\\n")
                    insert_idx = 0

                    # Find imports section
                    for i, line in enumerate(lines):
                        if line.startswith("import ") or line.startswith("from "):
                            insert_idx = i
                        elif line.startswith("from ") and insert_idx < i:
                            insert_idx = i

                    # Insert after existing imports
                    if insert_idx > 0:
                        lines.insert(insert_idx + 1, "from typing import Optional")
                    else:
                        lines.insert(0, "from typing import Optional")

                    content = "\\n".join(lines)

        # Only write if content changed
        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Fixed: {file_path}")
            return True
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

    return False


def main():
    """Fix all Python files in project-service"""
    project_service_path = Path(
        "/Users/al02475493/Documents/ai-script-generator-v3/services/project-service/src"
    )

    if not project_service_path.exists():
        print("Project service path not found")
        return

    files_fixed = 0
    total_files = 0

    for py_file in project_service_path.rglob("*.py"):
        total_files += 1
        if fix_type_unions_in_file(py_file):
            files_fixed += 1

    print(f"\\nFixed {files_fixed} out of {total_files} Python files")


if __name__ == "__main__":
    main()
