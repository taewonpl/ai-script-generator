#!/usr/bin/env python3
"""
Version Management Script for AI Script Core

Automates version bumping across pyproject.toml and package files.
"""

import argparse
import re
import sys
from pathlib import Path


class VersionManager:
    """Manages version bumping for the project"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.pyproject_path = project_root / "pyproject.toml"
        self.package_init_path = project_root / "src" / "ai_script_core" / "__init__.py"

    def get_current_version(self) -> str | None:
        """Get current version from pyproject.toml"""
        if not self.pyproject_path.exists():
            return None

        with open(self.pyproject_path) as f:
            content = f.read()

        version_match = re.search(r'version\s*=\s*"([^"]+)"', content)
        return version_match.group(1) if version_match else None

    def parse_version(self, version: str) -> tuple[int, int, int]:
        """Parse version string into major, minor, patch components"""
        parts = version.split(".")
        if len(parts) != 3:
            raise ValueError(f"Invalid version format: {version}")

        try:
            return int(parts[0]), int(parts[1]), int(parts[2])
        except ValueError:
            raise ValueError(f"Invalid version format: {version}") from e

    def bump_version(self, current: str, bump_type: str) -> str:
        """Bump version based on type (major, minor, patch)"""
        major, minor, patch = self.parse_version(current)

        if bump_type == "major":
            return f"{major + 1}.0.0"
        elif bump_type == "minor":
            return f"{major}.{minor + 1}.0"
        elif bump_type == "patch":
            return f"{major}.{minor}.{patch + 1}"
        else:
            raise ValueError(f"Invalid bump type: {bump_type}")

    def update_pyproject_toml(self, new_version: str) -> None:
        """Update version in pyproject.toml"""
        with open(self.pyproject_path) as f:
            content = f.read()

        new_content = re.sub(
            r'version\s*=\s*"[^"]+"', f'version = "{new_version}"', content
        )

        with open(self.pyproject_path, "w") as f:
            f.write(new_content)

    def update_package_init(self, new_version: str) -> None:
        """Update version in package __init__.py"""
        with open(self.package_init_path) as f:
            content = f.read()

        new_content = re.sub(
            r'__version__\s*=\s*"[^"]+"', f'__version__ = "{new_version}"', content
        )

        with open(self.package_init_path, "w") as f:
            f.write(new_content)

    def update_version(self, new_version: str) -> None:
        """Update version in all relevant files"""
        print(f"Updating version to {new_version}...")

        # Update pyproject.toml
        self.update_pyproject_toml(new_version)
        print(f"✅ Updated {self.pyproject_path}")

        # Update package __init__.py
        self.update_package_init(new_version)
        print(f"✅ Updated {self.package_init_path}")

    def validate_version_consistency(self) -> bool:
        """Validate that versions are consistent across files"""
        # Get version from pyproject.toml
        pyproject_version = self.get_current_version()

        # Get version from package __init__.py
        with open(self.package_init_path) as f:
            init_content = f.read()

        init_match = re.search(r'__version__\s*=\s*"([^"]+)"', init_content)
        init_version = init_match.group(1) if init_match else None

        if pyproject_version != init_version:
            print("❌ Version mismatch:")
            print(f"   pyproject.toml: {pyproject_version}")
            print(f"   __init__.py: {init_version}")
            return False

        print(f"✅ Version consistency check passed: {pyproject_version}")
        return True


def main():
    parser = argparse.ArgumentParser(description="Manage project version")
    parser.add_argument(
        "action", choices=["get", "bump", "set", "check"], help="Action to perform"
    )
    parser.add_argument(
        "--type",
        choices=["major", "minor", "patch"],
        help="Bump type (for bump action)",
    )
    parser.add_argument("--version", help="Specific version to set (for set action)")

    args = parser.parse_args()

    # Get project root (parent of scripts directory)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    manager = VersionManager(project_root)

    if args.action == "get":
        current = manager.get_current_version()
        if current:
            print(current)
        else:
            print("Version not found", file=sys.stderr)
            sys.exit(1)

    elif args.action == "check":
        if not manager.validate_version_consistency():
            sys.exit(1)

    elif args.action == "bump":
        if not args.type:
            print("--type is required for bump action", file=sys.stderr)
            sys.exit(1)

        current = manager.get_current_version()
        if not current:
            print("Current version not found", file=sys.stderr)
            sys.exit(1)

        try:
            new_version = manager.bump_version(current, args.type)
            print(f"Bumping version from {current} to {new_version}")
            manager.update_version(new_version)
            print(f"🎉 Successfully bumped version to {new_version}")
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.action == "set":
        if not args.version:
            print("--version is required for set action", file=sys.stderr)
            sys.exit(1)

        try:
            # Validate version format
            manager.parse_version(args.version)
            manager.update_version(args.version)
            print(f"🎉 Successfully set version to {args.version}")
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
