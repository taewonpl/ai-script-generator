# Release Checklist for AI Script Core

This checklist ensures all quality gates are met before releasing a new version.

## Pre-Release Validation

### 1. Code Quality ✅
- [ ] All tests pass (`python -m pytest tests/`)
- [ ] Static analysis passes (`./scripts/lint.sh`)
- [ ] Runtime validation passes (`python scripts/runtime_test.py`)
- [ ] Build test passes (`./scripts/build_test.sh`)
- [ ] API surface tests pass (`python -m pytest tests/test_api_surface.py`)
- [ ] No TODO/FIXME comments in production code
- [ ] All public functions have docstrings

### 2. Documentation ✅
- [ ] CHANGELOG.md updated with new features/fixes
- [ ] Version number updated in all files
- [ ] README.md reflects current functionality
- [ ] API documentation is up to date
- [ ] Breaking changes documented (if any)

### 3. Version Management ✅
- [ ] Version consistency check passes (`python scripts/version_bump.py check`)
- [ ] Version follows semantic versioning (MAJOR.MINOR.PATCH)
- [ ] Version bump appropriate for changes made
- [ ] Git tag matches version number

### 4. Security & Dependencies ✅
- [ ] Dependency security scan passes
- [ ] No known vulnerabilities in dependencies
- [ ] No hardcoded secrets or sensitive information
- [ ] All dependencies have compatible licenses

### 5. Compatibility Testing ✅
- [ ] Tests pass on Python 3.10
- [ ] Tests pass on Python 3.11  
- [ ] Tests pass on Python 3.12
- [ ] Pydantic v2 compatibility verified
- [ ] FastAPI integration tested
- [ ] Import paths work correctly

## Release Process

### 1. Prepare Release
```bash
# Run full validation suite
./scripts/validate_production.sh

# Update version (choose appropriate bump type)
python scripts/version_bump.py bump --type patch  # or minor/major

# Update CHANGELOG.md with new version and release date
# Commit version bump
git add .
git commit -m "chore: bump version to X.Y.Z"
```

### 2. Create Release
```bash
# Create and push tag
git tag vX.Y.Z
git push origin vX.Y.Z

# Create GitHub release (triggers CI/CD)
# Go to GitHub > Releases > Create new release
# Use tag vX.Y.Z, copy relevant CHANGELOG section
```

### 3. Post-Release Verification
- [ ] GitHub Actions CI/CD pipeline completes successfully
- [ ] Package published to PyPI
- [ ] Package installable from PyPI (`pip install ai-script-core==X.Y.Z`)
- [ ] All import tests pass with PyPI version
- [ ] Documentation deployed successfully

### 4. Communication
- [ ] Release announcement prepared
- [ ] Breaking changes communicated (if any)
- [ ] Migration guide updated (if needed)
- [ ] Community notified through appropriate channels

## Emergency Hotfix Process

For critical bugs requiring immediate release:

1. Create hotfix branch from main: `git checkout -b hotfix/X.Y.Z main`
2. Make minimal fix
3. Run abbreviated test suite: `python scripts/runtime_test.py`
4. Bump patch version: `python scripts/version_bump.py bump --type patch`
5. Update CHANGELOG.md
6. Create PR to main
7. After merge, create release tag immediately

## Rollback Process

If a release has critical issues:

1. **Immediate**: Remove package from PyPI (if possible)
2. **Short-term**: Create hotfix release with fix
3. **Communication**: Notify users of issue and remediation
4. **Post-mortem**: Document what went wrong and how to prevent

## Quality Gates

### Automated (CI/CD)
- ✅ Linting (ruff)
- ✅ Type checking (mypy)
- ✅ Unit tests (pytest)
- ✅ Security scanning (bandit, safety)
- ✅ Build validation
- ✅ Import matrix testing

### Manual (Release Manager)
- ✅ Functional testing with real-world scenarios
- ✅ Documentation review
- ✅ Breaking change assessment
- ✅ Version number validation
- ✅ Release notes review

## Version Strategy

### Semantic Versioning Rules
- **MAJOR** (X.0.0): Breaking API changes
- **MINOR** (X.Y.0): New features, backward compatible
- **PATCH** (X.Y.Z): Bug fixes, backward compatible

### Pre-release Versions
- **Alpha** (X.Y.Z-alpha.N): Early development, API unstable
- **Beta** (X.Y.Z-beta.N): Feature complete, API stable, testing phase
- **RC** (X.Y.Z-rc.N): Release candidate, final testing

## Support Policy

- **Current version (X.Y.Z)**: Full support, new features
- **Previous minor (X.Y-1.*)**: Security fixes only
- **Older versions**: End of life, no support

## Contact

For release-related questions or issues:
- **Release Manager**: [GitHub Issues](https://github.com/ai-script-generator/ai-script-generator-v3/issues)
- **Security Issues**: [Security Policy](SECURITY.md)
- **General Questions**: [Discussions](https://github.com/ai-script-generator/ai-script-generator-v3/discussions)