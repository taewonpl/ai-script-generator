"""
Local provider for fine-tuned Llama models
"""

import json
import logging
import time
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from .base_provider import (
    BaseProvider,
    GenerationRequest,
    GenerationResponse,
    ModelInfo,
    ModelType,
    ProviderConnectionError,
    ProviderError,
    ProviderRateLimitError,
)

logger = logging.getLogger(__name__)


class LocalProvider(BaseProvider):
    """Local fine-tuned Llama model provider implementation"""

    def __init__(self, config: dict[str, Any]):
        super().__init__("local", config)

        self.endpoint_url = config.get("endpoint_url")
        if not self.endpoint_url:
            raise ValueError("Local model endpoint URL is required")

        self.model_name = config.get("model_name", "llama-3-8b-script-tuned")
        self.api_key = config.get("api_key")  # Optional for local models
        self.timeout = config.get("timeout", 120)  # Local models might be slower

        # HTTP client configuration
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout), headers=self._get_headers()
        )

        logger.info(f"Local provider initialized with endpoint: {self.endpoint_url}")

    def _get_headers(self) -> dict[str, str]:
        """Get HTTP headers for requests"""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "generation-service/3.0.0",
        }

        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        return headers

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Generate content using local Llama model"""

        start_time = time.time()

        try:
            # Prepare payload for local model
            payload = {
                "model": self.model_name,
                "prompt": self._format_prompt(request),
                "temperature": request.temperature,
                "top_p": request.top_p,
                "stream": False,
            }

            if request.max_tokens:
                payload["max_tokens"] = request.max_tokens

            if request.stop_sequences:
                payload["stop"] = request.stop_sequences

            # Add additional parameters
            if request.additional_params:
                # Common parameters for local models
                valid_params = [
                    "top_k",
                    "repetition_penalty",
                    "frequency_penalty",
                    "presence_penalty",
                ]
                for key, value in request.additional_params.items():
                    if key in valid_params:
                        payload[key] = value

            # Make API call to local endpoint
            response = await self.client.post(
                f"{self.endpoint_url}/v1/completions", json=payload
            )

            if response.status_code == 429:
                raise ProviderRateLimitError("Local model is busy", self.name)
            elif response.status_code == 503:
                raise ProviderConnectionError("Local model is unavailable", self.name)
            elif response.status_code >= 400:
                error_text = response.text
                raise ProviderError(f"Local model error: {error_text}", self.name)

            response.raise_for_status()
            result = response.json()

            generation_time = time.time() - start_time

            # Extract response data
            content = ""
            finish_reason = "completed"

            if result.get("choices"):
                choice = result["choices"][0]
                content = choice.get("text", "")
                finish_reason = choice.get("finish_reason", "completed")
            elif "response" in result:
                # Alternative response format
                content = result["response"]

            # Estimate tokens used (local models might not provide exact counts)
            tokens_used = self._estimate_tokens(request.prompt + content)

            # Create metrics
            metrics = self._create_metrics(
                tokens_used, generation_time, self.model_name
            )

            return GenerationResponse(
                content=content,
                finish_reason=finish_reason,
                metrics=metrics,
                model_info=self.get_model_info(),
            )

        except httpx.TimeoutException:
            logger.error("Local model request timed out")
            raise ProviderConnectionError("Request timed out", self.name)

        except httpx.ConnectError:
            logger.error("Failed to connect to local model")
            raise ProviderConnectionError("Connection failed", self.name)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise ProviderRateLimitError("Local model is busy", self.name)
            else:
                raise ProviderError(f"HTTP error: {e.response.status_code}", self.name)

        except Exception as e:
            logger.error(f"Unexpected error in local provider: {e}")
            raise ProviderError(f"Unexpected error: {e}", self.name)

    async def generate_stream(
        self, request: GenerationRequest
    ) -> AsyncGenerator[str, None]:
        """Generate content with streaming response"""

        try:
            # Prepare payload for streaming
            payload = {
                "model": self.model_name,
                "prompt": self._format_prompt(request),
                "temperature": request.temperature,
                "top_p": request.top_p,
                "stream": True,
            }

            if request.max_tokens:
                payload["max_tokens"] = request.max_tokens

            if request.stop_sequences:
                payload["stop"] = request.stop_sequences

            # Add additional parameters
            if request.additional_params:
                valid_params = ["top_k", "repetition_penalty"]
                for key, value in request.additional_params.items():
                    if key in valid_params:
                        payload[key] = value

            # Make streaming request
            async with self.client.stream(
                "POST", f"{self.endpoint_url}/v1/completions", json=payload
            ) as response:
                if response.status_code >= 400:
                    error_text = await response.aread()
                    raise ProviderError(
                        f"Streaming error: {error_text.decode()}", self.name
                    )

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]  # Remove "data: " prefix

                        if data.strip() == "[DONE]":
                            break

                        try:
                            chunk = json.loads(data)
                            if chunk.get("choices"):
                                choice = chunk["choices"][0]
                                if "text" in choice:
                                    yield choice["text"]
                        except json.JSONDecodeError:
                            continue

        except httpx.TimeoutException:
            logger.error("Local model streaming timed out")
            raise ProviderConnectionError("Streaming timed out", self.name)

        except httpx.ConnectError:
            logger.error("Failed to connect to local model for streaming")
            raise ProviderConnectionError("Streaming connection failed", self.name)

        except Exception as e:
            logger.error(f"Unexpected error in local streaming: {e}")
            raise ProviderError(f"Streaming error: {e}", self.name)

    async def validate_connection(self) -> bool:
        """Validate connection to local model"""

        try:
            # Test with a health check or simple request
            health_url = f"{self.endpoint_url}/health"

            try:
                response = await self.client.get(health_url)
                if response.status_code == 200:
                    return True
            except:
                pass  # Try alternative validation

            # Fallback: test with a simple generation request
            test_payload = {
                "model": self.model_name,
                "prompt": "Test",
                "max_tokens": 1,
                "temperature": 0,
            }

            response = await self.client.post(
                f"{self.endpoint_url}/v1/completions", json=test_payload
            )

            return response.status_code == 200

        except Exception as e:
            logger.error(f"Local model connection validation failed: {e}")
            return False

    def get_model_info(self) -> ModelInfo:
        """Get local model information"""

        # Default configuration for Llama-based models
        # These can be overridden in config
        return ModelInfo(
            name=self.model_name,
            provider="local",
            model_type=ModelType.LOCAL_LLAMA,
            max_tokens=self.config.get("max_tokens", 4096),
            context_length=self.config.get("context_length", 8192),
            supports_streaming=True,
            cost_per_1k_tokens=0.0,  # Local models have no per-token cost
            description=self.config.get(
                "description", "Fine-tuned Llama model for script generation"
            ),
        )

    def _format_prompt(self, request: GenerationRequest) -> str:
        """Format prompt for local model"""

        # For Llama models, we might need special formatting
        if request.system_prompt:
            # Use Llama chat format or custom format
            formatted = f"<|system|>\n{request.system_prompt}\n<|user|>\n{request.prompt}\n<|assistant|>\n"
        else:
            formatted = request.prompt

        return formatted

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for local model"""
        # Rough estimation: 1 token ≈ 4 characters for English text
        return max(1, len(text) // 4)

    async def get_model_status(self) -> dict[str, Any]:
        """Get local model status and metrics"""
        try:
            response = await self.client.get(f"{self.endpoint_url}/status")
            if response.status_code == 200:
                return response.json()
            else:
                return {"status": "unknown", "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def get_usage_stats(self) -> dict[str, Any] | None:
        """Get usage statistics for local model"""
        try:
            status = await self.get_model_status()
            return {
                "provider": self.name,
                "model": self.model_name,
                "endpoint": self.endpoint_url,
                "status": status,
                "cost_per_token": 0.0,
            }
        except Exception:
            return {
                "provider": self.name,
                "model": self.model_name,
                "status": "unavailable",
            }

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.client.aclose()
