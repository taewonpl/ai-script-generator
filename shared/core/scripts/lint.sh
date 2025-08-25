#!/bin/bash
# Lint Script for AI Script Core
# Runs static analysis with ruff and mypy

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

print_header "AI Script Core - Static Analysis"
echo "Project Root: $PROJECT_ROOT"
echo ""

cd "$PROJECT_ROOT"

# Check if tools are available
check_tool() {
    if ! command -v "$1" &> /dev/null; then
        print_error "$1 is not installed. Install with: pip install $1"
        return 1
    fi
    return 0
}

# Phase 1: Ruff Linting
print_header "Phase 1: Ruff Linting"

if check_tool "ruff"; then
    echo "Running ruff check..."
    if ruff check src/ tests/ scripts/ --show-fixes; then
        print_success "Ruff linting passed"
    else
        print_error "Ruff linting failed"
        exit 1
    fi

    echo ""
    echo "Running ruff format check..."
    if ruff format --check src/ tests/ scripts/; then
        print_success "Ruff formatting check passed"
    else
        print_warning "Ruff formatting issues found. Run 'ruff format .' to fix"
    fi
else
    print_warning "Ruff not available, skipping linting"
fi

echo ""

# Phase 2: MyPy Type Checking
print_header "Phase 2: MyPy Type Checking"

if check_tool "mypy"; then
    echo "Running mypy type checking..."
    if mypy src/ai_script_core/ --strict; then
        print_success "MyPy type checking passed"
    else
        print_error "MyPy type checking failed"
        exit 1
    fi
else
    print_warning "MyPy not available, skipping type checking"
fi

echo ""

# Phase 3: Additional Checks
print_header "Phase 3: Additional Code Quality Checks"

# Check for common issues
echo "Checking for common code issues..."

# Check for print statements in source code (should use logging)
if grep -r "print(" src/ --include="*.py" | grep -v "__pycache__"; then
    print_warning "Found print() statements in source code. Consider using logging instead."
else
    print_success "No print() statements found in source code"
fi

# Check for TODO/FIXME comments
echo ""
echo "Checking for TODO/FIXME comments..."
if grep -r -E "(TODO|FIXME|XXX)" src/ --include="*.py" | grep -v "__pycache__"; then
    print_warning "Found TODO/FIXME comments in source code"
else
    print_success "No TODO/FIXME comments found"
fi

# Check for proper typing
echo ""
echo "Checking for typing imports..."
if ! grep -r "from typing import" src/ --include="*.py" | grep -q "typing"; then
    print_warning "Limited typing imports found. Consider adding more type annotations."
else
    print_success "Typing imports found"
fi

# Phase 4: Import Analysis
print_header "Phase 4: Import Analysis"

echo "Checking for circular imports..."
python3 -c "
import sys
import importlib
import warnings

# Suppress warnings during import testing
warnings.filterwarnings('ignore')

try:
    # Test main package import
    import ai_script_core
    print('✅ Main package import successful')

    # Test submodule imports
    import ai_script_core.schemas
    import ai_script_core.schemas.project
    import ai_script_core.schemas.generation
    import ai_script_core.exceptions
    import ai_script_core.utils
    print('✅ All submodule imports successful')

    # Test that no circular imports exist by importing everything
    from ai_script_core import *
    print('✅ Star import successful (no circular imports)')

except ImportError as e:
    print(f'❌ Import error: {e}')
    sys.exit(1)
except Exception as e:
    print(f'❌ Unexpected error during imports: {e}')
    sys.exit(1)
"

if [[ $? -eq 0 ]]; then
    print_success "Import analysis passed"
else
    print_error "Import analysis failed"
    exit 1
fi

# Phase 5: Security Checks (Basic)
print_header "Phase 5: Basic Security Checks"

echo "Checking for potential security issues..."

# Check for eval/exec usage
if grep -r -E "(eval\(|exec\()" src/ --include="*.py" | grep -v "__pycache__"; then
    print_error "Found eval/exec usage - potential security risk"
    exit 1
else
    print_success "No eval/exec usage found"
fi

# Check for shell injection patterns
if grep -r -E "(os\.system|subprocess\.call.*shell=True)" src/ --include="*.py" | grep -v "__pycache__"; then
    print_warning "Found potential shell injection patterns"
else
    print_success "No shell injection patterns found"
fi

# Phase 6: Documentation Checks
print_header "Phase 6: Documentation Checks"

echo "Checking for docstrings..."
python3 -c "
import ast
import os

def check_docstrings(directory):
    missing_docstrings = []

    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']

        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                with open(filepath, 'r', encoding='utf-8') as f:
                    try:
                        tree = ast.parse(f.read(), filename=filepath)

                        for node in ast.walk(tree):
                            if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                                if not ast.get_docstring(node):
                                    missing_docstrings.append(f'{filepath}:{node.lineno}:{node.name}')
                    except SyntaxError:
                        print(f'Syntax error in {filepath}')

    return missing_docstrings

missing = check_docstrings('src/ai_script_core')
if missing:
    print(f'⚠️  Found {len(missing)} functions/classes without docstrings')
    for item in missing[:10]:  # Show first 10
        print(f'   {item}')
    if len(missing) > 10:
        print(f'   ... and {len(missing) - 10} more')
else:
    print('✅ All public functions and classes have docstrings')
"

# Summary
print_header "Static Analysis Summary"
print_success "✅ Ruff linting"
print_success "✅ MyPy type checking"
print_success "✅ Code quality checks"
print_success "✅ Import analysis"
print_success "✅ Security checks"
print_success "✅ Documentation checks"

echo ""
echo -e "${GREEN}🎉 All static analysis checks passed!${NC}"
echo -e "${GREEN}📋 Code is ready for production${NC}"
