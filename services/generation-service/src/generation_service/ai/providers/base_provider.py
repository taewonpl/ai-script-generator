"""
Abstract base class for AI providers with Core Module integration
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel

# Import retry library
try:
    from tenacity import (
        before_sleep_log,
        retry,
        retry_if_exception_type,
        stop_after_attempt,
        wait_exponential,
    )

    TENACITY_AVAILABLE = True
except ImportError:
    TENACITY_AVAILABLE = False

# Import Core Module components
try:
    from ai_script_core import (
        AIModelConfigDTO,
        BaseServiceException,
        ErrorCategory,
        ErrorSeverity,
        ExternalServiceError,
        GenerationMetadataDTO,
        GenerationServiceError,
        ServiceUnavailableError,
        ValidationException,
        calculate_hash,
        generate_uuid,
        get_service_logger,
        safe_json_dumps,
        safe_json_loads,
        utc_now,
    )

    CORE_AVAILABLE = True
    logger = get_service_logger("generation-service.base_provider")
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


class ModelType(str, Enum):
    """Supported AI model types"""

    OPENAI_GPT4O = "openai_gpt4o"
    ANTHROPIC_CLAUDE = "anthropic_claude"
    LOCAL_LLAMA = "local_llama"


class ProviderStatus(str, Enum):
    """Provider connection status"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


if CORE_AVAILABLE:
    # Use Core Module DTOs when available
    class ModelInfo(BaseModel):
        """Model information and capabilities using Core patterns"""

        name: str
        provider: str
        model_type: ModelType
        max_tokens: int
        context_length: int
        supports_streaming: bool
        cost_per_1k_tokens: float | None = None
        description: str = ""

        # Core integration fields
        created_at: datetime = None
        model_hash: str | None = None

        def __post_init__(self):
            if self.created_at is None:
                self.created_at = utc_now()
            if self.model_hash is None:
                self.model_hash = calculate_hash(f"{self.name}:{self.provider}")

    class ProviderGenerationRequest(BaseModel):
        """AI generation request using Core patterns"""

        prompt: str
        max_tokens: int | None = None
        temperature: float = 0.7
        top_p: float = 1.0
        stop_sequences: list[str] | None = None
        stream: bool = False
        system_prompt: str | None = None
        additional_params: dict[str, Any] | None = None

        # Core integration
        request_id: str = None
        created_at: datetime = None

        def __post_init__(self):
            if self.request_id is None:
                self.request_id = generate_uuid()
            if self.created_at is None:
                self.created_at = utc_now()

    class ProviderGenerationResponse(BaseModel):
        """AI generation response using Core patterns"""

        content: str
        finish_reason: str
        model_info: ModelInfo
        created_at: datetime = None

        # Core metadata integration
        metadata: dict[str, Any] | None = None
        request_id: str | None = None

        def __post_init__(self):
            if self.created_at is None:
                self.created_at = utc_now()

else:
    # Fallback implementations
    @dataclass
    class ModelInfo:
        """Model information and capabilities"""

        name: str
        provider: str
        model_type: ModelType
        max_tokens: int
        context_length: int
        supports_streaming: bool
        cost_per_1k_tokens: float | None = None
        description: str = ""

    class ProviderGenerationRequest(BaseModel):
        """Request for AI generation"""

        prompt: str
        max_tokens: int | None = None
        temperature: float = 0.7
        top_p: float = 1.0
        stop_sequences: list[str] | None = None
        stream: bool = False
        system_prompt: str | None = None
        additional_params: dict[str, Any] | None = None

    class ProviderGenerationResponse(BaseModel):
        """Response from AI generation"""

        content: str
        finish_reason: str
        model_info: ModelInfo
        created_at: datetime = datetime.now()


# Legacy compatibility
GenerationRequest = ProviderGenerationRequest
GenerationResponse = ProviderGenerationResponse


