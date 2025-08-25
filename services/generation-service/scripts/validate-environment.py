#!/usr/bin/env python3
"""
Environment configuration validation script for Generation Service
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from generation_service.config import settings
    from generation_service.utils.config_validator import (
        ConfigValidator,
        get_config_summary,
        validate_environment_compatibility,
        validate_external_connections,
    )
except ImportError as e:
    print(f"❌ Failed to import Generation Service modules: {e}")
    print(
        "Make sure you're running from the correct directory and dependencies are installed"
    )
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("environment-validator")


def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_subsection(title: str):
    """Print a formatted subsection header"""
    print(f"\n{'-'*40}")
    print(f"  {title}")
    print(f"{'-'*40}")


def print_results(results: list[str], result_type: str, icon: str):
    """Print validation results"""
    if results:
        print(f"\n{icon} {result_type.upper()} ({len(results)}):")
        for i, result in enumerate(results, 1):
            print(f"  {i}. {result}")
    else:
        print(f"\n✅ No {result_type.lower()}")


async def main():
    """Main validation routine"""
    print("🔍 Generation Service Environment Validation")
    print(f"Python: {sys.version}")
    print(f"Working Directory: {os.getcwd()}")

    validation_results = {
        "config_validation": False,
        "external_connections": False,
        "environment_compatibility": True,
        "overall": False,
    }

    # 1. Configuration Validation
    print_section("1. Configuration Validation")

    try:
        validator = ConfigValidator()
        is_valid, errors, warnings = validator.validate_all(settings)

        validation_results["config_validation"] = is_valid

        print(f"Validated {len(validator.validated_keys)} configuration keys")
        print_results(errors, "errors", "❌")
        print_results(warnings, "warnings", "⚠️")

        if is_valid:
            print("\n✅ Configuration validation PASSED")
        else:
            print(f"\n❌ Configuration validation FAILED ({len(errors)} errors)")

    except Exception as e:
        print(f"❌ Configuration validation error: {e}")
        validation_results["config_validation"] = False

    # 2. Environment Compatibility
    print_section("2. Environment Compatibility")

    try:
        compatibility_issues = validate_environment_compatibility()

        if compatibility_issues:
            validation_results["environment_compatibility"] = False
            print_results(compatibility_issues, "compatibility issues", "❌")
        else:
            print("✅ Environment compatibility check PASSED")

    except Exception as e:
        print(f"❌ Environment compatibility check error: {e}")
        validation_results["environment_compatibility"] = False

    # 3. External Service Connections
    print_section("3. External Service Connections")

    try:
        all_healthy, conn_errors, conn_warnings = await validate_external_connections(
            settings
        )

        validation_results["external_connections"] = all_healthy

        print_results(conn_errors, "connection errors", "❌")
        print_results(conn_warnings, "connection warnings", "⚠️")

        if all_healthy:
            print("\n✅ External connections validation PASSED")
        else:
            print("\n⚠️ External connections validation completed with issues")

    except Exception as e:
        print(f"❌ External connections validation error: {e}")
        validation_results["external_connections"] = False

    # 4. Configuration Summary
    print_section("4. Configuration Summary")

    try:
        config_summary = get_config_summary(settings)

        print("\nCurrent Configuration:")
        print(json.dumps(config_summary, indent=2, default=str))

    except Exception as e:
        print(f"❌ Failed to generate configuration summary: {e}")

    # 5. Critical Issues Check
    print_section("5. Critical Issues Check")

    critical_issues = []

    # Check for missing API keys
    if not getattr(settings, "OPENAI_API_KEY", "") or settings.OPENAI_API_KEY in [
        "",
        "your_openai_api_key_here",
    ]:
        critical_issues.append("OpenAI API key not configured")

    if not getattr(settings, "ANTHROPIC_API_KEY", "") or settings.ANTHROPIC_API_KEY in [
        "",
        "your_anthropic_api_key_here",
    ]:
        critical_issues.append("Anthropic API key not configured")

    # Check ChromaDB path
    chroma_path = getattr(settings, "CHROMA_DB_PATH", "")
    if chroma_path:
        chroma_dir = Path(chroma_path).parent
        if not chroma_dir.exists():
            try:
                chroma_dir.mkdir(parents=True, exist_ok=True)
                print(f"✅ Created ChromaDB directory: {chroma_dir}")
            except Exception as e:
                critical_issues.append(f"Cannot create ChromaDB directory: {e}")
        elif not os.access(chroma_dir, os.W_OK):
            critical_issues.append(
                f"No write permission for ChromaDB directory: {chroma_dir}"
            )

    # Check database URL
    database_url = getattr(settings, "DATABASE_URL", "")
    if not database_url:
        critical_issues.append("Database URL not configured")

    if critical_issues:
        print_results(critical_issues, "critical issues", "🚨")
    else:
        print("✅ No critical issues found")

    # 6. Performance Recommendations
    print_section("6. Performance Recommendations")

    recommendations = []

    # Check memory settings
    max_context_length = getattr(settings, "MAX_CONTEXT_LENGTH", 8000)
    if max_context_length > 16000:
        recommendations.append(
            "Consider reducing MAX_CONTEXT_LENGTH for better performance"
        )

    # Check batch size
    embedding_batch_size = getattr(settings, "EMBEDDING_BATCH_SIZE", 100)
    if embedding_batch_size > 200:
        recommendations.append("Large embedding batch size may cause memory issues")

    # Check concurrent requests
    max_concurrent = getattr(settings, "MAX_CONCURRENT_RAG_REQUESTS", 10)
    if max_concurrent > 20:
        recommendations.append("High concurrent RAG requests may impact performance")

    if recommendations:
        print_results(recommendations, "recommendations", "💡")
    else:
        print("✅ Performance settings look good")

    # 7. Security Checks
    print_section("7. Security Checks")

    security_issues = []

    # Check for debug mode in production
    if getattr(settings, "DEBUG", False):
        security_issues.append("DEBUG mode enabled - disable for production")

    # Check for default credentials
    database_url = getattr(settings, "DATABASE_URL", "")
    if "postgres:postgres@" in database_url:
        security_issues.append(
            "Using default database credentials - change for production"
        )

    # Check CORS settings
    allowed_origins = getattr(settings, "ALLOWED_ORIGINS", [])
    if "*" in str(allowed_origins):
        security_issues.append("Wildcard CORS origin allowed - restrict for production")

    if security_issues:
        print_results(security_issues, "security issues", "🔒")
    else:
        print("✅ No security issues found")

    # Overall Result
    print_section("8. Overall Validation Result")

    # Determine overall status
    critical_failures = (
        not validation_results["config_validation"]
        or not validation_results["environment_compatibility"]
        or len(critical_issues) > 0
    )

    validation_results["overall"] = not critical_failures

    if validation_results["overall"]:
        print("🎉 Environment validation PASSED")
        print("✅ Generation Service is ready to run")
        exit_code = 0
    else:
        print("❌ Environment validation FAILED")
        print("🚨 Critical issues must be resolved before running Generation Service")
        exit_code = 1

    # Summary
    print("\nValidation Summary:")
    for check, passed in validation_results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {check.replace('_', ' ').title()}: {status}")

    if critical_issues:
        print(f"\n🚨 {len(critical_issues)} critical issues found")

    if security_issues:
        print(f"🔒 {len(security_issues)} security issues found")

    if recommendations:
        print(f"💡 {len(recommendations)} performance recommendations")

    print("\nFor detailed logs, check the console output above.")

    return exit_code


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️  Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Validation failed with unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
