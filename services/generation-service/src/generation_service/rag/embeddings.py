"""
Embedding service with OpenAI integration and Core Module patterns
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

try:
    import openai
    from openai import AsyncOpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import tiktoken

    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False

# Import Core Module components
try:
    from ai_script_core import (
        BaseServiceException,
        ExternalServiceError,
        ValidationException,
        calculate_hash,
        generate_uuid,
        get_service_logger,
        safe_json_dumps,
        utc_now,
    )

    CORE_AVAILABLE = True
    logger = get_service_logger("generation-service.embeddings")
except (ImportError, RuntimeError):
    CORE_AVAILABLE = False
    import logging

    logger = logging.getLogger(__name__)  # type: ignore[assignment]

    # Fallback utility functions
    def utc_now() -> datetime:
        """Fallback UTC timestamp"""
        from datetime import datetime, timezone

        return datetime.now(timezone.utc)

    def generate_uuid() -> str:
        """Fallback UUID generation"""
        import uuid

        return str(uuid.uuid4())

    def calculate_hash(data: str) -> str:
        """Fallback hash calculation"""
        import hashlib

        return hashlib.md5(data.encode()).hexdigest()

    def safe_json_dumps(data: Any) -> str:
        """Fallback JSON serialization"""
        import json

        return json.dumps(data, default=str)

    # Fallback exception classes
    class BaseServiceException(Exception):
        """Fallback base service exception"""

        pass

    class ExternalServiceError(BaseServiceException):
        """Fallback external service error"""

        pass

    class ValidationException(BaseServiceException):
        """Fallback validation exception"""

        pass

    def generate_id() -> str:
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


@dataclass
class EmbeddingRequest:
    """Request for embedding generation"""

    texts: list[str]
    model: str = "text-embedding-ada-002"
    request_id: str | None = None
    chunk_size: int = 100

    def __post_init__(self) -> None:
        if CORE_AVAILABLE and self.request_id is None:
            self.request_id = generate_uuid()


@dataclass
class EmbeddingResponse:
    """Response from embedding generation"""

    embeddings: list[list[float]]
    model: str
    usage: dict[str, int]
    request_id: str | None = None
    processing_time: float = 0.0

    def __post_init__(self) -> None:
        if CORE_AVAILABLE and self.request_id is None:
            self.request_id = generate_uuid()


class EmbeddingError(Exception):
    """Base exception for embedding operations"""

    def __init__(
        self, message: str, operation: str = "embedding_generation", **kwargs: Any
    ) -> None:
        super().__init__(message)
        self.operation = operation
        self.kwargs = kwargs


if CORE_AVAILABLE:
    # Override the fallback EmbeddingError with Core-based version
    class EmbeddingError(ExternalServiceError):  # type: ignore[misc]
        """Embedding error using Core exception"""

        def __init__(
            self, message: str, operation: str = "embedding_generation", **kwargs: Any
        ) -> None:
            super().__init__(
                service_name="openai_embeddings",
                operation=operation,
                response_body=message,
                **kwargs,
            )


class EmbeddingService:
    """OpenAI embedding service with Core Module integration"""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "text-embedding-ada-002",
        batch_size: int = 100,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        if not OPENAI_AVAILABLE:
            raise EmbeddingError(
                "OpenAI library not available. Install with: pip install openai"
            )

        self.api_key = api_key
        self.model = model
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Initialize OpenAI client
        self.client = AsyncOpenAI(api_key=api_key)

        # Initialize tokenizer for cost calculation
        if TIKTOKEN_AVAILABLE:
            try:
                self.tokenizer = tiktoken.encoding_for_model(model)
            except KeyError:
                self.tokenizer = tiktoken.get_encoding("cl100k_base")
                logger.warning(f"Tokenizer for {model} not found, using cl100k_base")
        else:
            self.tokenizer = None
            logger.warning("tiktoken not available, token counting will be approximate")

        # Core Module integration
        if CORE_AVAILABLE:
            self.service_id = generate_uuid()
            self.created_at = utc_now()
            logger.info(
                "Embedding service initialized with Core integration",
                extra={
                    "service_id": self.service_id,
                    "model": model,
                    "batch_size": batch_size,
                    "max_retries": max_retries,
                },
            )
        else:
            self.service_id = f"embedding_{hash(model + str(batch_size))}"
            logger.info(f"Embedding service initialized: {model}")

        # Caching and metrics
        self._embedding_cache: dict[str, list[float]] = {}
        self._metrics = {
            "total_requests": 0,
            "total_tokens": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_cost": 0.0,
        }

    def _calculate_tokens(self, text: str) -> int:
        """Calculate token count for text"""
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        else:
            # Rough approximation: 1 token ≈ 4 characters
            return len(text) // 4

    def _calculate_cost(self, token_count: int) -> float:
        """Calculate cost for embedding generation"""
        # OpenAI text-embedding-ada-002 pricing: $0.0001 per 1K tokens
        return (token_count / 1000) * 0.0001

    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text"""
        if CORE_AVAILABLE:
            return calculate_hash(f"{self.model}:{text}")
        else:
            return str(hash(f"{self.model}:{text}"))

    def _chunk_texts(self, texts: list[str], chunk_size: int) -> list[list[str]]:
        """Split texts into batches for processing"""
        return [texts[i : i + chunk_size] for i in range(0, len(texts), chunk_size)]

    async def generate_embeddings(
        self, texts: str | list[str], use_cache: bool = True
    ) -> EmbeddingResponse:
        """Generate embeddings for texts"""

        if isinstance(texts, str):
            texts = [texts]

        if not texts:
            raise EmbeddingError(
                "No texts provided for embedding", operation="generate_embeddings"
            )

        start_time = utc_now() if CORE_AVAILABLE else time.time()
        request_id = generate_uuid() if CORE_AVAILABLE else f"req_{int(time.time())}"

        try:
            embeddings = []
            total_tokens = 0
            cache_hits = 0
            cache_misses = 0

            # Process in batches
            for batch in self._chunk_texts(texts, self.batch_size):
                (
                    batch_embeddings,
                    batch_tokens,
                    batch_cache_hits,
                    batch_cache_misses,
                ) = await self._process_batch(batch, use_cache)
                embeddings.extend(batch_embeddings)
                total_tokens += batch_tokens
                cache_hits += batch_cache_hits
                cache_misses += batch_cache_misses

            # Calculate metrics
            processing_time = (
                (utc_now() - start_time).total_seconds()
                if CORE_AVAILABLE
                else (time.time() - start_time)
            )
            cost = self._calculate_cost(total_tokens)

            # Update service metrics
            self._metrics["total_requests"] += 1
            self._metrics["total_tokens"] += total_tokens
            self._metrics["cache_hits"] += cache_hits
            self._metrics["cache_misses"] += cache_misses
            self._metrics["total_cost"] += cost

            # Log results
            if CORE_AVAILABLE:
                logger.info(
                    "Embedding generation completed",
                    extra={
                        "service_id": self.service_id,
                        "request_id": request_id,
                        "text_count": len(texts),
                        "total_tokens": total_tokens,
                        "processing_time_seconds": processing_time,
                        "cost_estimate": cost,
                        "cache_hits": cache_hits,
                        "cache_misses": cache_misses,
                        "cache_hit_rate": cache_hits / len(texts) if texts else 0,
                    },
                )
            else:
                logger.info(
                    f"Generated embeddings for {len(texts)} texts in {processing_time:.2f}s"
                )

            return EmbeddingResponse(
                embeddings=embeddings,
                model=self.model,
                usage={"total_tokens": total_tokens},
                request_id=request_id,
                processing_time=processing_time,
            )

        except Exception as e:
            error_msg = f"Embedding generation failed: {e!s}"
            logger.error(error_msg)
            raise EmbeddingError(error_msg, operation="generate_embeddings")

    async def _process_batch(
        self, texts: list[str], use_cache: bool
    ) -> tuple[list[list[float]], int, int, int]:
        """Process a batch of texts"""

        embeddings = []
        total_tokens = 0
        cache_hits = 0
        cache_misses = 0
        texts_to_embed = []
        cache_results = {}

        # Check cache first
        if use_cache:
            for text in texts:
                cache_key = self._get_cache_key(text)
                if cache_key in self._embedding_cache:
                    cache_results[text] = self._embedding_cache[cache_key]
                    cache_hits += 1
                else:
                    texts_to_embed.append(text)
                    cache_misses += 1
        else:
            texts_to_embed = texts
            cache_misses = len(texts)

        # Generate embeddings for uncached texts
        new_embeddings = {}
        if texts_to_embed:
            api_embeddings = await self._call_openai_api(texts_to_embed)

            # Calculate tokens and update cache
            for i, text in enumerate(texts_to_embed):
                embedding = api_embeddings[i]
                new_embeddings[text] = embedding

                # Add to cache
                if use_cache:
                    cache_key = self._get_cache_key(text)
                    self._embedding_cache[cache_key] = embedding

                # Count tokens
                total_tokens += self._calculate_tokens(text)

        # Combine cached and new embeddings in original order
        for text in texts:
            if text in cache_results:
                embeddings.append(cache_results[text])
            else:
                embeddings.append(new_embeddings[text])

        return embeddings, total_tokens, cache_hits, cache_misses

    async def _call_openai_api(self, texts: list[str]) -> list[list[float]]:
        """Call OpenAI embeddings API with retry logic"""

        for attempt in range(self.max_retries + 1):
            try:
                response = await self.client.embeddings.create(
                    model=self.model, input=texts
                )

                return [embedding.embedding for embedding in response.data]

            except openai.RateLimitError as e:
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * (2**attempt)
                    logger.warning(
                        f"Rate limited, waiting {wait_time}s before retry {attempt + 1}"
                    )
                    await asyncio.sleep(wait_time)
                    continue
                raise EmbeddingError(
                    f"Rate limit exceeded: {e!s}", operation="api_call"
                )

            except openai.APIError as e:
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * (2**attempt)
                    logger.warning(f"API error, retrying in {wait_time}s: {e!s}")
                    await asyncio.sleep(wait_time)
                    continue
                raise EmbeddingError(f"API error: {e!s}", operation="api_call")

            except Exception as e:
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * (2**attempt)
                    logger.warning(f"Unexpected error, retrying in {wait_time}s: {e!s}")
                    await asyncio.sleep(wait_time)
                    continue
                raise EmbeddingError(f"Unexpected error: {e!s}", operation="api_call")

        raise EmbeddingError("All retry attempts failed", operation="api_call")

    def get_metrics(self) -> dict[str, Any]:
        """Get service metrics"""

        metrics = self._metrics.copy()

        if CORE_AVAILABLE:
            metrics.update(
                {
                    "service_id": self.service_id,
                    "model": self.model,
                    "cache_size": len(self._embedding_cache),
                    "cache_hit_rate": self._metrics["cache_hits"]
                    / max(self._metrics["total_requests"] * self.batch_size, 1),
                    "avg_cost_per_request": self._metrics["total_cost"]
                    / max(self._metrics["total_requests"], 1),
                    "last_updated": utc_now().isoformat(),
                }
            )
        else:
            metrics.update(
                {
                    "service_id": self.service_id,
                    "model": self.model,
                    "cache_size": len(self._embedding_cache),
                }
            )

        return metrics

    def clear_cache(self) -> None:
        """Clear embedding cache"""

        cache_size = len(self._embedding_cache)
        self._embedding_cache.clear()

        if CORE_AVAILABLE:
            logger.info(
                "Embedding cache cleared",
                extra={"service_id": self.service_id, "cleared_entries": cache_size},
            )
        else:
            logger.info(f"Cleared {cache_size} cached embeddings")

    def optimize_chunking(
        self, texts: list[str], max_tokens: int = 8000
    ) -> list[list[str]]:
        """Optimize text chunking based on token limits"""

        chunks = []
        current_chunk = []
        current_tokens = 0

        for text in texts:
            text_tokens = self._calculate_tokens(text)

            # If single text exceeds limit, split it
            if text_tokens > max_tokens:
                # Add current chunk if not empty
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = []
                    current_tokens = 0

                # Split large text (simple sentence-based splitting)
                sentences = text.split(". ")
                temp_chunk = []
                temp_tokens = 0

                for sentence in sentences:
                    sentence_tokens = self._calculate_tokens(sentence)
                    if temp_tokens + sentence_tokens > max_tokens and temp_chunk:
                        chunks.append([". ".join(temp_chunk)])
                        temp_chunk = [sentence]
                        temp_tokens = sentence_tokens
                    else:
                        temp_chunk.append(sentence)
                        temp_tokens += sentence_tokens

                if temp_chunk:
                    chunks.append([". ".join(temp_chunk)])

            # If adding this text would exceed limit
            elif current_tokens + text_tokens > max_tokens and current_chunk:
                chunks.append(current_chunk)
                current_chunk = [text]
                current_tokens = text_tokens
            else:
                current_chunk.append(text)
                current_tokens += text_tokens

        # Add remaining chunk
        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    async def health_check(self) -> dict[str, Any]:
        """Perform health check on embedding service"""

        try:
            # Test with a simple embedding
            test_text = "Health check test"
            response = await self.generate_embeddings([test_text], use_cache=False)

            health_status = {
                "status": "healthy",
                "service_id": self.service_id,
                "model": self.model,
                "test_embedding_length": len(response.embeddings[0]),
                "metrics": self.get_metrics(),
            }

            if CORE_AVAILABLE:
                health_status["checked_at"] = utc_now().isoformat()

            return health_status

        except Exception as e:
            error_msg = f"Health check failed: {e!s}"
            logger.error(error_msg)
            return {
                "status": "unhealthy",
                "service_id": self.service_id,
                "error": error_msg,
            }
