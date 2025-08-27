#!/usr/bin/env python3
"""
Docker Build Validation Test
Validates that all Dockerfiles are syntactically correct and contain required components.
"""

import sys
from pathlib import Path
from typing import Dict, Any


def validate_dockerfile(dockerfile_path: Path) -> Dict[str, Any]:
    """Validate a single Dockerfile"""
    result = {
        "path": str(dockerfile_path),
        "exists": dockerfile_path.exists(),
        "issues": [],
        "recommendations": [],
        "security_score": 0,
        "best_practices": [],
    }

    if not result["exists"]:
        result["issues"].append("Dockerfile does not exist")
        return result

    try:
        with open(dockerfile_path, "r") as f:
            content = f.read()

        lines = content.split("\n")

        # Required components check
        required_components = {
            "FROM": False,
            "WORKDIR": False,
            "COPY": False,
            "EXPOSE": False,
            "CMD": False,
        }

        security_practices = {
            "non_root_user": False,
            "no_root_operations": True,
            "minimal_base_image": False,
            "healthcheck": False,
            "env_variables": False,
        }

        for line in lines:
            line_stripped = line.strip().upper()

            # Check for required components
            for component in required_components:
                if line_stripped.startswith(component):
                    required_components[component] = True

            # Security practice checks
            if "USER " in line and "root" not in line.lower():
                security_practices["non_root_user"] = True

            if line_stripped.startswith("FROM"):
                if "alpine" in line.lower() or "slim" in line.lower():
                    security_practices["minimal_base_image"] = True

            if line_stripped.startswith("HEALTHCHECK"):
                security_practices["healthcheck"] = True

            if line_stripped.startswith("ENV"):
                security_practices["env_variables"] = True

            # Check for potential security issues
            if "curl" in line.lower() and "apt-get" in line.lower():
                result["recommendations"].append(
                    "Consider using multi-stage builds to reduce attack surface"
                )

            if "ADD" in line_stripped and "http" in line.lower():
                result["issues"].append(
                    "Using ADD with URLs is discouraged, use COPY or RUN wget/curl"
                )

        # Validate required components
        missing_components = [
            comp for comp, present in required_components.items() if not present
        ]
        if missing_components:
            result["issues"].append(
                f"Missing required components: {missing_components}"
            )

        # Security scoring
        security_score = sum(1 for practice in security_practices.values() if practice)
        result["security_score"] = (security_score / len(security_practices)) * 100

        # Security recommendations
        if not security_practices["non_root_user"]:
            result["recommendations"].append("Add non-root user for better security")
        if not security_practices["healthcheck"]:
            result["recommendations"].append("Add HEALTHCHECK instruction")
        if not security_practices["minimal_base_image"]:
            result["recommendations"].append(
                "Consider using minimal base images (alpine, slim)"
            )

        # Best practices found
        if security_practices["non_root_user"]:
            result["best_practices"].append("✅ Uses non-root user")
        if security_practices["healthcheck"]:
            result["best_practices"].append("✅ Includes healthcheck")
        if security_practices["minimal_base_image"]:
            result["best_practices"].append("✅ Uses minimal base image")

    except Exception as e:
        result["issues"].append(f"Error reading Dockerfile: {e}")

    return result


