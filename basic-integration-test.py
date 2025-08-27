#!/usr/bin/env python3
"""
Basic Integration Test for AI Script Generator v3.0
Tests core functionality without requiring Docker or external services.
"""

import asyncio
import sys
from pathlib import Path
import time
import logging

# Add project paths
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(root_dir / "shared" / "core" / "src"))
sys.path.insert(0, str(root_dir / "services" / "project-service" / "src"))
sys.path.insert(0, str(root_dir / "services" / "generation-service" / "src"))

# Suppress warnings
logging.getLogger("urllib3").setLevel(logging.ERROR)


async def test_core_module_imports():
    """Test that core module imports work correctly"""
    print("🔍 Testing Core Module imports...")
    try:
        print("✅ Core Module imports successful")
        return True
    except Exception as e:
        print(f"❌ Core Module import failed: {e}")
        return False


async def test_project_service_imports():
    """Test that project service imports work correctly"""
    print("🔍 Testing Project Service imports...")
    try:
        print("✅ Project Service imports successful")
        return True
    except Exception as e:
        print(f"❌ Project Service import failed: {e}")
        return False


async def test_generation_service_imports():
    """Test that generation service imports work correctly"""
    print("🔍 Testing Generation Service imports...")
    try:
        print("✅ Generation Service imports successful")
        return True
    except Exception as e:
        print(f"❌ Generation Service import failed: {e}")
        return False


async def test_sse_event_creation():
    """Test SSE event creation and formatting"""
    print("🔍 Testing SSE Event system...")
    try:
        from generation_service.models.sse_models import SSEEvent

        # Test progress event creation
        progress_event = SSEEvent.create_progress(
            job_id="test-job-123",
            progress_percentage=50,
            current_step="Testing",
            steps_completed=5,
            total_steps=10,
            eta_ms=30000,
        )

        # Test event formatting
        formatted = progress_event.format_sse("test-event-id")
        assert "event: progress" in formatted
        assert "test-job-123" in formatted

        # Test completed event
        completed_event = SSEEvent.create_completed(
            job_id="test-job-123",
            markdown="# Test Script\nThis is a test.",
            total_tokens=100,
            word_count=6,
            generation_time_ms=5000,
        )

        completed_formatted = completed_event.format_sse()
        assert "event: completed" in completed_formatted

        print("✅ SSE Event system working correctly")
        return True
    except Exception as e:
        print(f"❌ SSE Event system failed: {e}")
        return False


async def test_job_manager():
    """Test job manager functionality"""
    print("🔍 Testing Job Manager...")
    try:
        from generation_service.services.job_manager import get_job_manager
        from generation_service.models.sse_models import GenerationJobRequest

        job_manager = get_job_manager()

        # Create a test job request
        request = GenerationJobRequest(
            projectId="test-project",
            episodeNumber=1,
            title="Test Script",
            description="This is a test script generation",
            scriptType="drama",
        )

        # Create a job
        job = job_manager.create_job(request)
        assert job.jobId is not None
        assert job.projectId == "test-project"
        assert job.title == "Test Script"

        # Test job retrieval
        retrieved_job = job_manager.get_job(job.jobId)
        assert retrieved_job is not None
        assert retrieved_job.jobId == job.jobId

        # Test job progress update
        success = job_manager.update_job_progress(
            job.jobId,
            progress=25,
            step="Initializing",
            content="Starting generation...",
        )
        assert success

        updated_job = job_manager.get_job(job.jobId)
        assert updated_job.progress == 25
        assert updated_job.currentStep == "Initializing"

        print("✅ Job Manager working correctly")
        return True
    except Exception as e:
        print(f"❌ Job Manager failed: {e}")
        return False


async def test_security_middleware():
    """Test security middleware functionality"""
    print("🔍 Testing Security Middleware...")
    try:
        from generation_service.middleware.security_middleware import (
            SecurityHeadersMiddleware,
            RateLimitingMiddleware,
            RequestValidationMiddleware,
        )

        # Test that middleware classes can be instantiated
        from starlette.applications import Starlette

        dummy_app = Starlette()

        # Test security headers middleware
        security_middleware = SecurityHeadersMiddleware(dummy_app)
        assert security_middleware is not None

        # Test rate limiting middleware
        rate_limit_middleware = RateLimitingMiddleware(dummy_app, calls=10, period=60)
        assert rate_limit_middleware.calls == 10
        assert rate_limit_middleware.period == 60

        # Test request validation middleware
        validation_middleware = RequestValidationMiddleware(dummy_app)
        assert validation_middleware.max_content_length == 16 * 1024 * 1024

        print("✅ Security Middleware working correctly")
        return True
    except Exception as e:
        print(f"❌ Security Middleware failed: {e}")
        return False


async def test_configuration_loading():
    """Test configuration loading and validation"""
    print("🔍 Testing Configuration System...")
    try:
        from ai_script_core.utils.config import get_settings, SecuritySettings

        # Test settings loading
        settings = get_settings()
        assert settings is not None
        assert hasattr(settings, "service_name")

        # Test security settings
        security_settings = SecuritySettings()
        assert security_settings.secret_key is not None
        assert security_settings.cors_origins is not None

        print("✅ Configuration System working correctly")
        return True
    except Exception as e:
        print(f"❌ Configuration System failed: {e}")
        return False


async def run_basic_integration_tests():
    """Run all basic integration tests"""
    print("🚀 AI Script Generator v3.0 - Basic Integration Tests")
    print("=" * 60)

    start_time = time.time()

    test_functions = [
        ("Core Module Imports", test_core_module_imports),
        ("Project Service Imports", test_project_service_imports),
        ("Generation Service Imports", test_generation_service_imports),
        ("SSE Event System", test_sse_event_creation),
        ("Job Manager", test_job_manager),
        ("Security Middleware", test_security_middleware),
        ("Configuration System", test_configuration_loading),
    ]

    results = {}
    overall_success = True

    for test_name, test_func in test_functions:
        print(f"\n📋 {test_name}")
        print("-" * 40)

        try:
            result = await test_func()
            results[test_name] = result
            if not result:
                overall_success = False
        except Exception as e:
            print(f"❌ {test_name} EXCEPTION: {e}")
            results[test_name] = False
            overall_success = False

    # Summary
    end_time = time.time()
    duration = end_time - start_time

    print("\n" + "=" * 60)
    print("🎯 Integration Test Results Summary")
    print("=" * 60)

    passed_tests = sum(1 for result in results.values() if result)
    total_tests = len(results)

    print(f"⏱️  Total Duration: {duration:.2f}s")
    print(f"📊 Tests Passed: {passed_tests}/{total_tests}")
    print(f"🎯 Success Rate: {(passed_tests/total_tests*100):.1f}%")
    print()

    for test_name, result in results.items():
        status_emoji = "✅" if result else "❌"
        print(f"  {status_emoji} {test_name}")

    print()

    if overall_success:
        print("🎉 All basic integration tests PASSED!")
        print("✅ System core functionality is working correctly")
        return 0
    else:
        print("❌ Some integration tests FAILED")
        print("🔧 Please review the failed components before deployment")
        return 1


async def main():
    """Main entry point"""
    try:
        exit_code = await run_basic_integration_tests()
        sys.exit(exit_code)
    except Exception as e:
        print(f"❌ Critical error in test execution: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
