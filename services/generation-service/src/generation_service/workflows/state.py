"""
LangGraph workflow state definitions for script generation
"""

from datetime import datetime
from typing import Any, Optional, TypedDict

# Import Core Module components
try:
    from ai_script_core import (
        generate_uuid,
        get_service_logger,
        utc_now,
    )

    CORE_AVAILABLE = True
    logger = get_service_logger("generation-service.state")
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


from generation_service.models.generation import GenerationRequest


class ExecutionLogEntry(TypedDict):
    """Individual execution log entry"""

    node_name: str
    start_time: str
    end_time: Optional[str]
    execution_time_seconds: Optional[float]
    success: bool
    error_message: Optional[str]
    metadata: dict[str, Any]


class GenerationMetadata(TypedDict):
    """Generation metadata for workflow"""

    generation_id: str
    workflow_version: str
    total_execution_time: Optional[float]
    nodes_executed: list[str]
    nodes_skipped: list[str]
    quality_scores: dict[str, float]
    token_usage: dict[str, int]
    model_usage: dict[str, str]
    rag_context_used: bool
    specialized_prompts_used: bool


class GenerationState(TypedDict):
    """
    LangGraph state for script generation workflow

    This state is passed between all nodes in the workflow and contains
    all necessary data for the multi-stage AI collaboration process.
    """

    # Input and context
    original_request: GenerationRequest
    rag_context: str
    generation_id: str

    # Script stages (논의된 하이브리드 워크플로우)
    draft_script: Optional[str]  # Architect 결과 (Claude)
    styled_script: Optional[str]  # Stylist 결과 (Llama)
    enhanced_script: Optional[str]  # Special Agent 결과 (GPT)
    final_script: Optional[str]  # 최종 결과

    # Intermediate data
    architect_structure: Optional[str]  # 구조적 기반
    style_metadata: Optional[dict[str, Any]]  # 스타일 메타데이터
    enhancement_metadata: Optional[dict[str, Any]]  # 향상 메타데이터

    # Workflow control
    execution_log: list[ExecutionLogEntry]
    generation_metadata: GenerationMetadata

    # Decision flags for conditional edges
    needs_plot_enhancement: bool
    needs_dialogue_improvement: bool
    needs_detail_addition: bool
    requires_special_agent: bool
    special_agent_type: Optional[str]

    # Error handling
    has_errors: bool
    error_messages: list[str]

    # Quality tracking
    quality_checkpoints: dict[str, float]
    current_quality_score: float


def create_initial_state(
    request: GenerationRequest,
    rag_context: str = "",
    generation_id: Optional[str] = None,
) -> GenerationState:
    """Create initial workflow state from generation request"""

    if generation_id is None:
        if CORE_AVAILABLE:
            generation_id = generate_uuid()
        else:
            from datetime import datetime

            generation_id = f"gen_{int(datetime.now().timestamp())}"

    # Create generation metadata
    metadata = GenerationMetadata(
        generation_id=generation_id,
        workflow_version="1.0.0",
        total_execution_time=None,
        nodes_executed=[],
        nodes_skipped=[],
        quality_scores={},
        token_usage={},
        model_usage={},
        rag_context_used=bool(rag_context),
        specialized_prompts_used=True,
    )

    # Initialize state
    state = GenerationState(
        # Input and context
        original_request=request,
        rag_context=rag_context,
        generation_id=generation_id,
        # Script stages - all start as None
        draft_script=None,
        styled_script=None,
        enhanced_script=None,
        final_script=None,
        # Intermediate data
        architect_structure=None,
        style_metadata=None,
        enhancement_metadata=None,
        # Workflow control
        execution_log=[],
        generation_metadata=metadata,
        # Decision flags - will be set during execution
        needs_plot_enhancement=False,
        needs_dialogue_improvement=False,
        needs_detail_addition=False,
        requires_special_agent=False,
        special_agent_type=None,
        # Error handling
        has_errors=False,
        error_messages=[],
        # Quality tracking
        quality_checkpoints={},
        current_quality_score=0.0,
    )

    if CORE_AVAILABLE:
        logger.info(
            "Initial workflow state created",
            extra={
                "generation_id": generation_id,
                "workflow_version": metadata["workflow_version"],
                "rag_context_available": bool(rag_context),
                "request_title": getattr(request, "title", "Untitled"),
            },
        )

    return state