if CORE_AVAILABLE:
    # Use Core Module exceptions
    class ProviderError(ExternalServiceError):
        """Base exception for provider errors using Core exception"""

        def __init__(
            self, message: str, provider: str, retryable: bool = False, **kwargs
        ):
            super().__init__(service_name=provider, operation="ai_generation", **kwargs)
            self.provider = provider
            self.retryable = retryable

    class ProviderConnectionError(ServiceUnavailableError):
        """Provider connection error using Core exception"""

        def __init__(self, message: str, provider: str, retry_after: int | None = None):
            super().__init__(
                service_name=provider, reason=message, retry_after=retry_after
            )
            self.provider = provider
            self.retryable = True

    class ProviderRateLimitError(ServiceUnavailableError):
        """Provider rate limit error using Core exception"""

        def __init__(self, message: str, provider: str, retry_after: int | None = None):
            super().__init__(
                service_name=provider,
                reason=f"Rate limit exceeded: {message}",
                retry_after=retry_after,
            )
            self.provider = provider
            self.retry_after = retry_after
            self.retryable = True

    class ProviderQuotaError(ExternalServiceError):
        """Provider quota exceeded error using Core exception"""

        def __init__(self, message: str, provider: str, **kwargs):
            super().__init__(
                service_name=provider,
                operation="quota_check",
                response_body=message,
                **kwargs,
            )
            self.provider = provider
            self.retryable = False

else:
    # Fallback exception classes
    class ProviderError(Exception):
        """Base exception for provider errors"""

        def __init__(self, message: str, provider: str, retryable: bool = False):
            super().__init__(message)
            self.provider = provider
            self.retryable = retryable

    class ProviderConnectionError(ProviderError):
        """Provider connection error"""

        def __init__(self, message: str, provider: str):
            super().__init__(message, provider, retryable=True)

    class ProviderRateLimitError(ProviderError):
        """Provider rate limit error"""

        def __init__(self, message: str, provider: str, retry_after: int | None = None):
            super().__init__(message, provider, retryable=True)
            self.retry_after = retry_after

    class ProviderQuotaError(ProviderError):
        """Provider quota exceeded error"""

        def __init__(self, message: str, provider: str):
            super().__init__(message, provider, retryable=False)


