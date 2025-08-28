"""
Anthropic provider for Claude 3.5 Sonnet model with Core Module integration
"""

import logging
import time
from collections.abc import AsyncGenerator
from typing import Any, Optional

import anthropic
from anthropic import AsyncAnthropic

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
    logger = get_service_logger("generation-service.anthropic_provider")
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


class AnthropicProvider(BaseProvider):
    """Anthropic Claude 3.5 Sonnet provider implementation"""

    def __init__(self, config: dict[str, Any]):
        super().__init__("anthropic", config)

        self.api_key = config.get("api_key")
        if not self.api_key:
            raise ValueError("Anthropic API key is required")

        self.model = config.get("model", "claude-3-5-sonnet-20241022")
        self.base_url = config.get("base_url")

        # Initialize Anthropic client
        client_kwargs = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        self.client = AsyncAnthropic(**client_kwargs)

        # Core Module enhanced logging
        if CORE_AVAILABLE:
            logger.info(
                "Anthropic provider initialized with Core integration",
                extra={
                    "provider_id": self.provider_id,
                    "model": self.model,
                    "base_url": self.base_url,
                    "context_length": self.get_model_info().context_length,
                    "config_hash": calculate_hash(
                        safe_json_dumps(
                            {"model": self.model, "base_url": self.base_url}
                        )
                    ),
                },
            )
        else:
            logger.info(f"Anthropic provider initialized with model: {self.model}")

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Generate content using Anthropic Claude"""

        start_time = time.time()

        try:
            # Prepare parameters
            params = {
                "model": self.model,
                "messages": [{"role": "user", "content": request.prompt}],
                "temperature": request.temperature,
                "top_p": request.top_p,
                "stream": False,
            }

            if request.max_tokens:
                params["max_tokens"] = min(request.max_tokens, 4096)
            else:
                params["max_tokens"] = 4096

            if request.stop_sequences:
                params["stop_sequences"] = request.stop_sequences

            if request.system_prompt:
                params["system"] = request.system_prompt

            # Add additional parameters
            if request.additional_params:
                # Filter valid Anthropic parameters
                valid_params = ["top_k", "metadata", "tools", "tool_choice"]
                for key, value in request.additional_params.items():
                    if key in valid_params:
                        params[key] = value

            # Make API call
            response = await self.client.messages.create(**params)

            generation_time = time.time() - start_time

            # Extract response data
            content = ""
            if response.content:
                content = (
                    response.content[0].text
                    if response.content[0].type == "text"
                    else ""
                )

            finish_reason = response.stop_reason or "completed"

            # Calculate tokens used
            tokens_used = (
                response.usage.input_tokens + response.usage.output_tokens
                if response.usage
                else 0
            )

            # Create metrics
            metrics = self._create_metrics(tokens_used, generation_time, self.model)

            return GenerationResponse(
                content=content,
                finish_reason=finish_reason,
                metrics=metrics,
                model_info=self.get_model_info(),
            )

        except anthropic.RateLimitError as e:
            logger.warning(f"Anthropic rate limit exceeded: {e}")
            raise ProviderRateLimitError(str(e), self.name) from e

        except anthropic.AuthenticationError as e:
            logger.error(f"Anthropic authentication error: {e}")
            raise ProviderError(f"Authentication failed: {e}", self.name) from e

        except anthropic.PermissionDeniedError as e:
            logger.error(f"Anthropic permission denied: {e}")
            raise ProviderQuotaError(f"Permission denied: {e}", self.name) from e

        except anthropic.APIConnectionError as e:
            logger.error(f"Anthropic connection error: {e}")
            raise ProviderConnectionError(f"Connection failed: {e}", self.name) from e

        except anthropic.APIError as e:
            logger.error(f"Anthropic API error: {e}")
            raise ProviderError(f"API error: {e}", self.name) from e

        except Exception as e:
            logger.error(f"Unexpected error in Anthropic provider: {e}")
            raise ProviderError(f"Unexpected error: {e}", self.name) from e

    async def generate_stream(
        self, request: GenerationRequest
    ) -> AsyncGenerator[str, None]:
        """Generate content with streaming response"""

        try:
            # Prepare parameters
            params = {
                "model": self.model,
                "messages": [{"role": "user", "content": request.prompt}],
                "temperature": request.temperature,
                "top_p": request.top_p,
                "stream": True,
            }

            if request.max_tokens:
                params["max_tokens"] = min(request.max_tokens, 4096)
            else:
                params["max_tokens"] = 4096

            if request.stop_sequences:
                params["stop_sequences"] = request.stop_sequences

            if request.system_prompt:
                params["system"] = request.system_prompt

            # Add additional parameters
            if request.additional_params:
                valid_params = ["top_k", "metadata"]
                for key, value in request.additional_params.items():
                    if key in valid_params:
                        params[key] = value

            # Make streaming API call
            async with self.client.messages.stream(**params) as stream:
                async for text in stream.text_stream:
                    yield text

        except anthropic.RateLimitError as e:
            logger.warning(f"Anthropic rate limit exceeded: {e}")
            raise ProviderRateLimitError(str(e), self.name) from e

        except anthropic.AuthenticationError as e:
            logger.error(f"Anthropic authentication error: {e}")
            raise ProviderError(f"Authentication failed: {e}", self.name) from e

        except anthropic.APIConnectionError as e:
            logger.error(f"Anthropic connection error: {e}")
            raise ProviderConnectionError(f"Connection failed: {e}", self.name) from e

        except Exception as e:
            logger.error(f"Unexpected error in Anthropic streaming: {e}")
            raise ProviderError(f"Streaming error: {e}", self.name) from e

    async def validate_connection(self) -> bool:
        """Validate connection to Anthropic"""

        try:
            # Test with a simple request
            response = await self.client.messages.create(
                model=self.model,
                messages=[{"role": "user", "content": "Test"}],
                max_tokens=1,
            )
            return True

        except anthropic.AuthenticationError:
            logger.error("Anthropic authentication failed")
            return False

        except anthropic.PermissionDeniedError:
            logger.error("Anthropic permission denied")
            return False

        except Exception as e:
            logger.error(f"Anthropic connection validation failed: {e}")
            return False

    def get_model_info(self) -> ModelInfo:
        """Get Anthropic model information"""

        # Model configurations for different Claude variants
        model_configs = {
            "claude-3-5-sonnet-20241022": {
                "max_tokens": 4096,
                "context_length": 200000,
                "cost_per_1k_tokens": 0.003,
                "description": "Claude 3.5 Sonnet - Latest high-intelligence model",
            },
            "claude-3-5-haiku-20241022": {
                "max_tokens": 4096,
                "context_length": 200000,
                "cost_per_1k_tokens": 0.00025,
                "description": "Claude 3.5 Haiku - Fast and efficient model",
            },
            "claude-3-opus-20240229": {
                "max_tokens": 4096,
                "context_length": 200000,
                "cost_per_1k_tokens": 0.015,
                "description": "Claude 3 Opus - Highest capability model",
            },
        }

        config = model_configs.get(
            self.model, model_configs["claude-3-5-sonnet-20241022"]
        )

        return ModelInfo(
            name=self.model,
            provider="anthropic",
            model_type=ModelType.ANTHROPIC_CLAUDE,
            max_tokens=config["max_tokens"],
            context_length=config["context_length"],
            supports_streaming=True,
            cost_per_1k_tokens=config["cost_per_1k_tokens"],
            description=config["description"],
        )

    async def count_tokens(self, text: str) -> int:
        """Count tokens in text using Anthropic's tokenizer"""
        try:
            # Anthropic provides a count_tokens method
            result = await self.client.count_tokens(text)
            return result.input_tokens
        except Exception as e:
            logger.warning(f"Failed to count tokens: {e}")
            # Fallback: rough estimation (1 token ≈ 4 characters)
            return len(text) // 4

    async def get_usage_stats(self) -> Optional[dict[str, Any]]:
        """Get usage statistics"""
        return {
            "provider": self.name,
            "model": self.model,
            "max_context_length": self.get_model_info().context_length,
            "supports_streaming": True,
            "status": "Available",
        }

    def supports_large_context(self) -> bool:
        """Check if model supports large context"""
        return self.get_model_info().context_length >= 100000

    async def optimize_for_large_content(
        self, request: GenerationRequest
    ) -> GenerationRequest:
        """Optimize request for large content generation"""
        # For Claude, we can use the full context length
        model_info = self.get_model_info()

        # Estimate current token usage
        prompt_tokens = await self.count_tokens(request.prompt)
        system_tokens = 0
        if request.system_prompt:
            system_tokens = await self.count_tokens(request.system_prompt)

        total_input_tokens = prompt_tokens + system_tokens
        available_tokens = (
            model_info.context_length - total_input_tokens - 1000
        )  # Buffer

        # Adjust max_tokens if needed
        if not request.max_tokens or request.max_tokens > available_tokens:
            request.max_tokens = min(available_tokens, model_info.max_tokens)

        logger.info(
            f"Optimized request: {total_input_tokens} input tokens, {request.max_tokens} max output tokens"
        )

        return request
