"""
Base class for specialized AI agents
"""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any

# Import Core Module components
try:
    from ai_script_core import (
        get_service_logger,
        utc_now,
    )

    CORE_AVAILABLE = True
    logger = get_service_logger("generation-service.base_agent")
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


from generation_service.ai.providers.base_provider import ProviderGenerationRequest
from generation_service.workflows.state import GenerationState


class AgentExecutionError(Exception):
    """Error during agent execution"""

    def __init__(
        self, agent_name: str, message: str, original_error: Exception | None = None
    ):
        self.agent_name = agent_name
        self.message = message
        self.original_error = original_error
        super().__init__(f"Agent {agent_name} failed: {message}")


class AgentCapability(str, Enum):
    """Agent capabilities"""

    PLOT_ENHANCEMENT = "plot_enhancement"
    CHARACTER_DEVELOPMENT = "character_development"
    DIALOGUE_IMPROVEMENT = "dialogue_improvement"
    VISUAL_ENHANCEMENT = "visual_enhancement"
    TENSION_BUILDING = "tension_building"
    HUMOR_INJECTION = "humor_injection"
    PACING_OPTIMIZATION = "pacing_optimization"
    EMOTION_AMPLIFICATION = "emotion_amplification"


class AgentPriority(int, Enum):
    """Agent execution priority"""

    LOW = 1
    MEDIUM = 5
    HIGH = 8
    CRITICAL = 10


