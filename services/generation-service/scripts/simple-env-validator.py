#!/usr/bin/env python3
"""
Simple environment validation script without dependencies
"""

import logging
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("env-validator")


class SimpleConfigValidator:
    """Simple configuration validator without external dependencies"""

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.validated_keys = []
        self.env_vars = {}

    def load_env_file(self):
        """Load .env file if it exists"""
        env_files = [".env", ".env.local", ".env.example"]
        found_env_file = False

        for env_file in env_files:
            if os.path.exists(env_file):
                found_env_file = True
                try:
                    with open(env_file) as f:
                        content = f.read()

                    logger.info(f"Loading environment file: {env_file}")

                    # Parse .env format
                    lines = content.split("\n")
                    for i, line in enumerate(lines, 1):
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            key = key.strip()
                            value = value.strip().strip("\"'")

                            if key:
                                self.env_vars[key] = value
                                # Set in os.environ if not already set
                                if key not in os.environ:
                                    os.environ[key] = value

                    self.validated_keys.append(f"env_file:{env_file}")
                    break

                except Exception as e:
                    self.errors.append(f"Cannot read .env file {env_file}: {e}")

        if not found_env_file:
            self.warnings.append(
                "No .env file found - using environment variables only"
            )

    def get_env_value(self, key: str, default: str = ""):
        """Get environment variable value"""
        return os.getenv(key, self.env_vars.get(key, default))

    def validate_required_variables(self):
        """Validate required environment variables"""
        required_vars = ["SERVICE_NAME", "PORT", "DATABASE_URL"]

        optional_vars = [
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "CHROMA_DB_PATH",
            "PROJECT_SERVICE_URL",
        ]

        logger.info("Validating required environment variables...")

        for var in required_vars:
            value = self.get_env_value(var)
            if not value:
                self.errors.append(
                    f"Required environment variable {var} is missing or empty"
                )
            else:
                self.validated_keys.append(f"required_var:{var}")
                logger.info(f"✓ {var}: {value[:20]}...")

        for var in optional_vars:
            value = self.get_env_value(var)
            if not value or value in [
                "your_openai_api_key_here",
                "your_anthropic_api_key_here",
            ]:
                self.warnings.append(
                    f"Optional environment variable {var} is not configured"
                )
            else:
                self.validated_keys.append(f"optional_var:{var}")
                # Mask sensitive information
                if "key" in var.lower() or "password" in var.lower():
                    masked_value = (
                        f"{'*' * (len(value) - 4)}{value[-4:]}"
                        if len(value) > 4
                        else "****"
                    )
                    logger.info(f"✓ {var}: {masked_value}")
                else:
                    logger.info(f"✓ {var}: {value}")

    def validate_api_keys(self):
        """Validate API key formats"""
        logger.info("Validating API key formats...")

        api_key_configs = [
            ("OPENAI_API_KEY", r"^sk-[A-Za-z0-9]{20,}$", "OpenAI API key"),
            ("ANTHROPIC_API_KEY", r"^sk-ant-[A-Za-z0-9-_]{20,}$", "Anthropic API key"),
        ]

        for var_name, pattern, description in api_key_configs:
            api_key = self.get_env_value(var_name)

            if api_key and api_key not in [
                "",
                "your_openai_api_key_here",
                "your_anthropic_api_key_here",
            ]:
                if not re.match(pattern, api_key):
                    self.errors.append(f"Invalid {description} format: {var_name}")
                else:
                    self.validated_keys.append(f"api_key:{var_name}")
                    logger.info(f"✓ {description} format valid")

                # Check for common mistakes
                if api_key.startswith(" ") or api_key.endswith(" "):
                    self.errors.append(f"{description} has leading/trailing whitespace")

                if len(api_key) < 20:
                    self.errors.append(f"{description} appears too short")
            else:
                self.warnings.append(f"{description} not configured")

    def validate_database_config(self):
        """Validate database configuration"""
        logger.info("Validating database configuration...")

        database_url = self.get_env_value("DATABASE_URL")

        if not database_url:
            self.errors.append("DATABASE_URL is required")
            return

        try:
            parsed = urlparse(database_url)

            # Validate scheme
            if parsed.scheme not in ["postgresql", "postgres", "sqlite"]:
                self.errors.append(f"Unsupported database scheme: {parsed.scheme}")
            else:
                logger.info(f"✓ Database scheme: {parsed.scheme}")

            # Validate PostgreSQL specific settings
            if parsed.scheme in ["postgresql", "postgres"]:
                if not parsed.hostname:
                    self.errors.append("Database hostname is missing")
                else:
                    logger.info(f"✓ Database host: {parsed.hostname}")

                if parsed.port and (parsed.port < 1 or parsed.port > 65535):
                    self.errors.append(f"Invalid database port: {parsed.port}")
                elif parsed.port:
                    logger.info(f"✓ Database port: {parsed.port}")

                if not parsed.path or parsed.path == "/":
                    self.errors.append("Database name is missing")
                else:
                    logger.info(f"✓ Database name: {parsed.path.lstrip('/')}")

                # Security warning for default credentials
                if (
                    parsed.username == "postgres" and parsed.password == "postgres"
                ):  # pragma: allowlist secret
                    self.warnings.append(
                        "Using default PostgreSQL credentials - change for production"
                    )

            self.validated_keys.append("database_config")

        except Exception as e:
            self.errors.append(f"Invalid DATABASE_URL format: {e}")

    def validate_chroma_config(self):
        """Validate ChromaDB configuration"""
        logger.info("Validating ChromaDB configuration...")

        chroma_path = self.get_env_value("CHROMA_DB_PATH", "./data/chroma")

        try:
            path_obj = Path(chroma_path)

            # Check if path is absolute
            if not path_obj.is_absolute():
                self.warnings.append(f"ChromaDB path is relative: {chroma_path}")

            logger.info(f"✓ ChromaDB path: {chroma_path}")

            # Check parent directory
            parent_dir = path_obj.parent
            if not parent_dir.exists():
                try:
                    parent_dir.mkdir(parents=True, exist_ok=True)
                    logger.info(f"✓ Created ChromaDB directory: {parent_dir}")
                    self.validated_keys.append("chroma_path_created")
                except Exception as e:
                    self.errors.append(
                        f"Cannot create ChromaDB directory {parent_dir}: {e}"
                    )
            else:
                # Check write permissions
                if not os.access(parent_dir, os.W_OK):
                    self.errors.append(
                        f"No write permission for ChromaDB directory: {parent_dir}"
                    )
                else:
                    logger.info(f"✓ ChromaDB directory writable: {parent_dir}")
                    self.validated_keys.append("chroma_path_writable")

            # Validate collection name
            collection_name = self.get_env_value(
                "CHROMA_COLLECTION_NAME", "script_knowledge"
            )
            if not re.match(r"^[a-zA-Z0-9_-]+$", collection_name):
                self.errors.append(
                    f"Invalid ChromaDB collection name: {collection_name}"
                )
            else:
                logger.info(f"✓ ChromaDB collection name: {collection_name}")
                self.validated_keys.append("chroma_collection_name")

        except Exception as e:
            self.errors.append(f"Invalid ChromaDB path: {e}")

    def validate_external_services(self):
        """Validate external service configurations"""
        logger.info("Validating external service configurations...")

        project_service_url = self.get_env_value(
            "PROJECT_SERVICE_URL", "http://localhost:8001"
        )

        if project_service_url:
            try:
                parsed = urlparse(project_service_url)
                if not parsed.scheme or not parsed.netloc:
                    self.errors.append(
                        f"Invalid PROJECT_SERVICE_URL: {project_service_url}"
                    )
                else:
                    logger.info(f"✓ Project service URL: {project_service_url}")
                    self.validated_keys.append("project_service_url")
            except Exception as e:
                self.errors.append(f"Invalid PROJECT_SERVICE_URL format: {e}")

    def validate_numeric_settings(self):
        """Validate numeric configuration settings"""
        logger.info("Validating numeric configuration settings...")

        numeric_settings = [
            ("PORT", 1, 65535, 8002),
            ("MAX_SCRIPT_LENGTH", 1000, 100000, 10000),
            ("MAX_CONTEXT_LENGTH", 1000, 32000, 8000),
            ("EMBEDDING_BATCH_SIZE", 1, 1000, 100),
            ("MAX_SEARCH_RESULTS", 1, 100, 10),
            ("MAX_CONCURRENT_RAG_REQUESTS", 1, 50, 10),
        ]

        for setting_name, min_val, max_val, default in numeric_settings:
            value_str = self.get_env_value(setting_name, str(default))
            try:
                value = int(value_str)
                if not (min_val <= value <= max_val):
                    self.warnings.append(
                        f"{setting_name} ({value}) outside recommended range {min_val}-{max_val}"
                    )
                else:
                    logger.info(f"✓ {setting_name}: {value}")
                    self.validated_keys.append(f"numeric_setting:{setting_name}")
            except (ValueError, TypeError):
                self.errors.append(
                    f"Invalid numeric value for {setting_name}: {value_str}"
                )

        # Validate float settings
        similarity_threshold = self.get_env_value("SIMILARITY_THRESHOLD", "0.7")
        try:
            float_value = float(similarity_threshold)
            if not (0.0 <= float_value <= 1.0):
                self.errors.append(
                    f"SIMILARITY_THRESHOLD must be between 0.0 and 1.0: {float_value}"
                )
            else:
                logger.info(f"✓ SIMILARITY_THRESHOLD: {float_value}")
                self.validated_keys.append("similarity_threshold")
        except (ValueError, TypeError):
            self.errors.append(
                f"Invalid float value for SIMILARITY_THRESHOLD: {similarity_threshold}"
            )

    def check_security_issues(self):
        """Check for security-related configuration issues"""
        logger.info("Checking security configuration...")

        security_issues = []

        # Check for debug mode
        debug = self.get_env_value("DEBUG", "false").lower()
        if debug in ["true", "1", "yes"]:
            security_issues.append("DEBUG mode enabled - disable for production")

        # Check for default credentials
        database_url = self.get_env_value("DATABASE_URL", "")
        if "postgres:postgres@" in database_url:
            security_issues.append(
                "Using default database credentials - change for production"
            )

        # Check CORS settings
        allowed_origins = self.get_env_value("ALLOWED_ORIGINS", "")
        if "*" in allowed_origins:
            security_issues.append(
                "Wildcard CORS origin allowed - restrict for production"
            )

        if security_issues:
            self.warnings.extend(security_issues)
            for issue in security_issues:
                logger.warning(f"🔒 Security issue: {issue}")
        else:
            logger.info("✓ No obvious security issues found")

    def validate_all(self):
        """Run all validations"""
        logger.info("Starting comprehensive environment validation...")

        try:
            self.load_env_file()
            self.validate_required_variables()
            self.validate_api_keys()
            self.validate_database_config()
            self.validate_chroma_config()
            self.validate_external_services()
            self.validate_numeric_settings()
            self.check_security_issues()

            return len(self.errors) == 0, self.errors, self.warnings

        except Exception as e:
            self.errors.append(f"Validation failed with unexpected error: {e}")
            return False, self.errors, self.warnings


