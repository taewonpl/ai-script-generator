#!/usr/bin/env python3
"""
Test data path unification and configuration consistency
"""

import sys
from pathlib import Path

# Add src to path
current_dir = Path(__file__).parent.parent
src_path = current_dir / "src"
sys.path.insert(0, str(src_path))


def test_data_path_unification():
    """Test that all data paths are unified and consistent"""

    print("🔍 Testing Generation Service data path unification...")

    # Test 1: Configuration consistency
    print("\n1. Testing configuration consistency...")

    try:
        from generation_service.config.environment_manager import (
            get_environment_manager,
        )
        from generation_service.config_loader import settings

        # Get data paths from settings
        data_paths = settings.get_data_paths()

        expected_paths = {
            "root": "/app/data",
            "chroma": "/app/data/chroma",
            "vectors": "/app/data/vectors",
            "logs": "/app/data/logs",
            "cache": "/app/data/cache",
        }

        path_checks = []

        for path_type, expected_path in expected_paths.items():
            actual_path = data_paths.get(path_type)
            if actual_path:
                # Check if path follows unified pattern
                if actual_path.startswith("/app/data/") or actual_path == "/app/data":
                    path_checks.append(f"✓ {path_type}: {actual_path}")
                else:
                    path_checks.append(
                        f"❌ {path_type}: {actual_path} (should be under /app/data/)"
                    )
            else:
                path_checks.append(f"❌ {path_type}: missing")

        for check in path_checks:
            print(f"   {check}")

        unified_paths = all("✓" in check for check in path_checks)

    except ImportError as e:
        print(f"   ❌ Configuration import failed: {e}")
        return False

    # Test 2: Environment detection and file loading
    print("\n2. Testing environment detection...")

    try:
        env_manager = get_environment_manager()
        env_info = env_manager.get_environment_info()

        print(f"   ✓ Environment: {env_info['environment']}")
        print(f"   ✓ Docker: {env_info['is_docker']}")
        print(f"   ✓ Debug: {env_info['is_debug']}")

        # Check data paths from environment
        env_data_paths = env_info["data_paths"]
        for path_type, path_value in env_data_paths.items():
            if path_value.startswith("/app/data") or path_value == "/app/data":
                print(f"   ✓ {path_type}: {path_value}")
            else:
                print(f"   ⚠️ {path_type}: {path_value} (not unified)")

    except Exception as e:
        print(f"   ❌ Environment detection failed: {e}")
        return False

    # Test 3: Environment file format validation
    print("\n3. Testing environment file formats...")

    env_files = [".env.example", ".env.development", ".env.production"]

    env_file_checks = []

    for env_file in env_files:
        file_path = current_dir / env_file
        if file_path.exists():
            try:
                with open(file_path) as f:
                    content = f.read()

                # Check for unified data paths
                required_paths = [
                    "DATA_ROOT_PATH=/app/data",
                    "CHROMA_DB_PATH=/app/data/chroma",
                    "VECTOR_DATA_PATH=/app/data/vectors",
                    "LOG_DATA_PATH=/app/data/logs",
                    "CACHE_DATA_PATH=/app/data/cache",
                ]

                file_valid = True
                for required_path in required_paths:
                    if required_path not in content and not env_file.endswith(
                        "development"
                    ):
                        # Development can have different paths (./data)
                        if env_file.endswith("development"):
                            # Check for relative paths in development
                            dev_path = required_path.replace("/app/data", "./data")
                            if dev_path not in content:
                                file_valid = False
                                break
                        else:
                            file_valid = False
                            break

                if file_valid:
                    env_file_checks.append(f"✓ {env_file}")
                else:
                    env_file_checks.append(f"❌ {env_file} (missing unified paths)")

            except Exception as e:
                env_file_checks.append(f"❌ {env_file} (read error: {e})")
        else:
            env_file_checks.append(f"❌ {env_file} (not found)")

    for check in env_file_checks:
        print(f"   {check}")

    env_files_valid = all("✓" in check for check in env_file_checks)

    # Test 4: Docker configuration validation
    print("\n4. Testing Docker configuration...")

    dockerfile_path = current_dir / "Dockerfile"
    docker_checks = []

    if dockerfile_path.exists():
        with open(dockerfile_path) as f:
            dockerfile_content = f.read()

        # Check for unified data directory creation
        if "mkdir -p /app/data/chroma" in dockerfile_content:
            docker_checks.append("✓ ChromaDB directory creation")
        else:
            docker_checks.append("❌ Missing ChromaDB directory creation")

        if "mkdir -p /app/data/vectors" in dockerfile_content:
            docker_checks.append("✓ Vectors directory creation")
        else:
            docker_checks.append("❌ Missing vectors directory creation")

        if "mkdir -p /app/data/logs" in dockerfile_content:
            docker_checks.append("✓ Logs directory creation")
        else:
            docker_checks.append("❌ Missing logs directory creation")

        if "mkdir -p /app/data/cache" in dockerfile_content:
            docker_checks.append("✓ Cache directory creation")
        else:
            docker_checks.append("❌ Missing cache directory creation")

        # Check environment variables
        if "ENV CHROMA_DB_PATH=/app/data/chroma" in dockerfile_content:
            docker_checks.append("✓ ChromaDB path environment variable")
        else:
            docker_checks.append("❌ Missing ChromaDB path environment variable")

        if "chmod -R 755 /app/data" in dockerfile_content:
            docker_checks.append("✓ Data directory permissions")
        else:
            docker_checks.append("⚠️ No explicit data directory permissions")
    else:
        docker_checks.append("❌ Dockerfile not found")

    for check in docker_checks:
        print(f"   {check}")

    docker_valid = (
        sum(1 for check in docker_checks if check.startswith("✓"))
        >= len(docker_checks) * 0.8
    )

    # Test 5: Model configuration consistency
    print("\n5. Testing model configuration consistency...")

    try:
        # Test RAG models
        from generation_service.models.rag_models import RAGConfigDTO

        # Create instance to check default paths
        rag_config = RAGConfigDTO()

        model_checks = []

        if rag_config.chroma_db_path.startswith("/app/data/chroma"):
            model_checks.append("✓ RAG model ChromaDB path unified")
        else:
            model_checks.append(
                f"❌ RAG model ChromaDB path not unified: {rag_config.chroma_db_path}"
            )

        for check in model_checks:
            print(f"   {check}")

        models_valid = all("✓" in check for check in model_checks)

    except Exception as e:
        print(f"   ❌ Model configuration test failed: {e}")
        models_valid = False

    # Test 6: Path validation functionality
    print("\n6. Testing path validation functionality...")

    try:
        validation_result = settings.validate_configuration()

        validation_checks = []

        if validation_result["overall_valid"]:
            validation_checks.append("✓ Overall configuration valid")
        else:
            validation_checks.append("❌ Configuration validation failed")

            # Show specific errors
            if validation_result["data_paths"]["errors"]:
                for error in validation_result["data_paths"]["errors"]:
                    validation_checks.append(f"   - Data path error: {error}")

            if validation_result["settings"]["errors"]:
                for error in validation_result["settings"]["errors"]:
                    validation_checks.append(f"   - Settings error: {error}")

        # Show warnings
        if validation_result["data_paths"]["warnings"]:
            for warning in validation_result["data_paths"]["warnings"]:
                validation_checks.append(f"   ⚠️ Data path warning: {warning}")

        for check in validation_checks:
            print(f"   {check}")

        validation_functional = "✓ Overall configuration valid" in validation_checks

    except Exception as e:
        print(f"   ❌ Validation functionality test failed: {e}")
        validation_functional = False

    # Summary
    print("\n📊 Data Path Unification Test Results:")
    print(f"  Configuration consistency: {'✅' if unified_paths else '❌'}")
    print(
        f"  Environment detection: {'✅' if True else '❌'}"
    )  # Environment detection passed if we got here
    print(f"  Environment files: {'✅' if env_files_valid else '❌'}")
    print(f"  Docker configuration: {'✅' if docker_valid else '❌'}")
    print(f"  Model consistency: {'✅' if models_valid else '❌'}")
    print(f"  Validation functionality: {'✅' if validation_functional else '❌'}")

    overall_success = (
        unified_paths
        and env_files_valid
        and docker_valid
        and models_valid
        and validation_functional
    )

    if overall_success:
        print("\n🎉 Data path unification PASSED!")
        print("✅ All data paths unified under /app/data/")
        print("✅ Environment-specific configuration working")
        print("✅ Docker setup optimized")
        print("✅ Validation and error handling robust")
    else:
        print("\n⚠️ Some data path unification issues remain")
        print("Manual review recommended")

    return overall_success


if __name__ == "__main__":
    success = test_data_path_unification()
    sys.exit(0 if success else 1)
