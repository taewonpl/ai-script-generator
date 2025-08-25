"""
Base prompt template class for specialized node prompts
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any

# Import Core Module components
try:
    from ai_script_core import (
        generate_uuid,
        get_service_logger,
        utc_now,
    )

    CORE_AVAILABLE = True
    logger = get_service_logger("generation-service.base_prompt")
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


class PromptType(str, Enum):
    """Types of specialized prompts"""

    ARCHITECT = "architect"
    STYLIST = "stylist"
    SPECIAL_AGENT = "special_agent"


class ScriptType(str, Enum):
    """Script types for prompt customization"""

    DRAMA = "drama"
    COMEDY = "comedy"
    THRILLER = "thriller"
    DOCUMENTARY = "documentary"
    VARIETY = "variety"
    NEWS = "news"
    EDUCATIONAL = "educational"


@dataclass
class PromptContext:
    """Context information for prompt generation"""

    project_id: str | None = None
    episode_id: str | None = None
    title: str = ""
    description: str = ""
    script_type: ScriptType = ScriptType.DRAMA
    target_audience: str = "general"
    channel_style: str = "standard"
    rag_context: str = ""
    additional_context: dict[str, Any] = None

    def __post_init__(self):
        if self.additional_context is None:
            self.additional_context = {}


@dataclass
class PromptResult:
    """Result of prompt generation"""

    prompt: str
    system_prompt: str
    prompt_type: PromptType
    context_used: PromptContext
    metadata: dict[str, Any]

    def __post_init__(self):
        if CORE_AVAILABLE:
            self.generated_at = utc_now()
            self.prompt_id = generate_uuid()
        else:
            from datetime import datetime

            self.generated_at = datetime.now()
            self.prompt_id = f"prompt_{hash(self.prompt[:100])}"


class BasePromptTemplate(ABC):
    """Base class for specialized prompt templates"""

    def __init__(self, prompt_type: PromptType):
        self.prompt_type = prompt_type
        self.logger = logger

        if CORE_AVAILABLE:
            self.template_id = generate_uuid()
            self.created_at = utc_now()
        else:
            from datetime import datetime

            self.template_id = (
                f"template_{prompt_type.value}_{hash(str(datetime.now()))}"
            )
            self.created_at = datetime.now()

    @abstractmethod
    def create_system_prompt(self, context: PromptContext) -> str:
        """Create system prompt for the AI model"""
        pass

    @abstractmethod
    def create_user_prompt(self, context: PromptContext) -> str:
        """Create user prompt with context"""
        pass

    def generate_prompt(self, context: PromptContext) -> PromptResult:
        """Generate complete prompt with system and user parts"""

        try:
            # Generate system and user prompts
            system_prompt = self.create_system_prompt(context)
            user_prompt = self.create_user_prompt(context)

            # Create result
            result = PromptResult(
                prompt=user_prompt,
                system_prompt=system_prompt,
                prompt_type=self.prompt_type,
                context_used=context,
                metadata={
                    "template_id": self.template_id,
                    "prompt_length": len(user_prompt),
                    "system_prompt_length": len(system_prompt),
                    "rag_context_used": bool(context.rag_context),
                    "rag_context_length": (
                        len(context.rag_context) if context.rag_context else 0
                    ),
                },
            )

            if CORE_AVAILABLE:
                self.logger.info(
                    "Prompt generated successfully",
                    extra={
                        "prompt_type": self.prompt_type.value,
                        "template_id": self.template_id,
                        "prompt_id": result.prompt_id,
                        "prompt_length": len(user_prompt),
                        "rag_context_used": bool(context.rag_context),
                    },
                )

            return result

        except Exception as e:
            error_msg = f"Failed to generate {self.prompt_type.value} prompt: {e!s}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)

    def _format_rag_context(self, rag_context: str, max_length: int = 4000) -> str:
        """Format RAG context for inclusion in prompts"""

        if not rag_context or not rag_context.strip():
            return ""

        # Truncate if too long
        if len(rag_context) > max_length:
            rag_context = rag_context[:max_length] + "..."

        return f"""
RELEVANT CONTEXT FROM KNOWLEDGE BASE:
{rag_context.strip()}

Use this context to inform your response while maintaining originality and coherence for the current project.
"""

    def _get_script_type_guidance(self, script_type: ScriptType) -> str:
        """Get script type specific guidance"""

        guidance_map = {
            ScriptType.DRAMA: "Focus on emotional depth, character development, and narrative tension.",
            ScriptType.COMEDY: "Emphasize humor, timing, and lighthearted character interactions.",
            ScriptType.THRILLER: "Build suspense, maintain tension, and create compelling mysteries.",
            ScriptType.DOCUMENTARY: "Ensure factual accuracy, clear narration, and educational value.",
            ScriptType.VARIETY: "Create engaging entertainment with diverse content segments.",
            ScriptType.NEWS: "Maintain journalistic integrity, clarity, and informative content.",
            ScriptType.EDUCATIONAL: "Focus on learning objectives, clear explanations, and engagement.",
        }

        return guidance_map.get(
            script_type, "Create engaging and well-structured content."
        )

    def _validate_context(self, context: PromptContext) -> None:
        """Validate prompt context"""

        if not context.title and not context.description:
            raise ValueError("Either title or description must be provided")

        if len(context.title) > 200:
            raise ValueError("Title too long (max 200 characters)")

        if len(context.description) > 2000:
            raise ValueError("Description too long (max 2000 characters)")

    def get_template_info(self) -> dict[str, Any]:
        """Get template information"""

        return {
            "template_id": self.template_id,
            "prompt_type": self.prompt_type.value,
            "created_at": self.created_at.isoformat(),
            "supported_script_types": [st.value for st in ScriptType],
        }


class PromptTemplateRegistry:
    """Registry for managing prompt templates"""

    def __init__(self):
        self._templates: dict[PromptType, BasePromptTemplate] = {}

        if CORE_AVAILABLE:
            self.registry_id = generate_uuid()
            logger.info(
                "Prompt template registry initialized",
                extra={"registry_id": self.registry_id},
            )
        else:
            from datetime import datetime

            self.registry_id = f"registry_{hash(str(datetime.now()))}"
            logger.info("Prompt template registry initialized")

    def register_template(self, template: BasePromptTemplate) -> None:
        """Register a prompt template"""

        self._templates[template.prompt_type] = template

        if CORE_AVAILABLE:
            logger.info(
                "Template registered",
                extra={
                    "registry_id": self.registry_id,
                    "prompt_type": template.prompt_type.value,
                    "template_id": template.template_id,
                },
            )

    def get_template(self, prompt_type: PromptType) -> BasePromptTemplate | None:
        """Get a registered template"""

        return self._templates.get(prompt_type)

    def list_templates(self) -> list[dict[str, Any]]:
        """List all registered templates"""

        return [template.get_template_info() for template in self._templates.values()]

    def generate_prompt(
        self, prompt_type: PromptType, context: PromptContext
    ) -> PromptResult:
        """Generate prompt using registered template"""

        template = self.get_template(prompt_type)
        if not template:
            raise ValueError(
                f"No template registered for prompt type: {prompt_type.value}"
            )

        return template.generate_prompt(context)


# Global registry instance
prompt_registry = PromptTemplateRegistry()
