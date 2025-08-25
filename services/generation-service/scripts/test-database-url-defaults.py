#!/usr/bin/env python3
"""
Test DATABASE_URL environment-specific defaults
"""

import os
import sys
import tempfile
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_database_url_defaults():
    """Test DATABASE_URL defaults for different environments"""

    print("🔍 Testing DATABASE_URL environment-specific defaults...")

    # Backup original environment variables
    original_env = {}
    env_vars_to_backup = ["DATABASE_URL", "ENVIRONMENT", "DEBUG", "PYTEST_CURRENT_TEST"]

    for var in env_vars_to_backup:
        original_env[var] = os.environ.get(var)
        if var in os.environ:
            del os.environ[var]

    test_results = []

    try:
        # Test 1: Development environment with DEBUG=true
        print("\n1. Testing development environment (DEBUG=true)...")
        os.environ["ENVIRONMENT"] = "development"
        os.environ["DEBUG"] = "true"

        # Import after setting environment
        from generation_service.config_loader import Settings

        settings = Settings()
        db_settings = settings.get_database_settings()

        expected_path_contains = "sqlite+aiosqlite:///"
        actual_url = db_settings.get("url", "")

        if expected_path_contains in actual_url and "app.db" in actual_url:
            print(f"   ✅ Development environment: {actual_url}")
            test_results.append(True)
        else:
            print(f"   ❌ Development environment failed: {actual_url}")
            test_results.append(False)

        # Clear imports to test fresh
        if "generation_service.config_loader" in sys.modules:
            del sys.modules["generation_service.config_loader"]
        if "generation_service.config.base_settings" in sys.modules:
            del sys.modules["generation_service.config.base_settings"]

        # Clear environment for next test
        for var in env_vars_to_backup:
            if var in os.environ:
                del os.environ[var]

        # Test 2: Test environment
        print("\n2. Testing test environment...")
        os.environ["ENVIRONMENT"] = "test"

        from generation_service.config_loader import Settings

        settings = Settings()
        db_settings = settings.get_database_settings()

        actual_url = db_settings.get("url", "")
        if actual_url == "sqlite+aiosqlite:///:memory:":
            print(f"   ✅ Test environment: {actual_url}")
            test_results.append(True)
        else:
            print(f"   ❌ Test environment failed: {actual_url}")
            test_results.append(False)

        # Clear imports
        if "generation_service.config_loader" in sys.modules:
            del sys.modules["generation_service.config_loader"]
        if "generation_service.config.base_settings" in sys.modules:
            del sys.modules["generation_service.config.base_settings"]

        for var in env_vars_to_backup:
            if var in os.environ:
                del os.environ[var]

        # Test 3: Production environment without explicit DATABASE_URL
        print("\n3. Testing production environment (no DATABASE_URL)...")
        os.environ["ENVIRONMENT"] = "production"

        from generation_service.config_loader import Settings

        settings = Settings()
        db_settings = settings.get_database_settings()

        actual_url = db_settings.get("url", "")
        if actual_url is None:
            print(
                f"   ✅ Production environment requires explicit DATABASE_URL: {actual_url}"
            )
            test_results.append(True)
        else:
            print(
                f"   ❌ Production environment should require explicit DATABASE_URL: {actual_url}"
            )
            test_results.append(False)

        # Clear imports
        if "generation_service.config_loader" in sys.modules:
            del sys.modules["generation_service.config_loader"]
        if "generation_service.config.base_settings" in sys.modules:
            del sys.modules["generation_service.config.base_settings"]

        for var in env_vars_to_backup:
            if var in os.environ:
                del os.environ[var]

        # Test 4: Production environment with explicit DATABASE_URL
        print("\n4. Testing production environment (with DATABASE_URL)...")
        os.environ["ENVIRONMENT"] = "production"
        os.environ["DATABASE_URL"] = (
            "postgresql://user:pass@prod-db:5432/prod_db"  # pragma: allowlist secret
        )

        from generation_service.config_loader import Settings

        settings = Settings()
        db_settings = settings.get_database_settings()

        actual_url = db_settings.get("url", "")
        expected_url = (
            "postgresql://user:pass@prod-db:5432/prod_db"  # pragma: allowlist secret
        )
        if actual_url == expected_url:
            print(f"   ✅ Production with explicit DATABASE_URL: {actual_url}")
            test_results.append(True)
        else:
            print(f"   ❌ Production explicit DATABASE_URL failed: {actual_url}")
            test_results.append(False)

        # Clear imports
        if "generation_service.config_loader" in sys.modules:
            del sys.modules["generation_service.config_loader"]
        if "generation_service.config.base_settings" in sys.modules:
            del sys.modules["generation_service.config.base_settings"]

        for var in env_vars_to_backup:
            if var in os.environ:
                del os.environ[var]

        # Test 5: PYTEST environment detection
        print("\n5. Testing pytest environment detection...")
        os.environ["PYTEST_CURRENT_TEST"] = "test_something.py::test_function"

        from generation_service.config_loader import Settings

        settings = Settings()
        db_settings = settings.get_database_settings()

        actual_url = db_settings.get("url", "")
        if actual_url == "sqlite+aiosqlite:///:memory:":
            print(f"   ✅ Pytest environment detected: {actual_url}")
            test_results.append(True)
        else:
            print(f"   ❌ Pytest environment detection failed: {actual_url}")
            test_results.append(False)

        # Clear imports
        if "generation_service.config_loader" in sys.modules:
            del sys.modules["generation_service.config_loader"]
        if "generation_service.config.base_settings" in sys.modules:
            del sys.modules["generation_service.config.base_settings"]

        for var in env_vars_to_backup:
            if var in os.environ:
                del os.environ[var]

        # Test 6: Custom DATABASE_URL override
        print("\n6. Testing custom DATABASE_URL override...")
        os.environ["ENVIRONMENT"] = "development"
        # Use test database URL from environment or default to in-memory SQLite
        test_db_url = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")
        os.environ["DATABASE_URL"] = test_db_url

        from generation_service.config_loader import Settings

        settings = Settings()
        db_settings = settings.get_database_settings()

        actual_url = db_settings.get("url", "")
        expected_url = test_db_url
        if actual_url == expected_url:
            print(f"   ✅ Custom DATABASE_URL override: {actual_url}")
            test_results.append(True)
        else:
            print(f"   ❌ Custom DATABASE_URL override failed: {actual_url}")
            test_results.append(False)

        # Summary
        print("\n📊 DATABASE_URL Default Tests Results:")
        success_count = sum(test_results)
        total_count = len(test_results)

        print(f"  ✅ Development environment: {'✅' if test_results[0] else '❌'}")
        print(f"  ✅ Test environment: {'✅' if test_results[1] else '❌'}")
        print(f"  ✅ Production (no DATABASE_URL): {'✅' if test_results[2] else '❌'}")
        print(
            f"  ✅ Production (with DATABASE_URL): {'✅' if test_results[3] else '❌'}"
        )
        print(f"  ✅ Pytest detection: {'✅' if test_results[4] else '❌'}")
        print(f"  ✅ Custom override: {'✅' if test_results[5] else '❌'}")

        overall_success = success_count == total_count

        if overall_success:
            print(
                f"\n🎉 All DATABASE_URL default tests PASSED! ({success_count}/{total_count})"
            )
            print("✅ Development: SQLite local file")
            print("✅ Test: In-memory SQLite")
            print("✅ Production: Requires explicit DATABASE_URL")
            print("✅ Custom override: Working")
            print("✅ Pytest detection: Working")
            return True
        else:
            print(f"\n⚠️ Some DATABASE_URL tests failed ({success_count}/{total_count})")
            return False

    finally:
        # Restore original environment variables
        for var, value in original_env.items():
            if value is not None:
                os.environ[var] = value
            elif var in os.environ:
                del os.environ[var]


