"""
Vector document models with Core Module integration
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

# Import Core Module components
try:
    from ai_script_core import (
        BaseDTO,
        generate_prefixed_id,
        generate_uuid,
        get_service_logger,
        utc_now,
    )

    CORE_AVAILABLE = True
    logger = get_service_logger("generation-service.vector_document")
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


class DocumentType(str, Enum):
    """Types of documents in the vector store"""

    STORY_BIBLE = "story_bible"
    CHARACTER_PROFILE = "character_profile"
    WORLD_BUILDING = "world_building"
    PLOT_OUTLINE = "plot_outline"
    DIALOGUE_SAMPLE = "dialogue_sample"
    SCENE_DESCRIPTION = "scene_description"
    STYLE_GUIDE = "style_guide"
    PRODUCTION_NOTE = "production_note"
    RESEARCH_NOTE = "research_note"
    REFERENCE_MATERIAL = "reference_material"


class DocumentImportance(str, Enum):
    """Importance levels for documents"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


if CORE_AVAILABLE:
    # Use Core Module DTOs when available
    class DocumentMetadataDTO(BaseDTO):
        """Document metadata using Core DTO pattern"""

        document_type: DocumentType = Field(..., description="Type of document")
        importance: DocumentImportance = Field(
            default=DocumentImportance.MEDIUM, description="Document importance"
        )
        project_id: str | None = Field(None, description="Associated project ID")
        episode_id: str | None = Field(None, description="Associated episode ID")
        character_name: str | None = Field(
            None, description="Character name if character-related"
        )
        scene_type: str | None = Field(None, description="Scene type if scene-related")
        chapter: int | None = Field(None, description="Chapter number if applicable")
        tags: list[str] = Field(default_factory=list, description="Document tags")
        author: str | None = Field(None, description="Document author")
        source: str | None = Field(None, description="Document source")
        language: str = Field(default="en", description="Document language")
        version: int = Field(default=1, description="Document version")

        # Core integration fields
        created_by: str | None = Field(
            None, description="User who created the document"
        )
        last_modified_by: str | None = Field(
            None, description="User who last modified the document"
        )

        class Config:
            use_enum_values = True

    class VectorDocumentDTO(BaseDTO):
        """Vector document using Core DTO pattern"""

        document_id: str = Field(
            default_factory=lambda: generate_prefixed_id("doc"),
            description="Unique document ID",
        )
        content: str = Field(
            ..., min_length=1, max_length=50000, description="Document content"
        )
        title: str | None = Field(None, max_length=500, description="Document title")
        summary: str | None = Field(
            None, max_length=1000, description="Document summary"
        )
        metadata: DocumentMetadataDTO = Field(..., description="Document metadata")

        # Vector-specific fields
        embedding: list[float] | None = Field(
            None, description="Document embedding vector"
        )
        embedding_model: str | None = Field(
            None, description="Model used for embedding"
        )
        token_count: int | None = Field(
            None, ge=0, description="Token count of content"
        )

        # Core integration fields automatically added by BaseDTO

        @field_validator("content")
        @classmethod
        def validate_content(cls, v):
            if not v or not v.strip():
                raise ValueError("Content cannot be empty")
            return v.strip()

        @field_validator("title")
        @classmethod
        def validate_title(cls, v):
            if v is not None:
                return v.strip()
            return v

        class Config:
            use_enum_values = True

else:
    # Fallback implementations without Core module
    class DocumentMetadataDTO(BaseModel):
        """Document metadata fallback implementation"""

        document_type: DocumentType = Field(..., description="Type of document")
        importance: DocumentImportance = Field(
            default=DocumentImportance.MEDIUM, description="Document importance"
        )
        project_id: str | None = Field(None, description="Associated project ID")
        episode_id: str | None = Field(None, description="Associated episode ID")
        character_name: str | None = Field(
            None, description="Character name if character-related"
        )
        scene_type: str | None = Field(None, description="Scene type if scene-related")
        chapter: int | None = Field(None, description="Chapter number if applicable")
        tags: list[str] = Field(default_factory=list, description="Document tags")
        author: str | None = Field(None, description="Document author")
        source: str | None = Field(None, description="Document source")
        language: str = Field(default="en", description="Document language")
        version: int = Field(default=1, description="Document version")

        # Fallback fields
        created_at: datetime = Field(
            default_factory=datetime.now, description="Creation timestamp"
        )
        updated_at: datetime = Field(
            default_factory=datetime.now, description="Last update timestamp"
        )
        created_by: str | None = Field(
            None, description="User who created the document"
        )
        last_modified_by: str | None = Field(
            None, description="User who last modified the document"
        )

        class Config:
            use_enum_values = True

    class VectorDocumentDTO(BaseModel):
        """Vector document fallback implementation"""

        document_id: str = Field(
            default_factory=lambda: f"doc_{hash(str(datetime.now()))}",
            description="Unique document ID",
        )
        content: str = Field(
            ..., min_length=1, max_length=50000, description="Document content"
        )
        title: str | None = Field(None, max_length=500, description="Document title")
        summary: str | None = Field(
            None, max_length=1000, description="Document summary"
        )
        metadata: DocumentMetadataDTO = Field(..., description="Document metadata")

        # Vector-specific fields
        embedding: list[float] | None = Field(
            None, description="Document embedding vector"
        )
        embedding_model: str | None = Field(
            None, description="Model used for embedding"
        )
        token_count: int | None = Field(
            None, ge=0, description="Token count of content"
        )

        # Fallback fields
        created_at: datetime = Field(
            default_factory=datetime.now, description="Creation timestamp"
        )
        updated_at: datetime = Field(
            default_factory=datetime.now, description="Last update timestamp"
        )

        @field_validator("content")
        @classmethod
        def validate_content(cls, v):
            if not v or not v.strip():
                raise ValueError("Content cannot be empty")
            return v.strip()

        @field_validator("title")
        @classmethod
        def validate_title(cls, v):
            if v is not None:
                return v.strip()
            return v

        class Config:
            use_enum_values = True


