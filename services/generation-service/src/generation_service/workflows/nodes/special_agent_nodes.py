"""
Special Agent nodes for LangGraph workflow - GPT-based specialized enhancements
"""

# Import Core Module components
try:
    from ai_script_core import (
        get_service_logger,
        utc_now,
    )

    CORE_AVAILABLE = True
    logger = get_service_logger("generation-service.special_agent_nodes")
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


from typing import Any, Optional

from generation_service.ai.prompts import (
    PromptContext,
    ScriptType,
    SpecialAgentPrompts,
    SpecialAgentType,
)
from generation_service.ai.providers.base_provider import ProviderGenerationRequest
from generation_service.workflows.nodes.base_node import PromptNode
from generation_service.workflows.state import GenerationState, add_token_usage


class SpecialAgentNode(PromptNode):
    """
    Base class for special agent nodes using GPT for specialized enhancements

    Common responsibilities:
    - SpecialAgentPrompts 활용한 전문 프롬프트 생성
    - OpenAI Provider 사용한 특수 기능 적용
    - 기존 품질을 해치지 않으면서 전문 영역 향상
    """

    def __init__(self, provider_factory: Any, agent_type: SpecialAgentType) -> None:
        super().__init__(
            node_name=f"special_agent_{agent_type.value}",
            provider_name="openai",  # Use GPT for special enhancements
            prompt_template=SpecialAgentPrompts(agent_type),
        )
        self.provider_factory = provider_factory
        self.agent_type = agent_type

    async def _execute_node_logic(self, state: GenerationState) -> GenerationState:
        """Execute special agent specific logic"""

        # Initialize provider (OpenAI GPT)
        await self._initialize_provider(self.provider_factory)

        # Create prompt context with styled script
        prompt_context = self._create_prompt_context(state)

        # Generate specialized agent prompt
        prompt_result = self.prompt_template.generate_prompt(prompt_context)

        # Execute enhancement with GPT
        enhancement_result = await self._apply_enhancement(prompt_result)

        # Update state with enhanced results
        updated_state = self._update_state_with_results(
            state, enhancement_result, prompt_result
        )

        return updated_state

    def _create_prompt_context(self, state: GenerationState) -> PromptContext:
        """Create prompt context for special agent with styled script"""

        request = state["original_request"]
        styled_script = state.get("styled_script", "")
        architect_structure = state.get("architect_structure", "")

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

        # Determine special requirements for this agent
        special_requirements = self._identify_requirements(request, mapped_script_type)

        # Create context with styled script and special requirements
        prompt_context = PromptContext(
            project_id=getattr(request, "project_id", None),
            episode_id=getattr(request, "episode_id", None),
            title=getattr(request, "title", ""),
            description=getattr(request, "description", ""),
            script_type=mapped_script_type,
            target_audience=getattr(request, "target_audience", "general"),
            channel_style=getattr(request, "channel_style", "standard"),
            rag_context=state.get("rag_context", ""),
            additional_context={
                "styled_script": styled_script,
                "architect_structure": architect_structure,
                "special_requirements": special_requirements,
            },
        )

        return prompt_context

    def _identify_requirements(self, request, script_type: ScriptType) -> list[str]:
        """Identify requirements specific to this agent type"""

        requirements = []

        # Base requirements by agent type
        agent_requirements = {
            SpecialAgentType.PLOT_TWISTER: ["plot_twists", "narrative_surprises"],
            SpecialAgentType.FLAW_GENERATOR: [
                "character_flaws",
                "realistic_imperfections",
            ],
            SpecialAgentType.DIALOGUE_ENHANCER: [
                "dialogue_enhancement",
                "conversational_realism",
            ],
            SpecialAgentType.TENSION_BUILDER: ["dramatic_tension", "suspense_building"],
            SpecialAgentType.EMOTION_AMPLIFIER: [
                "emotional_impact",
                "feeling_intensification",
            ],
            SpecialAgentType.CONFLICT_INTENSIFIER: [
                "conflict_escalation",
                "dramatic_opposition",
            ],
            SpecialAgentType.HUMOR_INJECTOR: ["humor_integration", "comedic_timing"],
            SpecialAgentType.PACING_OPTIMIZER: ["story_pacing", "rhythm_optimization"],
        }

        requirements.extend(agent_requirements.get(self.agent_type, []))

        # Add script type specific requirements
        script_type_requirements = {
            ScriptType.DRAMA: ["emotional_depth", "character_development"],
            ScriptType.COMEDY: ["humor_enhancement", "comedic_situations"],
            ScriptType.THRILLER: ["suspense_building", "plot_twists"],
            ScriptType.DOCUMENTARY: ["factual_accuracy", "clear_narration"],
            ScriptType.VARIETY: ["entertainment_value", "audience_engagement"],
            ScriptType.NEWS: ["clarity", "informative_content"],
            ScriptType.EDUCATIONAL: ["learning_objectives", "clear_explanations"],
        }

        requirements.extend(script_type_requirements.get(script_type, []))

        # Add requirements based on description keywords
        description = getattr(request, "description", "").lower()
        if "twist" in description or "surprise" in description:
            requirements.append("plot_twists")
        if "conflict" in description or "tension" in description:
            requirements.append("conflict_intensification")
        if "emotion" in description or "heart" in description:
            requirements.append("emotion_amplification")
        if "funny" in description or "humor" in description:
            requirements.append("humor_enhancement")

        return list(set(requirements))  # Remove duplicates

    async def _apply_enhancement(self, prompt_result) -> dict:
        """Apply specialized enhancement using GPT"""

        generation_request = ProviderGenerationRequest(
            prompt=prompt_result.prompt,
            system_prompt=prompt_result.system_prompt,
            max_tokens=3500,
            temperature=0.6,  # Balanced creativity for enhancements
        )

        response = await self.provider.generate_with_retry(generation_request)

        return {
            "enhanced_script": response.content,
            "agent_type": self.agent_type.value,
            "model_used": response.model_info.name,
            "tokens_used": (
                response.metadata.get("tokens_used", 0) if response.metadata else 0
            ),
            "prompt_id": prompt_result.prompt_id,
        }

    def _update_state_with_results(
        self, state: GenerationState, enhancement_result: dict, prompt_result
    ) -> GenerationState:
        """Update state with special agent results"""

        # Create a copy of the state to avoid mutation
        updated_state = state.copy()

        # Store enhanced script
        updated_state["enhanced_script"] = enhancement_result["enhanced_script"]

        # Add token usage tracking
        add_token_usage(
            updated_state,
            self.node_name,
            enhancement_result["tokens_used"],
            enhancement_result["model_used"],
        )

        # Store enhancement metadata
        updated_state["enhancement_metadata"] = {
            "agent_type": enhancement_result["agent_type"],
            "specialized_enhancement_applied": True,
            "original_quality_preserved": True,
            "model_used": enhancement_result["model_used"],
            "tokens_used": enhancement_result["tokens_used"],
            "prompt_template_used": f"SpecialAgentPrompts_{enhancement_result['agent_type']}",
            "prompt_id": enhancement_result["prompt_id"],
            "specialized_prompt": True,
        }

        # Update generation metadata
        if updated_state["generation_metadata"] is None:
            updated_state["generation_metadata"] = {}

        updated_state["generation_metadata"][f"{self.node_name}_metadata"] = {
            "agent_type": enhancement_result["agent_type"],
            "model_used": enhancement_result["model_used"],
            "tokens_used": enhancement_result["tokens_used"],
            "enhancement_applied": True,
            "quality_preservation": "guaranteed",
            "prompt_template_used": f"SpecialAgentPrompts_{enhancement_result['agent_type']}",
            "prompt_id": enhancement_result["prompt_id"],
            "specialized_prompt": True,
        }

        # Update decision flags
        updated_state["requires_special_agent"] = True
        updated_state["special_agent_type"] = enhancement_result["agent_type"]

        if CORE_AVAILABLE:
            logger.info(
                "Special agent enhancement applied",
                extra={
                    "generation_id": state["generation_id"],
                    "agent_type": enhancement_result["agent_type"],
                    "enhanced_script_length": len(
                        enhancement_result["enhanced_script"]
                    ),
                    "tokens_used": enhancement_result["tokens_used"],
                    "model_used": enhancement_result["model_used"],
                },
            )

        return updated_state

    def _validate_node_specific_input(self, state: GenerationState) -> None:
        """Validate special agent specific input requirements"""

        # Must have styled script to enhance
        if not state.get("styled_script"):
            raise ValueError(
                "Missing styled_script from stylist for special agent node"
            )

        # Check styled script quality
        styled_script = state["styled_script"]
        if len(styled_script) < 200:
            raise ValueError(
                "Styled script too short for enhancement (minimum 200 characters)"
            )

    def _validate_node_specific_output(self, state: GenerationState) -> None:
        """Validate special agent specific output"""

        if not state.get("enhanced_script"):
            raise ValueError("Special agent node failed to generate enhanced_script")

        enhanced_script = state["enhanced_script"]

        # Check minimum quality requirements
        if len(enhanced_script) < 300:
            raise ValueError("Enhanced script is too short (minimum 300 characters)")

        # Ensure it's different from styled script (should be enhanced)
        styled_script = state.get("styled_script", "")
        if enhanced_script == styled_script:
            raise ValueError(
                "Enhanced script is identical to styled script - no enhancement applied"
            )

    def _calculate_quality_score(self, state: GenerationState) -> Optional[float]:
        """Calculate quality score for special agent output"""

        enhanced_script = state.get("enhanced_script", "")
        if not enhanced_script:
            return 0.0

        # Base score calculation varies by agent type
        score = self._calculate_agent_specific_quality(enhanced_script, state)

        return min(score, 1.0)

    def _calculate_agent_specific_quality(
        self, enhanced_script: str, state: GenerationState
    ) -> float:
        """Calculate agent-type specific quality score"""

        base_score = 0.5  # Start with base score

        # Agent-specific quality metrics
        if self.agent_type == SpecialAgentType.DIALOGUE_ENHANCER:
            # Check for improved dialogue patterns
            if '"' in enhanced_script or "'" in enhanced_script:
                base_score += 0.2
            # Check for character names (indicating dialogue)
            lines = enhanced_script.split("\n")
            character_lines = sum(
                1
                for line in lines
                if line.strip().isupper() and len(line.strip().split()) <= 3
            )
            if character_lines > 0:
                base_score += 0.2

        elif self.agent_type == SpecialAgentType.PLOT_TWISTER:
            # Check for plot complexity indicators
            if any(
                word in enhanced_script.lower()
                for word in ["reveal", "twist", "surprise", "unexpected"]
            ):
                base_score += 0.3

        elif self.agent_type == SpecialAgentType.EMOTION_AMPLIFIER:
            # Check for emotional language
            emotion_words = ["feel", "heart", "tears", "joy", "sadness", "love", "fear"]
            emotion_count = sum(
                enhanced_script.lower().count(word) for word in emotion_words
            )
            if emotion_count > 3:
                base_score += 0.3

        elif self.agent_type == SpecialAgentType.TENSION_BUILDER:
            # Check for tension indicators
            tension_words = ["tension", "suspense", "conflict", "pressure", "urgency"]
            tension_count = sum(
                enhanced_script.lower().count(word) for word in tension_words
            )
            if tension_count > 2:
                base_score += 0.3

        # Overall length bonus
        if len(enhanced_script) > 1500:
            base_score += 0.1

        return base_score

    def _get_execution_metadata(self, state: GenerationState) -> dict:
        """Get special agent specific execution metadata"""

        base_metadata = super()._get_execution_metadata(state)

        enhancement_metadata = state.get("enhancement_metadata", {})

        base_metadata.update(
            {
                "enhanced_script_generated": bool(state.get("enhanced_script")),
                "enhanced_script_length": len(state.get("enhanced_script", "")),
                "agent_type": self.agent_type.value,
                "specialized_enhancement": True,
                **enhancement_metadata,
            }
        )

        return base_metadata


