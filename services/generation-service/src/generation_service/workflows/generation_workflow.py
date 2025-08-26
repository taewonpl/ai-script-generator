"""
Main LangGraph workflow for script generation
"""

from typing import Any, Dict, Optional, Union

# Import Core Module components
try:
    from ai_script_core import (
        get_service_logger,
        utc_now,
    )

    CORE_AVAILABLE = True
    logger = get_service_logger("generation-service.generation_workflow")
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


# LangGraph imports
try:
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.graph import END, StateGraph

    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    logger.warning("LangGraph not available - workflow functionality will be limited")

from generation_service.models.generation import GenerationRequest, GenerationResponse
from generation_service.workflows.edges import route_after_stylist
from generation_service.workflows.nodes import (
    ArchitectNode,
    SpecialAgentRouter,
    StylistNode,
)
from generation_service.workflows.state import (
    GenerationState,
    create_initial_state,
    finalize_state,
)


class GenerationWorkflow:
    """
    Main LangGraph workflow for script generation

    Orchestrates the multi-stage AI collaboration process:
    1. Architect (Claude) - Structural design
    2. Stylist (Llama) - Channel style application
    3. Special Agent (GPT) - Specialized enhancements [conditional]
    4. Finalization - Result compilation
    """

    def __init__(self, provider_factory: Any, rag_service: Optional[Any] = None) -> None:
        self.provider_factory = provider_factory
        self.rag_service = rag_service

        # Initialize workflow components
        self.architect_node = ArchitectNode(provider_factory, rag_service)
        self.stylist_node = StylistNode(provider_factory)
        self.special_agent_router = SpecialAgentRouter(provider_factory)

        # Initialize workflow graph
        self.workflow = None
        self.app = None

        if LANGGRAPH_AVAILABLE:
            self._build_workflow()
        else:
            logger.warning("LangGraph not available - using fallback execution")

        if CORE_AVAILABLE:
            logger.info(
                "GenerationWorkflow initialized",
                extra={
                    "langgraph_available": LANGGRAPH_AVAILABLE,
                    "rag_service_available": rag_service is not None,
                },
            )

    def _build_workflow(self) -> None:
        """Build the LangGraph StateGraph workflow"""

        if not LANGGRAPH_AVAILABLE:
            return

        try:
            # Create state graph
            workflow = StateGraph(GenerationState)

            # Add nodes
            workflow.add_node("architect", self._architect_wrapper)
            workflow.add_node("stylist", self._stylist_wrapper)
            workflow.add_node("special_agent", self._special_agent_wrapper)
            workflow.add_node("finalization", self._finalization_wrapper)

            # Set entry point
            workflow.set_entry_point("architect")

            # Add edges
            workflow.add_edge("architect", "stylist")

            # Conditional edge after stylist
            workflow.add_conditional_edges(
                "stylist",
                route_after_stylist,
                {"special_agent": "special_agent", "finalization": "finalization"},
            )

            # Edge from special agent to finalization
            workflow.add_edge("special_agent", "finalization")

            # End at finalization
            workflow.add_edge("finalization", END)

            # Add memory saver for checkpoints
            memory = MemorySaver()

            # Compile the workflow
            self.app = workflow.compile(checkpointer=memory)
            self.workflow = workflow

            if CORE_AVAILABLE:
                logger.info(
                    "LangGraph workflow compiled successfully",
                    extra={
                        "nodes": [
                            "architect",
                            "stylist",
                            "special_agent",
                            "finalization",
                        ],
                        "entry_point": "architect",
                        "checkpointer": "memory",
                    },
                )

        except Exception as e:
            logger.error(f"Failed to build workflow: {e}")
            self.workflow = None
            self.app = None

    async def _architect_wrapper(self, state: GenerationState) -> GenerationState:
        """Wrapper for architect node execution"""
        return await self.architect_node.execute(state)

    async def _stylist_wrapper(self, state: GenerationState) -> GenerationState:
        """Wrapper for stylist node execution"""
        return await self.stylist_node.execute(state)

    async def _special_agent_wrapper(self, state: GenerationState) -> GenerationState:
        """Wrapper for special agent router execution"""
        return await self.special_agent_router.execute_special_agent(state)

    async def _finalization_wrapper(self, state: GenerationState) -> GenerationState:
        """Wrapper for finalization process"""

        try:
            # Finalize the state
            finalize_state(state)

            # Ensure final script is set
            if not state.get("final_script"):
                # Use the most advanced script available
                final_script = (
                    state.get("enhanced_script")
                    or state.get("styled_script")
                    or state.get("draft_script")
                    or ""
                )
                state["final_script"] = final_script

            if CORE_AVAILABLE:
                logger.info(
                    "Workflow finalized",
                    extra={
                        "generation_id": state["generation_id"],
                        "final_script_length": len(state.get("final_script", "")),
                        "total_execution_time": state["generation_metadata"][
                            "total_execution_time"
                        ],
                        "nodes_executed": len(
                            state["generation_metadata"]["nodes_executed"]
                        ),
                        "final_quality_score": state["current_quality_score"],
                    },
                )

            return state

        except Exception as e:
            logger.error(f"Error in finalization: {e}")
            state["has_errors"] = True
            state["error_messages"].append(f"Finalization error: {e!s}")
            return state

    async def execute(
        self, request: GenerationRequest, generation_id: Optional[str] = None
    ) -> GenerationResponse:
        """
        Execute the complete workflow

        Args:
            request: Generation request with script requirements
            generation_id: Optional generation ID (will be generated if not provided)

        Returns:
            GenerationResponse with the generated script and metadata
        """

        if CORE_AVAILABLE:
            start_time = utc_now()
        else:
            from datetime import datetime

            start_time = datetime.now()

        try:
            # Get RAG context if available
            rag_context = ""
            if self.rag_service:
                try:
                    rag_context = await self.rag_service.search_for_architect_context(
                        title=getattr(request, "title", ""),
                        description=getattr(request, "description", ""),
                        script_type=str(getattr(request, "script_type", "")),
                        project_id=getattr(request, "project_id", None),
                    )
                except Exception as e:
                    logger.warning(f"Failed to get RAG context: {e}")

            # Create initial state
            initial_state = create_initial_state(request, rag_context, generation_id)

            if CORE_AVAILABLE:
                logger.info(
                    "Starting workflow execution",
                    extra={
                        "generation_id": initial_state["generation_id"],
                        "request_title": getattr(request, "title", "Untitled"),
                        "rag_context_available": bool(rag_context),
                        "workflow_type": "langgraph" if self.app else "fallback",
                    },
                )

            # Execute workflow
            if self.app and LANGGRAPH_AVAILABLE:
                final_state = await self._execute_langgraph_workflow(initial_state)
            else:
                final_state = await self._execute_fallback_workflow(initial_state)

            # Create response
            response = self._create_response(final_state, start_time)

            if CORE_AVAILABLE:
                end_time = utc_now()
                total_time = (end_time - start_time).total_seconds()

                logger.info(
                    "Workflow execution completed",
                    extra={
                        "generation_id": final_state["generation_id"],
                        "total_execution_time": total_time,
                        "final_quality_score": final_state["current_quality_score"],
                        "has_errors": final_state["has_errors"],
                        "nodes_executed": len(
                            final_state["generation_metadata"]["nodes_executed"]
                        ),
                    },
                )

            return response

        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")

            # Create error response
            return self._create_error_response(
                request, generation_id or "unknown", str(e), start_time
            )

    async def _execute_langgraph_workflow(
        self, initial_state: GenerationState
    ) -> GenerationState:
        """Execute workflow using LangGraph"""

        config = {"configurable": {"thread_id": initial_state["generation_id"]}}

        # Execute the workflow
        result = await self.app.ainvoke(initial_state, config=config)

        return result

    async def _execute_fallback_workflow(
        self, initial_state: GenerationState
    ) -> GenerationState:
        """Execute workflow without LangGraph (fallback mode)"""

        state = initial_state

        try:
            # Execute architect
            state = await self.architect_node.execute(state)

            # Execute stylist
            state = await self.stylist_node.execute(state)

            # Check if special agent is needed
            routing_decision = route_after_stylist(state)

            if routing_decision == "special_agent":
                # Execute special agent
                state = await self.special_agent_router.execute_special_agent(state)

            # Finalize
            finalize_state(state)

            # Set final script
            if not state.get("final_script"):
                final_script = (
                    state.get("enhanced_script")
                    or state.get("styled_script")
                    or state.get("draft_script")
                    or ""
                )
                state["final_script"] = final_script

            return state

        except Exception as e:
            logger.error(f"Fallback workflow execution failed: {e}")
            state["has_errors"] = True
            state["error_messages"].append(f"Fallback execution error: {e!s}")
            return state

    def _create_response(
        self, final_state: GenerationState, start_time: Any
    ) -> GenerationResponse:
        """Create generation response from final state"""

        if CORE_AVAILABLE:
            end_time = utc_now()
        else:
            from datetime import datetime

            end_time = datetime.now()

        total_time = (end_time - start_time).total_seconds()

        # Extract metadata
        metadata = final_state["generation_metadata"]
        request = final_state["original_request"]

        # Create response
        response_data = {
            "generation_id": final_state["generation_id"],
            "project_id": getattr(request, "project_id", None),
            "episode_id": getattr(request, "episode_id", None),
            "status": "failed" if final_state["has_errors"] else "completed",
            "generated_script": final_state.get("final_script", ""),
            "word_count": (
                len(final_state.get("final_script", "").split())
                if final_state.get("final_script")
                else 0
            ),
            "created_at": start_time,
            "completed_at": end_time,
            "updated_at": end_time,
            "generation_time_seconds": total_time,
        }

        # Add optional fields if they exist in the request
        for field in ["script_type", "title", "description", "model"]:
            if hasattr(request, field):
                response_data[field] = getattr(request, field)

        # Add workflow metadata
        response_data["workflow_metadata"] = {
            "workflow_version": metadata["workflow_version"],
            "nodes_executed": metadata["nodes_executed"],
            "nodes_skipped": metadata["nodes_skipped"],
            "quality_scores": metadata["quality_scores"],
            "token_usage": metadata["token_usage"],
            "model_usage": metadata["model_usage"],
            "rag_context_used": metadata["rag_context_used"],
            "specialized_prompts_used": metadata["specialized_prompts_used"],
            "execution_log": final_state["execution_log"],
            "langgraph_used": self.app is not None,
        }

        # Add quality score
        response_data["quality_score"] = final_state["current_quality_score"]

        # Add error information if present
        if final_state["has_errors"]:
            response_data["error_message"] = "; ".join(final_state["error_messages"])

        return GenerationResponse(**response_data)

    def _create_error_response(
        self,
        request: GenerationRequest,
        generation_id: str,
        error_message: str,
        start_time: Any,
    ) -> GenerationResponse:
        """Create error response"""

        if CORE_AVAILABLE:
            end_time = utc_now()
        else:
            from datetime import datetime

            end_time = datetime.now()

        return GenerationResponse(
            generation_id=generation_id,
            project_id=getattr(request, "project_id", None),
            episode_id=getattr(request, "episode_id", None),
            status="failed",
            generated_script="",
            word_count=0,
            created_at=start_time,
            updated_at=end_time,
            generation_time_seconds=(end_time - start_time).total_seconds(),
            error_message=error_message,
            script_type=getattr(request, "script_type", None),
            title=getattr(request, "title", ""),
            description=getattr(request, "description", ""),
            workflow_metadata={
                "workflow_version": "1.0.0",
                "nodes_executed": [],
                "error": error_message,
                "langgraph_used": False,
            },
        )

    def get_workflow_info(self) -> Dict[str, Any]:
        """Get information about the workflow"""

        return {
            "workflow_version": "1.0.0",
            "langgraph_available": LANGGRAPH_AVAILABLE,
            "workflow_compiled": self.app is not None,
            "nodes": ["architect", "stylist", "special_agent", "finalization"],
            "providers": {
                "architect": "anthropic",
                "stylist": "local",
                "special_agent": "openai",
            },
            "rag_service_available": self.rag_service is not None,
            "core_module_available": CORE_AVAILABLE,
        }
