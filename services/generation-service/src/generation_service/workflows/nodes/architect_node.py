"""
Architect node for LangGraph workflow - Claude-based structural design
"""

# Import Core Module components
try:
    from ai_script_core import (
        get_service_logger,
        utc_now,
    )

    CORE_AVAILABLE = True
    logger = get_service_logger("generation-service.architect_node")
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


from generation_service.ai.prompts import ArchitectPrompts, PromptContext, ScriptType
from generation_service.ai.providers.base_provider import ProviderGenerationRequest
from generation_service.workflows.nodes.base_node import PromptNode
from generation_service.workflows.state import GenerationState, add_token_usage


class ArchitectNode(PromptNode):
    """
    Architect node for structural script design using Claude

    Responsibilities:
    - RAG Service 통합으로 컨텍스트 수집
    - ArchitectPrompts 활용한 전문 프롬프트 생성
    - Claude Provider 사용한 구조적 스크립트 생성
    - 논리적 완성도에만 집중 (스타일 적용 금지)
    """

    def __init__(self, provider_factory, rag_service=None):
        super().__init__(
            node_name="architect",
            provider_name="anthropic",  # Use Claude for architectural work
            prompt_template=ArchitectPrompts(),
        )
        self.provider_factory = provider_factory
        self.rag_service = rag_service

    async def _execute_node_logic(self, state: GenerationState) -> GenerationState:
        """Execute architect-specific logic"""

        # Initialize provider
        await self._initialize_provider(self.provider_factory)

        # Get RAG context if available
        rag_context = await self._retrieve_rag_context(state)

        # Create prompt context
        prompt_context = self._create_prompt_context(state, rag_context)

        # Generate specialized architect prompt
        prompt_result = self.prompt_template.generate_prompt(prompt_context)

        # Execute generation with Claude
        structure_result = await self._generate_structure(prompt_result)

        # Update state with results
        updated_state = self._update_state_with_results(
            state, structure_result, rag_context, prompt_result
        )

        return updated_state

    async def _retrieve_rag_context(self, state: GenerationState) -> str:
        """Retrieve relevant context from RAG system"""

        if not self.rag_service:
            if CORE_AVAILABLE:
                logger.info("No RAG service available for architect context")
            return ""

        try:
            request = state["original_request"]

            # Use RAG service's specialized method for architect context
            rag_context = await self.rag_service.search_for_architect_context(
                title=getattr(request, "title", ""),
                description=getattr(request, "description", ""),
                script_type=str(getattr(request, "script_type", "")),
                project_id=getattr(request, "project_id", None),
            )

            if CORE_AVAILABLE:
                logger.info(
                    "RAG context retrieved for architect",
                    extra={
                        "generation_id": state["generation_id"],
                        "context_length": len(rag_context),
                        "project_id": getattr(request, "project_id", None),
                    },
                )

            return rag_context

        except Exception as e:
            logger.warning(f"Failed to retrieve RAG context for architect: {e}")
            return ""

    def _create_prompt_context(
        self, state: GenerationState, rag_context: str
    ) -> PromptContext:
        """Create prompt context for architect"""

        request = state["original_request"]

        # Map script type
        script_type_mapping = {
            "drama": ScriptType.DRAMA,
            "comedy": ScriptType.COMEDY,
            "thriller": ScriptType.THRILLER,
            "documentary": ScriptType.DOCUMENTARY,
            "variety": ScriptType.VARIETY,
            "news": ScriptType.NEWS,
            "educational": ScriptType.EDUCATIONAL,
        }

        request_script_type = getattr(request, "script_type", None)
        if request_script_type:
            script_type_str = (
                request_script_type.value
                if hasattr(request_script_type, "value")
                else str(request_script_type).lower()
            )
            mapped_script_type = script_type_mapping.get(
                script_type_str, ScriptType.DRAMA
            )
        else:
            mapped_script_type = ScriptType.DRAMA

        return PromptContext(
            project_id=getattr(request, "project_id", None),
            episode_id=getattr(request, "episode_id", None),
            title=getattr(request, "title", ""),
            description=getattr(request, "description", ""),
            script_type=mapped_script_type,
            target_audience=getattr(request, "target_audience", "general"),
            channel_style=getattr(request, "channel_style", "standard"),
            rag_context=rag_context,
            additional_context={},
        )

    async def _generate_structure(self, prompt_result) -> dict:
        """Generate structural foundation using Claude"""

        generation_request = ProviderGenerationRequest(
            prompt=prompt_result.prompt,
            system_prompt=prompt_result.system_prompt,
            max_tokens=3000,
            temperature=0.7,  # Balanced creativity for structure
        )

        response = await self.provider.generate_with_retry(generation_request)

        return {
            "structure": response.content,
            "model_used": response.model_info.name,
            "tokens_used": (
                response.metadata.get("tokens_used", 0) if response.metadata else 0
            ),
            "prompt_id": prompt_result.prompt_id,
        }

    def _update_state_with_results(
        self,
        state: GenerationState,
        structure_result: dict,
        rag_context: str,
        prompt_result,
    ) -> GenerationState:
        """Update state with architect results"""

        # Create a copy of the state to avoid mutation
        updated_state = state.copy()

        # Store structural foundation
        updated_state["draft_script"] = structure_result["structure"]
        updated_state["architect_structure"] = structure_result["structure"]

        # Update RAG context in state for use by other nodes
        updated_state["rag_context"] = rag_context

        # Add token usage tracking
        add_token_usage(
            updated_state,
            self.node_name,
            structure_result["tokens_used"],
            structure_result["model_used"],
        )

        # Store architect-specific metadata
        if updated_state["generation_metadata"] is None:
            updated_state["generation_metadata"] = {}

        updated_state["generation_metadata"][f"{self.node_name}_metadata"] = {
            "model_used": structure_result["model_used"],
            "tokens_used": structure_result["tokens_used"],
            "rag_context_used": bool(rag_context),
            "rag_context_length": len(rag_context) if rag_context else 0,
            "prompt_template_used": "ArchitectPrompts",
            "prompt_id": structure_result["prompt_id"],
            "specialized_prompt": True,
        }

        if CORE_AVAILABLE:
            logger.info(
                "Architect structure generated",
                extra={
                    "generation_id": state["generation_id"],
                    "structure_length": len(structure_result["structure"]),
                    "tokens_used": structure_result["tokens_used"],
                    "model_used": structure_result["model_used"],
                    "rag_context_used": bool(rag_context),
                },
            )

        return updated_state

    def _validate_node_specific_input(self, state: GenerationState) -> None:
        """Validate architect-specific input requirements"""

        request = state.get("original_request")
        if not request:
            raise ValueError("Missing original_request for architect node")

        # Check for required request fields
        if not hasattr(request, "title") or not request.title:
            raise ValueError("Missing title in generation request")

        if not hasattr(request, "description") or not request.description:
            raise ValueError("Missing description in generation request")

    def _validate_node_specific_output(self, state: GenerationState) -> None:
        """Validate architect-specific output"""

        if not state.get("draft_script"):
            raise ValueError("Architect node failed to generate draft_script")

        if not state.get("architect_structure"):
            raise ValueError("Architect node failed to generate architect_structure")

        # Check minimum quality requirements
        draft_script = state["draft_script"]
        if len(draft_script) < 100:
            raise ValueError(
                "Generated structure is too short (minimum 100 characters)"
            )

    def _calculate_quality_score(self, state: GenerationState) -> float | None:
        """Calculate quality score for architect output"""

        structure = state.get("draft_script", "")
        if not structure:
            return 0.0

        score = 0.0
        structure_lower = structure.lower()

        # Check for key structural elements (same logic as in generation_service.py)
        if "act" in structure_lower:
            score += 0.2

        if "character" in structure_lower:
            score += 0.2

        if "scene" in structure_lower:
            score += 0.2

        if "dialogue" in structure_lower:
            score += 0.2

        # Overall completeness (length and detail)
        if len(structure) > 500:
            score += 0.2

        # Boost score if RAG context was used
        if state.get("rag_context") and len(state["rag_context"]) > 100:
            score = min(score + 0.1, 1.0)

        return min(score, 1.0)

    def _get_execution_metadata(self, state: GenerationState) -> dict:
        """Get architect-specific execution metadata"""

        base_metadata = super()._get_execution_metadata(state)

        architect_metadata = state.get("generation_metadata", {}).get(
            f"{self.node_name}_metadata", {}
        )

        base_metadata.update(
            {
                "structure_generated": bool(state.get("draft_script")),
                "structure_length": len(state.get("draft_script", "")),
                "rag_service_available": self.rag_service is not None,
                **architect_metadata,
            }
        )

        return base_metadata
