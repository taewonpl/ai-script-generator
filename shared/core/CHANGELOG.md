# Changelog

All notable changes to the AI Script Core library will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive test suite with 85%+ coverage
- Production-ready packaging with PEP 621 compliance
- Static analysis with ruff and mypy
- CI/CD pipeline with GitHub Actions
- Security scanning with bandit and safety
- API surface protection and stability tests

### Changed
- Upgraded to full Pydantic v2 compatibility with ConfigDict
- Replaced `@validator` with `@field_validator` decorators
- Added `protected_namespaces=()` to prevent model_ prefix warnings
- Streamlined public API to essential symbols only

### Fixed
- All Pydantic v2 deprecation warnings resolved
- Import path standardization for better compatibility
- Enhanced error messages for validation failures

## [0.1.0] - 2024-01-15

### Added
- Initial release of AI Script Core library
- **Schemas Module**: Pydantic-based DTOs for microservices communication
  - `ProjectCreateDTO`, `ProjectUpdateDTO`, `ProjectResponseDTO`
  - `EpisodeCreateDTO`, `EpisodeUpdateDTO`, `EpisodeResponseDTO`
  - `GenerationRequestDTO`, `GenerationResponseDTO`
  - `AIModelConfigDTO`, `RAGConfigDTO`
  - Base schemas with mixins (`BaseSchema`, `IDMixin`, `TimestampMixin`)
  - Common response types and pagination support

- **Exceptions Module**: Comprehensive error handling system
  - `BaseServiceException` with severity and category classification
  - Service-specific exceptions (`ProjectServiceError`, `GenerationServiceError`, etc.)
  - Utility decorators and formatters for error handling
  - Structured error responses with context tracking

- **Utils Module**: Essential utility functions
  - Configuration management with Pydantic settings
  - Structured JSON logging with service context
  - UUID generation utilities
  - Date/time formatting and processing
  - Text sanitization and processing
  - Service health monitoring utilities
  - Safe JSON operations

- **Core Features**:
  - 32+ exception classes for comprehensive error handling
  - 44+ utility functions for common operations
  - Type-safe APIs with full type hints
  - FastAPI integration support
  - Environment-based configuration
  - Microservices-ready architecture

### Technical Details
- Python 3.9+ support
- Pydantic 2.5+ compatibility
- FastAPI 0.104+ integration
- Comprehensive test coverage (630+ tests)
- Standard packaging with setuptools
- MIT license

### Development
- Modular architecture supporting microservices
- Backward compatibility aliases for smooth migration
- Extensive documentation and examples
- Development tools integration (pytest, mypy, ruff)

---

## Version History Summary

| Version | Release Date | Key Features |
|---------|-------------|--------------|
| 0.1.0   | 2024-01-15  | Initial release with schemas, exceptions, and utilities |

## Migration Guide

### From Pre-1.0 Versions
This is the initial stable release. No migration needed.

### Future Breaking Changes
We follow semantic versioning. Breaking changes will only occur in major version releases (e.g., 1.0.0 → 2.0.0).

## Contributing

Please see our [Contributing Guidelines](CONTRIBUTING.md) for information on how to contribute to this project.

## Support

- **Documentation**: [https://ai-script-generator.readthedocs.io/](https://ai-script-generator.readthedocs.io/)
- **Issues**: [GitHub Issues](https://github.com/ai-script-generator/ai-script-generator-v3/issues)
- **Discussions**: [GitHub Discussions](https://github.com/ai-script-generator/ai-script-generator-v3/discussions)