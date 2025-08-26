"""
Context builder for creating structured prompts from RAG search results
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

try:
    import tiktoken

    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False

# Import Core Module components
try:
    from ai_script_core import (
        BaseServiceException,
        ValidationException,
        generate_uuid,
        get_service_logger,
        safe_json_dumps,
        utc_now,
    )

    CORE_AVAILABLE = True
    logger = get_service_logger("generation-service.context_builder")
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


from .retriever import SearchResult


class ContextType(str, Enum):
    """Types of context structures"""

    STORY_BIBLE = "story_bible"
    CHARACTER_PROFILES = "character_profiles"
    WORLD_BUILDING = "world_building"
    PLOT_GUIDELINES = "plot_guidelines"
    STYLE_GUIDE = "style_guide"
    MIXED = "mixed"


@dataclass
class ContextBuildRequest:
    """Request for building context from search results"""

    search_results: list[SearchResult]
    context_type: ContextType = ContextType.MIXED
    max_context_tokens: int = 8000
    include_metadata: bool = True
    prioritize_recent: bool = True
    remove_duplicates: bool = True
    template_format: str = "default"
    project_id: str | None = None

    def __post_init__(self):
        if CORE_AVAILABLE and not hasattr(self, "request_id"):
            self.request_id = generate_uuid()


@dataclass
class ContextSection:
    """Individual section of context"""

    title: str
    content: str
    document_type: str
    relevance_score: float
    token_count: int
    metadata: dict[str, Any]

    def __post_init__(self):
        # Ensure relevance score is in [0, 1] range
        self.relevance_score = max(0.0, min(1.0, self.relevance_score))


@dataclass
class ContextBuildResponse:
    """Response from context building"""

    formatted_context: str
    sections: list[ContextSection]
    total_tokens: int
    context_type: ContextType
    build_time: float
    request_id: str | None = None

    def __post_init__(self):
        if CORE_AVAILABLE and self.request_id is None:
            self.request_id = generate_uuid()


class ContextBuildError(Exception):
    """Base exception for context building operations"""

    pass


if CORE_AVAILABLE:

    class ContextBuildError(ValidationException):
        """Context build error using Core exception"""

        def __init__(self, message: str, field: str = "context_request", **kwargs):
            super().__init__(message, field=field, **kwargs)


class ContextBuilder:
    """Builder for creating structured context from search results"""

    def __init__(
        self,
        default_max_tokens: int = 8000,
        overlap_threshold: float = 0.8,
        model_name: str = "gpt-4",
    ):
        self.default_max_tokens = default_max_tokens
        self.overlap_threshold = overlap_threshold
        self.model_name = model_name

        # Initialize tokenizer for accurate token counting
        if TIKTOKEN_AVAILABLE:
            try:
                self.tokenizer = tiktoken.encoding_for_model(model_name)
            except KeyError:
                self.tokenizer = tiktoken.get_encoding("cl100k_base")
                logger.warning(
                    f"Tokenizer for {model_name} not found, using cl100k_base"
                )
        else:
            self.tokenizer = None
            logger.warning("tiktoken not available, token counting will be approximate")

        # Core Module integration
        if CORE_AVAILABLE:
            self.builder_id = generate_uuid()
            self.created_at = utc_now()
            logger.info(
                "Context builder initialized with Core integration",
                extra={
                    "builder_id": self.builder_id,
                    "max_tokens": default_max_tokens,
                    "model_name": model_name,
                },
            )
        else:
            self.builder_id = f"context_{hash(str(default_max_tokens))}"
            self.created_at = datetime.now()
            logger.info("Context builder initialized")

        # Context templates
        self.templates = self._initialize_templates()

        # Build metrics
        self._build_metrics = {
            "total_builds": 0,
            "avg_build_time": 0.0,
            "avg_sections_per_build": 0.0,
            "avg_tokens_per_build": 0.0,
            "total_tokens_processed": 0,
        }

    def _initialize_templates(self) -> dict[str, str]:
        """Initialize context templates for different types"""

        return {
            "story_bible": """## Story Bible Context

### Project Overview
{overview}

### Story Elements
{story_elements}

### Guidelines
{guidelines}
""",
            "character_profiles": """## Character Information

### Main Characters
{main_characters}

### Supporting Characters
{supporting_characters}

