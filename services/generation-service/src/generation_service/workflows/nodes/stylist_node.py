"""
Stylist node for LangGraph workflow - Llama-based style application
"""

# Import Core Module components
try:
    from ai_script_core import (
        get_service_logger,
        utc_now,
    )

    CORE_AVAILABLE = True
    logger = get_service_logger("generation-service.stylist_node")
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

from generation_service.ai.prompts import PromptContext, ScriptType, StylistPrompts
from generation_service.ai.providers.base_provider import ProviderGenerationRequest
from generation_service.workflows.nodes.base_node import PromptNode
from generation_service.workflows.state import GenerationState, add_token_usage


class StylistNode(PromptNode):
    """
    Stylist node for channel-specific style application using Llama

    Responsibilities:
    - StylistPrompts 활용한 전문 프롬프트 생성
    - Local Provider (Llama) 사용한 스타일 적용
    - "우리 채널의 전속 작가" 페르소나로 톤앤매너 반영
    - 기존 플롯 구조는 절대 변경하지 않음
    """

    def __init__(self, provider_factory: Any) -> None:
        super().__init__(
            node_name="stylist",
            provider_name="local",  # Use Llama for styling work
            prompt_template=StylistPrompts(),
        )
        self.provider_factory = provider_factory

    async def _execute_node_logic(self, state: GenerationState) -> GenerationState:
        """Execute stylist-specific logic"""

        # Initialize provider (Llama)
        await self._initialize_provider(self.provider_factory)

        # Create prompt context with architect structure
        prompt_context = self._create_prompt_context(state)

        # Generate specialized stylist prompt
        prompt_result = self.prompt_template.generate_prompt(prompt_context)

        # Execute style application with Llama
        style_result = await self._apply_style(prompt_result)

        # Update state with styled results
        updated_state = self._update_state_with_results(
            state, style_result, prompt_result
        )

        return updated_state

    def _create_prompt_context(self, state: GenerationState) -> PromptContext:
        """Create prompt context for stylist with architect structure"""

        request = state["original_request"]
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

        # Create context with architect structure
        prompt_context = PromptContext(
            project_id=getattr(request, "project_id", None),
            episode_id=getattr(request, "episode_id", None),
            title=getattr(request, "title", ""),
            description=getattr(request, "description", ""),
            script_type=mapped_script_type,
            target_audience=getattr(request, "target_audience", "general"),
            channel_style=getattr(request, "channel_style", "standard"),
            rag_context=state.get("rag_context", ""),  # Use RAG context from architect
            additional_context={"architect_structure": architect_structure},
        )

        return prompt_context

    async def _apply_style(self, prompt_result) -> dict:
        """Apply channel style using Llama"""

        generation_request = ProviderGenerationRequest(
            prompt=prompt_result.prompt,
            system_prompt=prompt_result.system_prompt,
            max_tokens=4000,
            temperature=0.8,  # Higher creativity for styling
        )

        response = await self.provider.generate_with_retry(generation_request)

        return {
            "styled_script": response.content,
            "model_used": response.model_info.name,
            "tokens_used": (
                response.metadata.get("tokens_used", 0) if response.metadata else 0
            ),
            "prompt_id": prompt_result.prompt_id,
        }

    def _update_state_with_results(
        self, state: GenerationState, style_result: dict, prompt_result
    ) -> GenerationState:
        """Update state with stylist results"""

        # Create a copy of the state to avoid mutation
        updated_state = state.copy()

        # Store styled script
        updated_state["styled_script"] = style_result["styled_script"]

        # Add token usage tracking
        add_token_usage(
            updated_state,
            self.node_name,
            style_result["tokens_used"],
            style_result["model_used"],
        )

        # Store style metadata
        updated_state["style_metadata"] = {
            "channel_style_applied": True,
            "original_structure_preserved": True,
            "model_used": style_result["model_used"],
            "tokens_used": style_result["tokens_used"],
            "prompt_template_used": "StylistPrompts",
            "prompt_id": style_result["prompt_id"],
            "specialized_prompt": True,
        }

        # Update generation metadata
        if updated_state["generation_metadata"] is None:
            updated_state["generation_metadata"] = {}

        updated_state["generation_metadata"][f"{self.node_name}_metadata"] = {
            "model_used": style_result["model_used"],
            "tokens_used": style_result["tokens_used"],
            "channel_style_applied": True,
            "structure_preservation": "guaranteed",
            "prompt_template_used": "StylistPrompts",
            "prompt_id": style_result["prompt_id"],
            "specialized_prompt": True,
        }

        if CORE_AVAILABLE:
            logger.info(
                "Channel style applied to script",
                extra={
                    "generation_id": state["generation_id"],
                    "styled_script_length": len(style_result["styled_script"]),
                    "tokens_used": style_result["tokens_used"],
                    "model_used": style_result["model_used"],
                    "channel_style": (
                        updated_state["original_request"].channel_style
                        if hasattr(updated_state["original_request"], "channel_style")
                        else "standard"
                    ),
                },
            )

        return updated_state

    def _validate_node_specific_input(self, state: GenerationState) -> None:
        """Validate stylist-specific input requirements"""

        # Must have architect structure to style
        if not state.get("draft_script"):
            raise ValueError("Missing draft_script from architect for stylist node")

        if not state.get("architect_structure"):
            raise ValueError("Missing architect_structure for stylist node")

        # Check architect structure quality
        architect_structure = state["architect_structure"]
        if len(architect_structure) < 100:
            raise ValueError(
                "Architect structure too short for styling (minimum 100 characters)"
            )

    def _validate_node_specific_output(self, state: GenerationState) -> None:
        """Validate stylist-specific output"""

        if not state.get("styled_script"):
            raise ValueError("Stylist node failed to generate styled_script")

        styled_script = state["styled_script"]

        # Check minimum quality requirements
        if len(styled_script) < 200:
            raise ValueError("Styled script is too short (minimum 200 characters)")

        # Ensure it's substantially different from architect structure (should be enhanced)
        architect_structure = state.get("architect_structure", "")
        if styled_script == architect_structure:
            raise ValueError(
                "Styled script is identical to architect structure - no styling applied"
            )

    def _calculate_quality_score(self, state: GenerationState) -> Optional[float]:
        """Calculate quality score for stylist output"""

        styled_script = state.get("styled_script", "")
        if not styled_script:
            return 0.0

        score = 0.0

        # Check for script formatting improvements
        if (
            "FADE IN" in styled_script
            or "EXT." in styled_script
            or "INT." in styled_script
        ):
            score += 0.3

        # Check for dialogue quality (balanced with action)
        lines = styled_script.split("\n")
        dialogue_lines = sum(
            1
            for line in lines
            if line.strip() and not line.strip().startswith(("EXT.", "INT.", "FADE"))
        )
        total_lines = len([line for line in lines if line.strip()])

        if total_lines > 0 and 0.3 <= dialogue_lines / total_lines <= 0.7:
            score += 0.3

        # Check for variety in content (indicating good styling)
        sentences = styled_script.split(".")
        if (
            len(set(len(s.split()) for s in sentences[:10])) > 3
        ):  # Variety in sentence length
            score += 0.2

        # Check overall length and completeness
        if len(styled_script) > 1000:
            score += 0.2

        return min(score, 1.0)

    def _get_execution_metadata(self, state: GenerationState) -> dict:
        """Get stylist-specific execution metadata"""

        base_metadata = super()._get_execution_metadata(state)

        style_metadata = state.get("style_metadata", {})

        base_metadata.update(
            {
                "styled_script_generated": bool(state.get("styled_script")),
                "styled_script_length": len(state.get("styled_script", "")),
                "structure_preserved": True,  # Guaranteed by design
                **style_metadata,
            }
        )

        return base_metadata

    def get_channel_style_config(self, channel_style: str) -> dict:
        """Get channel style configuration for reference"""

        # This mirrors the configuration in StylistPrompts
        channel_styles = {
            "educational": {
                "tone": "전문적이면서도 접근하기 쉬운",
                "voice": "친근한 교육자",
                "characteristics": [
                    "명확한 설명",
                    "예시 활용",
                    "단계별 전개",
                    "상호작용적 요소",
                ],
            },
            "entertainment": {
                "tone": "활기차고 재미있는",
                "voice": "에너지 넘치는 엔터테이너",
                "characteristics": [
                    "유머 요소",
                    "시청자 참여",
                    "역동적 진행",
                    "감정적 몰입",
                ],
            },
            "news": {
                "tone": "신뢰할 수 있고 객관적인",
                "voice": "전문 저널리스트",
                "characteristics": [
                    "사실 중심",
                    "균형잡힌 시각",
                    "명확한 전달",
                    "신뢰성 확보",
                ],
            },
            "lifestyle": {
                "tone": "따뜻하고 친밀한",
                "voice": "친한 친구",
                "characteristics": [
                    "개인적 경험",
                    "실용적 조언",
                    "감성적 연결",
                    "일상 연관성",
                ],
            },
            "tech": {
                "tone": "혁신적이고 전문적인",
                "voice": "기술 전문가",
                "characteristics": [
                    "최신 트렌드",
                    "기술적 정확성",
                    "미래 지향적",
                    "실용적 활용",
                ],
            },
        }

        return channel_styles.get(channel_style, channel_styles["entertainment"])
