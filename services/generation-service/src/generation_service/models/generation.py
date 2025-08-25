"""
Generation request and response models using Core Module schemas
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import ConfigDict, Field, field_validator, model_validator

# Import Core Module schemas and components
try:
    from ai_script_core import (
        AIModelConfigDTO,
        BaseSchema,
        GenerationMetadataDTO,
        GenerationRequestDTO,
        GenerationResponseDTO,
        GenerationStatus,
        RAGConfigDTO,
    )

    CORE_AVAILABLE = True
except (ImportError, RuntimeError):
    # Fallback if Core module is not available or Python version incompatible
    from pydantic import BaseModel as BaseSchema

    CORE_AVAILABLE = False


class ScriptType(str, Enum):
    """Script type enumeration for legacy compatibility"""

    DRAMA = "drama"
    COMEDY = "comedy"
    DOCUMENTARY = "documentary"
    COMMERCIAL = "commercial"
    EDUCATIONAL = "educational"


if CORE_AVAILABLE:
    # Use Core Module DTOs when available
    class GenerationRequest(GenerationRequestDTO):
        """Enhanced generation request using Core DTO"""

        # Add service-specific fields
        script_type: ScriptType | None = Field(
            None, description="Legacy script type field"
        )
        length_target: int | None = Field(
            None, ge=100, le=50000, description="Target script length in words"
        )

        @model_validator(mode="before")
        @classmethod
        def set_defaults(cls, values):
            # Set default purpose based on script_type
            if not values.get("purpose") and values.get("script_type"):
                script_type = values["script_type"]
                if hasattr(script_type, "value"):
                    values["purpose"] = f"Generate {script_type.value} script"
                else:
                    values["purpose"] = f"Generate {script_type} script"
            elif not values.get("purpose"):
                values["purpose"] = "Generate script content"

            # Set default generation_type
            if not values.get("generation_type"):
                values["generation_type"] = "script"

            return values

    class GenerationResponse(GenerationResponseDTO):
        """Enhanced generation response using Core DTO"""

        model_config = ConfigDict(protected_namespaces=())

        # Add legacy compatibility fields
        script_type: ScriptType | None = Field(
            None, description="Legacy script type field"
        )
        generated_script: str | None = Field(
            None, description="Legacy field for content"
        )
        word_count: int | None = Field(
            None, description="Word count of generated content"
        )
        generation_time_seconds: float | None = Field(
            None, description="Legacy timing field"
        )
        model_used: str | None = Field(None, description="Legacy model field")

        @model_validator(mode="before")
        @classmethod
        def sync_and_calculate(cls, values):
            # Sync generated_script with content field
            if (
                "content" in values
                and values["content"]
                and not values.get("generated_script")
            ):
                values["generated_script"] = values["content"]

            # Calculate word count
            if values.get("word_count") is None and values.get("content"):
                values["word_count"] = len(values["content"].split())

            return values

    class GenerationMetadata(GenerationMetadataDTO):
        """Enhanced generation metadata using Core DTO"""

        # Add legacy compatibility fields
        generation_id: str = Field(..., description="Generation ID")
        user_id: str | None = None
        ip_address: str | None = None
        user_agent: str | None = None
        tokens_used: int | None = None
        cost_estimate: float | None = None
        quality_score: float | None = Field(None, ge=0.0, le=1.0)
        user_rating: int | None = Field(None, ge=1, le=5)

else:
    # Fallback implementations when Core module is not available
    class GenerationStatus(str, Enum):
        """Generation status enumeration"""

        PENDING = "pending"
        IN_PROGRESS = "in_progress"
        COMPLETED = "completed"
        FAILED = "failed"
        CANCELLED = "cancelled"

    class GenerationRequest(BaseSchema):
        """Request model for script generation"""

        project_id: str = Field(..., description="Project ID from project service")
        episode_id: str | None = Field(
            None, description="Episode ID if generating for specific episode"
        )

        script_type: ScriptType = Field(..., description="Type of script to generate")
        title: str = Field(
            ..., min_length=1, max_length=200, description="Script title"
        )
        description: str = Field(
            ...,
            min_length=10,
            max_length=2000,
            description="Script description/synopsis",
        )

        # Generation parameters
        length_target: int | None = Field(
            None, ge=100, le=50000, description="Target script length in words"
        )
        tone: str | None = Field(None, max_length=100, description="Desired tone")
        audience: str | None = Field(
            None, max_length=100, description="Target audience"
        )

        # AI model preferences
        model: str | None = Field(None, description="Preferred AI model")
        temperature: float | None = Field(
            0.7, ge=0.0, le=2.0, description="Creativity level"
        )

        # Additional context
        context: dict[str, Any] | None = Field(None, description="Additional context")
        references: list[str] | None = Field(None, description="Reference materials")

        @field_validator("description")
        @classmethod
        def validate_description(cls, v):
            if len(v.strip()) < 10:
                raise ValueError("Description must be at least 10 characters long")
            return v.strip()

    class GenerationResponse(BaseSchema):
        """Response model for script generation"""

        model_config = ConfigDict(protected_namespaces=())

        generation_id: str = Field(..., description="Unique generation ID")
        project_id: str = Field(..., description="Associated project ID")
        episode_id: str | None = Field(None, description="Associated episode ID")

        status: GenerationStatus = Field(..., description="Current generation status")

        # Request data
        script_type: ScriptType = Field(..., description="Type of script")
        title: str = Field(..., description="Script title")
        description: str = Field(..., description="Script description")

        # Generation results
        generated_script: str | None = Field(
            None, description="Generated script content"
        )
        word_count: int | None = Field(
            None, description="Word count of generated script"
        )

        # Metadata
        created_at: datetime = Field(..., description="Creation timestamp")
        updated_at: datetime = Field(..., description="Last update timestamp")
        completed_at: datetime | None = Field(None, description="Completion timestamp")

        # Generation details
        model_used: str | None = Field(None, description="AI model used for generation")
        generation_time_seconds: float | None = Field(
            None, description="Time taken to generate"
        )

        # Error information
        error_message: str | None = Field(
            None, description="Error message if generation failed"
        )

    class GenerationMetadata(BaseSchema):
        """Metadata for generation tracking"""

        generation_id: str
        user_id: str | None = None
        ip_address: str | None = None
        user_agent: str | None = None

        # Performance metrics
        tokens_used: int | None = None
        cost_estimate: float | None = None

        # Quality metrics
        quality_score: float | None = Field(None, ge=0.0, le=1.0)
        user_rating: int | None = Field(None, ge=1, le=5)

        created_at: datetime = Field(default_factory=datetime.now)


# Common update model that works with both Core and fallback
class GenerationUpdate(BaseSchema):
    """Model for updating generation status"""

    model_config = ConfigDict(protected_namespaces=())

    status: str | None = None  # Use string to support both enum types
    generated_script: str | None = None
    content: str | None = None  # Core module field
    error_message: str | None = None
    model_used: str | None = None
    generation_time_seconds: float | None = None


# ========================================================================================
# Hybrid Workflow Models
# ========================================================================================


class WorkflowNodeType(str, Enum):
    """Available workflow nodes"""

    ARCHITECT = "architect"
    STYLIST = "stylist"
    SPECIAL_AGENT = "special_agent"
    FINALIZATION = "finalization"


class WorkflowStatus(str, Enum):
    """Workflow execution status"""

    PENDING = "pending"
    RUNNING = "running"
    NODE_EXECUTING = "node_executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ContextData(BaseSchema):
    """Context data for script generation"""

    characters: list[dict[str, Any]] | None = Field(
        None, description="Character information"
    )
    setting: dict[str, Any] | None = Field(None, description="Setting and environment")
    mood: str | None = Field(None, description="Overall mood and atmosphere")
    themes: list[str] | None = Field(None, description="Themes to explore")
    constraints: list[str] | None = Field(None, description="Creative constraints")


class QualityPreferences(BaseSchema):
    """Quality preferences and thresholds"""

    minimum_quality_score: float | None = Field(
        0.7, ge=0.0, le=1.0, description="Minimum acceptable quality"
    )
    focus_areas: list[str] | None = Field(
        None, description="Areas to focus quality improvements"
    )
    strict_requirements: bool | None = Field(
        False, description="Enforce strict quality requirements"
    )


class WorkflowOptions(BaseSchema):
    """Workflow execution options"""

    enabled_nodes: list[WorkflowNodeType] | None = Field(
        None, description="Nodes to execute"
    )
    skip_nodes: list[WorkflowNodeType] | None = Field(None, description="Nodes to skip")
    use_fallback_on_error: bool | None = Field(
        True, description="Use fallback execution on node errors"
    )
    parallel_execution: bool | None = Field(
        False, description="Enable parallel node execution where possible"
    )
    save_intermediate_results: bool | None = Field(
        True, description="Save results from each node"
    )


class ScriptGenerationRequest(BaseSchema):
    """Enhanced script generation request for hybrid workflow"""

    model_config = ConfigDict(protected_namespaces=())

    # Core request fields
    project_id: str = Field(..., description="Project ID from project service")
    episode_id: str | None = Field(
        None, description="Episode ID if generating for specific episode"
    )
    generation_type: str = Field(
        "hybrid_script", description="Type of generation to perform"
    )

    # Script details
    script_type: ScriptType = Field(..., description="Type of script to generate")
    title: str = Field(..., min_length=1, max_length=200, description="Script title")
    description: str = Field(
        ..., min_length=10, max_length=2000, description="Script description/synopsis"
    )

    # Enhanced context
    context: ContextData | None = Field(None, description="Rich context for generation")

    # Generation requirements
    requirements: dict[str, Any] | None = Field(
        None, description="Specific generation requirements"
    )
    length_target: int | None = Field(
        None, ge=100, le=50000, description="Target script length in words"
    )
    style_preferences: list[str] | None = Field(None, description="Style preferences")

    # Workflow configuration
    workflow_options: WorkflowOptions | None = Field(
        None, description="Workflow execution options"
    )
    quality_preferences: QualityPreferences | None = Field(
        None, description="Quality preferences"
    )

    # AI model preferences
    model_preferences: dict[str, str] | None = Field(
        None, description="Model preferences per node"
    )
    temperature: float | None = Field(
        0.7, ge=0.0, le=2.0, description="Creativity level"
    )

    # Additional options
    priority: int | None = Field(0, ge=0, le=10, description="Execution priority")
    timeout_seconds: int | None = Field(
        300, ge=30, le=3600, description="Maximum execution time"
    )


class NodeExecutionResult(BaseSchema):
    """Result from individual node execution"""

    model_config = ConfigDict(protected_namespaces=())

    node_type: WorkflowNodeType = Field(
        ..., description="Node that produced this result"
    )
    status: str = Field(..., description="Execution status")
    content: str | None = Field(None, description="Generated content")
    quality_score: float | None = Field(
        None, ge=0.0, le=1.0, description="Quality score"
    )
    execution_time: float | None = Field(None, description="Execution time in seconds")
    tokens_used: int | None = Field(None, description="Tokens consumed")
    model_used: str | None = Field(None, description="AI model used")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")
    error_message: str | None = Field(None, description="Error message if failed")


class WorkflowProgress(BaseSchema):
    """Workflow execution progress"""

    total_nodes: int = Field(..., description="Total number of nodes")
    completed_nodes: int = Field(..., description="Number of completed nodes")
    current_node: WorkflowNodeType | None = Field(
        None, description="Currently executing node"
    )
    progress_percentage: float = Field(
        ..., ge=0.0, le=100.0, description="Overall progress percentage"
    )
    estimated_completion: datetime | None = Field(
        None, description="Estimated completion time"
    )


class HybridWorkflowResponse(BaseSchema):
    """Response for hybrid workflow execution"""

    # Workflow identification
    workflow_id: str = Field(..., description="Unique workflow execution ID")
    generation_id: str = Field(..., description="Generation ID for tracking")
    project_id: str = Field(..., description="Associated project ID")
    episode_id: str | None = Field(None, description="Associated episode ID")

    # Workflow status
    status: WorkflowStatus = Field(..., description="Current workflow status")
    progress: WorkflowProgress = Field(..., description="Execution progress")

    # Results
    final_script: str | None = Field(None, description="Final generated script")
    partial_results: list[NodeExecutionResult] = Field(
        default_factory=list, description="Results from each node"
    )

    # Quality metrics
    quality_scores: dict[str, float] = Field(
        default_factory=dict, description="Quality scores by metric"
    )
    overall_quality_score: float | None = Field(
        None, ge=0.0, le=1.0, description="Overall quality score"
    )

    # Execution metadata
    execution_metadata: dict[str, Any] = Field(
        default_factory=dict, description="Execution metadata"
    )
    total_tokens_used: int | None = Field(None, description="Total tokens consumed")
    total_execution_time: float | None = Field(None, description="Total execution time")

    # Timing
    started_at: datetime = Field(..., description="Workflow start time")
    updated_at: datetime = Field(..., description="Last update time")
    completed_at: datetime | None = Field(None, description="Completion time")

    # Error handling
    error_message: str | None = Field(
        None, description="Error message if workflow failed"
    )
    warnings: list[str] = Field(default_factory=list, description="Warning messages")

    model_config = ConfigDict()


class CustomWorkflowRequest(BaseSchema):
    """Request for custom workflow execution"""

    # Base request
    base_request: ScriptGenerationRequest = Field(
        ..., description="Base generation request"
    )

    # Custom workflow definition
    custom_nodes: list[dict[str, Any]] = Field(
        ..., description="Custom node configurations"
    )
    workflow_path: list[WorkflowNodeType] = Field(
        ..., description="Custom execution path"
    )
    node_parameters: dict[str, dict[str, Any]] = Field(
        default_factory=dict, description="Parameters per node"
    )

    # Advanced options
    conditional_routing: dict[str, Any] | None = Field(
        None, description="Custom routing conditions"
    )
    retry_policies: dict[str, dict[str, Any]] | None = Field(
        None, description="Retry policies per node"
    )
    fallback_strategies: dict[str, str] | None = Field(
        None, description="Fallback strategies per node"
    )


class WorkflowStatusResponse(BaseSchema):
    """Response for workflow status queries"""

    workflow_id: str = Field(..., description="Workflow ID")
    status: WorkflowStatus = Field(..., description="Current status")
    progress: WorkflowProgress = Field(..., description="Progress information")

    # Current execution details
    current_node_details: dict[str, Any] | None = Field(
        None, description="Details about current node"
    )
    last_update: datetime = Field(..., description="Last status update time")

    # Partial results
    available_results: list[WorkflowNodeType] = Field(
        default_factory=list, description="Nodes with available results"
    )
    latest_content: str | None = Field(None, description="Latest generated content")

    # Performance metrics
    execution_metrics: dict[str, Any] = Field(
        default_factory=dict, description="Real-time execution metrics"
    )
    resource_usage: dict[str, Any] = Field(
        default_factory=dict, description="Resource usage statistics"
    )

    model_config = ConfigDict()