def test_data_directory_creation():
    """Test that data directories are created properly for SQLite"""

    print("\n🗂️  Testing data directory creation for SQLite...")

    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set custom data root path
        os.environ["DATA_ROOT_PATH"] = temp_dir
        os.environ["ENVIRONMENT"] = "development"
        os.environ["DEBUG"] = "true"

        # Clear any existing DATABASE_URL
        if "DATABASE_URL" in os.environ:
            del os.environ["DATABASE_URL"]

        try:
            # Clear imports
            modules_to_clear = [
                "generation_service.config_loader",
                "generation_service.config.base_settings",
                "generation_service.config.environment_manager",
            ]
            for module in modules_to_clear:
                if module in sys.modules:
                    del sys.modules[module]

            from generation_service.config_loader import Settings

            settings = Settings()
            db_settings = settings.get_database_settings()

            db_url = db_settings.get("url", "")

            # Check that the URL points to the temporary directory
            if temp_dir in db_url and "app.db" in db_url:
                print(f"   ✅ SQLite database path in custom directory: {db_url}")
                return True
            else:
                print(f"   ❌ SQLite database path incorrect: {db_url}")
                return False

        except Exception as e:
            print(f"   ❌ Data directory creation test failed: {e}")
            return False
        finally:
            # Clean up environment
            if "DATA_ROOT_PATH" in os.environ:
                del os.environ["DATA_ROOT_PATH"]
            if "ENVIRONMENT" in os.environ:
                del os.environ["ENVIRONMENT"]
            if "DEBUG" in os.environ:
                del os.environ["DEBUG"]