class DocumentSearchFilter(BaseModel):
    """Filter for document search operations"""

    document_types: list[DocumentType] | None = Field(
        None, description="Filter by document types"
    )
    project_ids: list[str] | None = Field(None, description="Filter by project IDs")
    episode_ids: list[str] | None = Field(None, description="Filter by episode IDs")
    character_names: list[str] | None = Field(
        None, description="Filter by character names"
    )
    tags: list[str] | None = Field(None, description="Filter by tags (OR logic)")
    importance_levels: list[DocumentImportance] | None = Field(
        None, description="Filter by importance levels"
    )
    language: str | None = Field(None, description="Filter by language")
    date_from: datetime | None = Field(
        None, description="Filter documents created after this date"
    )
    date_to: datetime | None = Field(
        None, description="Filter documents created before this date"
    )

    class Config:
        use_enum_values = True


class DocumentBatch(BaseModel):
    """Batch of documents for bulk operations"""

    documents: list[VectorDocumentDTO] = Field(..., description="List of documents")
    batch_id: str = Field(
        default_factory=lambda: (
            generate_uuid()
            if CORE_AVAILABLE
            else f"batch_{int(datetime.now().timestamp())}"
        ),
        description="Batch identifier",
    )
    batch_metadata: dict[str, Any] = Field(
        default_factory=dict, description="Batch-level metadata"
    )

    @field_validator("documents")
    @classmethod
    def validate_documents(cls, v):
        if not v:
            raise ValueError("Batch must contain at least one document")
        if len(v) > 1000:  # Reasonable batch size limit
            raise ValueError("Batch size cannot exceed 1000 documents")
        return v


class DocumentUpdate(BaseModel):
    """Model for document update operations"""

    document_id: str = Field(..., description="Document ID to update")
    content: str | None = Field(
        None, min_length=1, max_length=50000, description="Updated content"
    )
    title: str | None = Field(None, max_length=500, description="Updated title")
    summary: str | None = Field(None, max_length=1000, description="Updated summary")
    metadata: DocumentMetadataDTO | None = Field(None, description="Updated metadata")

    @field_validator("content")
    @classmethod
    def validate_content(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError("Content cannot be empty")
        return v.strip() if v else v

    @field_validator("title")
    @classmethod
    def validate_title(cls, v):
        if v is not None:
            return v.strip()
        return v


class DocumentDeleteRequest(BaseModel):
    """Request for deleting documents"""

    document_ids: list[str] = Field(..., description="List of document IDs to delete")
    force_delete: bool = Field(
        default=False, description="Force delete even if referenced"
    )

    @field_validator("document_ids")
    @classmethod
    def validate_document_ids(cls, v):
        if not v:
            raise ValueError("Must specify at least one document ID")
        if len(v) > 100:  # Reasonable limit for bulk deletes
            raise ValueError("Cannot delete more than 100 documents at once")
        return v


# Factory functions for creating documents
def create_character_document(
    name: str,
    description: str,
    project_id: str | None = None,
    importance: DocumentImportance = DocumentImportance.MEDIUM,
    **kwargs,
) -> VectorDocumentDTO:
    """Create a character profile document"""

    metadata = DocumentMetadataDTO(
        document_type=DocumentType.CHARACTER_PROFILE,
        importance=importance,
        project_id=project_id,
        character_name=name,
        **kwargs,
    )

    return VectorDocumentDTO(
        title=f"Character Profile: {name}", content=description, metadata=metadata
    )


def create_story_bible_document(
    title: str,
    content: str,
    project_id: str | None = None,
    importance: DocumentImportance = DocumentImportance.CRITICAL,
    **kwargs,
) -> VectorDocumentDTO:
    """Create a story bible document"""

    metadata = DocumentMetadataDTO(
        document_type=DocumentType.STORY_BIBLE,
        importance=importance,
        project_id=project_id,
        **kwargs,
    )

    return VectorDocumentDTO(title=title, content=content, metadata=metadata)


def create_world_building_document(
    title: str,
    description: str,
    project_id: str | None = None,
    importance: DocumentImportance = DocumentImportance.HIGH,
    **kwargs,
) -> VectorDocumentDTO:
    """Create a world building document"""

    metadata = DocumentMetadataDTO(
        document_type=DocumentType.WORLD_BUILDING,
        importance=importance,
        project_id=project_id,
        **kwargs,
    )

    return VectorDocumentDTO(title=title, content=description, metadata=metadata)


def create_scene_document(
    scene_description: str,
    scene_type: str,
    project_id: str | None = None,
    episode_id: str | None = None,
    chapter: int | None = None,
    **kwargs,
) -> VectorDocumentDTO:
    """Create a scene description document"""

    metadata = DocumentMetadataDTO(
        document_type=DocumentType.SCENE_DESCRIPTION,
        project_id=project_id,
        episode_id=episode_id,
        scene_type=scene_type,
        chapter=chapter,
        **kwargs,
    )

    return VectorDocumentDTO(
        title=f"Scene: {scene_type}", content=scene_description, metadata=metadata
    )
