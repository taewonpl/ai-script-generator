#!/usr/bin/env python3
"""
Fix Python 3.9 type union compatibility issues in generation-service
Convert Type | None syntax to Optional[Type]
"""

import os
import subprocess


def fix_type_unions_in_directory():
    """Fix type union syntax in all Python files"""

    # Change to generation-service directory
    os.chdir(
        "/Users/al02475493/Documents/ai-script-generator-v3/services/generation-service"
    )

    print("🔧 Fixing Python 3.9 type union compatibility in generation-service...")

    # Fix Type | None patterns
    patterns_to_fix = [
        (r'r"([A-Za-z_][A-Za-z0-9_]*) \| None"', r"Optional[\1]"),
        (r'r"([A-Za-z_][A-Za-z0-9_]*\[[^\]]+\]) \| None"', r"Optional[\1]"),
        (r'r"None \| ([A-Za-z_][A-Za-z0-9_]*)"', r"Optional[\1]"),
        (r'r"None \| ([A-Za-z_][A-Za-z0-9_]*\[[^\]]+\])"', r"Optional[\1]"),
        (r'r"(list\[[^\]]+\]) \| None"', r"Optional[\1]"),
        (r'r"(dict\[[^\]]+\]) \| None"', r"Optional[\1]"),
        (r'r"(tuple\[[^\]]+\]) \| None"', r"Optional[\1]"),
        (r'r"(Any) \| None"', r"Optional[\1]"),
        (r'r"None \| (Any)"', r"Optional[\1]"),
        # Complex union patterns
        (
            r'r"([A-Za-z_][A-Za-z0-9_]*) \| ([A-Za-z_][A-Za-z0-9_]*) \| None"',
            r"Optional[Union[\1, \2]]",
        ),
        (r'r"([A-Za-z_][A-Za-z0-9_]*) \| ([A-Za-z_][A-Za-z0-9_]*)"', r"Union[\1, \2]"),
    ]

    # Run sed commands to fix type unions
    commands = [
        # Fix basic Type | None patterns
        "find src -name '*.py' -exec sed -i '' 's/\\([A-Za-z_][A-Za-z0-9_]*\\) | None/Optional[\\1]/g' {} \\;",
        "find src -name '*.py' -exec sed -i '' 's/None | \\([A-Za-z_][A-Za-z0-9_]*\\)/Optional[\\1]/g' {} \\;",
        # Fix complex type patterns
        "find src -name '*.py' -exec sed -i '' 's/\\(list\\[[^]]*\\]\\) | None/Optional[\\1]/g' {} \\;",
        "find src -name '*.py' -exec sed -i '' 's/\\(dict\\[[^]]*\\]\\) | None/Optional[\\1]/g' {} \\;",
        "find src -name '*.py' -exec sed -i '' 's/\\(tuple\\[[^]]*\\]\\) | None/Optional[\\1]/g' {} \\;",
        "find src -name '*.py' -exec sed -i '' 's/Any | None/Optional[Any]/g' {} \\;",
        "find src -name '*.py' -exec sed -i '' 's/None | Any/Optional[Any]/g' {} \\;",
        # Fix Union patterns for non-Optional cases
        "find src -name '*.py' -exec sed -i '' 's/\\([A-Za-z_][A-Za-z0-9_]*\\) | \\([A-Za-z_][A-Za-z0-9_]*\\)\\([^|]*\\)$/Union[\\1, \\2]\\3/g' {} \\;",
    ]

    for cmd in commands:
        print(f"Running: {cmd}")
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Warning: Command failed: {result.stderr}")
        except Exception as e:
            print(f"Error running command: {e}")

    # Add missing imports
    print("\n🔧 Adding missing imports...")

    # Find files that use Optional but don't import it
    find_and_fix_imports()

    print("✅ Python 3.9 type union fixes completed!")


def find_and_fix_imports():
    """Add missing Optional and Union imports to files that need them"""

    import_commands = [
        # Add Optional import to files that use it but don't import it
        """find src -name '*.py' -exec sh -c '
            if grep -q "Optional\\[" "$1" && ! grep -q "from typing import.*Optional" "$1"; then
                sed -i "" "s/from typing import/from typing import Optional,/" "$1"
            fi
        ' _ {} \\;""",
        # Add Union import to files that use it but don't import it
        """find src -name '*.py' -exec sh -c '
            if grep -q "Union\\[" "$1" && ! grep -q "from typing import.*Union" "$1"; then
                sed -i "" "s/from typing import/from typing import Union,/" "$1"
            fi
        ' _ {} \\;""",
        # Clean up duplicate commas in imports
        "find src -name '*.py' -exec sed -i '' 's/from typing import \\([^,]*\\),, /from typing import \\1, /g' {} \\;",
        "find src -name '*.py' -exec sed -i '' 's/from typing import \\([^,]*\\),,/from typing import \\1,/g' {} \\;",
        "find src -name '*.py' -exec sed -i '' 's/, ,/, /g' {} \\;",
        "find src -name '*.py' -exec sed -i '' 's/,,/,/g' {} \\;",
    ]

    for cmd in import_commands:
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Warning: Import command failed: {result.stderr}")
        except Exception as e:
            print(f"Error running import command: {e}")


if __name__ == "__main__":
    fix_type_unions_in_directory()
