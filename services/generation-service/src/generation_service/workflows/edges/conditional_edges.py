"""
Conditional edges for LangGraph workflow routing
"""

from typing import Literal

# Import Core Module components
try:
    from ai_script_core import get_service_logger

    CORE_AVAILABLE = True
    logger = get_service_logger("generation-service.workflows.edges")
except (ImportError, RuntimeError):
    CORE_AVAILABLE = False
    import logging

    logger = logging.getLogger(__name__)

from generation_service.workflows.state import GenerationState


def should_enhance_plot(state: GenerationState) -> bool:
    """
    Determine if plot enhancement is needed

    Returns True if the script would benefit from plot twists or narrative surprises
    """

    try:
        request = state["original_request"]
        styled_script = state.get("styled_script", "")

        # Check script type
        script_type = getattr(request, "script_type", None)
        if script_type:
            script_type_str = (
                script_type.value
                if hasattr(script_type, "value")
                else str(script_type).lower()
            )
            if "thriller" in script_type_str or "mystery" in script_type_str:
                return True

        # Check description for plot enhancement keywords
        description = getattr(request, "description", "").lower()
        plot_keywords = [
            "twist",
            "surprise",
            "unexpected",
            "reveal",
            "secret",
            "mystery",
        ]
        if any(keyword in description for keyword in plot_keywords):
            return True

        # Check styled script for plot simplicity (might need enhancement)
        if styled_script:
            # Simple heuristic: if script is very straightforward, might benefit from plot enhancement
            script_lower = styled_script.lower()
            if (
                len(script_lower) > 1000 and script_lower.count("then") > 5
            ):  # Too linear
                return True

        # Check current quality score
        if state.get("current_quality_score", 0.0) < 0.7:
            return True

        return False

    except Exception as e:
        logger.warning(f"Error in should_enhance_plot: {e}")
        return False


def should_improve_dialogue(state: GenerationState) -> bool:
    """
    Determine if dialogue improvement is needed

    Returns True if the script would benefit from dialogue enhancement
    """

    try:
        styled_script = state.get("styled_script", "")

        if not styled_script:
            return False

        # Check dialogue quality indicators
        has_dialogue = '"' in styled_script or "'" in styled_script
        if not has_dialogue:
            return True  # Definitely needs dialogue

        # Check for character names (indicating proper dialogue formatting)
        lines = styled_script.split("\n")
        character_lines = sum(
            1
            for line in lines
            if line.strip().isupper() and len(line.strip().split()) <= 3
        )
        total_lines = len([line for line in lines if line.strip()])

        if total_lines > 0:
            dialogue_ratio = character_lines / total_lines
            if dialogue_ratio < 0.1:  # Very little dialogue
                return True

        # Check for exposition-heavy dialogue (needs improvement)
        exposition_indicators = ["as you know", "remember when", "let me explain"]
        if any(
            indicator in styled_script.lower() for indicator in exposition_indicators
        ):
            return True

        # Check current quality score from stylist
        stylist_quality = state.get("quality_checkpoints", {}).get("stylist", 0.0)
        if stylist_quality < 0.8:
            return True

        return False

    except Exception as e:
        logger.warning(f"Error in should_improve_dialogue: {e}")
        return False


def should_add_details(state: GenerationState) -> bool:
    """
    Determine if additional details are needed

    Returns True if the script would benefit from more descriptive details or scene enhancement
    """

    try:
        styled_script = state.get("styled_script", "")

        if not styled_script:
            return False

        # Check script length - too short might need details
        if len(styled_script) < 1500:
            return True

        # Check for scene description density
        scene_indicators = ["ext.", "int.", "fade", "cut to", "close-up", "wide shot"]
        scene_count = sum(
            styled_script.lower().count(indicator) for indicator in scene_indicators
        )

        if scene_count < 3:  # Very few scene descriptions
            return True

        # Check for emotional depth indicators
        emotion_words = ["feel", "emotion", "heart", "tears", "smile", "frown", "sigh"]
        emotion_count = sum(styled_script.lower().count(word) for word in emotion_words)

        if emotion_count < 2:  # Lacks emotional depth
            return True

        # Check request type for detail requirements
        request = state["original_request"]
        script_type = getattr(request, "script_type", None)
        if script_type:
            script_type_str = (
                script_type.value
                if hasattr(script_type, "value")
                else str(script_type).lower()
            )
            if "drama" in script_type_str:  # Drama typically needs rich details
                return True

        return False

    except Exception as e:
        logger.warning(f"Error in should_add_details: {e}")
        return False


