"""
OpenAI provider for GPT-4o model with Core Module integration
"""

import logging
import time
from collections.abc import AsyncGenerator
from typing import Any, Optional

import openai
from openai import AsyncOpenAI

from .base_provider import (
    CORE_AVAILABLE,
    BaseProvider,
    GenerationRequest,
    GenerationResponse,
    ModelInfo,
    ModelType,
    ProviderConnectionError,
    ProviderError,
    ProviderQuotaError,
    ProviderRateLimitError,
)

# Import Core Module components
try:
    from ai_script_core import (
        calculate_hash,
        get_service_logger,
        safe_json_dumps,
        utc_now,
    )

    CORE_AVAILABLE = True
    logger = get_service_logger("generation-service.openai_provider")
except (ImportError, RuntimeError):
    CORE_AVAILABLE = False
    import logging

    logger = logging.getLogger(__name__)

    # Fallback utility functions
    def utc_now():
        """Fallback UTC timestamp"""
        from datetime import datetime, timezone

        return datetime.now(timezone.utc)

    def generate_uuid():
        """Fallback UUID generation"""
        import uuid

        return str(uuid.uuid4())

    def generate_id():
        """Fallback ID generation"""
        import uuid

        return str(uuid.uuid4())[:8]

    # Fallback base classes
    class BaseDTO:
        """Fallback base DTO class"""

        pass

    class SuccessResponseDTO:
        """Fallback success response DTO"""

        pass

    class ErrorResponseDTO:
        """Fallback error response DTO"""

        pass