### Character Relationships
{relationships}
""",
            "world_building": """## World Building Context

### Setting Information
{setting_info}

### Environment Details
{environment}

### Cultural Context
{culture}
""",
            "plot_guidelines": """## Plot Guidelines

### Story Structure
{structure}

### Key Plot Points
{plot_points}

### Pacing Guidelines
{pacing}
""",
            "style_guide": """## Style Guidelines

### Writing Style
{writing_style}

### Tone and Voice
{tone}

### Format Requirements
{format}
""",
            "mixed": """## Context Information

{sections}
""",
        }

    def _count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        else:
            # Rough approximation: 1 token ≈ 4 characters
            return len(text) // 4

    async def build_context(self, request: ContextBuildRequest) -> ContextBuildResponse:
        """Build structured context from search results"""

        start_time = utc_now() if CORE_AVAILABLE else datetime.now()

        # Validate request
        self._validate_build_request(request)

        try:
            # Process search results into sections
            sections = self._process_search_results(request)

            # Remove duplicates if requested
            if request.remove_duplicates:
                sections = self._remove_duplicate_sections(sections)

            # Prioritize sections
            prioritized_sections = self._prioritize_sections(sections, request)

            # Fit sections within token limit
            final_sections = self._fit_sections_to_limit(
                prioritized_sections, request.max_context_tokens
            )

            # Format context using appropriate template
            formatted_context = self._format_context(final_sections, request)

            # Calculate total tokens
            total_tokens = self._count_tokens(formatted_context)

            # Calculate build time
            build_time = (
                (utc_now() - start_time).total_seconds()
                if CORE_AVAILABLE
                else (datetime.now() - start_time).total_seconds()
            )

            # Update metrics
            self._update_build_metrics(build_time, len(final_sections), total_tokens)

            # Log build completion
            if CORE_AVAILABLE:
                logger.info(
                    "Context build completed",
                    extra={
                        "builder_id": self.builder_id,
                        "context_type": request.context_type.value,
                        "sections_count": len(final_sections),
                        "total_tokens": total_tokens,
                        "build_time_seconds": build_time,
                        "request_id": getattr(request, "request_id", None),
                    },
                )

            return ContextBuildResponse(
                formatted_context=formatted_context,
                sections=final_sections,
                total_tokens=total_tokens,
                context_type=request.context_type,
                build_time=build_time,
                request_id=getattr(request, "request_id", None),
            )

        except Exception as e:
            error_msg = f"Context build failed: {e!s}"
            logger.error(error_msg)
            raise ContextBuildError(error_msg)

    def _validate_build_request(self, request: ContextBuildRequest) -> None:
        """Validate context build request"""

        if not request.search_results:
            raise ContextBuildError(
                "No search results provided", field="search_results"
            )

        if request.max_context_tokens <= 0:
            raise ContextBuildError(
                "max_context_tokens must be positive", field="max_context_tokens"
            )

        if request.max_context_tokens > 50000:  # Reasonable upper limit
            raise ContextBuildError(
                "max_context_tokens exceeds reasonable limit",
                field="max_context_tokens",
            )

    def _process_search_results(
        self, request: ContextBuildRequest
    ) -> list[ContextSection]:
        """Process search results into context sections"""

        sections = []

        for result in request.search_results:
            # Determine document type from metadata
            doc_type = result.metadata.get("document_type", "unknown")

            # Create section title
            title = self._create_section_title(result, doc_type)

            # Count tokens in content
            token_count = self._count_tokens(result.content)

            # Create section
            section = ContextSection(
                title=title,
                content=result.content,
                document_type=doc_type,
                relevance_score=result.similarity_score,
                token_count=token_count,
                metadata=result.metadata,
            )

            sections.append(section)

        return sections

    def _create_section_title(self, result: SearchResult, doc_type: str) -> str:
        """Create appropriate title for section"""

        # Try to get title from metadata
        if "title" in result.metadata:
            return result.metadata["title"]

        # Create title based on document type
        type_titles = {
            "character": "Character Information",
            "setting": "Setting Details",
            "plot": "Plot Guidelines",
            "style": "Style Guidelines",
            "dialogue": "Dialogue Examples",
            "scene": "Scene Description",
            "story_bible": "Story Bible",
            "world_building": "World Building",
        }

        base_title = type_titles.get(doc_type, "Context Information")

        # Add specificity if available
        if "character_name" in result.metadata:
            return f"{base_title}: {result.metadata['character_name']}"
        elif "scene_type" in result.metadata:
            return f"{base_title}: {result.metadata['scene_type']}"
        elif "chapter" in result.metadata:
            return f"{base_title}: Chapter {result.metadata['chapter']}"

        return base_title

    def _remove_duplicate_sections(
        self, sections: list[ContextSection]
    ) -> list[ContextSection]:
        """Remove duplicate or highly similar sections"""

        unique_sections = []

        for section in sections:
            is_duplicate = False

            for existing in unique_sections:
                # Check content similarity
                similarity = self._calculate_content_similarity(
                    section.content, existing.content
                )

                if similarity > self.overlap_threshold:
                    # Keep the section with higher relevance score
                    if section.relevance_score > existing.relevance_score:
                        # Replace existing with current
                        unique_sections.remove(existing)
                        unique_sections.append(section)
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_sections.append(section)

        return unique_sections

    def _calculate_content_similarity(self, content1: str, content2: str) -> float:
        """Calculate similarity between two content pieces"""

        # Simple word-based similarity (can be enhanced with embeddings)
        words1 = set(content1.lower().split())
        words2 = set(content2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))

        return intersection / union if union > 0 else 0.0

    def _prioritize_sections(
        self, sections: list[ContextSection], request: ContextBuildRequest
    ) -> list[ContextSection]:
        """Prioritize sections based on various criteria"""

        # Calculate priority scores
        for section in sections:
            priority_score = 0.0

            # Base score from relevance
            priority_score += section.relevance_score * 0.4

            # Bonus for specific document types based on context type
            type_bonus = self._get_type_bonus(
                section.document_type, request.context_type
            )
            priority_score += type_bonus * 0.3

            # Recency bonus if prioritize_recent is True
            if request.prioritize_recent and "created_at" in section.metadata:
                recency_bonus = self._calculate_recency_bonus(
                    section.metadata["created_at"]
                )
                priority_score += recency_bonus * 0.2

            # Project relevance bonus
            if (
                request.project_id
                and section.metadata.get("project_id") == request.project_id
            ):
                priority_score += 0.1

            # Store priority score in metadata
            section.metadata["priority_score"] = priority_score

        # Sort by priority score
        return sorted(
            sections, key=lambda s: s.metadata.get("priority_score", 0.0), reverse=True
        )

    def _get_type_bonus(self, doc_type: str, context_type: ContextType) -> float:
        """Get bonus score for document type based on context type"""

        type_bonuses = {
            ContextType.STORY_BIBLE: {
                "story_bible": 1.0,
                "plot": 0.8,
                "world_building": 0.6,
                "character": 0.4,
            },
            ContextType.CHARACTER_PROFILES: {
                "character": 1.0,
                "dialogue": 0.8,
                "relationship": 0.6,
                "plot": 0.3,
            },
            ContextType.WORLD_BUILDING: {
                "world_building": 1.0,
                "setting": 0.9,
                "environment": 0.8,
                "culture": 0.7,
            },
            ContextType.PLOT_GUIDELINES: {
                "plot": 1.0,
                "structure": 0.9,
                "pacing": 0.8,
                "scene": 0.6,
            },
            ContextType.STYLE_GUIDE: {
                "style": 1.0,
                "tone": 0.9,
                "format": 0.8,
                "dialogue": 0.6,
            },
        }

        if context_type in type_bonuses:
            return type_bonuses[context_type].get(doc_type, 0.2)

        return 0.5  # Default bonus for mixed context

    def _calculate_recency_bonus(self, created_at_str: str) -> float:
        """Calculate bonus based on document recency"""

        try:
            if CORE_AVAILABLE:
                from datetime import datetime

                created_at = datetime.fromisoformat(
                    created_at_str.replace("Z", "+00:00")
                )
                now = utc_now()
            else:
                from datetime import datetime

                created_at = datetime.fromisoformat(created_at_str.replace("Z", ""))
                now = datetime.now()

            # Calculate days since creation
            days_old = (now - created_at).days

            # Exponential decay: newer documents get higher bonus
            if days_old <= 1:
                return 1.0
            elif days_old <= 7:
                return 0.8
            elif days_old <= 30:
                return 0.6
            elif days_old <= 90:
                return 0.4
            else:
                return 0.2

        except Exception:
            return 0.5  # Default if parsing fails

    def _fit_sections_to_limit(
        self, sections: list[ContextSection], max_tokens: int
    ) -> list[ContextSection]:
        """Fit sections within token limit while preserving most important content"""

        final_sections = []
        current_tokens = 0

        # Reserve tokens for template formatting
        template_overhead = 200  # Estimated tokens for template structure
        available_tokens = max_tokens - template_overhead

        for section in sections:
            section_tokens = section.token_count

            # If section fits entirely
            if current_tokens + section_tokens <= available_tokens:
                final_sections.append(section)
                current_tokens += section_tokens

            # If we have some remaining space, try to truncate content
            elif (
                current_tokens < available_tokens * 0.9
            ):  # Use 90% to leave some buffer
                remaining_tokens = available_tokens - current_tokens

                if remaining_tokens > 100:  # Only truncate if meaningful space remains
                    truncated_content = self._truncate_content(
                        section.content, remaining_tokens
                    )

                    if truncated_content:
                        truncated_section = ContextSection(
                            title=section.title,
                            content=truncated_content,
                            document_type=section.document_type,
                            relevance_score=section.relevance_score,
                            token_count=self._count_tokens(truncated_content),
                            metadata=section.metadata,
                        )
                        final_sections.append(truncated_section)
                        current_tokens += truncated_section.token_count

                break  # Stop adding more sections
            else:
                break  # No more space

        return final_sections

    def _truncate_content(self, content: str, max_tokens: int) -> str:
        """Truncate content to fit within token limit"""

        if self._count_tokens(content) <= max_tokens:
            return content

        # Split into sentences for better truncation
        sentences = content.split(". ")
        truncated_sentences = []
        current_tokens = 0

        for sentence in sentences:
            sentence_tokens = self._count_tokens(sentence)

            if current_tokens + sentence_tokens <= max_tokens - 20:  # Leave buffer
                truncated_sentences.append(sentence)
                current_tokens += sentence_tokens
            else:
                break

        if truncated_sentences:
            truncated = ". ".join(truncated_sentences)
            if not truncated.endswith("."):
                truncated += "..."
            return truncated

        # Fallback: character-based truncation
        char_limit = max_tokens * 4  # Rough approximation
        return content[:char_limit] + "..."

    def _format_context(
        self, sections: list[ContextSection], request: ContextBuildRequest
    ) -> str:
        """Format sections into final context using appropriate template"""

        template = self.templates.get(
            request.context_type.value, self.templates["mixed"]
        )

        if request.context_type == ContextType.MIXED:
            # Simple concatenation for mixed context
            formatted_sections = []
            for section in sections:
                section_text = f"### {section.title}\n{section.content}\n"
                if request.include_metadata and section.metadata:
                    # Add relevant metadata
                    metadata_text = self._format_metadata(section.metadata)
                    if metadata_text:
                        section_text += f"\n*{metadata_text}*\n"
                formatted_sections.append(section_text)

            return template.format(sections="\n".join(formatted_sections))

        else:
            # Categorized formatting for specific context types
            categorized_content = self._categorize_sections(
                sections, request.context_type
            )
            return template.format(**categorized_content)

    def _format_metadata(self, metadata: dict[str, Any]) -> str:
        """Format metadata for display"""

        relevant_fields = [
            "source",
            "author",
            "chapter",
            "scene_type",
            "character_name",
            "created_at",
        ]
        formatted_parts = []

        for field in relevant_fields:
            if metadata.get(field):
                value = metadata[field]
                if field == "created_at":
                    # Format date nicely
                    try:
                        from datetime import datetime

                        dt = datetime.fromisoformat(str(value).replace("Z", ""))
                        value = dt.strftime("%Y-%m-%d")
                    except:
                        pass
                formatted_parts.append(f"{field.replace('_', ' ').title()}: {value}")

        return " | ".join(formatted_parts)

    def _categorize_sections(
        self, sections: list[ContextSection], context_type: ContextType
    ) -> dict[str, str]:
        """Categorize sections for structured templates"""

        categories = {}

        if context_type == ContextType.CHARACTER_PROFILES:
            main_chars = []
            supporting_chars = []
            relationships = []

            for section in sections:
                if section.document_type == "character":
                    if section.metadata.get("character_importance") == "main":
                        main_chars.append(f"#### {section.title}\n{section.content}")
                    else:
                        supporting_chars.append(
                            f"#### {section.title}\n{section.content}"
                        )
                elif section.document_type == "relationship":
                    relationships.append(f"#### {section.title}\n{section.content}")

            categories = {
                "main_characters": "\n\n".join(main_chars)
                or "No main character information available.",
                "supporting_characters": "\n\n".join(supporting_chars)
                or "No supporting character information available.",
                "relationships": "\n\n".join(relationships)
                or "No relationship information available.",
            }

        elif context_type == ContextType.WORLD_BUILDING:
            setting_info = []
            environment = []
            culture = []

            for section in sections:
                if section.document_type in ["setting", "location"]:
                    setting_info.append(f"#### {section.title}\n{section.content}")
                elif section.document_type == "environment":
                    environment.append(f"#### {section.title}\n{section.content}")
                elif section.document_type in ["culture", "society"]:
                    culture.append(f"#### {section.title}\n{section.content}")
                else:
                    setting_info.append(f"#### {section.title}\n{section.content}")

            categories = {
                "setting_info": "\n\n".join(setting_info)
                or "No setting information available.",
                "environment": "\n\n".join(environment)
                or "No environment details available.",
                "culture": "\n\n".join(culture) or "No cultural context available.",
            }

        else:
            # Default categorization for other types
            formatted_sections = []
            for section in sections:
                formatted_sections.append(f"#### {section.title}\n{section.content}")

            section_content = "\n\n".join(formatted_sections)
            categories = {
                "overview": section_content or "No context information available.",
                "story_elements": "",
                "guidelines": "",
                "structure": section_content,
                "plot_points": "",
                "pacing": "",
                "writing_style": section_content,
                "tone": "",
                "format": "",
            }

        return categories

    def _update_build_metrics(
        self, build_time: float, sections_count: int, tokens_count: int
    ):
        """Update build metrics"""

        self._build_metrics["total_builds"] += 1
        total = self._build_metrics["total_builds"]

        # Update averages
        self._build_metrics["avg_build_time"] = (
            self._build_metrics["avg_build_time"] * (total - 1) + build_time
        ) / total
        self._build_metrics["avg_sections_per_build"] = (
            self._build_metrics["avg_sections_per_build"] * (total - 1) + sections_count
        ) / total
        self._build_metrics["avg_tokens_per_build"] = (
            self._build_metrics["avg_tokens_per_build"] * (total - 1) + tokens_count
        ) / total
        self._build_metrics["total_tokens_processed"] += tokens_count

    def get_build_metrics(self) -> dict[str, Any]:
        """Get context build metrics"""

        metrics = self._build_metrics.copy()

        if CORE_AVAILABLE:
            metrics.update(
                {
                    "builder_id": self.builder_id,
                    "created_at": self.created_at.isoformat(),
                    "last_updated": utc_now().isoformat(),
                }
            )
        else:
            metrics.update(
                {
                    "builder_id": self.builder_id,
                    "created_at": self.created_at.isoformat(),
                }
            )

        return metrics

    async def health_check(self) -> dict[str, Any]:
        """Perform health check on context builder"""

        try:
            # Test basic context building
            from .retriever import SearchResult

            test_result = SearchResult(
                document_id="test_doc",
                content="Test document content for health check",
                metadata={"document_type": "test"},
                similarity_score=0.9,
                rank=1,
            )

            test_request = ContextBuildRequest(
                search_results=[test_result],
                context_type=ContextType.MIXED,
                max_context_tokens=1000,
            )

            response = await self.build_context(test_request)

            health_status = {
                "status": "healthy",
                "builder_id": self.builder_id,
                "test_build_time": response.build_time,
                "test_tokens": response.total_tokens,
                "metrics": self.get_build_metrics(),
            }

            if CORE_AVAILABLE:
                health_status["checked_at"] = utc_now().isoformat()

            return health_status

        except Exception as e:
            error_msg = f"Health check failed: {e!s}"
            logger.error(error_msg)
            return {
                "status": "unhealthy",
                "builder_id": self.builder_id,
                "error": error_msg,
            }