class BaseSpecialAgent(ABC):
    """
    Base class for all specialized AI agents

    Each agent focuses on a specific aspect of script enhancement:
    - Plot enhancement, character development, dialogue improvement, etc.
    - Provides consistent interface for execution and quality assessment
    - Supports both independent and coordinated execution
    """

    def __init__(
        self,
        agent_name: str,
        capabilities: list[AgentCapability],
        priority: AgentPriority = AgentPriority.MEDIUM,
        provider_factory: Any | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        self.agent_name = agent_name
        self.capabilities = capabilities
        self.priority = priority
        self.provider_factory = provider_factory
        self.config = config or {}
        self.provider = None

        # Execution metrics
        self.execution_count = 0
        self.success_count = 0
        self.total_execution_time = 0.0
        self.average_quality_improvement = 0.0

        if CORE_AVAILABLE:
            logger.info(
                f"Initialized {agent_name} agent",
                extra={
                    "agent_name": agent_name,
                    "capabilities": [cap.value for cap in capabilities],
                    "priority": priority.value,
                },
            )

    @abstractmethod
    async def analyze_content(self, state: GenerationState) -> dict[str, Any]:
        """
        Analyze content to determine if this agent should be applied

        Returns:
            Dict with analysis results and recommendations
        """
        pass

    @abstractmethod
    async def enhance_content(self, state: GenerationState) -> dict[str, Any]:
        """
        Apply agent-specific enhancements to the content

        Returns:
            Dict with enhanced content and metadata
        """
        pass

    @abstractmethod
    def calculate_quality_improvement(
        self, original_content: str, enhanced_content: str
    ) -> float:
        """
        Calculate quality improvement score (0.0 to 1.0)
        """
        pass

    async def execute(self, state: GenerationState) -> GenerationState:
        """
        Execute the agent with full error handling and metrics
        """
        start_time = utc_now() if CORE_AVAILABLE else datetime.now()

        try:
            # Initialize provider if needed
            if not self.provider and self.provider_factory:
                await self._initialize_provider()

            # Validate input state
            self._validate_input_state(state)

            # Analyze content to determine if enhancement is needed
            analysis = await self.analyze_content(state)

            if not analysis.get("should_enhance", False):
                logger.info(
                    f"Agent {self.agent_name} skipping - enhancement not needed"
                )
                return self._create_skip_result(state, analysis)

            # Apply enhancements
            enhancement_result = await self.enhance_content(state)

            # Update state with results
            updated_state = self._update_state_with_enhancement(
                state, enhancement_result, analysis
            )

            # Calculate execution metrics
            end_time = utc_now() if CORE_AVAILABLE else datetime.now()
            execution_time = (end_time - start_time).total_seconds()

            self._update_execution_metrics(execution_time, enhancement_result)

            if CORE_AVAILABLE:
                logger.info(
                    f"Agent {self.agent_name} completed successfully",
                    extra={
                        "agent_name": self.agent_name,
                        "generation_id": state["generation_id"],
                        "execution_time": execution_time,
                        "quality_improvement": enhancement_result.get(
                            "quality_improvement", 0.0
                        ),
                    },
                )

            return updated_state

        except Exception as e:
            logger.error(f"Agent {self.agent_name} execution failed: {e}")

            # Update error metrics
            self.execution_count += 1

            # Create error state
            error_state = state.copy()
            error_state["has_errors"] = True
            error_state["error_messages"].append(
                f"Agent {self.agent_name} failed: {e!s}"
            )

            # Don't fail the entire workflow - continue with original content
            return error_state

    async def _initialize_provider(self) -> None:
        """Initialize AI provider for the agent"""

        try:
            # Use GPT-4o for specialized enhancements
            self.provider = await self.provider_factory.get_provider("openai")

            if not self.provider:
                logger.warning(f"No provider available for agent {self.agent_name}")

        except Exception as e:
            logger.error(f"Failed to initialize provider for {self.agent_name}: {e}")

    def _validate_input_state(self, state: GenerationState) -> None:
        """Validate input state has required content"""

        # Check for required content
        if not state.get("styled_script") and not state.get("draft_script"):
            raise AgentExecutionError(
                self.agent_name, "No script content available for enhancement"
            )

    def _create_skip_result(
        self, state: GenerationState, analysis: dict[str, Any]
    ) -> GenerationState:
        """Create result when agent is skipped"""

        skip_state = state.copy()

        # Add skip metadata
        skip_metadata = {
            "agent_name": self.agent_name,
            "skipped": True,
            "skip_reason": analysis.get("skip_reason", "Enhancement not needed"),
            "analysis": analysis,
        }

        # Update execution log
        if "execution_log" not in skip_state:
            skip_state["execution_log"] = []

        skip_state["execution_log"].append(
            {
                "node": f"agent_{self.agent_name}",
                "status": "skipped",
                "timestamp": (
                    utc_now().isoformat()
                    if CORE_AVAILABLE
                    else datetime.now().isoformat()
                ),
                "metadata": skip_metadata,
            }
        )

        return skip_state

    def _update_state_with_enhancement(
        self,
        state: GenerationState,
        enhancement_result: dict[str, Any],
        analysis: dict[str, Any],
    ) -> GenerationState:
        """Update state with enhancement results"""

        enhanced_state = state.copy()

        # Update content
        if "enhanced_content" in enhancement_result:
            enhanced_state["enhanced_script"] = enhancement_result["enhanced_content"]

        # Update quality scores
        if "quality_improvement" in enhancement_result:
            current_score = enhanced_state.get("current_quality_score", 0.0)
            improved_score = min(
                current_score + enhancement_result["quality_improvement"], 1.0
            )
            enhanced_state["current_quality_score"] = improved_score

        # Update metadata
        agent_metadata = {
            "agent_name": self.agent_name,
            "capabilities_applied": [cap.value for cap in self.capabilities],
            "analysis": analysis,
            "enhancement_result": enhancement_result,
            "quality_improvement": enhancement_result.get("quality_improvement", 0.0),
            "tokens_used": enhancement_result.get("tokens_used", 0),
            "model_used": enhancement_result.get("model_used", "unknown"),
        }

        # Update generation metadata
        if "generation_metadata" not in enhanced_state:
            enhanced_state["generation_metadata"] = {}

        enhanced_state["generation_metadata"][
            f"agent_{self.agent_name}"
        ] = agent_metadata

        # Update execution log
        if "execution_log" not in enhanced_state:
            enhanced_state["execution_log"] = []

        enhanced_state["execution_log"].append(
            {
                "node": f"agent_{self.agent_name}",
                "status": "completed",
                "timestamp": (
                    utc_now().isoformat()
                    if CORE_AVAILABLE
                    else datetime.now().isoformat()
                ),
                "metadata": agent_metadata,
            }
        )

        return enhanced_state

    def _update_execution_metrics(
        self, execution_time: float, enhancement_result: dict[str, Any]
    ) -> None:
        """Update agent execution metrics"""

        self.execution_count += 1
        self.success_count += 1
        self.total_execution_time += execution_time

        # Update quality improvement average
        quality_improvement = enhancement_result.get("quality_improvement", 0.0)
        current_avg = self.average_quality_improvement
        self.average_quality_improvement = (
            current_avg * (self.success_count - 1) + quality_improvement
        ) / self.success_count

    async def create_enhancement_prompt(
        self, content: str, analysis: dict[str, Any]
    ) -> str:
        """
        Create agent-specific enhancement prompt
        Override in subclasses for specialized prompts
        """

        return f"""
Enhance the following script content with {self.agent_name} improvements:

CONTENT TO ENHANCE:
{content}

ANALYSIS CONTEXT:
{analysis.get('context', 'No specific context provided')}

ENHANCEMENT FOCUS:
{', '.join([cap.value.replace('_', ' ').title() for cap in self.capabilities])}

REQUIREMENTS:
- Maintain the original story structure and character voices
- Apply {self.agent_name} specific improvements
- Ensure natural integration with existing content
- Preserve script formatting and style

Please provide the enhanced version of the script.
"""

    async def execute_ai_enhancement(
        self, prompt: str, max_tokens: int = 3000
    ) -> dict[str, Any]:
        """Execute AI enhancement using the provider"""

        if not self.provider:
            raise AgentExecutionError(
                self.agent_name, "No AI provider available for enhancement"
            )

        generation_request = ProviderGenerationRequest(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=0.7,  # Balanced creativity for enhancements
        )

        response = await self.provider.generate_with_retry(generation_request)

        return {
            "enhanced_content": response.content,
            "model_used": response.model_info.name,
            "tokens_used": (
                response.metadata.get("tokens_used", 0) if response.metadata else 0
            ),
        }

    def get_agent_metrics(self) -> dict[str, Any]:
        """Get agent performance metrics"""

        success_rate = (
            self.success_count / self.execution_count
            if self.execution_count > 0
            else 0.0
        )
        avg_execution_time = (
            self.total_execution_time / self.execution_count
            if self.execution_count > 0
            else 0.0
        )

        return {
            "agent_name": self.agent_name,
            "capabilities": [cap.value for cap in self.capabilities],
            "priority": self.priority.value,
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "success_rate": success_rate,
            "average_execution_time": avg_execution_time,
            "average_quality_improvement": self.average_quality_improvement,
            "total_execution_time": self.total_execution_time,
        }

    def is_applicable(self, state: GenerationState) -> bool:
        """
        Quick check if agent is applicable to current state
        Override in subclasses for specific conditions
        """

        # Basic check for content availability
        return bool(state.get("styled_script") or state.get("draft_script"))

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get configuration value for the agent"""
        return self.config.get(key, default)
