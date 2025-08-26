"""
Base node class for LangGraph workflow nodes
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

# Import Core Module components
try:
    from ai_script_core import (
        BaseServiceException,
        ValidationException,
        get_service_logger,
        utc_now,
    )

    CORE_AVAILABLE = True
    logger = get_service_logger("generation-service.base_node")
except (ImportError, RuntimeError):
    CORE_AVAILABLE = False
    import logging

    logger = logging.getLogger(__name__)

    # Fallback utility functions
    def utc_now() -> datetime:
        """Fallback UTC timestamp"""
        from datetime import datetime, timezone

        return datetime.now(timezone.utc)

    def generate_uuid() -> str:
        """Fallback UUID generation"""
        import uuid

        return str(uuid.uuid4())

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


from generation_service.workflows.state import (
    GenerationState,
    add_execution_log,
    update_quality_score,
)


class NodeExecutionError(Exception):
    """Base exception for node execution errors"""

    def __init__(
        self, message: str, node_name: str, original_error: Exception | None = None
    ):
        self.message = message
        self.node_name = node_name
        self.original_error = original_error
        super().__init__(message)


if CORE_AVAILABLE:

    class NodeExecutionError(BaseServiceException):
        """Node execution error using Core Module"""

        def __init__(
            self,
            message: str,
            node_name: str,
            original_error: Exception | None = None,
        ):
            super().__init__(
                message=message,
                error_code=f"NODE_{node_name.upper()}_ERROR",
                context={
                    "node_name": node_name,
                    "original_error": str(original_error) if original_error else None,
                },
            )
            self.node_name = node_name
            self.original_error = original_error


class BaseNode(ABC):
    """
    Base class for all LangGraph workflow nodes

    Provides common functionality for:
    - Execution logging and state tracking
    - Core Module exception handling
    - Performance monitoring
    - Quality score management
    """

    def __init__(self, node_name: str) -> None:
        self.node_name = node_name
        self.logger = logger

        if CORE_AVAILABLE:
            self.logger.info(f"Node {node_name} initialized with Core integration")
        else:
            self.logger.info(f"Node {node_name} initialized")

    async def execute(self, state: GenerationState) -> GenerationState:
        """
        Execute the node with full error handling and logging

        This is the main entry point that should be called by LangGraph.
        It wraps the actual node logic with common functionality.
        """

        start_time = utc_now() if CORE_AVAILABLE else datetime.now()

        if CORE_AVAILABLE:
            self.logger.info(
                f"Starting execution of {self.node_name}",
                extra={
                    "generation_id": state["generation_id"],
                    "node_name": self.node_name,
                },
            )
        else:
            self.logger.info(f"Starting execution of {self.node_name}")

        try:
            # Validate input state
            self._validate_input_state(state)

            # Execute the actual node logic
            updated_state = await self._execute_node_logic(state)

            # Validate output state
            self._validate_output_state(updated_state)

            # Calculate execution time
            end_time = utc_now() if CORE_AVAILABLE else datetime.now()
            execution_time = (end_time - start_time).total_seconds()

            # Add successful execution log
            add_execution_log(
                updated_state,
                self.node_name,
                success=True,
                start_time=start_time,
                end_time=end_time,
                metadata={
                    "execution_time_seconds": execution_time,
                    **self._get_execution_metadata(updated_state),
                },
            )

            # Update quality score if applicable
            quality_score = self._calculate_quality_score(updated_state)
            if quality_score is not None:
                update_quality_score(updated_state, self.node_name, quality_score)

            if CORE_AVAILABLE:
                self.logger.info(
                    f"Successfully completed {self.node_name}",
                    extra={
                        "generation_id": state["generation_id"],
                        "node_name": self.node_name,
                        "execution_time_seconds": execution_time,
                        "quality_score": quality_score,
                    },
                )

            return updated_state

        except Exception as e:
            # Calculate execution time for failed execution
            end_time = utc_now() if CORE_AVAILABLE else datetime.now()
            execution_time = (end_time - start_time).total_seconds()

            # Handle the error
            error_message = self._handle_execution_error(e, state)

            # Add failed execution log
            add_execution_log(
                state,
                self.node_name,
                success=False,
                start_time=start_time,
                end_time=end_time,
                error_message=error_message,
                metadata={
                    "execution_time_seconds": execution_time,
                    "error_type": type(e).__name__,
                },
            )

            if CORE_AVAILABLE:
                self.logger.error(
                    f"Failed to execute {self.node_name}",
                    extra={
                        "generation_id": state["generation_id"],
                        "node_name": self.node_name,
                        "error_message": error_message,
                        "execution_time_seconds": execution_time,
                    },
                )

            # Re-raise as NodeExecutionError
            raise NodeExecutionError(
                message=f"Node {self.node_name} execution failed: {error_message}",
                node_name=self.node_name,
                original_error=e,
            )

    @abstractmethod
    async def _execute_node_logic(self, state: GenerationState) -> GenerationState:
        """
        Execute the actual node logic

        This method must be implemented by each concrete node class.
        It should contain the core functionality of the node.
        """
        pass

    def _validate_input_state(self, state: GenerationState) -> None:
        """
        Validate the input state before execution

        Override this method to add node-specific input validation.
        """

        # Basic validation
        if not state.get("generation_id"):
            raise ValidationException(
                "Missing generation_id in state", field="generation_id"
            )

        if not state.get("original_request"):
            raise ValidationException(
                "Missing original_request in state", field="original_request"
            )

        # Node-specific validation (override in subclasses)
        self._validate_node_specific_input(state)

    def _validate_output_state(self, state: GenerationState) -> None:
        """
        Validate the output state after execution

        Override this method to add node-specific output validation.
        """

        # Node-specific validation (override in subclasses)
        self._validate_node_specific_output(state)

    def _validate_node_specific_input(self, state: GenerationState) -> None:
        """Override this method for node-specific input validation"""
        pass

    def _validate_node_specific_output(self, state: GenerationState) -> None:
        """Override this method for node-specific output validation"""
        pass

    def _handle_execution_error(self, error: Exception, state: GenerationState) -> str:
        """
        Handle execution errors and return formatted error message

        Override this method for custom error handling.
        """

        error_message = str(error)

        # Log the error appropriately
        if CORE_AVAILABLE and isinstance(error, BaseServiceException):
            # Core Module exception - already properly logged
            pass
        else:
            # Standard exception
            self.logger.error(
                f"Error in {self.node_name}: {error_message}", exc_info=True
            )

        return error_message

    def _get_execution_metadata(self, state: GenerationState) -> dict[str, Any]:
        """
        Get execution metadata for logging

        Override this method to add node-specific metadata.
        """

        return {
            "current_stage": self._determine_current_stage(state),
            "quality_score": state.get("current_quality_score", 0.0),
        }

    def _calculate_quality_score(self, state: GenerationState) -> float | None:
        """
        Calculate quality score for this node's output

        Override this method to implement node-specific quality scoring.
        Returns None if quality scoring is not applicable for this node.
        """

        return None

    def _determine_current_stage(self, state: GenerationState) -> str:
        """Determine the current stage based on completed work"""

        if state.get("final_script"):
            return "completed"
        elif state.get("enhanced_script"):
            return "finalizing"
        elif state.get("styled_script"):
            return "enhancing"
        elif state.get("draft_script"):
            return "styling"
        else:
            return "architecting"

    def get_node_info(self) -> dict[str, Any]:
        """Get information about this node"""

        return {
            "node_name": self.node_name,
            "node_type": self.__class__.__name__,
            "core_available": CORE_AVAILABLE,
        }


class ProviderNode(BaseNode):
    """
    Base class for nodes that use AI providers

    Extends BaseNode with AI provider specific functionality.
    """

    def __init__(self, node_name: str, provider_name: str) -> None:
        super().__init__(node_name)
        self.provider_name = provider_name
        self.provider = None

    async def _initialize_provider(self, provider_factory: Any) -> None:
        """Initialize the AI provider"""

        try:
            self.provider = await provider_factory.get_provider(self.provider_name)

            if CORE_AVAILABLE:
                self.logger.info(
                    f"Provider {self.provider_name} initialized for {self.node_name}"
                )

        except Exception as e:
            error_msg = f"Failed to initialize provider {self.provider_name}: {e!s}"
            self.logger.error(error_msg)
            raise NodeExecutionError(error_msg, self.node_name, e)

    def _get_execution_metadata(self, state: GenerationState) -> dict[str, Any]:
        """Add provider-specific metadata"""

        base_metadata = super()._get_execution_metadata(state)
        base_metadata.update(
            {
                "provider_name": self.provider_name,
                "provider_available": self.provider is not None,
            }
        )

        return base_metadata


class PromptNode(ProviderNode):
    """
    Base class for nodes that use specialized prompts

    Extends ProviderNode with prompt template functionality.
    """

    def __init__(
        self, node_name: str, provider_name: str, prompt_template: Any
    ) -> None:
        super().__init__(node_name, provider_name)
        self.prompt_template = prompt_template

    def _get_execution_metadata(self, state: GenerationState) -> dict[str, Any]:
        """Add prompt-specific metadata"""

        base_metadata = super()._get_execution_metadata(state)
        base_metadata.update(
            {
                "prompt_template_type": self.prompt_template.__class__.__name__,
                "specialized_prompt_used": True,
            }
        )

        return base_metadata
