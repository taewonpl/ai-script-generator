#!/bin/bash
# Build and Test Script for AI Script Core
# Tests packaging, installation, and import matrix in clean environment

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print functions
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
TEMP_DIR=$(mktemp -d)

cleanup() {
    echo "Cleaning up temporary directory: $TEMP_DIR"
    rm -rf "$TEMP_DIR"
}
trap cleanup EXIT

print_header "AI Script Core - Build & Test Validation"
echo "Project Root: $PROJECT_ROOT"
echo "Temp Directory: $TEMP_DIR"
echo ""

# Phase 1: Clean Build
print_header "Phase 1: Clean Build Test"
cd "$PROJECT_ROOT"

# Remove any existing build artifacts
rm -rf build/ dist/ *.egg-info/
print_success "Cleaned existing build artifacts"

# Build the package
python3 -m build --outdir "$TEMP_DIR/dist"
print_success "Package built successfully"

# Check build artifacts
if [[ ! -f "$TEMP_DIR/dist"/*.whl ]]; then
    print_error "Wheel file not found in build output"
    exit 1
fi

if [[ ! -f "$TEMP_DIR/dist"/*.tar.gz ]]; then
    print_error "Source distribution not found in build output"
    exit 1
fi

print_success "Build artifacts created: wheel and sdist"

# Phase 2: Twine Check
print_header "Phase 2: Distribution Validation"

# Check with twine
if command -v twine &> /dev/null; then
    twine check "$TEMP_DIR/dist"/*
    print_success "Twine check passed - ready for PyPI"
else
    print_warning "Twine not available - skipping PyPI readiness check"
fi

# Phase 3: Clean Environment Installation Test
print_header "Phase 3: Clean Environment Installation"

# Create virtual environment
python3 -m venv "$TEMP_DIR/test_env"
source "$TEMP_DIR/test_env/bin/activate"

# Upgrade pip
pip install --upgrade pip

# Install from wheel
pip install "$TEMP_DIR/dist"/*.whl
print_success "Package installed from wheel in clean environment"

# Phase 4: Import Matrix Test
print_header "Phase 4: Import Matrix Verification"

# Test import matrix
python3 -c "
import sys
print(f'Python version: {sys.version}')

# Test 1: Main package import
try:
    import ai_script_core
    print('✅ ai_script_core import successful')
    print(f'   Version: {ai_script_core.__version__}')
except Exception as e:
    print(f'❌ ai_script_core import failed: {e}')
    sys.exit(1)

# Test 2: Schemas module
try:
    import ai_script_core.schemas
    print('✅ ai_script_core.schemas import successful')
except Exception as e:
    print(f'❌ ai_script_core.schemas import failed: {e}')
    sys.exit(1)

# Test 3: Project schemas
try:
    import ai_script_core.schemas.project
    from ai_script_core.schemas.project import ProjectCreateDTO
    print('✅ ai_script_core.schemas.project import successful')
except Exception as e:
    print(f'❌ ai_script_core.schemas.project import failed: {e}')
    sys.exit(1)

# Test 4: Generation schemas
try:
    import ai_script_core.schemas.generation
    from ai_script_core.schemas.generation import GenerationRequestDTO
    print('✅ ai_script_core.schemas.generation import successful')
except Exception as e:
    print(f'❌ ai_script_core.schemas.generation import failed: {e}')
    sys.exit(1)

# Test 5: Exceptions module
try:
    import ai_script_core.exceptions
    from ai_script_core.exceptions import BaseServiceException
    print('✅ ai_script_core.exceptions import successful')
except Exception as e:
    print(f'❌ ai_script_core.exceptions import failed: {e}')
    sys.exit(1)

# Test 6: Utils module
try:
    import ai_script_core.utils
    from ai_script_core.utils import generate_uuid
    print('✅ ai_script_core.utils import successful')
except Exception as e:
    print(f'❌ ai_script_core.utils import failed: {e}')
    sys.exit(1)

# Test 7: Direct imports from main package
try:
    from ai_script_core import (
        ProjectCreateDTO,
        GenerationRequestDTO,
        BaseServiceException,
        generate_uuid,
        get_service_logger
    )
    print('✅ Direct imports from ai_script_core successful')
except Exception as e:
    print(f'❌ Direct imports from ai_script_core failed: {e}')
    sys.exit(1)

print('🎉 All import matrix tests passed!')
"

if [[ $? -eq 0 ]]; then
    print_success "Import matrix verification passed"
else
    print_error "Import matrix verification failed"
    exit 1
fi

# Phase 5: Basic Functionality Test
print_header "Phase 5: Basic Functionality Test"

python3 -c "
from ai_script_core import ProjectCreateDTO, GenerationRequestDTO, AIModelConfigDTO
import uuid

# Test DTO creation
try:
    project = ProjectCreateDTO(
        name='Build Test Project',
        type='drama',
        description='Testing build functionality'
    )
    print(f'✅ ProjectCreateDTO created: {project.name}')
except Exception as e:
    print(f'❌ ProjectCreateDTO creation failed: {e}')
    exit(1)

# Test AI config
try:
    ai_config = AIModelConfigDTO(
        model_name='gpt-4',
        provider='openai'
    )
    print(f'✅ AIModelConfigDTO created: {ai_config.model_name}')
except Exception as e:
    print(f'❌ AIModelConfigDTO creation failed: {e}')
    exit(1)

# Test validation
try:
    # This should fail due to invalid model name
    bad_config = AIModelConfigDTO(
        model_name='invalid-model',
        provider='openai'
    )
    print('❌ Validation should have failed for invalid model')
    exit(1)
except ValueError:
    print('✅ Validation correctly rejected invalid model name')
except Exception as e:
    print(f'❌ Unexpected validation error: {e}')
    exit(1)

print('🎉 Basic functionality tests passed!')
"

if [[ $? -eq 0 ]]; then
    print_success "Basic functionality test passed"
else
    print_error "Basic functionality test failed"
    exit 1
fi

# Deactivate virtual environment
deactivate

print_header "Build Test Summary"
print_success "✅ Clean build successful"
print_success "✅ Distribution validation passed"
print_success "✅ Clean environment installation successful"
print_success "✅ Import matrix verification passed"
print_success "✅ Basic functionality test passed"

echo ""
echo -e "${GREEN}🎉 All build and packaging tests passed!${NC}"
echo -e "${GREEN}📦 Package is ready for production deployment${NC}"