def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_results(results: list, result_type: str, icon: str):
    """Print validation results"""
    if results:
        print(f"\n{icon} {result_type.upper()} ({len(results)}):")
        for i, result in enumerate(results, 1):
            print(f"  {i}. {result}")
    else:
        print(f"\n✅ No {result_type.lower()}")


def main():
    """Main validation routine"""
    print("🔍 Generation Service Environment Validation")
    print(f"Python: {sys.version}")
    print(f"Working Directory: {os.getcwd()}")

    print_section("Environment Configuration Validation")

    validator = SimpleConfigValidator()
    is_valid, errors, warnings = validator.validate_all()

    print(f"\nValidated {len(validator.validated_keys)} configuration items")

    print_results(errors, "errors", "❌")
    print_results(warnings, "warnings", "⚠️")

    print_section("Validation Summary")

    if is_valid:
        print("🎉 Environment validation PASSED")
        print("✅ Generation Service configuration is ready")
        exit_code = 0
    else:
        print("❌ Environment validation FAILED")
        print("🚨 Critical issues must be resolved before running Generation Service")
        exit_code = 1

    # Summary stats
    print("\nValidation Results:")
    print(f"  Configuration items validated: {len(validator.validated_keys)}")
    print(f"  Errors found: {len(errors)}")
    print(f"  Warnings: {len(warnings)}")

    if errors:
        print(
            f"\n🚨 {len(errors)} critical issues found - service will not start properly"
        )

    if warnings:
        print(f"⚠️  {len(warnings)} warnings - review for production deployment")

    return exit_code


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️  Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Validation failed with unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