class OpenAIProvider(BaseProvider):
    """OpenAI GPT-4o provider implementation"""

    def __init__(self, config: dict[str, Any]):
        super().__init__("openai", config)

        self.api_key = config.get("api_key")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")

        self.model = config.get("model", "gpt-4o")
        self.organization = config.get("organization")
        self.base_url = config.get("base_url")

        # Initialize OpenAI client
        self.client = AsyncOpenAI(
            api_key=self.api_key, organization=self.organization, base_url=self.base_url
        )

        # Core Module enhanced logging
        if CORE_AVAILABLE:
            logger.info(
                "OpenAI provider initialized with Core integration",
                extra={
                    "provider_id": self.provider_id,
                    "model": self.model,
                    "organization": self.organization,
                    "base_url": self.base_url,
                    "config_hash": calculate_hash(
                        safe_json_dumps(
                            {
                                "model": self.model,
                                "organization": self.organization,
                                "base_url": self.base_url,
                            }
                        )
                    ),
                },
            )
        else:
            logger.info(f"OpenAI provider initialized with model: {self.model}")

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Generate content using OpenAI GPT-4o with Core Module integration"""

        start_time = utc_now() if CORE_AVAILABLE else time.time()
        request_id = getattr(request, "request_id", "unknown")

        # Core Module structured logging
        if CORE_AVAILABLE:
            logger.info(
                "Starting OpenAI generation",
                extra={
                    "provider_id": self.provider_id,
                    "model": self.model,
                    "request_id": request_id,
                    "prompt_length": len(request.prompt),
                    "max_tokens": request.max_tokens,
                    "temperature": request.temperature,
                },
            )

        try:
            # Prepare messages
            messages = []
            if request.system_prompt:
                messages.append({"role": "system", "content": request.system_prompt})
            messages.append({"role": "user", "content": request.prompt})

            # Prepare parameters
            params = {
                "model": self.model,
                "messages": messages,
                "temperature": request.temperature,
                "top_p": request.top_p,
                "stream": False,
            }

            if request.max_tokens:
                params["max_tokens"] = request.max_tokens

            if request.stop_sequences:
                params["stop"] = request.stop_sequences

            # Add additional parameters
            if request.additional_params:
                params.update(request.additional_params)

            # Make API call
            response = await self.client.chat.completions.create(**params)

            if CORE_AVAILABLE:
                generation_time = (utc_now() - start_time).total_seconds()
            else:
                generation_time = time.time() - start_time

            # Extract response data
            choice = response.choices[0]
            content = choice.message.content
            finish_reason = choice.finish_reason

            # Calculate tokens used
            tokens_used = response.usage.total_tokens if response.usage else 0

            # Core Module enhanced response logging
            if CORE_AVAILABLE:
                logger.info(
                    "OpenAI generation completed",
                    extra={
                        "provider_id": self.provider_id,
                        "model": self.model,
                        "request_id": request_id,
                        "tokens_used": tokens_used,
                        "generation_time_ms": int(generation_time * 1000),
                        "content_length": len(content) if content else 0,
                        "finish_reason": finish_reason,
                        "cost_estimate": self._calculate_cost(tokens_used),
                    },
                )

            # Create response with Core integration
            response_data = {
                "content": content,
                "finish_reason": finish_reason,
                "model_info": self.get_model_info(),
            }

            if CORE_AVAILABLE:
                response_data.update(
                    {
                        "request_id": request_id,
                        "created_at": utc_now(),
                        "metadata": {
                            "tokens_used": tokens_used,
                            "generation_time_seconds": generation_time,
                            "cost_estimate": self._calculate_cost(tokens_used),
                            "model_used": self.model,
                            "provider_used": self.name,
                        },
                    }
                )

            return GenerationResponse(**response_data)

        except openai.RateLimitError as e:
            logger.warning(f"OpenAI rate limit exceeded: {e}")
            raise ProviderRateLimitError(str(e), self.name) from e

        except openai.AuthenticationError as e:
            logger.error(f"OpenAI authentication error: {e}")
            raise ProviderError(f"Authentication failed: {e}", self.name) from e

        except openai.PermissionDeniedError as e:
            logger.error(f"OpenAI permission denied: {e}")
            raise ProviderQuotaError(f"Permission denied: {e}", self.name) from e

        except openai.APIConnectionError as e:
            logger.error(f"OpenAI connection error: {e}")
            raise ProviderConnectionError(f"Connection failed: {e}", self.name) from e

        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise ProviderError(f"API error: {e}", self.name) from e

        except Exception as e:
            logger.error(f"Unexpected error in OpenAI provider: {e}")
            raise ProviderError(f"Unexpected error: {e}", self.name) from e

    async def generate_stream(
        self, request: GenerationRequest
    ) -> AsyncGenerator[str, None]:
        """Generate content with streaming response"""

        try:
            # Prepare messages
            messages = []
            if request.system_prompt:
                messages.append({"role": "system", "content": request.system_prompt})
            messages.append({"role": "user", "content": request.prompt})

            # Prepare parameters
            params = {
                "model": self.model,
                "messages": messages,
                "temperature": request.temperature,
                "top_p": request.top_p,
                "stream": True,
            }

            if request.max_tokens:
                params["max_tokens"] = request.max_tokens

            if request.stop_sequences:
                params["stop"] = request.stop_sequences

            # Add additional parameters
            if request.additional_params:
                params.update(request.additional_params)

            # Make streaming API call
            stream = await self.client.chat.completions.create(**params)

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except openai.RateLimitError as e:
            logger.warning(f"OpenAI rate limit exceeded: {e}")
            raise ProviderRateLimitError(str(e), self.name) from e

        except openai.AuthenticationError as e:
            logger.error(f"OpenAI authentication error: {e}")
            raise ProviderError(f"Authentication failed: {e}", self.name) from e

        except openai.APIConnectionError as e:
            logger.error(f"OpenAI connection error: {e}")
            raise ProviderConnectionError(f"Connection failed: {e}", self.name) from e

        except Exception as e:
            logger.error(f"Unexpected error in OpenAI streaming: {e}")
            raise ProviderError(f"Streaming error: {e}", self.name) from e

    async def validate_connection(self) -> bool:
        """Validate connection to OpenAI"""

        try:
            # Test with a simple request
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Test"}],
                max_tokens=1,
            )
            return True

        except openai.AuthenticationError:
            logger.error("OpenAI authentication failed")
            return False

        except openai.PermissionDeniedError:
            logger.error("OpenAI permission denied")
            return False

        except Exception as e:
            logger.error(f"OpenAI connection validation failed: {e}")
            return False

    def get_model_info(self) -> ModelInfo:
        """Get OpenAI model information"""

        # Model configurations for different GPT-4o variants
        model_configs = {
            "gpt-4o": {
                "max_tokens": 4096,
                "context_length": 128000,
                "cost_per_1k_tokens": 0.03,
                "description": "GPT-4o - Latest multimodal model",
            },
            "gpt-4o-mini": {
                "max_tokens": 16384,
                "context_length": 128000,
                "cost_per_1k_tokens": 0.00015,
                "description": "GPT-4o Mini - Faster and cheaper variant",
            },
            "gpt-4": {
                "max_tokens": 4096,
                "context_length": 8192,
                "cost_per_1k_tokens": 0.06,
                "description": "GPT-4 - High capability model",
            },
        }

        config = model_configs.get(self.model, model_configs["gpt-4o"])

        return ModelInfo(
            name=self.model,
            provider="openai",
            model_type=ModelType.OPENAI_GPT4O,
            max_tokens=config["max_tokens"],
            context_length=config["context_length"],
            supports_streaming=True,
            cost_per_1k_tokens=config["cost_per_1k_tokens"],
            description=config["description"],
        )

    async def list_available_models(self) -> list:
        """List available OpenAI models"""
        try:
            models = await self.client.models.list()
            return [model.id for model in models.data if "gpt" in model.id]
        except Exception as e:
            logger.error(f"Failed to list OpenAI models: {e}")
            return []

    async def get_usage_stats(self) -> Optional[dict[str, Any]]:
        """Get usage statistics (if available)"""
        # OpenAI doesn't provide direct usage stats via API
        # This could be implemented with external tracking
        return {
            "provider": self.name,
            "model": self.model,
            "status": "Usage stats not available via API",
        }