def route_after_stylist(
    state: GenerationState,
) -> Literal["special_agent", "finalization"]:
    """
    Route decision after stylist node

    Determines whether to proceed with special agent enhancement or go directly to finalization
    """

    try:
        # Check if any enhancement is needed
        needs_plot = should_enhance_plot(state)
        needs_dialogue = should_improve_dialogue(state)
        needs_details = should_add_details(state)

        # Update state flags for tracking
        state["needs_plot_enhancement"] = needs_plot
        state["needs_dialogue_improvement"] = needs_dialogue
        state["needs_detail_addition"] = needs_details

        # If any enhancement is needed, route to special agent
        if needs_plot or needs_dialogue or needs_details:
            state["requires_special_agent"] = True

            if CORE_AVAILABLE:
                logger.info(
                    "Routing to special agent",
                    extra={
                        "generation_id": state["generation_id"],
                        "needs_plot": needs_plot,
                        "needs_dialogue": needs_dialogue,
                        "needs_details": needs_details,
                    },
                )

            return "special_agent"
        else:
            state["requires_special_agent"] = False

            if CORE_AVAILABLE:
                logger.info(
                    "Routing to finalization",
                    extra={
                        "generation_id": state["generation_id"],
                        "reason": "no_enhancement_needed",
                    },
                )

            return "finalization"

    except Exception as e:
        logger.error(f"Error in route_after_stylist: {e}")
        # Default to finalization on error
        state["requires_special_agent"] = False
        return "finalization"


def route_to_finalization(state: GenerationState) -> Literal["finalization"]:
    """
    Final routing to finalization (always goes to finalization)

    This is used after special agent processing to ensure workflow completion
    """

    if CORE_AVAILABLE:
        logger.info(
            "Routing to finalization after special agent",
            extra={
                "generation_id": state["generation_id"],
                "enhanced_script_available": bool(state.get("enhanced_script")),
            },
        )

    return "finalization"


def determine_special_agent_type(
    state: GenerationState,
) -> Literal[
    "plot_twister",
    "dialogue_enhancer",
    "emotion_amplifier",
    "tension_builder",
    "conflict_intensifier",
    "humor_injector",
    "flaw_generator",
    "pacing_optimizer",
]:
    """
    Determine which specific special agent to use based on needs analysis
    """

    try:
        # Priority-based selection based on needs
        if state.get("needs_plot_enhancement", False):
            return "plot_twister"

        if state.get("needs_dialogue_improvement", False):
            return "dialogue_enhancer"

        if state.get("needs_detail_addition", False):
            # Choose based on script type
            request = state["original_request"]
            script_type = getattr(request, "script_type", None)

            if script_type:
                script_type_str = (
                    script_type.value
                    if hasattr(script_type, "value")
                    else str(script_type).lower()
                )

                if "drama" in script_type_str:
                    return "emotion_amplifier"
                elif "thriller" in script_type_str:
                    return "tension_builder"
                elif "comedy" in script_type_str:
                    return "humor_injector"
                else:
                    return "emotion_amplifier"  # Default for detail addition

        # Analyze request description for specific agent selection
        request = state["original_request"]
        description = getattr(request, "description", "").lower()

        if "conflict" in description:
            return "conflict_intensifier"
        elif "character" in description and "flaw" in description:
            return "flaw_generator"
        elif "pace" in description or "rhythm" in description:
            return "pacing_optimizer"
        elif "tension" in description:
            return "tension_builder"
        elif "emotion" in description:
            return "emotion_amplifier"
        elif "funny" in description or "humor" in description:
            return "humor_injector"

        # Default fallback
        return "dialogue_enhancer"

    except Exception as e:
        logger.warning(f"Error determining special agent type: {e}")
        return "dialogue_enhancer"  # Safe default


def should_continue_workflow(state: GenerationState) -> bool:
    """
    Determine if workflow should continue or terminate

    Used for error handling and early termination scenarios
    """

    try:
        # Check for critical errors
        if state.get("has_errors", False):
            error_messages = state.get("error_messages", [])
            # Only continue if errors are non-critical
            critical_errors = [
                msg for msg in error_messages if "critical" in msg.lower()
            ]
            if critical_errors:
                return False

        # Check minimum progress requirements
        if not state.get("draft_script") and not state.get("styled_script"):
            return False  # No meaningful progress made

        # Check if we have enough for a basic script
        current_script = (
            state.get("enhanced_script")
            or state.get("styled_script")
            or state.get("draft_script")
            or ""
        )

        if len(current_script) < 100:
            return False  # Script too short to be useful

        return True

    except Exception as e:
        logger.error(f"Error in should_continue_workflow: {e}")
        return False  # Err on the side of caution
