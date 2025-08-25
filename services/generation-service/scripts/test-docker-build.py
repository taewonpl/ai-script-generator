#!/usr/bin/env python3
"""
Test Docker build resolution and validation
"""

import sys
from pathlib import Path


def test_docker_build_resolution():
    """Test Docker build configuration and resolution"""

    print("🔍 Testing Generation Service Docker build resolution...")

    current_dir = Path(__file__).parent.parent

    # Test 1: Dockerfile existence and Core Module dependency removal
    print("\n1. Testing Dockerfile configuration...")

    dockerfile_checks = []

    # Check root Dockerfile
    root_dockerfile = current_dir / "Dockerfile"
    if root_dockerfile.exists():
        with open(root_dockerfile) as f:
            content = f.read()

        # Check for Core Module copy issues
        if "COPY ../../shared/core" in content:
            dockerfile_checks.append(
                "❌ Root Dockerfile contains problematic Core Module copy"
            )
        else:
            dockerfile_checks.append(
                "✅ Root Dockerfile free from Core Module copy issues"
            )

        # Check for multi-stage build
        if "FROM python:3.11-slim as builder" in content:
            dockerfile_checks.append("✅ Root Dockerfile uses multi-stage build")
        else:
            dockerfile_checks.append("❌ Root Dockerfile not using multi-stage build")

        # Check for security features
        if "USER generation" in content:
            dockerfile_checks.append(
                "✅ Root Dockerfile includes security (non-root user)"
            )
        else:
            dockerfile_checks.append("❌ Root Dockerfile missing security features")

        # Check for unified data paths
        if "/app/data/chroma" in content and "/app/data/vectors" in content:
            dockerfile_checks.append("✅ Root Dockerfile uses unified data paths")
        else:
            dockerfile_checks.append("❌ Root Dockerfile missing unified data paths")

        # Check for correct port
        if "EXPOSE 8002" in content:
            dockerfile_checks.append("✅ Root Dockerfile exposes correct port (8002)")
        else:
            dockerfile_checks.append("❌ Root Dockerfile not exposing port 8002")

        # Check for correct entrypoint
        if "generation_service.main:app" in content:
            dockerfile_checks.append("✅ Root Dockerfile uses correct entrypoint")
        else:
            dockerfile_checks.append("❌ Root Dockerfile incorrect entrypoint")
    else:
        dockerfile_checks.append("❌ Root Dockerfile not found")

    for check in dockerfile_checks:
        print(f"   {check}")

    # Test 2: Docker Compose configuration
    print("\n2. Testing Docker Compose configuration...")

    compose_checks = []

    # Development compose
    dev_compose = current_dir / "docker" / "docker-compose.yml"
    if dev_compose.exists():
        with open(dev_compose) as f:
            dev_content = f.read()

        if "dockerfile: Dockerfile" in dev_content:
            compose_checks.append("✅ Development compose uses root Dockerfile")
        else:
            compose_checks.append("❌ Development compose not using root Dockerfile")

        if "8002:8002" in dev_content:
            compose_checks.append("✅ Development compose uses correct port mapping")
        else:
            compose_checks.append("❌ Development compose incorrect port mapping")

        if "generation-data:/app/data" in dev_content:
            compose_checks.append("✅ Development compose uses unified data volume")
        else:
            compose_checks.append("❌ Development compose missing unified data volume")
    else:
        compose_checks.append("❌ Development docker-compose.yml not found")

    # Production compose
    prod_compose = current_dir / "docker" / "docker-compose.prod.yml"
    if prod_compose.exists():
        with open(prod_compose) as f:
            prod_content = f.read()

        if "dockerfile: Dockerfile" in prod_content:
            compose_checks.append("✅ Production compose uses root Dockerfile")
        else:
            compose_checks.append("❌ Production compose not using root Dockerfile")

        if "8002:8002" in prod_content:
            compose_checks.append("✅ Production compose uses correct port mapping")
        else:
            compose_checks.append("❌ Production compose incorrect port mapping")
    else:
        compose_checks.append("❌ Production docker-compose.prod.yml not found")

    for check in compose_checks:
        print(f"   {check}")

    # Test 3: Docker scripts validation
    print("\n3. Testing Docker support scripts...")

    script_checks = []

    docker_scripts = ["docker/entrypoint.sh", "docker/health-check.sh"]

    for script_path in docker_scripts:
        script_file = current_dir / script_path
        if script_file.exists():
            script_checks.append(f"✅ {script_path} exists")
        else:
            script_checks.append(f"❌ {script_path} missing")

    for check in script_checks:
        print(f"   {check}")

    # Test 4: README documentation
    print("\n4. Testing README documentation...")

    readme_checks = []

    readme_file = current_dir / "README.md"
    if readme_file.exists():
        with open(readme_file) as f:
            readme_content = f.read()

        if "## Docker Deployment" in readme_content:
            readme_checks.append("✅ README includes Docker deployment section")
        else:
            readme_checks.append("❌ README missing Docker deployment section")

        if "docker build -t generation-service:latest ." in readme_content:
            readme_checks.append("✅ README includes correct build command")
        else:
            readme_checks.append("❌ README missing correct build command")

        if "8002:8002" in readme_content:
            readme_checks.append("✅ README uses correct port (8002)")
        else:
            readme_checks.append("❌ README incorrect port documentation")

        if "/app/data/" in readme_content:
            readme_checks.append("✅ README documents unified data paths")
        else:
            readme_checks.append("❌ README missing data path documentation")
    else:
        readme_checks.append("❌ README.md not found")

    for check in readme_checks:
        print(f"   {check}")

    # Test 5: Environment configuration
    print("\n5. Testing environment configuration...")

    env_checks = []

    env_files = [".env.example", ".env.development", ".env.production"]

    for env_file in env_files:
        env_path = current_dir / env_file
        if env_path.exists():
            env_checks.append(f"✅ {env_file} exists")

            with open(env_path) as f:
                env_content = f.read()

            # Check for unified data paths in environment files
            if "DATA_ROOT_PATH" in env_content:
                env_checks.append(f"   ✅ {env_file} includes unified data paths")
            else:
                env_checks.append(f"   ❌ {env_file} missing unified data paths")
        else:
            env_checks.append(f"❌ {env_file} missing")

    for check in env_checks:
        print(f"   {check}")

    # Test 6: Build context validation
    print("\n6. Testing build context...")

    build_checks = []

    # Check for files that should exist for Docker build
    required_files = [
        "requirements.txt",
        "pyproject.toml",
        "main.py",
        "src/generation_service/__init__.py",
        "src/generation_service/main.py",
    ]

    for req_file in required_files:
        file_path = current_dir / req_file
        if file_path.exists():
            build_checks.append(f"✅ {req_file} available for build")
        else:
            build_checks.append(f"❌ {req_file} missing for build")

    for check in build_checks:
        print(f"   {check}")

    # Summary
    print("\n📊 Docker Build Resolution Test Results:")

    dockerfile_success = all("✅" in check for check in dockerfile_checks)
    compose_success = all("✅" in check for check in compose_checks)
    scripts_success = all("✅" in check for check in script_checks)
    readme_success = all("✅" in check for check in readme_checks)
    env_success = (
        sum(1 for check in env_checks if "✅" in check) >= len(env_checks) * 0.8
    )
    build_success = all("✅" in check for check in build_checks)

    print(f"  Dockerfile configuration: {'✅' if dockerfile_success else '❌'}")
    print(f"  Docker Compose setup: {'✅' if compose_success else '❌'}")
    print(f"  Support scripts: {'✅' if scripts_success else '❌'}")
    print(f"  README documentation: {'✅' if readme_success else '❌'}")
    print(f"  Environment config: {'✅' if env_success else '❌'}")
    print(f"  Build context: {'✅' if build_success else '❌'}")

    overall_success = (
        dockerfile_success
        and compose_success
        and scripts_success
        and readme_success
        and env_success
        and build_success
    )

    if overall_success:
        print("\n🎉 Docker build resolution PASSED!")
        print("✅ Core Module copy issues resolved")
        print("✅ Multi-stage build optimized")
        print("✅ Security features implemented")
        print("✅ Unified data paths configured")
        print("✅ Docker Compose updated")
        print("✅ Documentation complete")
    else:
        print("\n⚠️ Some Docker build issues remain")
        print("Manual review recommended")

    return overall_success


if __name__ == "__main__":
    success = test_docker_build_resolution()
    sys.exit(0 if success else 1)