def validate_all_dockerfiles() -> Dict[str, Any]:
    """Validate all Dockerfiles in the project"""
    root_dir = Path(__file__).parent

    # Find all Dockerfiles
    dockerfile_paths = [
        root_dir / "frontend" / "Dockerfile",
        root_dir / "services" / "project-service" / "Dockerfile",
        root_dir / "services" / "generation-service" / "Dockerfile",
    ]

    results = []
    overall_issues = []

    print("🔍 Docker Build Validation")
    print("=" * 50)

    for dockerfile_path in dockerfile_paths:
        print(f"\n📋 Validating: {dockerfile_path.relative_to(root_dir)}")
        print("-" * 30)

        result = validate_dockerfile(dockerfile_path)
        results.append(result)

        if result["exists"]:
            print("✅ File exists")
            print(f"🔒 Security score: {result['security_score']:.0f}%")

            if result["best_practices"]:
                print("🏆 Best practices:")
                for practice in result["best_practices"]:
                    print(f"  {practice}")

            if result["issues"]:
                print("❌ Issues found:")
                for issue in result["issues"]:
                    print(f"  • {issue}")
                overall_issues.extend(result["issues"])

            if result["recommendations"]:
                print("💡 Recommendations:")
                for rec in result["recommendations"]:
                    print(f"  • {rec}")
        else:
            print("❌ File missing")
            overall_issues.append(f"Missing Dockerfile: {dockerfile_path}")

    # Summary
    print("\n" + "=" * 50)
    print("🎯 Docker Build Validation Summary")
    print("=" * 50)

    total_dockerfiles = len(dockerfile_paths)
    existing_dockerfiles = sum(1 for r in results if r["exists"])
    avg_security_score = sum(r["security_score"] for r in results if r["exists"]) / max(
        existing_dockerfiles, 1
    )

    print(f"📊 Dockerfiles found: {existing_dockerfiles}/{total_dockerfiles}")
    print(f"🔒 Average security score: {avg_security_score:.0f}%")
    print(f"❌ Total issues: {len(overall_issues)}")

    success = len(overall_issues) == 0 and existing_dockerfiles == total_dockerfiles

    if success:
        print("✅ All Dockerfiles are valid and follow best practices!")
        return {"status": "PASSED", "results": results, "issues": overall_issues}
    else:
        print("❌ Some Dockerfiles need attention")
        if overall_issues:
            print("\n🔧 Issues to fix:")
            for issue in set(overall_issues):  # Remove duplicates
                print(f"  • {issue}")
        return {"status": "FAILED", "results": results, "issues": overall_issues}


def validate_docker_compose():
    """Validate docker-compose.yml files"""
    print("\n🔍 Docker Compose Validation")
    print("=" * 50)

    root_dir = Path(__file__).parent
    compose_files = [
        root_dir / "docker-compose.yml",
        root_dir / "docker-compose.override.yml",
        root_dir / "docker-compose.prod.yml",
    ]

    issues = []

    for compose_file in compose_files:
        print(f"\n📋 Checking: {compose_file.name}")

        if not compose_file.exists():
            if compose_file.name == "docker-compose.yml":
                issues.append(f"Required file missing: {compose_file.name}")
                print("❌ Missing required file")
            else:
                print("ℹ️  Optional file not present")
            continue

        try:
            import yaml

            with open(compose_file, "r") as f:
                compose_content = yaml.safe_load(f)

            # Basic validation
            if "services" not in compose_content:
                issues.append(f"{compose_file.name}: Missing 'services' section")
                print("❌ Missing 'services' section")
            else:
                services = compose_content["services"]
                print(
                    f"✅ Found {len(services)} services: {', '.join(services.keys())}"
                )

                # Check for common required sections
                for service_name, service_config in services.items():
                    if "build" not in service_config and "image" not in service_config:
                        issues.append(
                            f"{compose_file.name}: Service '{service_name}' missing build or image"
                        )

            print("✅ Valid YAML syntax")

        except ImportError:
            print("⚠️  Cannot validate YAML (pyyaml not available)")
        except Exception as e:
            issues.append(f"{compose_file.name}: {str(e)}")
            print(f"❌ Validation error: {e}")

    return issues


def main():
    """Main validation function"""
    print("🚀 AI Script Generator v3.0 - Docker Build Validation")
    print("=" * 70)

    # Validate Dockerfiles
    dockerfile_results = validate_all_dockerfiles()

    # Validate docker-compose files
    compose_issues = validate_docker_compose()

    # Overall summary
    print("\n" + "=" * 70)
    print("🎯 Overall Docker Validation Results")
    print("=" * 70)

    total_issues = len(dockerfile_results["issues"]) + len(compose_issues)

    if total_issues == 0:
        print("🎉 All Docker configurations are valid!")
        print("✅ Ready for containerized deployment")
        return 0
    else:
        print(f"❌ Found {total_issues} issues that need attention")
        print("🔧 Please fix the issues before building Docker images")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