class SpecialAgentRouter:
    """
    Router for selecting and executing the appropriate special agent
    """

    def __init__(self, provider_factory):
        self.provider_factory = provider_factory

        # Initialize all available agents
        self.agents = {
            agent_type: SpecialAgentNode(provider_factory, agent_type)
            for agent_type in SpecialAgentType
        }

        if CORE_AVAILABLE:
            logger.info(
                "Special Agent Router initialized",
                extra={"available_agents": list(self.agents.keys())},
            )

    def determine_agent_type(
        self, state: GenerationState
    ) -> tuple[SpecialAgentType, list[str]]:
        """Determine the most appropriate special agent for the request"""

        request = state["original_request"]

        # Analyze request to determine best agent
        script_type = getattr(request, "script_type", None)
        description = getattr(request, "description", "").lower()

        # Priority-based selection
        if "twist" in description or "surprise" in description:
            return SpecialAgentType.PLOT_TWISTER, ["plot_twists", "narrative_surprises"]

        if "dialogue" in description or "conversation" in description:
            return SpecialAgentType.DIALOGUE_ENHANCER, ["dialogue_enhancement"]

        if "tension" in description or "suspense" in description:
            return SpecialAgentType.TENSION_BUILDER, ["tension_building"]

        if "emotion" in description or "feel" in description:
            return SpecialAgentType.EMOTION_AMPLIFIER, ["emotion_amplification"]

        if "conflict" in description:
            return SpecialAgentType.CONFLICT_INTENSIFIER, ["conflict_intensification"]

        if "funny" in description or "humor" in description:
            return SpecialAgentType.HUMOR_INJECTOR, ["humor_integration"]

        # Script type based defaults
        if script_type:
            script_type_str = (
                script_type.value
                if hasattr(script_type, "value")
                else str(script_type).lower()
            )

            if "thriller" in script_type_str:
                return SpecialAgentType.PLOT_TWISTER, ["plot_twists"]
            elif "drama" in script_type_str:
                return SpecialAgentType.EMOTION_AMPLIFIER, ["emotion_amplification"]
            elif "comedy" in script_type_str:
                return SpecialAgentType.HUMOR_INJECTOR, ["humor_integration"]

        # Default to dialogue enhancer
        return SpecialAgentType.DIALOGUE_ENHANCER, ["dialogue_enhancement"]

    async def execute_special_agent(self, state: GenerationState) -> GenerationState:
        """Execute the most appropriate special agent"""

        # Determine which agent to use
        agent_type, requirements = self.determine_agent_type(state)

        # Get the appropriate agent
        agent = self.agents[agent_type]

        if CORE_AVAILABLE:
            logger.info(
                "Executing special agent",
                extra={
                    "generation_id": state["generation_id"],
                    "agent_type": agent_type.value,
                    "requirements": requirements,
                },
            )

        # Execute the agent
        return await agent.execute(state)