def add_execution_log(
    state: GenerationState,
    node_name: str,
    success: bool,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    error_message: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    """Add execution log entry to state"""

    if start_time is None:
        start_time = utc_now() if CORE_AVAILABLE else datetime.now()

    if end_time is None:
        end_time = utc_now() if CORE_AVAILABLE else datetime.now()

    execution_time = None
    if start_time and end_time:
        execution_time = (end_time - start_time).total_seconds()

    log_entry = ExecutionLogEntry(
        node_name=node_name,
        start_time=start_time.isoformat(),
        end_time=end_time.isoformat() if end_time else None,
        execution_time_seconds=execution_time,
        success=success,
        error_message=error_message,
        metadata=metadata or {},
    )

    state["execution_log"].append(log_entry)

    # Update metadata
    if success:
        if node_name not in state["generation_metadata"]["nodes_executed"]:
            state["generation_metadata"]["nodes_executed"].append(node_name)
    else:
        state["has_errors"] = True
        if error_message:
            state["error_messages"].append(f"{node_name}: {error_message}")


def update_quality_score(
    state: GenerationState, checkpoint_name: str, score: float
) -> None:
    """Update quality score for a checkpoint"""

    # Clamp score to [0, 1] range
    score = max(0.0, min(1.0, score))

    state["quality_checkpoints"][checkpoint_name] = score
    state["generation_metadata"]["quality_scores"][checkpoint_name] = score

    # Calculate current overall quality score
    if state["quality_checkpoints"]:
        state["current_quality_score"] = sum(
            state["quality_checkpoints"].values()
        ) / len(state["quality_checkpoints"])


def add_token_usage(
    state: GenerationState, node_name: str, tokens_used: int, model_name: str
) -> None:
    """Add token usage information"""

    state["generation_metadata"]["token_usage"][node_name] = tokens_used
    state["generation_metadata"]["model_usage"][node_name] = model_name


def finalize_state(state: GenerationState) -> None:
    """Finalize the workflow state with total execution time and summary"""

    # Calculate total execution time
    total_time = 0.0
    for log_entry in state["execution_log"]:
        if log_entry["execution_time_seconds"]:
            total_time += log_entry["execution_time_seconds"]

    state["generation_metadata"]["total_execution_time"] = total_time

    # Set final script if not already set
    if not state["final_script"]:
        # Use the most advanced script available
        if state["enhanced_script"]:
            state["final_script"] = state["enhanced_script"]
        elif state["styled_script"]:
            state["final_script"] = state["styled_script"]
        elif state["draft_script"]:
            state["final_script"] = state["draft_script"]

    if CORE_AVAILABLE:
        logger.info(
            "Workflow state finalized",
            extra={
                "generation_id": state["generation_id"],
                "total_execution_time": total_time,
                "nodes_executed": len(state["generation_metadata"]["nodes_executed"]),
                "final_quality_score": state["current_quality_score"],
                "has_errors": state["has_errors"],
            },
        )


def get_state_summary(state: GenerationState) -> dict[str, Any]:
    """Get a summary of the current state"""

    return {
        "generation_id": state["generation_id"],
        "current_stage": _determine_current_stage(state),
        "progress_percentage": _calculate_progress(state),
        "quality_score": state["current_quality_score"],
        "nodes_executed": state["generation_metadata"]["nodes_executed"],
        "has_errors": state["has_errors"],
        "total_execution_time": state["generation_metadata"]["total_execution_time"],
        "rag_context_used": state["generation_metadata"]["rag_context_used"],
    }


def _determine_current_stage(state: GenerationState) -> str:
    """Determine the current stage of the workflow"""

    if state["final_script"]:
        return "completed"
    elif state["enhanced_script"]:
        return "finalizing"
    elif state["styled_script"]:
        return "enhancing"
    elif state["draft_script"]:
        return "styling"
    else:
        return "starting"


def _calculate_progress(state: GenerationState) -> float:
    """Calculate progress percentage based on completed stages"""

    total_stages = 4  # architect, stylist, special_agent, finalization
    completed_stages = 0

    if state["draft_script"]:
        completed_stages += 1
    if state["styled_script"]:
        completed_stages += 1
    if state["enhanced_script"]:
        completed_stages += 1
    if state["final_script"]:
        completed_stages += 1

    return (completed_stages / total_stages) * 100.0


def validate_state(state: GenerationState) -> list[str]:
    """Validate the workflow state and return any issues"""

    issues = []

    # Check required fields
    if not state.get("generation_id"):
        issues.append("Missing generation_id")

    if not state.get("original_request"):
        issues.append("Missing original_request")

    # Check consistency
    if state["styled_script"] and not state["draft_script"]:
        issues.append("Styled script exists without draft script")

    if state["enhanced_script"] and not state["styled_script"]:
        issues.append("Enhanced script exists without styled script")

    if state["final_script"] and not any(
        [state["draft_script"], state["styled_script"], state["enhanced_script"]]
    ):
        issues.append("Final script exists without any intermediate scripts")

    # Check error consistency
    if state["has_errors"] and not state["error_messages"]:
        issues.append("has_errors is True but no error messages")

    return issues
