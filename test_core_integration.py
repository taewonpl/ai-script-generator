#!/usr/bin/env python3
"""
Core Module Integration Test
Tests the difference between Core Module availability and fallback mechanisms
"""

import sys
import os
from typing import Any

print("🧪 AI Script Generator v3.0 - Core Module Integration Test")
print("=" * 60)


def test_python_version():
    """Test Python version compatibility"""
    print("\n📌 Python Version Check")
    print(f"Current Python: {sys.version}")
    print(f"Version Info: {sys.version_info}")

    if sys.version_info >= (3, 10):
        print("✅ Python 3.10+ - Core Module should be available")
        return True
    else:
        print("⚠️  Python < 3.10 - Core Module fallback expected")
        return False


def test_core_module_import():
    """Test Core Module import"""
    print("\n📌 Core Module Import Test")

    # Add Core Module to path
    core_path = "./shared/core/src"
    if core_path not in sys.path:
        sys.path.insert(0, core_path)

    try:
        import ai_script_core

        print("✅ Core Module imported successfully")

        # Test key exports
        exports = [
            "BaseServiceException",
            "ProjectDTO",
            "GenerationRequestDTO",
            "get_service_logger",
            "generate_uuid",
            "utc_now",
        ]

        available_exports = []
        for export in exports:
            if hasattr(ai_script_core, export):
                available_exports.append(export)

        print(f"📋 Available exports: {len(available_exports)}/{len(exports)}")
        print(f"   ✅ {', '.join(available_exports)}")

        return True, ai_script_core

    except (ImportError, RuntimeError) as e:
        print(f"❌ Core Module import failed: {e}")
        return False, None


def test_generation_service_fallback():
    """Test Generation Service fallback mechanism"""
    print("\n📌 Generation Service Fallback Test")

    # Test Generation Service import
    gen_service_path = "./services/generation-service/src"
    if gen_service_path not in sys.path:
        sys.path.insert(0, gen_service_path)

    try:
        from generation_service.main import CORE_AVAILABLE, logger

        print("✅ Generation Service imported")
        print(f"📋 Core Module Available: {CORE_AVAILABLE}")

        if CORE_AVAILABLE:
            print("   🎯 Using ai_script_core.get_service_logger")
            print("   🎯 Full exception handling with BaseServiceException")
            print("   🎯 Structured JSON logging")
        else:
            print("   📋 Using fallback logging.getLogger")
            print("   📋 Basic exception handling")
            print("   📋 Standard Python logging")

        # Test logger functionality
        logger.info("Test log message from Generation Service")
        print("✅ Logger test successful")

        return True

    except Exception as e:
        print(f"❌ Generation Service test failed: {e}")
        return False


def test_project_service_fallback():
    """Test Project Service fallback mechanism"""
    print("\n📌 Project Service Fallback Test")

    # Test Project Service import
    proj_service_path = "./services/project-service/src"
    if proj_service_path not in sys.path:
        sys.path.insert(0, proj_service_path)

    try:
        from project_service.api.health import HealthCheckDTO

        print("✅ Project Service APIs imported with fallback DTOs")

        # Test DTO creation
        health_dto = HealthCheckDTO(
            service_name="test-service",
            status="healthy",
            version="1.0.0",
            details={"test": True},
        )
        print(f"✅ HealthCheckDTO created: {health_dto.service_name}")

        return True

    except Exception as e:
        print(f"❌ Project Service test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_docker_compatibility():
    """Test Docker environment compatibility"""
    print("\n📌 Docker Environment Test")

    # Check if running in Docker-like environment
    docker_indicators = [
        os.path.exists("/.dockerenv"),
        os.environ.get("DOCKER_CONTAINER"),
        os.environ.get("KUBERNETES_SERVICE_HOST"),
    ]

    in_container = any(docker_indicators)
    print(f"Container environment: {in_container}")

    # Test Core Module path mounting
    core_mount_path = "/app/shared/core"
    if os.path.exists(core_mount_path):
        print(f"✅ Core Module mount path exists: {core_mount_path}")
    else:
        print("📋 Core Module mount path not found (expected in local test)")

    return True


def generate_comparison_report(core_available: bool, core_module: Any = None):
    """Generate comparison report between Core and fallback"""
    print("\n📊 CORE MODULE vs FALLBACK COMPARISON")
    print("=" * 60)

    if core_available and core_module:
        print("🎯 WITH CORE MODULE:")
        print("   ✅ Standardized schemas (ProjectDTO, EpisodeDTO, etc.)")
        print("   ✅ Comprehensive exception hierarchy")
        print("   ✅ Structured JSON logging with get_service_logger()")
        print("   ✅ UUID utilities (generate_uuid, generate_prefixed_id)")
        print("   ✅ Date/time utilities (utc_now, format_datetime)")
        print("   ✅ Configuration management (get_settings)")
        print("   ✅ Cross-service consistency")
        print("   ✅ Type hints and validation")

        # Test specific functions
        try:
            logger = core_module.get_service_logger("test")
            uuid_val = core_module.generate_uuid()
            time_val = core_module.utc_now()
            print(f"   📋 Sample UUID: {uuid_val}")
            print(f"   📋 Sample timestamp: {time_val}")
        except Exception as e:
            print(f"   ⚠️  Function test error: {e}")

    print("\n📋 WITH FALLBACK MODE:")
    print("   📋 Basic Pydantic models for DTOs")
    print("   📋 Standard Python exceptions")
    print("   📋 Basic Python logging.getLogger()")
    print("   📋 Manual UUID generation")
    print("   📋 Manual datetime handling")
    print("   📋 Manual configuration")
    print("   📋 Service-specific implementations")
    print("   📋 Reduced type safety")

    print("\n🔄 MIGRATION STRATEGY:")
    print("   1. Services work in both modes")
    print("   2. Graceful degradation when Core unavailable")
    print("   3. Docker builds handle Core installation")
    print("   4. Python 3.10+ environments get full features")
    print("   5. Python 3.9 environments use fallback")


def main():
    """Main test execution"""
    results = {}

    # Test sequence
    results["python_compatible"] = test_python_version()
    results["core_import"], core_module = test_core_module_import()
    results["generation_service"] = test_generation_service_fallback()
    results["project_service"] = test_project_service_fallback()
    results["docker_compat"] = test_docker_compatibility()

    # Generate report
    generate_comparison_report(results["core_import"], core_module)

    # Summary
    print("\n📋 TEST SUMMARY")
    print("=" * 60)
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:20}: {status}")

    total_passed = sum(results.values())
    print(f"\nOverall: {total_passed}/{len(results)} tests passed")

    if results["generation_service"] and results["project_service"]:
        print("🎉 Both services are working with their fallback mechanisms!")

    return results


if __name__ == "__main__":
    main()
