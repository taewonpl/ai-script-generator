"""
Factory for creating AI providers with lazy loading
"""

import logging
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

from .base_provider import BaseProvider, ProviderStatus

# Type hints for providers (only for static analysis)
if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class ProviderType(str, Enum):
    """Available provider types"""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"
    HUGGINGFACE = "huggingface"


class ProviderFactory:
    """Factory for creating and managing AI providers with lazy loading"""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self._providers: dict[str, BaseProvider] = {}
        self._provider_configs = config.get("ai_providers", {})
        self._import_failures: dict[str, str] = {}  # Track import failures

        logger.info("Provider factory initialized with lazy loading")

    def create_provider(
        self, provider_type: ProviderType, provider_config: dict[str, Any]
    ) -> BaseProvider:
        """Create a provider instance with lazy loading"""

        try:
            if provider_type == ProviderType.OPENAI:
                # Lazy import for OpenAI provider
                try:
                    from .openai_provider import OpenAIProvider

                    return OpenAIProvider(provider_config)
                except ImportError as import_err:
                    error_msg = f"OpenAI provider unavailable: {import_err}"
                    self._import_failures[ProviderType.OPENAI] = error_msg
                    logger.error(f"Failed to import OpenAI provider: {import_err}")
                    logger.info(
                        "This usually means OpenAI dependencies are not installed"
                    )
                    raise ImportError(
                        f"{error_msg}. Install OpenAI dependencies with: pip install openai"
                    ) from import_err

            elif provider_type == ProviderType.ANTHROPIC:
                # Lazy import for Anthropic provider
                try:
                    from .anthropic_provider import AnthropicProvider

                    return AnthropicProvider(provider_config)
                except ImportError as import_err:
                    error_msg = f"Anthropic provider unavailable: {import_err}"
                    self._import_failures[ProviderType.ANTHROPIC] = error_msg
                    logger.error(f"Failed to import Anthropic provider: {import_err}")
                    logger.info(
                        "This usually means Anthropic dependencies are not installed"
                    )
                    raise ImportError(
                        f"{error_msg}. Install Anthropic dependencies with: pip install anthropic"
                    ) from import_err

            elif provider_type == ProviderType.LOCAL:
                # Lazy import for Local provider
                try:
                    from .local_provider import LocalProvider

                    return LocalProvider(provider_config)
                except ImportError as import_err:
                    error_msg = f"Local provider unavailable: {import_err}"
                    self._import_failures[ProviderType.LOCAL] = error_msg
                    logger.error(f"Failed to import Local provider: {import_err}")
                    logger.info(
                        "This usually means local model dependencies are not installed"
                    )
                    raise ImportError(
                        f"{error_msg}. Check local model dependencies"
                    ) from import_err

            elif provider_type == ProviderType.HUGGINGFACE:
                # HuggingFace provider not implemented yet
                error_msg = "HuggingFace provider not implemented"
                self._import_failures[ProviderType.HUGGINGFACE] = error_msg
                logger.error("HuggingFace provider not implemented")
                raise ImportError(
                    f"{error_msg}. Use OpenAI, Anthropic, or Local providers instead"
                )

            else:
                raise ValueError(f"Unknown provider type: {provider_type}")

        except ImportError:
            # Re-raise ImportError with context
            raise
        except Exception as e:
            logger.error(f"Failed to create {provider_type} provider: {e}")
            raise

    async def get_provider(self, model_name: str) -> Optional[BaseProvider]:
        """Get provider for a specific model"""

        # Check if we already have this provider cached
        if model_name in self._providers:
            return self._providers[model_name]

        # Find provider configuration for this model
        provider_config = self._find_provider_config(model_name)
        if not provider_config:
            logger.error(f"No provider configuration found for model: {model_name}")
            return None

        try:
            # Create and cache provider
            provider_type = ProviderType(provider_config["type"])
            provider = self.create_provider(provider_type, provider_config)
            self._providers[model_name] = provider

            logger.info(f"Created provider for model: {model_name}")
            return provider

        except Exception as e:
            logger.error(f"Failed to get provider for {model_name}: {e}")
            return None

    def _find_provider_config(self, model_name: str) -> Optional[dict[str, Any]]:
        """Find provider configuration for a model"""

        # Check direct model configurations
        if model_name in self._provider_configs:
            return self._provider_configs[model_name]

        # Check provider-based configurations
        for provider_name, config in self._provider_configs.items():
            if isinstance(config, dict):
                models = config.get("models", [])
                if model_name in models or config.get("model") == model_name:
                    return config

        # Fallback: try to infer provider from model name
        return self._infer_provider_config(model_name)

    def _infer_provider_config(self, model_name: str) -> Optional[dict[str, Any]]:
        """Infer provider configuration from model name"""

        # OpenAI models
        if any(
            prefix in model_name.lower()
            for prefix in ["gpt", "davinci", "curie", "babbage", "ada"]
        ):
            if "openai" in self._provider_configs:
                config = self._provider_configs["openai"].copy()
                config["model"] = model_name
                return config

        # Anthropic models
        if "claude" in model_name.lower():
            if "anthropic" in self._provider_configs:
                config = self._provider_configs["anthropic"].copy()
                config["model"] = model_name
                return config

        # HuggingFace models
        if any(
            prefix in model_name.lower()
            for prefix in ["hf-", "huggingface/", "meta-llama/"]
        ):
            if "huggingface" in self._provider_configs:
                config = self._provider_configs["huggingface"].copy()
                config["model"] = model_name
                return config

        # Local models (assume anything else is local)
        if "local" in self._provider_configs:
            config = self._provider_configs["local"].copy()
            config["model_name"] = model_name
            return config

        return None

    async def list_available_models(self) -> list[dict[str, Any]]:
        """List all available models from all providers"""

        models = []

        for provider_name, config in self._provider_configs.items():
            if not isinstance(config, dict):
                continue

            try:
                provider_type = ProviderType(config.get("type", provider_name))
                provider = self.create_provider(provider_type, config)

                model_info = provider.get_model_info()
                models.append(
                    {
                        "name": model_info.name,
                        "provider": model_info.provider,
                        "type": model_info.model_type.value,
                        "max_tokens": model_info.max_tokens,
                        "context_length": model_info.context_length,
                        "supports_streaming": model_info.supports_streaming,
                        "cost_per_1k_tokens": model_info.cost_per_1k_tokens,
                        "description": model_info.description,
                    }
                )

            except Exception as e:
                logger.warning(f"Failed to get model info for {provider_name}: {e}")
                continue

        return models

    async def health_check_all_providers(self) -> dict[str, ProviderStatus]:
        """Health check all configured providers"""

        results = {}

        for provider_name, config in self._provider_configs.items():
            if not isinstance(config, dict):
                continue

            try:
                provider_type = ProviderType(config.get("type", provider_name))
                provider = self.create_provider(provider_type, config)

                status = await provider.health_check()
                results[provider_name] = status

            except Exception as e:
                logger.error(f"Health check failed for {provider_name}: {e}")
                results[provider_name] = ProviderStatus.UNAVAILABLE

        return results

    def get_default_model(self) -> Optional[str]:
        """Get the default model name"""
        return self.config.get("default_model")

    async def get_best_provider_for_task(
        self, task_type: str = "general"
    ) -> Optional[BaseProvider]:
        """Get the best provider for a specific task type with enhanced fallback"""

        # Task-specific provider preferences
        task_preferences = {
            "creative": ["anthropic", "openai", "local", "huggingface"],
            "analytical": ["openai", "anthropic", "local"],
            "long_form": ["anthropic", "local", "huggingface", "openai"],
            "fast": ["local", "openai", "anthropic", "huggingface"],
            "general": ["openai", "anthropic", "local", "huggingface"],
            "code": ["openai", "anthropic", "huggingface", "local"],
            "multilingual": ["huggingface", "anthropic", "openai", "local"],
        }

        preferences = task_preferences.get(task_type, task_preferences["general"])

        # Try providers in order of preference
        for provider_name in preferences:
            if provider_name in self._provider_configs:
                try:
                    config = self._provider_configs[provider_name]
                    if isinstance(config, dict):
                        provider_type = ProviderType(config.get("type", provider_name))

                        # Check availability before creating
                        if not self.is_provider_available(provider_type):
                            logger.info(f"Skipping {provider_name}: not available")
                            continue

                        provider = self.create_provider(provider_type, config)

                        # Check if provider is healthy
                        status = await provider.health_check()
                        if status == ProviderStatus.HEALTHY:
                            logger.info(
                                f"Selected {provider_name} provider for task: {task_type}"
                            )
                            return provider
                        else:
                            logger.warning(
                                f"Provider {provider_name} unhealthy: {status}"
                            )

                except ImportError as e:
                    logger.warning(f"Cannot import {provider_name} provider: {e}")
                    continue
                except Exception as e:
                    logger.warning(f"Failed to create {provider_name} provider: {e}")
                    continue

        # Enhanced fallback strategy
        return await self._fallback_provider_selection()

    async def load_balancer_provider(self, models: list[str]) -> Optional[BaseProvider]:
        """Get provider using load balancing across multiple models with enhanced error handling"""

        import random

        if not models:
            logger.warning("Load balancer called with empty models list")
            return None

        # Shuffle models for random load balancing
        shuffled_models = models.copy()
        random.shuffle(shuffled_models)

        tried_models = []
        last_error = None

        # Try each model until we find a healthy provider
        for model in shuffled_models:
            try:
                tried_models.append(model)
                provider = await self.get_provider(model)

                if provider:
                    try:
                        status = await provider.health_check()
                        if status == ProviderStatus.HEALTHY:
                            logger.info(f"Load balancer selected model: {model}")
                            return provider
                        else:
                            logger.warning(
                                f"Load balancer: model {model} unhealthy ({status})"
                            )

                    except Exception as health_error:
                        logger.warning(
                            f"Load balancer: health check failed for {model}: {health_error}"
                        )
                        last_error = health_error
                        continue

                else:
                    logger.warning(f"Load balancer: failed to get provider for {model}")

            except Exception as e:
                logger.warning(f"Load balancer: error with model {model}: {e}")
                last_error = e
                continue

        logger.error(
            f"Load balancer failed for all models {tried_models}. Last error: {last_error}"
        )

        # Try fallback selection as last resort
        logger.info("Load balancer attempting fallback provider selection...")
        return await self._fallback_provider_selection()

    def is_provider_available(self, provider_type: ProviderType) -> bool:
        """Check if a provider type is available (can be imported)"""

        # Quick check for previous import failures
        if provider_type in self._import_failures:
            return False

        try:
            # Test lazy import without creating instance
            if provider_type == ProviderType.OPENAI:
                from .openai_provider import OpenAIProvider

                return True
            elif provider_type == ProviderType.ANTHROPIC:
                from .anthropic_provider import AnthropicProvider

                return True
            elif provider_type == ProviderType.LOCAL:
                from .local_provider import LocalProvider

                return True
            elif provider_type == ProviderType.HUGGINGFACE:
                from .huggingface_provider import HuggingFaceProvider

                return True
            else:
                return False
        except ImportError:
            self._import_failures[provider_type] = (
                f"Import test failed for {provider_type}"
            )
            return False

    def get_available_provider_types(self) -> list[ProviderType]:
        """Get list of available provider types (can be imported)"""

        available = []
        for provider_type in ProviderType:
            if self.is_provider_available(provider_type):
                available.append(provider_type)

        return available

    def get_import_failures(self) -> dict[str, str]:
        """Get details about provider import failures"""
        return self._import_failures.copy()

    def get_provider_statistics(self) -> dict[str, Any]:
        """Get statistics about cached providers and availability"""

        available_types = self.get_available_provider_types()

        stats = {
            "total_providers": len(self._providers),
            "configured_providers": len(self._provider_configs),
            "cached_providers": list(self._providers.keys()),
            "all_provider_types": [pt.value for pt in ProviderType],
            "available_provider_types": [pt.value for pt in available_types],
            "unavailable_provider_types": [
                pt.value for pt in ProviderType if pt not in available_types
            ],
            "import_failures": len(self._import_failures),
            "lazy_loading": True,
        }

        return stats

    async def _fallback_provider_selection(self) -> Optional[BaseProvider]:
        """Enhanced fallback provider selection strategy"""

        logger.info("Attempting fallback provider selection...")

        # Strategy 1: Try any available provider regardless of task preference
        available_types = self.get_available_provider_types()
        if available_types:
            for provider_type in available_types:
                try:
                    # Find config for this provider type
                    for provider_name, config in self._provider_configs.items():
                        if (
                            isinstance(config, dict)
                            and config.get("type") == provider_type.value
                        ):
                            provider = self.create_provider(provider_type, config)
                            status = await provider.health_check()
                            if status == ProviderStatus.HEALTHY:
                                logger.info(
                                    f"Fallback: Selected {provider_type.value} provider"
                                )
                                return provider
                            break
                except Exception as e:
                    logger.warning(f"Fallback failed for {provider_type.value}: {e}")
                    continue

        # Strategy 2: Try default model if configured
        default_model = self.get_default_model()
        if default_model:
            try:
                provider = await self.get_provider(default_model)
                if provider:
                    logger.info(f"Fallback: Using default model {default_model}")
                    return provider
            except Exception as e:
                logger.warning(f"Default model fallback failed: {e}")

        # Strategy 3: Create basic local provider if no config exists
        if ProviderType.LOCAL in available_types:
            try:
                basic_config = {"type": "local", "model_name": "default"}
                provider = self.create_provider(ProviderType.LOCAL, basic_config)
                logger.warning(
                    "Fallback: Using basic local provider with minimal config"
                )
                return provider
            except Exception as e:
                logger.error(f"Basic local provider fallback failed: {e}")

        logger.error("All fallback strategies failed - no providers available")
        return None

    def get_provider_failure_summary(self) -> dict[str, Any]:
        """Get detailed summary of provider failures for debugging"""

        summary = {
            "import_failures": self.get_import_failures(),
            "available_types": [t.value for t in self.get_available_provider_types()],
            "configured_providers": list(self._provider_configs.keys()),
            "cached_providers": list(self._providers.keys()),
            "recommendations": [],
        }

        # Add recommendations based on failures
        if not summary["available_types"]:
            summary["recommendations"].append(
                "No AI providers available - install dependencies"
            )

        if not summary["configured_providers"]:
            summary["recommendations"].append(
                "No providers configured - check configuration"
            )

        if summary["import_failures"]:
            for provider, error in summary["import_failures"].items():
                if "openai" in error.lower():
                    summary["recommendations"].append(
                        "Install OpenAI: pip install openai"
                    )
                elif "anthropic" in error.lower():
                    summary["recommendations"].append(
                        "Install Anthropic: pip install anthropic"
                    )
                elif "huggingface" in error.lower():
                    summary["recommendations"].append(
                        "Install HuggingFace: pip install transformers torch"
                    )
                elif "local" in error.lower():
                    summary["recommendations"].append("Check local model dependencies")

        return summary

    async def validate_configuration(self) -> dict[str, Any]:
        """Validate provider configuration and return detailed status"""

        validation_result = {
            "is_valid": True,
            "providers": {},
            "issues": [],
            "warnings": [],
        }

        if not self._provider_configs:
            validation_result["is_valid"] = False
            validation_result["issues"].append("No provider configurations found")
            return validation_result

        # Validate each configured provider
        for provider_name, config in self._provider_configs.items():
            provider_status = {
                "configured": False,
                "importable": False,
                "healthy": False,
                "error": None,
            }

            if isinstance(config, dict) and "type" in config:
                provider_status["configured"] = True

                try:
                    provider_type = ProviderType(config["type"])

                    # Check if importable
                    if self.is_provider_available(provider_type):
                        provider_status["importable"] = True

                        # Check if healthy
                        try:
                            provider = self.create_provider(provider_type, config)
                            health_status = await provider.health_check()
                            provider_status["healthy"] = (
                                health_status == ProviderStatus.HEALTHY
                            )

                            if not provider_status["healthy"]:
                                provider_status["error"] = (
                                    f"Health check failed: {health_status}"
                                )

                        except Exception as e:
                            provider_status["error"] = f"Provider creation failed: {e}"

                    else:
                        provider_status["error"] = (
                            "Import failed - dependencies not available"
                        )

                except ValueError as e:
                    provider_status["error"] = f"Invalid provider type: {e}"
                    validation_result["is_valid"] = False

            else:
                provider_status["error"] = "Invalid configuration format"
                validation_result["is_valid"] = False

            validation_result["providers"][provider_name] = provider_status

            # Add warnings for non-critical issues
            if provider_status["configured"] and not provider_status["importable"]:
                validation_result["warnings"].append(
                    f"Provider {provider_name} configured but not importable"
                )

            if provider_status["importable"] and not provider_status["healthy"]:
                validation_result["warnings"].append(
                    f"Provider {provider_name} importable but not healthy"
                )

        # Check if at least one provider is fully functional
        healthy_providers = [
            name
            for name, status in validation_result["providers"].items()
            if status.get("healthy", False)
        ]

        if not healthy_providers:
            validation_result["is_valid"] = False
            validation_result["issues"].append("No healthy providers available")

        return validation_result

    async def cleanup(self):
        """Cleanup resources"""

        for provider in self._providers.values():
            if hasattr(provider, "client") and hasattr(provider.client, "aclose"):
                try:
                    await provider.client.aclose()
                except Exception as e:
                    logger.warning(f"Error closing provider client: {e}")

        self._providers.clear()
        logger.info("Provider factory cleaned up")
