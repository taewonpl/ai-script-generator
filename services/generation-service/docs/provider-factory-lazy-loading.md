# Provider Factory Lazy Loading Implementation

## Overview

The Provider Factory has been enhanced with lazy loading capabilities to avoid importing all AI provider libraries at module startup. This allows the service to function with minimal dependencies and load providers only when actually needed.

## Key Features

### 1. Lazy Import Pattern
- **No Module-Level Imports**: Provider modules are only imported when needed
- **TYPE_CHECKING Guards**: Type hints are available for static analysis without runtime imports
- **Import Failure Tracking**: Failed imports are tracked and reported
- **Error Context**: Detailed error messages with installation instructions

### 2. Supported Providers
The factory supports the following provider types with lazy loading:

| Provider | Type | Dependencies | Status |
|----------|------|-------------|--------|
| OpenAI | `openai` | `pip install openai` | ✅ Implemented |
| Anthropic | `anthropic` | `pip install anthropic` | ✅ Implemented |
| Local Models | `local` | Local model dependencies | ✅ Implemented |
| Cohere | `cohere` | `pip install cohere` | ✅ Implemented |
| HuggingFace | `huggingface` | `pip install transformers torch` | ✅ Implemented |
| Azure OpenAI | `azure_openai` | `pip install openai azure-identity` | ✅ Implemented |

### 3. Enhanced Error Handling
- **Graceful Degradation**: Service continues to work even if some providers fail to import
- **Detailed Recommendations**: Specific installation instructions for each provider
- **Multiple Fallback Strategies**: Enhanced fallback provider selection
- **Health Monitoring**: Provider health checks and availability tracking

### 4. Task-Optimized Provider Selection
Provider preferences are optimized for different task types:

```python
task_preferences = {
    "creative": ["anthropic", "openai", "cohere", "local", "huggingface"],
    "analytical": ["openai", "azure_openai", "anthropic", "cohere", "local"],
    "long_form": ["anthropic", "cohere", "local", "huggingface", "openai"],
    "fast": ["local", "cohere", "openai", "anthropic", "huggingface"],
    "general": ["openai", "anthropic", "azure_openai", "cohere", "local", "huggingface"],
    "code": ["openai", "azure_openai", "anthropic", "huggingface", "local"],
    "multilingual": ["cohere", "huggingface", "anthropic", "openai", "local"]
}
```

## Implementation Details

### Lazy Import Structure

```python
# Type hints only - not imported at runtime
if TYPE_CHECKING:
    from .openai_provider import OpenAIProvider
    from .anthropic_provider import AnthropicProvider
    # ... other providers

def create_provider(self, provider_type: ProviderType, config: Dict[str, Any]):
    if provider_type == ProviderType.OPENAI:
        try:
            from .openai_provider import OpenAIProvider  # Lazy import
            return OpenAIProvider(config)
        except ImportError as e:
            # Track failure and provide helpful error message
            self._import_failures[provider_type] = str(e)
            raise ImportError(f"OpenAI provider unavailable: {e}. Install with: pip install openai")
```

### Provider Availability Checking

```python
def is_provider_available(self, provider_type: ProviderType) -> bool:
    # Quick check for previously failed imports
    if provider_type in self._import_failures:
        return False
    
    try:
        # Test import without creating instance
        if provider_type == ProviderType.OPENAI:
            from .openai_provider import OpenAIProvider
            return True
    except ImportError:
        self._import_failures[provider_type] = f"Import test failed"
        return False
```

### Enhanced Fallback Strategy

1. **Task-Specific Selection**: Try providers in order of preference for the task type
2. **Availability Pre-Check**: Skip providers known to be unavailable
3. **Health Verification**: Verify provider health before selection
4. **Multi-Strategy Fallback**: Multiple fallback strategies if primary selection fails
5. **Basic Provider Creation**: Create minimal local provider as last resort

## Usage Examples

### Basic Usage
```python
from generation_service.ai.providers.provider_factory import ProviderFactory, ProviderType

# Initialize factory (no providers imported yet)
factory = ProviderFactory(config)

# Check what providers are available
available_types = factory.get_available_provider_types()
print(f"Available: {[t.value for t in available_types]}")

# Get provider for specific task
provider = await factory.get_best_provider_for_task("creative")
```

### Debugging and Monitoring
```python
# Get comprehensive failure information
summary = factory.get_provider_failure_summary()
print("Import failures:", summary["import_failures"])
print("Recommendations:", summary["recommendations"])

# Validate configuration
validation = await factory.validate_configuration()
if not validation["is_valid"]:
    print("Issues:", validation["issues"])
    print("Warnings:", validation["warnings"])

# Get statistics
stats = factory.get_provider_statistics()
print(f"Lazy loading: {stats['lazy_loading']}")
print(f"Available providers: {stats['available_provider_types']}")
```

## Benefits

### 1. **Reduced Startup Dependencies**
- Service can start without all AI provider libraries installed
- Useful for RAG-only deployments or testing environments
- Faster startup time with fewer imports

### 2. **Improved Error Handling**
- Clear error messages with installation instructions
- Service continues to work with partial provider availability
- Comprehensive debugging and monitoring capabilities

### 3. **Enhanced Flexibility**
- Easy to add new providers without affecting existing code
- Task-optimized provider selection
- Multiple fallback strategies for reliability

### 4. **Better Development Experience**
- Unit tests can run without all dependencies
- Type hints available for IDE support
- Comprehensive validation and debugging tools

## Testing

The implementation includes comprehensive tests:

- **Unit Tests**: 18 test cases covering all lazy loading functionality
- **Integration Tests**: End-to-end workflow testing
- **Validation Scripts**: Automated validation of lazy loading behavior
- **Import Isolation Tests**: Verify no provider imports at module level

Run tests with:
```bash
PYTHONPATH=src python3 -m pytest tests/test_provider_factory_lazy_loading.py -v
```

Run validation with:
```bash
python3 scripts/validate-lazy-loading.py
```

## Migration Guide

The lazy loading implementation is backward compatible. Existing code will continue to work without changes. However, you can now:

1. **Handle Import Failures Gracefully**:
   ```python
   try:
       provider = factory.create_provider(ProviderType.OPENAI, config)
   except ImportError as e:
       print(f"OpenAI not available: {e}")
       # Use fallback or alternative provider
   ```

2. **Check Provider Availability**:
   ```python
   if factory.is_provider_available(ProviderType.OPENAI):
       provider = factory.create_provider(ProviderType.OPENAI, config)
   else:
       print("OpenAI not available, using fallback")
   ```

3. **Use Enhanced Debugging**:
   ```python
   summary = factory.get_provider_failure_summary()
   for rec in summary["recommendations"]:
       print(f"💡 {rec}")
   ```

## Future Enhancements

Planned improvements include:
- **Dynamic Provider Discovery**: Automatically detect available providers
- **Plugin Architecture**: Support for external provider plugins
- **Provider Caching**: Intelligent caching of provider instances
- **Metrics Integration**: Enhanced monitoring and metrics collection

## Conclusion

The lazy loading implementation significantly improves the Provider Factory's flexibility and reliability while maintaining backward compatibility. It enables the service to work in various deployment scenarios and provides comprehensive error handling and debugging capabilities.