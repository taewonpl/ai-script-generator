"""
Provider safety utilities for robust AI provider handling
"""

import logging
from http import HTTPStatus

from fastapi import HTTPException

from ..ai.providers.base_provider import BaseProvider
from ..ai.providers.provider_factory import ProviderFactory

logger = logging.getLogger(__name__)


class ProviderUnavailableError(HTTPException):
    """Exception raised when AI provider is unavailable"""

    def __init__(
        self,
        model_name: str,
        available_providers: list[str],
        configured_providers: list[str],
        recommendations: list[str],
        detail_message: str = None,
    ):
        self.model_name = model_name
        self.available_providers = available_providers
        self.configured_providers = configured_providers
        self.recommendations = recommendations

        if detail_message is None:
            detail_message = (
                f"No AI provider available for model '{model_name}'. "
                f"Available provider types: {available_providers}. "
                f"Configured providers: {configured_providers}. "
                f"Check API keys and provider configurations."
            )

        super().__init__(
            status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            detail={
                "error": "AI Provider Unavailable",
                "message": detail_message,
                "model_requested": model_name,
                "available_providers": available_providers,
                "configured_providers": configured_providers,
                "recommendations": recommendations,
                "error_type": "provider_unavailable",
            },
        )


async def get_provider_safely(
    provider_factory: ProviderFactory,
    model_name: str,
    operation_context: str = "generation",
) -> BaseProvider:
    """
    Safely get a provider with comprehensive error handling

    Args:
        provider_factory: The provider factory instance
        model_name: Name of the model to get provider for
        operation_context: Context of the operation (for logging)

    Returns:
        BaseProvider: The provider instance

    Raises:
        ProviderUnavailableError: If no provider is available
    """

    logger.info(
        f"Attempting to get provider for model '{model_name}' (context: {operation_context})"
    )

    try:
        # Get provider
        provider = await provider_factory.get_provider(model_name)

        if provider is None:
            # Gather diagnostic information
            available_providers = provider_factory.get_available_provider_types()
            failure_summary = provider_factory.get_provider_failure_summary()

            # Enhanced error message with context
            error_msg = (
                f"Provider initialization failed for {operation_context} operation. "
                f"Model '{model_name}' is not available through any configured provider. "
            )

            # Add specific recommendations based on the failure
            if not available_providers:
                error_msg += "No AI provider dependencies are installed. "
            elif not failure_summary.get("configured_providers", []):
                error_msg += "No providers are configured with API keys. "
            else:
                error_msg += f"Providers are configured but unavailable: {failure_summary.get('configured_providers', [])}. "

            logger.error(f"Provider safety check failed: {error_msg}")

            raise ProviderUnavailableError(
                model_name=model_name,
                available_providers=[p.value for p in available_providers],
                configured_providers=failure_summary.get("configured_providers", []),
                recommendations=failure_summary.get("recommendations", []),
                detail_message=error_msg,
            )

        logger.info(
            f"Successfully obtained provider for model '{model_name}' (context: {operation_context})"
        )
        return provider

    except ProviderUnavailableError:
        # Re-raise our custom exception
        raise

    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Unexpected error getting provider for '{model_name}': {e}")

        # Try to get diagnostic info if possible
        try:
            available_providers = provider_factory.get_available_provider_types()
            failure_summary = provider_factory.get_provider_failure_summary()
        except Exception:
            available_providers = []
            failure_summary = {"configured_providers": [], "recommendations": []}

        error_msg = (
            f"Unexpected error during provider initialization for {operation_context}. "
            f"Error: {e!s}"
        )

        raise ProviderUnavailableError(
            model_name=model_name,
            available_providers=[p.value for p in available_providers],
            configured_providers=failure_summary.get("configured_providers", []),
            recommendations=failure_summary.get("recommendations", [])
            + [
                "Check service logs for detailed error information",
                "Verify provider factory configuration",
            ],
            detail_message=error_msg,
        )


def validate_provider_health(provider: BaseProvider, model_name: str) -> None:
    """
    Validate that a provider is healthy before use

    Args:
        provider: The provider to validate
        model_name: Name of the model for context

    Raises:
        HTTPException: If provider is not healthy
    """

    if provider is None:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail={
                "error": "Provider Validation Failed",
                "message": f"Provider for model '{model_name}' is None",
                "error_type": "provider_null",
            },
        )

    # Additional health checks could be added here
    # For example, checking provider status, connectivity, etc.


async def get_fallback_provider(
    provider_factory: ProviderFactory, preferred_model: str, task_type: str = "general"
) -> Optional[BaseProvider]:
    """
    Get a fallback provider when the preferred model is unavailable

    Args:
        provider_factory: The provider factory instance
        preferred_model: The originally requested model
        task_type: Type of task for provider selection

    Returns:
        Optional[BaseProvider]: A fallback provider if available
    """

    logger.warning(
        f"Attempting fallback provider selection (preferred: {preferred_model}, task: {task_type})"
    )

    try:
        # Try to get the best provider for the task type
        fallback_provider = await provider_factory.get_best_provider_for_task(task_type)

        if fallback_provider:
            logger.info(f"Found fallback provider for task type '{task_type}'")
            return fallback_provider
        else:
            logger.warning(
                f"No fallback provider available for task type '{task_type}'"
            )
            return None

    except Exception as e:
        logger.error(f"Error during fallback provider selection: {e}")
        return None


class ProviderSafetyMixin:
    """
    Mixin class to add provider safety methods to service classes
    """

    async def get_provider_with_safety(
        self, model_name: str, operation_context: str = "generation"
    ) -> BaseProvider:
        """
        Get provider with comprehensive safety checks

        Args:
            model_name: Name of the model
            operation_context: Context for logging and error reporting

        Returns:
            BaseProvider: The provider instance

        Raises:
            ProviderUnavailableError: If provider is unavailable
        """

        if not hasattr(self, "provider_factory"):
            raise AttributeError(
                "Service must have provider_factory attribute to use ProviderSafetyMixin"
            )

        return await get_provider_safely(
            self.provider_factory, model_name, operation_context
        )

    async def get_provider_with_fallback(
        self,
        model_name: str,
        task_type: str = "general",
        operation_context: str = "generation",
    ) -> BaseProvider:
        """
        Get provider with automatic fallback on failure

        Args:
            model_name: Preferred model name
            task_type: Type of task for fallback selection
            operation_context: Context for logging

        Returns:
            BaseProvider: The provider instance (preferred or fallback)

        Raises:
            ProviderUnavailableError: If no provider is available
        """

        try:
            # Try preferred model first
            return await self.get_provider_with_safety(model_name, operation_context)

        except ProviderUnavailableError:
            logger.warning(
                f"Preferred model '{model_name}' unavailable, trying fallback"
            )

            # Try fallback
            fallback_provider = await get_fallback_provider(
                self.provider_factory, model_name, task_type
            )

            if fallback_provider:
                logger.info(f"Using fallback provider for {operation_context}")
                return fallback_provider
            else:
                # Re-raise original error if no fallback
                logger.error(f"No fallback provider available for {operation_context}")
                raise
