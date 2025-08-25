#!/usr/bin/env python3
"""
Test entrypoint resolution and structure cleanup
"""

import sys
from pathlib import Path


def test_entrypoint_resolution():
    """Test that all entrypoints work correctly"""

    print("🔍 Testing Generation Service entrypoint resolution...")

    current_dir = Path(__file__).parent.parent
    src_path = current_dir / "src"

    # Test 1: Module imports without conflicts
    print("\n1. Testing module imports...")

    sys.path.insert(0, str(src_path))

    try:
        # Test config_loader import (renamed from config.py)
        import generation_service.config_loader

        print("   ✓ generation_service.config_loader imported successfully")

        # Test main app import
        from generation_service.main import app

        print("   ✓ generation_service.main:app imported successfully")

        # Test that config settings work
        from generation_service.config_loader import settings

        print(f"   ✓ Settings loaded: {settings.SERVICE_NAME}")

        # Test API imports
        from generation_service.api import generate, health, rag

        print("   ✓ API modules imported successfully")

    except ImportError as e:
        print(f"   ❌ Import failed: {e}")
        return False

    # Test 2: Check for file conflicts
    print("\n2. Checking for file naming conflicts...")

    conflicts = []

    # Check that config.py is renamed
    if (src_path / "generation_service" / "config.py").exists():
        conflicts.append("config.py still exists (should be config_loader.py)")

    if not (src_path / "generation_service" / "config_loader.py").exists():
        conflicts.append("config_loader.py not found")

    # Check config package exists
    if not (src_path / "generation_service" / "config" / "__init__.py").exists():
        conflicts.append("config package missing")

    if conflicts:
        for conflict in conflicts:
            print(f"   ❌ {conflict}")
        return False
    else:
        print("   ✓ No file naming conflicts found")

    # Test 3: Docker entrypoint validation
    print("\n3. Testing Docker entrypoint configuration...")

    dockerfile_path = current_dir / "Dockerfile"

    if not dockerfile_path.exists():
        print("   ❌ Dockerfile not found")
        return False

    with open(dockerfile_path) as f:
        dockerfile_content = f.read()

    docker_checks = []

    # Check CMD uses uvicorn directly
    if 'CMD ["uvicorn", "generation_service.main:app"' in dockerfile_content:
        docker_checks.append("✓ CMD uses uvicorn directly")
    else:
        docker_checks.append("❌ CMD not using uvicorn directly")

    # Check PYTHONPATH includes src
    if "PYTHONPATH=/app/generation-service/src" in dockerfile_content:
        docker_checks.append("✓ PYTHONPATH includes src directory")
    else:
        docker_checks.append("❌ PYTHONPATH missing src directory")

    for check in docker_checks:
        print(f"   {check}")

    docker_success = all(check.startswith("✓") for check in docker_checks)

    # Test 4: Root main.py wrapper
    print("\n4. Testing root main.py wrapper...")

    root_main_path = current_dir / "main.py"

    if not root_main_path.exists():
        print("   ❌ Root main.py not found")
        return False

    with open(root_main_path) as f:
        main_content = f.read()

    main_checks = []

    if "Entry Point Wrapper" in main_content:
        main_checks.append("✓ Root main.py is a wrapper")
    else:
        main_checks.append("❌ Root main.py not converted to wrapper")

    if "generation_service.main:app" in main_content:
        main_checks.append("✓ Wrapper delegates to correct module")
    else:
        main_checks.append("❌ Wrapper not delegating correctly")

    for check in main_checks:
        print(f"   {check}")

    main_success = all(check.startswith("✓") for check in main_checks)

    # Test 5: Dependencies check
    print("\n5. Checking added dependencies...")

    requirements_path = current_dir / "requirements.txt"

    if not requirements_path.exists():
        print("   ❌ requirements.txt not found")
        return False

    with open(requirements_path) as f:
        requirements_content = f.read()

    dep_checks = []

    if "psutil>=5.9.0" in requirements_content:
        dep_checks.append("✓ psutil dependency added")
    else:
        dep_checks.append("❌ psutil dependency missing")

    if "aiohttp>=3.9.0" in requirements_content:
        dep_checks.append("✓ aiohttp dependency added")
    else:
        dep_checks.append("❌ aiohttp dependency missing")

    for check in dep_checks:
        print(f"   {check}")

    deps_success = all(check.startswith("✓") for check in dep_checks)

    # Test 6: Module structure validation
    print("\n6. Validating module structure...")

    structure_checks = []

    critical_paths = [
        "src/generation_service/__init__.py",
        "src/generation_service/main.py",
        "src/generation_service/config_loader.py",
        "src/generation_service/config/__init__.py",
        "src/generation_service/api/__init__.py",
        "src/generation_service/models/__init__.py",
    ]

    for path in critical_paths:
        full_path = current_dir / path
        if full_path.exists():
            structure_checks.append(f"✓ {path}")
        else:
            structure_checks.append(f"❌ {path} missing")

    for check in structure_checks:
        print(f"   {check}")

    structure_success = all(check.startswith("✓") for check in structure_checks)

    # Summary
    print("\n📊 Entrypoint Resolution Test Results:")
    print(f"  Module imports: {'✅' if True else '❌'}")
    print(f"  File conflicts: {'✅' if len(conflicts) == 0 else '❌'}")
    print(f"  Docker config: {'✅' if docker_success else '❌'}")
    print(f"  Root main.py: {'✅' if main_success else '❌'}")
    print(f"  Dependencies: {'✅' if deps_success else '❌'}")
    print(f"  Structure: {'✅' if structure_success else '❌'}")

    overall_success = (
        len(conflicts) == 0
        and docker_success
        and main_success
        and deps_success
        and structure_success
    )

    if overall_success:
        print("\n🎉 Entrypoint resolution PASSED!")
        print("✅ Single unified entrypoint: uvicorn generation_service.main:app")
        print("✅ No file naming conflicts")
        print("✅ Clean module structure")
        print("✅ Docker configuration optimized")
    else:
        print("\n⚠️ Some entrypoint issues remain")
        print("Manual review recommended")

    return overall_success


if __name__ == "__main__":
    success = test_entrypoint_resolution()
    sys.exit(0 if success else 1)