def test_logging_output():
    """Test that logging output is clean and informative"""

    print("\n📝 Testing database configuration logging...")

    # Backup original environment
    original_env = os.environ.copy()

    try:
        # Clear environment
        for var in ["DATABASE_URL", "ENVIRONMENT", "DEBUG"]:
            if var in os.environ:
                del os.environ[var]

        # Set development environment
        os.environ["ENVIRONMENT"] = "development"
        os.environ["DEBUG"] = "true"

        # Clear imports
        modules_to_clear = [
            "generation_service.config_loader",
            "generation_service.config.base_settings",
        ]
        for module in modules_to_clear:
            if module in sys.modules:
                del sys.modules[module]

        # Capture log messages
        import logging

        log_messages = []

        class TestLogHandler(logging.Handler):
            def emit(self, record):
                log_messages.append(record.getMessage())

        handler = TestLogHandler()
        logging.getLogger("generation-service.config").addHandler(handler)
        logging.getLogger("generation-service.config").setLevel(logging.INFO)

        from generation_service.config_loader import Settings

        settings = Settings()
        db_settings = settings.get_database_settings()

        # Check for informative log messages
        sqlite_log_found = any(
            "Using local SQLite database for development" in msg for msg in log_messages
        )

        if sqlite_log_found:
            print("   ✅ Informative logging for development SQLite")
            return True
        else:
            print("   ❌ Missing informative logging")
            print(f"   Log messages: {log_messages}")
            return False

    except Exception as e:
        print(f"   ❌ Logging test failed: {e}")
        return False
    finally:
        # Restore environment
        os.environ.clear()
        os.environ.update(original_env)


if __name__ == "__main__":
    print("Generation Service DATABASE_URL Defaults Test")
    print("=" * 50)

    # Test 1: DATABASE_URL defaults
    defaults_success = test_database_url_defaults()

    # Test 2: Data directory creation
    directory_success = test_data_directory_creation()

    # Test 3: Logging output
    logging_success = test_logging_output()

    # Overall result
    overall_success = defaults_success and directory_success and logging_success

    if overall_success:
        print("\n🎉 ALL DATABASE_URL TESTS PASSED!")
        print("✅ Environment-specific defaults working")
        print("✅ Data directory creation working")
        print("✅ Logging output clean and informative")
        print("✅ Production requires explicit DATABASE_URL")
        sys.exit(0)
    else:
        print("\n❌ Some DATABASE_URL tests failed")
        sys.exit(1)
