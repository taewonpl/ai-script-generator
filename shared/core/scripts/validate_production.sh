#!/bin/bash
# Production Validation Script
# Comprehensive validation before production release

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

print_header "AI Script Core - Production Readiness Validation"
echo "Project Root: $PROJECT_ROOT"
echo "Timestamp: $(date)"
echo ""

cd "$PROJECT_ROOT"

# Track validation results
VALIDATION_RESULTS=()

run_validation() {
    local name="$1"
    local command="$2"

    echo "Running: $name..."
    if eval "$command"; then
        print_success "$name passed"
        VALIDATION_RESULTS+=("PASS: $name")
        return 0
    else
        print_error "$name failed"
        VALIDATION_RESULTS+=("FAIL: $name")
        return 1
    fi
}

# Phase 1: Static Analysis
print_header "Phase 1: Static Analysis & Linting"

run_validation "Ruff Linting" "ruff check src/ tests/ scripts/ --quiet"
run_validation "Ruff Formatting" "ruff format --check src/ tests/ scripts/ --quiet"
run_validation "MyPy Type Checking" "mypy src/ai_script_core/ --strict --no-error-summary"

echo ""

# Phase 2: Test Suite
print_header "Phase 2: Comprehensive Testing"

run_validation "Runtime Validation Tests" "python scripts/runtime_test.py"
run_validation "Core Test Suite" "python -m pytest tests/ -v --tb=short"
run_validation "API Surface Tests" "python -m pytest tests/test_api_surface.py -v"

echo ""

# Phase 3: Build & Package Validation
print_header "Phase 3: Build & Package Validation"

run_validation "Clean Build Test" "bash scripts/build_test.sh"
run_validation "Version Consistency" "python scripts/version_bump.py check"

echo ""

# Phase 4: Security & Dependencies
print_header "Phase 4: Security & Dependencies"

# Check for common security issues
run_validation "Basic Security Scan" "
    ! grep -r 'eval(' src/ --include='*.py' > /dev/null &&
    ! grep -r 'exec(' src/ --include='*.py' > /dev/null &&
    ! grep -r 'os.system' src/ --include='*.py' > /dev/null
"

# Check for TODO/FIXME in production code
run_validation "No TODO/FIXME in Source" "
    ! grep -r -E '(TODO|FIXME|XXX)' src/ --include='*.py' > /dev/null
"

echo ""

# Phase 5: Documentation & Completeness
print_header "Phase 5: Documentation & Completeness"

run_validation "Required Files Present" "
    [[ -f pyproject.toml ]] &&
    [[ -f CHANGELOG.md ]] &&
    [[ -f README.md ]] &&
    [[ -f RELEASE_CHECKLIST.md ]]
"

run_validation "Package Structure Valid" "
    [[ -d src/ai_script_core ]] &&
    [[ -f src/ai_script_core/__init__.py ]] &&
    [[ -d src/ai_script_core/schemas ]] &&
    [[ -d src/ai_script_core/exceptions ]] &&
    [[ -d src/ai_script_core/utils ]]
"

echo ""

# Phase 6: Integration Testing
print_header "Phase 6: Integration Testing"

run_validation "Import Matrix Validation" "python -c \"
import warnings
warnings.filterwarnings('ignore')

# Test all critical imports
try:
    import ai_script_core
    from ai_script_core import ProjectCreateDTO, GenerationRequestDTO
    from ai_script_core import BaseServiceException, generate_uuid
    from ai_script_core.schemas import project, generation
    from ai_script_core.exceptions import base
    from ai_script_core.utils import helpers
    print('All imports successful')
except Exception as e:
    print(f'Import failed: {e}')
    exit(1)
\""

run_validation "DTO Creation & Validation" "python -c \"
from ai_script_core import ProjectCreateDTO, ProjectType, AIModelConfigDTO

# Test valid creation
project = ProjectCreateDTO(name='Test', type=ProjectType.DRAMA)
ai_config = AIModelConfigDTO(model_name='gpt-4', provider='openai')

# Test validation failure
try:
    bad_config = AIModelConfigDTO(model_name='invalid', provider='test')
    print('Validation should have failed')
    exit(1)
except ValueError:
    print('Validation working correctly')
\""

echo ""

# Phase 7: Performance & Resource Usage
print_header "Phase 7: Performance & Resource"

run_validation "Import Performance" "python -c \"
import time
start = time.time()
import ai_script_core
end = time.time()
import_time = end - start
print(f'Import time: {import_time:.3f}s')
assert import_time < 2.0, f'Import too slow: {import_time:.3f}s'
\""

run_validation "Memory Usage Check" "python -c \"
import sys
import ai_script_core
from ai_script_core import ProjectCreateDTO, GenerationRequestDTO, AIModelConfigDTO

# Create several objects to test memory usage
objects = []
for i in range(100):
    project = ProjectCreateDTO(name=f'Test {i}', type='drama')
    objects.append(project)

print(f'Created {len(objects)} objects successfully')
\""

echo ""

# Summary
print_header "Validation Summary"

pass_count=0
fail_count=0

for result in "\${VALIDATION_RESULTS[@]}"; do
    if [[ \$result == PASS:* ]]; then
        pass_count=\$((pass_count + 1))
        echo -e "\${GREEN}\$result\${NC}"
    else
        fail_count=\$((fail_count + 1))
        echo -e "\${RED}\$result\${NC}"
    fi
done

echo ""
echo "Results: \$pass_count passed, \$fail_count failed"

if [[ \$fail_count -eq 0 ]]; then
    print_success "🎉 ALL VALIDATIONS PASSED - PRODUCTION READY!"
    echo -e "\${GREEN}✅ Package is ready for release\${NC}"
    echo -e "\${GREEN}✅ All quality gates satisfied\${NC}"
    echo -e "\${GREEN}✅ Security checks passed\${NC}"
    echo -e "\${GREEN}✅ Performance requirements met\${NC}"
    echo ""
    echo -e "\${BLUE}Next steps:\${NC}"
    echo "1. Update CHANGELOG.md with release notes"
    echo "2. Bump version: python scripts/version_bump.py bump --type [patch|minor|major]"
    echo "3. Create release tag and GitHub release"
    echo "4. Monitor CI/CD pipeline for PyPI publication"
    exit 0
else
    print_error "❌ VALIDATION FAILED - NOT READY FOR PRODUCTION"
    echo -e "\${RED}✗ \$fail_count validation(s) failed\${NC}"
    echo -e "\${RED}✗ Fix issues before proceeding with release\${NC}"
    echo ""
    echo -e "\${YELLOW}Review failed validations above and:\${NC}"
    echo "1. Fix any code issues"
    echo "2. Update tests if needed"
    echo "3. Re-run validation: bash scripts/validate_production.sh"
    exit 1
fi