class BaseProvider(ABC):
    """Abstract base class for AI providers with Core Module integration"""

    def __init__(self, name: str, config: dict[str, Any]):
        self.name = name
        self.config = config
        self._status = ProviderStatus.UNKNOWN
        self._last_health_check = None

        # Core Module integration
        if CORE_AVAILABLE:
            self.provider_id = generate_uuid()
            self.created_at = utc_now()
            logger.info(
                f"Provider {name} initialized with Core integration",
                extra={
                    "provider_id": self.provider_id,
                    "provider_name": name,
                    "config_hash": calculate_hash(safe_json_dumps(config)),
                },
            )
        else:
            self.provider_id = f"{name}_{hash(str(config))}"
            self.created_at = datetime.now()
            logger.info(f"Provider {name} initialized in fallback mode")

    @property
    def status(self) -> ProviderStatus:
        """Get current provider status"""
        return self._status

    @abstractmethod
    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Generate content using the AI model"""
        pass

    @abstractmethod
    async def generate_stream(
        self, request: GenerationRequest
    ) -> AsyncGenerator[str, None]:
        """Generate content with streaming response"""
        pass

    @abstractmethod
    async def validate_connection(self) -> bool:
        """Validate connection to the AI provider"""
        pass

    @abstractmethod
    def get_model_info(self) -> ModelInfo:
        """Get information about the model"""
        pass

    async def health_check(self) -> ProviderStatus:
        """Perform health check on the provider with Core Module integration"""
        start_time = utc_now() if CORE_AVAILABLE else datetime.now()

        try:
            is_healthy = await self.validate_connection()
            self._status = (
                ProviderStatus.HEALTHY if is_healthy else ProviderStatus.UNAVAILABLE
            )
            self._last_health_check = start_time

            # Core Module structured logging
            if CORE_AVAILABLE:
                logger.info(
                    f"Health check completed for {self.name}",
                    extra={
                        "provider_id": self.provider_id,
                        "provider_name": self.name,
                        "status": self._status.value,
                        "duration_ms": int(
                            (utc_now() - start_time).total_seconds() * 1000
                        ),
                        "healthy": is_healthy,
                    },
                )
            else:
                logger.info(f"Health check for {self.name}: {self._status}")

            return self._status

        except Exception as e:
            self._status = ProviderStatus.UNAVAILABLE

            if CORE_AVAILABLE:
                logger.error(
                    f"Health check failed for {self.name}",
                    extra={
                        "provider_id": self.provider_id,
                        "provider_name": self.name,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "duration_ms": int(
                            (utc_now() - start_time).total_seconds() * 1000
                        ),
                    },
                    exc_info=True,
                )
            else:
                logger.error(f"Health check failed for {self.name}: {e}")

            return self._status

    async def generate_with_retry(
        self, request: GenerationRequest, max_retries: int = 3, retry_delay: float = 1.0
    ) -> GenerationResponse:
        """Generate with enhanced retry logic using Core Module patterns"""

        if TENACITY_AVAILABLE and CORE_AVAILABLE:
            return await self._generate_with_tenacity_retry(
                request, max_retries, retry_delay
            )
        else:
            return await self._generate_with_basic_retry(
                request, max_retries, retry_delay
            )

    async def _generate_with_tenacity_retry(
        self, request: GenerationRequest, max_retries: int, retry_delay: float
    ) -> GenerationResponse:
        """Enhanced retry using tenacity library"""

        @retry(
            stop=stop_after_attempt(max_retries + 1),
            wait=wait_exponential(multiplier=retry_delay, min=1, max=60),
            retry=retry_if_exception_type(
                (ProviderConnectionError, ProviderRateLimitError)
            ),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )
        async def _retry_generate():
            try:
                return await self.generate(request)
            except ProviderQuotaError:
                # Don't retry quota errors
                raise
            except Exception as e:
                if CORE_AVAILABLE:
                    logger.warning(
                        f"Generation attempt failed for {self.name}",
                        extra={
                            "provider_id": self.provider_id,
                            "provider_name": self.name,
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "request_id": getattr(request, "request_id", "unknown"),
                        },
                    )
                raise

        return await _retry_generate()

    async def _generate_with_basic_retry(
        self, request: GenerationRequest, max_retries: int, retry_delay: float
    ) -> GenerationResponse:
        """Basic retry logic fallback"""

        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                return await self.generate(request)

            except ProviderRateLimitError as e:
                last_exception = e
                if attempt < max_retries:
                    wait_time = e.retry_after or (retry_delay * (2**attempt))
                    logger.warning(f"Rate limited by {self.name}, waiting {wait_time}s")
                    await asyncio.sleep(wait_time)
                    continue
                raise

            except ProviderConnectionError as e:
                last_exception = e
                if attempt < max_retries:
                    wait_time = retry_delay * (2**attempt)
                    logger.warning(
                        f"Connection error to {self.name}, retrying in {wait_time}s"
                    )
                    await asyncio.sleep(wait_time)
                    continue
                raise

            except ProviderQuotaError:
                # Don't retry quota errors
                raise

            except Exception as e:
                last_exception = e
                if attempt < max_retries:
                    wait_time = retry_delay * (2**attempt)
                    logger.warning(
                        f"Error with {self.name}, retrying in {wait_time}s: {e}"
                    )
                    await asyncio.sleep(wait_time)
                    continue
                raise

        # If we get here, all retries failed
        if last_exception:
            raise last_exception
        else:
            raise ProviderError(f"All retries failed for {self.name}", self.name)

    def _calculate_cost(self, tokens_used: int) -> float | None:
        """Calculate cost based on tokens used"""
        model_info = self.get_model_info()
        if model_info.cost_per_1k_tokens:
            return (tokens_used / 1000) * model_info.cost_per_1k_tokens
        return None

    def _create_metrics(
        self, tokens_used: int, generation_time: float, model_used: str
    ) -> dict[str, Any]:
        """Create generation metrics"""
        return {
            "tokens_used": tokens_used,
            "generation_time_seconds": generation_time,
            "cost_estimate": self._calculate_cost(tokens_used),
            "model_used": model_used,
            "provider_used": self.name,
        }

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, status={self.status})"
