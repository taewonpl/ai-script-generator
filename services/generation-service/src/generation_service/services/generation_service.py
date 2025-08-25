"""
LangGraph workflow-based generation service with Core Module integration
"""

import asyncio
import logging
import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from generation_service.ai.prompts import (
    ArchitectPrompts,
    PromptContext,
    ScriptType,
    SpecialAgentPrompts,
    SpecialAgentType,
    StylistPrompts,
    prompt_registry,
)
from generation_service.ai.providers.provider_factory import ProviderFactory
from generation_service.config_loader import settings
from generation_service.models.generation import (
    CustomWorkflowRequest,
    GenerationMetadata,
    GenerationRequest,
    GenerationResponse,
    GenerationStatus,
    HybridWorkflowResponse,
    NodeExecutionResult,
    # Hybrid workflow models
    ScriptGenerationRequest,
    WorkflowNodeType,
    WorkflowProgress,
    WorkflowStatus,
    WorkflowStatusResponse,
)
from generation_service.rag.rag_service import RAGService

# Import LangGraph workflow system
from generation_service.workflows.generation_workflow import GenerationWorkflow

# Import Core Module utilities
# Import Core Module components
try:
    from ai_script_core import (
        GenerationServiceError,
        NotFoundError,
        ValidationException,
        calculate_hash,
        generate_prefixed_id,
        generate_uuid,
        get_service_logger,
        safe_json_dumps,
        safe_json_loads,
        utc_now,
    )

    CORE_AVAILABLE = True
    logger = get_service_logger("generation-service.generation_service")
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


class NodeType(str, Enum):
    """LangGraph node types for script generation workflow"""

    ARCHITECT = "architect"
    STYLIST = "stylist"
    SPECIAL_AGENT = "special_agent"
    QUALITY_REVIEWER = "quality_reviewer"
    FINAL_ASSEMBLER = "final_assembler"


class NodeContext:
    """Context object passed between LangGraph nodes"""

    def __init__(self, generation_id: str, request: GenerationRequest):
        self.generation_id = generation_id
        self.request = request
        self.results: dict[str, Any] = {}
        self.metadata: dict[str, Any] = {}
        self.errors: list[str] = []
        self.quality_scores: dict[str, float] = {}

        if CORE_AVAILABLE:
            self.created_at = utc_now()
            self.context_hash = calculate_hash(
                f"{generation_id}_{safe_json_dumps(request.dict() if hasattr(request, 'dict') else str(request))}"
            )
        else:
            self.created_at = datetime.now()
            self.context_hash = str(hash(f"{generation_id}_{request!s}"))

    def add_result(self, node_type: str, result: Any):
        """Add result from a node"""
        self.results[node_type] = result

    def get_result(self, node_type: str) -> Any:
        """Get result from a specific node"""
        return self.results.get(node_type)

    def add_error(self, error: str):
        """Add error to context"""
        self.errors.append(error)

    def has_errors(self) -> bool:
        """Check if context has errors"""
        return len(self.errors) > 0

    def set_quality_score(self, metric: str, score: float):
        """Set quality score for a metric"""
        self.quality_scores[metric] = max(0.0, min(1.0, score))  # Clamp to [0,1]

    def get_overall_quality_score(self) -> float:
        """Calculate overall quality score"""
        if not self.quality_scores:
            return 0.0
        return sum(self.quality_scores.values()) / len(self.quality_scores)


class GenerationService:
    """LangGraph workflow-based script generation service"""

    def __init__(self):
        self._generations: dict[str, GenerationResponse] = {}
        self._metadata: dict[str, GenerationMetadata] = {}
        self._contexts: dict[str, NodeContext] = {}

        # Hybrid workflow storage
        self._workflows: dict[str, HybridWorkflowResponse] = {}
        self._workflow_tasks: dict[str, asyncio.Task] = {}
        self._workflow_progress: dict[str, WorkflowProgress] = {}
        self._node_results: dict[str, list[NodeExecutionResult]] = {}

        # Initialize AI provider factory
        self.provider_factory = ProviderFactory(settings.get_ai_provider_config())

        # Initialize RAG service for enhanced context retrieval
        try:
            rag_config = settings.get_rag_configuration()
            self.rag_service = RAGService(
                db_path=rag_config["chroma_db_path"],
                collection_name=rag_config["collection_name"],
                openai_api_key=settings.OPENAI_API_KEY,
                embedding_model=rag_config["embedding_model"],
                max_context_tokens=rag_config["max_context_length"],
            )
            logger.info("RAG service initialized for enhanced generation")
        except Exception as e:
            logger.warning(
                f"RAG service initialization failed, proceeding without RAG: {e}"
            )
            self.rag_service = None

        # Initialize LangGraph workflow
        self.langgraph_workflow = GenerationWorkflow(
            provider_factory=self.provider_factory, rag_service=self.rag_service
        )

        # Initialize specialized prompt templates (for legacy node functions)
        self.architect_prompts = ArchitectPrompts()
        self.stylist_prompts = StylistPrompts()
        self.special_agent_prompts = {}

        # Register prompt templates
        prompt_registry.register_template(self.architect_prompts)
        prompt_registry.register_template(self.stylist_prompts)

        # Initialize special agent prompts for different types
        for agent_type in SpecialAgentType:
            agent_prompts = SpecialAgentPrompts(agent_type)
            self.special_agent_prompts[agent_type] = agent_prompts

        logger.info("Specialized prompt templates initialized")

        # Node execution order for the legacy workflow
        self.node_workflow = [
            NodeType.ARCHITECT,
            NodeType.STYLIST,
            NodeType.SPECIAL_AGENT,
            NodeType.QUALITY_REVIEWER,
            NodeType.FINAL_ASSEMBLER,
        ]

        # Get workflow info for logging
        workflow_info = self.langgraph_workflow.get_workflow_info()

        if CORE_AVAILABLE:
            logger.info(
                "LangGraph workflow-based Generation Service initialized",
                extra={
                    "langgraph_available": workflow_info["langgraph_available"],
                    "workflow_compiled": workflow_info["workflow_compiled"],
                    "workflow_nodes": workflow_info["nodes"],
                    "providers": workflow_info["providers"],
                    "rag_available": workflow_info["rag_service_available"],
                },
            )
        else:
            logger.info("LangGraph workflow-based Generation Service initialized")

    async def generate_script(self, request: GenerationRequest) -> GenerationResponse:
        """Generate a script using LangGraph workflow system"""

        # Generate ID using Core module if available
        if CORE_AVAILABLE:
            generation_id = generate_prefixed_id("gen")
            created_time = utc_now()
        else:
            generation_id = str(uuid.uuid4())
            created_time = datetime.now()

        logger.info(f"Starting LangGraph workflow script generation: {generation_id}")

        # Validate request
        await self._validate_generation_request(request)

        try:
            # Execute LangGraph workflow directly
            workflow_response = await self.langgraph_workflow.execute(
                request, generation_id
            )

            # Store generation for tracking
            self._generations[generation_id] = workflow_response

            if CORE_AVAILABLE:
                logger.info(
                    f"LangGraph workflow completed: {generation_id}",
                    extra={
                        "generation_id": generation_id,
                        "project_id": getattr(request, "project_id", None),
                        "status": workflow_response.status,
                        "word_count": workflow_response.word_count,
                        "quality_score": getattr(
                            workflow_response, "quality_score", None
                        ),
                        "workflow_type": "langgraph",
                    },
                )

            return workflow_response

        except Exception as e:
            logger.error(f"LangGraph workflow failed for {generation_id}: {e}")

            # Fallback to legacy workflow if LangGraph fails
            logger.info(f"Falling back to legacy workflow for {generation_id}")
            return await self._execute_legacy_workflow(
                generation_id, request, created_time
            )

    async def _execute_legacy_workflow(
        self, generation_id: str, request: GenerationRequest, created_time: datetime
    ) -> GenerationResponse:
        """Execute legacy node-based workflow as fallback"""

        # Create initial response
        response = await self._create_initial_response(
            generation_id, request, created_time
        )

        # Store generation
        self._generations[generation_id] = response

        # Create metadata
        metadata = GenerationMetadata(generation_id=generation_id)
        self._metadata[generation_id] = metadata

        # Create node context
        context = NodeContext(generation_id, request)
        self._contexts[generation_id] = context

        if CORE_AVAILABLE:
            logger.info(
                f"Created legacy generation {generation_id}",
                extra={
                    "generation_id": generation_id,
                    "project_id": getattr(request, "project_id", None),
                    "context_hash": context.context_hash,
                    "workflow_nodes": [node.value for node in self.node_workflow],
                    "workflow_type": "legacy",
                },
            )

        # Start legacy workflow (async)
        await self._execute_langgraph_workflow(generation_id, context)

        return response

    async def get_generation_status(
        self, generation_id: str
    ) -> GenerationResponse | None:
        """Get the status of a generation request"""
        return self._generations.get(generation_id)

    async def cancel_generation(self, generation_id: str) -> bool:
        """Cancel a generation request"""
        generation = self._generations.get(generation_id)

        if not generation:
            return False

        if generation.status in [
            GenerationStatus.COMPLETED,
            GenerationStatus.FAILED,
            GenerationStatus.CANCELLED,
        ]:
            return False

        # Update status
        generation.status = GenerationStatus.CANCELLED
        generation.updated_at = datetime.now()

        logger.info(f"Cancelled generation {generation_id}")
        return True

    async def _execute_langgraph_workflow(
        self, generation_id: str, context: NodeContext
    ):
        """Execute the LangGraph workflow with all nodes"""

        generation = self._generations[generation_id]
        start_time = utc_now() if CORE_AVAILABLE else datetime.now()

        try:
            # Update status to in progress
            generation.status = GenerationStatus.IN_PROGRESS
            generation.updated_at = start_time

            logger.info(f"Starting LangGraph workflow for {generation_id}")

            # Execute nodes in sequence
            for node_type in self.node_workflow:
                try:
                    await self._execute_node(node_type, context)

                    if context.has_errors():
                        logger.warning(
                            f"Node {node_type} completed with errors for {generation_id}"
                        )

                except Exception as e:
                    error_msg = f"Node {node_type} failed: {e!s}"
                    context.add_error(error_msg)
                    logger.error(f"Node execution failed: {error_msg}")

                    # Continue with other nodes or fail completely based on criticality
                    if node_type in [NodeType.ARCHITECT, NodeType.FINAL_ASSEMBLER]:
                        raise  # Critical nodes must succeed

            # Calculate final results
            end_time = utc_now() if CORE_AVAILABLE else datetime.now()
            generation_time = (end_time - start_time).total_seconds()

            # Finalize generation
            await self._finalize_generation(generation_id, context, generation_time)

            if CORE_AVAILABLE:
                logger.info(
                    f"LangGraph workflow completed for {generation_id}",
                    extra={
                        "generation_id": generation_id,
                        "workflow_time_seconds": generation_time,
                        "nodes_executed": len(self.node_workflow),
                        "overall_quality_score": context.get_overall_quality_score(),
                        "error_count": len(context.errors),
                    },
                )

        except Exception as e:
            logger.error(f"LangGraph workflow failed for {generation_id}: {e}")

            generation.status = GenerationStatus.FAILED
            generation.error_message = str(e)
            generation.updated_at = utc_now() if CORE_AVAILABLE else datetime.now()

    # ========================================================================================
    # LangGraph Node Implementation Functions
    # ========================================================================================

    async def _execute_node(self, node_type: NodeType, context: NodeContext):
        """Execute a specific LangGraph node"""

        node_start_time = utc_now() if CORE_AVAILABLE else datetime.now()

        logger.info(
            f"Executing node {node_type.value} for generation {context.generation_id}"
        )

        try:
            if node_type == NodeType.ARCHITECT:
                await self.run_architect_generation(context)
            elif node_type == NodeType.STYLIST:
                await self.run_stylist_generation(context)
            elif node_type == NodeType.SPECIAL_AGENT:
                await self.run_special_agent_generation(context)
            elif node_type == NodeType.QUALITY_REVIEWER:
                await self.run_quality_review(context)
            elif node_type == NodeType.FINAL_ASSEMBLER:
                await self.run_final_assembly(context)
            else:
                raise ValueError(f"Unknown node type: {node_type}")

            node_end_time = utc_now() if CORE_AVAILABLE else datetime.now()
            execution_time = (node_end_time - node_start_time).total_seconds()

            context.metadata[f"{node_type.value}_execution_time"] = execution_time

            if CORE_AVAILABLE:
                logger.info(
                    f"Node {node_type.value} completed",
                    extra={
                        "generation_id": context.generation_id,
                        "node_type": node_type.value,
                        "execution_time_seconds": execution_time,
                    },
                )

        except Exception as e:
            error_msg = f"Node {node_type.value} execution failed: {e!s}"
            context.add_error(error_msg)
            logger.error(error_msg, exc_info=True)
            raise

    async def run_architect_generation(self, context: NodeContext):
        """Architect node: Creates structural foundation and story architecture with RAG enhancement"""

        request = context.request

        # Retrieve relevant context from RAG system if available
        rag_context = ""
        rag_tokens_used = 0

        if self.rag_service:
            try:
                rag_context = await self.rag_service.search_for_architect_context(
                    title=getattr(request, "title", ""),
                    description=getattr(request, "description", ""),
                    script_type=str(getattr(request, "script_type", "")),
                    project_id=getattr(request, "project_id", None),
                )

                if rag_context:
                    # Estimate tokens used (rough calculation)
                    rag_tokens_used = (
                        len(rag_context.split()) * 1.3
                    )  # Rough token estimation

                    if CORE_AVAILABLE:
                        logger.info(
                            "RAG context retrieved for architect node",
                            extra={
                                "generation_id": context.generation_id,
                                "project_id": getattr(request, "project_id", None),
                                "context_length": len(rag_context),
                                "estimated_tokens": rag_tokens_used,
                            },
                        )
                    else:
                        logger.info(
                            f"RAG context retrieved for architect node: {len(rag_context)} characters"
                        )

            except Exception as e:
                logger.warning(
                    f"Failed to retrieve RAG context for architect node: {e}"
                )
                rag_context = ""

        # Create prompt context for specialized template
        prompt_context = self._create_prompt_context(request, rag_context)

        # Generate specialized architect prompt
        prompt_result = self.architect_prompts.generate_prompt(prompt_context)

        # Get AI provider for architecture work
        provider = await self.provider_factory.get_provider(
            "anthropic"
        )  # Use Claude for architecture

        # Generate structural foundation using specialized prompt
        from generation_service.ai.providers.base_provider import (
            ProviderGenerationRequest,
        )

        generation_request = ProviderGenerationRequest(
            prompt=prompt_result.prompt,
            system_prompt=prompt_result.system_prompt,
            max_tokens=3000,
            temperature=0.7,
        )

        response = await provider.generate_with_retry(generation_request)

        # Store architect results with RAG and prompt metadata
        architect_result = {
            "structure": response.content,
            "model_used": response.model_info.name,
            "tokens_used": (
                response.metadata.get("tokens_used", 0) if response.metadata else 0
            ),
            "rag_context_used": bool(rag_context),
            "rag_context_length": len(rag_context) if rag_context else 0,
            "rag_tokens_estimated": rag_tokens_used,
            "prompt_template_used": "ArchitectPrompts",
            "prompt_id": prompt_result.prompt_id,
            "specialized_prompt": True,
        }

        context.add_result(NodeType.ARCHITECT.value, architect_result)

        # Set quality score based on structure completeness
        structure_score = self._evaluate_structure_quality(response.content)
        context.set_quality_score("structure", structure_score)

        # Boost quality score slightly if RAG context was successfully used
        if rag_context and len(rag_context) > 100:
            enhanced_structure_score = min(structure_score + 0.1, 1.0)
            context.set_quality_score("structure", enhanced_structure_score)

        logger.info(
            f"Architect generation completed for {context.generation_id} with RAG enhancement"
        )

    async def run_stylist_generation(self, context: NodeContext):
        """Stylist node: Enhances writing style, dialogue, and tone"""

        # Get architect results
        architect_result = context.get_result(NodeType.ARCHITECT.value)
        if not architect_result:
            raise ValueError("Architect results not available for stylist")

        # Create prompt context for stylist with architect structure
        prompt_context = self._create_prompt_context(context.request, "")
        prompt_context.additional_context["architect_structure"] = architect_result[
            "structure"
        ]

        # Generate specialized stylist prompt
        prompt_result = self.stylist_prompts.generate_prompt(prompt_context)

        # Get AI provider for styling work
        provider = await self.provider_factory.get_provider(
            "openai"
        )  # Use GPT-4o for styling

        from generation_service.ai.providers.base_provider import (
            ProviderGenerationRequest,
        )

        generation_request = ProviderGenerationRequest(
            prompt=prompt_result.prompt,
            system_prompt=prompt_result.system_prompt,
            max_tokens=4000,
            temperature=0.8,
        )

        response = await provider.generate_with_retry(generation_request)

        # Store stylist results with prompt metadata
        stylist_result = {
            "enhanced_script": response.content,
            "model_used": response.model_info.name,
            "tokens_used": (
                response.metadata.get("tokens_used", 0) if response.metadata else 0
            ),
            "prompt_template_used": "StylistPrompts",
            "prompt_id": prompt_result.prompt_id,
            "specialized_prompt": True,
        }

        context.add_result(NodeType.STYLIST.value, stylist_result)

        # Set quality score based on dialogue and style
        style_score = self._evaluate_style_quality(response.content)
        context.set_quality_score("style", style_score)

        logger.info(f"Stylist generation completed for {context.generation_id}")

    async def run_special_agent_generation(self, context: NodeContext):
        """Special Agent node: Handles specialized requirements and domain expertise"""

        # Get previous results
        stylist_result = context.get_result(NodeType.STYLIST.value)
        if not stylist_result:
            raise ValueError("Stylist results not available for special agent")

        # Determine special agent type and requirements
        agent_type, special_requirements = self._identify_special_agent_type(
            context.request
        )

        if not special_requirements or agent_type is None:
            # No special requirements, pass through
            context.add_result(
                NodeType.SPECIAL_AGENT.value,
                {
                    "enhanced_script": stylist_result["enhanced_script"],
                    "modifications": "No special requirements identified",
                    "model_used": "passthrough",
                    "agent_type": "none",
                },
            )
            return

        # Create prompt context for special agent
        prompt_context = self._create_prompt_context(context.request, "")
        prompt_context.additional_context["styled_script"] = stylist_result[
            "enhanced_script"
        ]
        prompt_context.additional_context["special_requirements"] = special_requirements

        # Get the appropriate special agent prompts
        agent_prompts = self.special_agent_prompts.get(agent_type)
        if not agent_prompts:
            # Fallback to dialogue enhancer
            agent_prompts = self.special_agent_prompts[
                SpecialAgentType.DIALOGUE_ENHANCER
            ]
            agent_type = SpecialAgentType.DIALOGUE_ENHANCER

        # Generate specialized prompt
        prompt_result = agent_prompts.generate_prompt(prompt_context)

        # Choose provider based on requirements
        provider_name = "local" if "technical" in special_requirements else "anthropic"
        provider = await self.provider_factory.get_provider(provider_name)

        from generation_service.ai.providers.base_provider import (
            ProviderGenerationRequest,
        )

        generation_request = ProviderGenerationRequest(
            prompt=prompt_result.prompt,
            system_prompt=prompt_result.system_prompt,
            max_tokens=3500,
            temperature=0.6,
        )

        response = await provider.generate_with_retry(generation_request)

        # Store special agent results with prompt metadata
        special_result = {
            "enhanced_script": response.content,
            "special_requirements": special_requirements,
            "agent_type": agent_type.value,
            "model_used": response.model_info.name,
            "tokens_used": (
                response.metadata.get("tokens_used", 0) if response.metadata else 0
            ),
            "prompt_template_used": f"SpecialAgentPrompts_{agent_type.value}",
            "prompt_id": prompt_result.prompt_id,
            "specialized_prompt": True,
        }

        context.add_result(NodeType.SPECIAL_AGENT.value, special_result)

        # Set quality score based on requirement fulfillment
        specialist_score = self._evaluate_specialist_quality(
            response.content, special_requirements
        )
        context.set_quality_score("specialist", specialist_score)

        logger.info(f"Special agent generation completed for {context.generation_id}")

    async def run_quality_review(self, context: NodeContext):
        """Quality Reviewer node: Performs comprehensive quality assessment"""

        # Get final content from special agent
        special_result = context.get_result(NodeType.SPECIAL_AGENT.value)
        if not special_result:
            raise ValueError("Special agent results not available for quality review")

        script_content = special_result["enhanced_script"]

        # Perform multiple quality checks
        quality_checks = await asyncio.gather(
            self._check_format_quality(script_content),
            self._check_content_quality(script_content, context.request),
            self._check_technical_quality(script_content),
            return_exceptions=True,
        )

        # Aggregate quality results
        quality_results = {
            "format_score": (
                quality_checks[0]
                if not isinstance(quality_checks[0], Exception)
                else 0.5
            ),
            "content_score": (
                quality_checks[1]
                if not isinstance(quality_checks[1], Exception)
                else 0.5
            ),
            "technical_score": (
                quality_checks[2]
                if not isinstance(quality_checks[2], Exception)
                else 0.5
            ),
            "overall_score": 0.0,
            "recommendations": [],
        }

        # Calculate overall score
        valid_scores = [
            score
            for score in [
                quality_results["format_score"],
                quality_results["content_score"],
                quality_results["technical_score"],
            ]
            if isinstance(score, (int, float))
        ]
        quality_results["overall_score"] = (
            sum(valid_scores) / len(valid_scores) if valid_scores else 0.5
        )

        # Generate recommendations if quality is low
        if quality_results["overall_score"] < 0.7:
            quality_results["recommendations"] = (
                await self._generate_quality_recommendations(
                    script_content, quality_results
                )
            )

        context.add_result(NodeType.QUALITY_REVIEWER.value, quality_results)

        # Set overall quality score
        context.set_quality_score("overall", quality_results["overall_score"])

        logger.info(
            f"Quality review completed for {context.generation_id} with score {quality_results['overall_score']:.2f}"
        )

    async def run_final_assembly(self, context: NodeContext):
        """Final Assembler node: Creates final output and metadata"""

        # Get all results
        architect_result = context.get_result(NodeType.ARCHITECT.value)
        stylist_result = context.get_result(NodeType.STYLIST.value)
        special_result = context.get_result(NodeType.SPECIAL_AGENT.value)
        quality_result = context.get_result(NodeType.QUALITY_REVIEWER.value)

        if not all([architect_result, stylist_result, special_result, quality_result]):
            raise ValueError("Missing required results for final assembly")

        # Get final script content
        final_script = special_result["enhanced_script"]

        # Apply quality improvements if recommended
        if quality_result["recommendations"]:
            final_script = await self._apply_quality_improvements(
                final_script, quality_result["recommendations"]
            )

        # Calculate final metrics
        word_count = len(final_script.split()) if final_script else 0
        character_count = len(final_script) if final_script else 0

        # Assemble final results
        final_result = {
            "final_script": final_script,
            "word_count": word_count,
            "character_count": character_count,
            "quality_score": quality_result["overall_score"],
            "workflow_metadata": {
                "architect_model": architect_result["model_used"],
                "stylist_model": stylist_result["model_used"],
                "special_agent_model": special_result["model_used"],
                "total_tokens": sum(
                    [
                        architect_result.get("tokens_used", 0),
                        stylist_result.get("tokens_used", 0),
                        special_result.get("tokens_used", 0),
                    ]
                ),
                "special_requirements": special_result.get("special_requirements", []),
                "quality_recommendations_applied": len(
                    quality_result["recommendations"]
                )
                > 0,
            },
        }

        context.add_result(NodeType.FINAL_ASSEMBLER.value, final_result)

        logger.info(f"Final assembly completed for {context.generation_id}")

    # ========================================================================================
    # Common Utility Functions
    # ========================================================================================

    async def _validate_generation_request(self, request: GenerationRequest):
        """Validate generation request with Core Module integration"""

        try:
            if (
                CORE_AVAILABLE
                and hasattr(request, "project_id")
                and not request.project_id
            ):
                raise ValidationException("Project ID is required", field="project_id")

            if hasattr(request, "title") and not request.title:
                error_msg = "Title is required for script generation"
                if CORE_AVAILABLE:
                    raise ValidationException(error_msg, field="title")
                else:
                    raise ValueError(error_msg)

            if hasattr(request, "description") and not request.description:
                error_msg = "Description is required for script generation"
                if CORE_AVAILABLE:
                    raise ValidationException(error_msg, field="description")
                else:
                    raise ValueError(error_msg)

        except Exception as e:
            logger.error(f"Request validation failed: {e}")
            raise

    async def _create_initial_response(
        self, generation_id: str, request: GenerationRequest, created_time: datetime
    ) -> GenerationResponse:
        """Create initial generation response"""

        response_data = {
            "generation_id": generation_id,
            "project_id": request.project_id,
            "episode_id": getattr(request, "episode_id", None),
            "status": GenerationStatus.PENDING if not CORE_AVAILABLE else "pending",
            "created_at": created_time,
            "updated_at": created_time,
        }

        # Add fields based on request type
        for field in ["script_type", "title", "description", "model"]:
            if hasattr(request, field):
                response_data[field] = getattr(request, field)

        # Handle Core module fields
        if CORE_AVAILABLE and hasattr(request, "prompt"):
            response_data["content"] = None  # Will be filled during generation

        return GenerationResponse(**response_data)

    async def _finalize_generation(
        self, generation_id: str, context: NodeContext, generation_time: float
    ):
        """Finalize generation with results from LangGraph workflow"""

        generation = self._generations[generation_id]
        final_result = context.get_result(NodeType.FINAL_ASSEMBLER.value)

        if not final_result:
            raise ValueError("Final assembly results not available")

        # Update generation with final results
        generation.status = GenerationStatus.COMPLETED
        generation.generated_script = final_result["final_script"]
        generation.word_count = final_result["word_count"]
        generation.completed_at = utc_now() if CORE_AVAILABLE else datetime.now()
        generation.updated_at = generation.completed_at
        generation.generation_time_seconds = generation_time

        # Add workflow metadata
        if hasattr(generation, "workflow_metadata"):
            generation.workflow_metadata = final_result["workflow_metadata"]

        # Add quality score
        if hasattr(generation, "quality_score"):
            generation.quality_score = final_result["quality_score"]

        logger.info(
            f"Generation {generation_id} finalized with {final_result['word_count']} words and quality score {final_result['quality_score']:.2f}"
        )

    def _create_architect_prompt(self, request: GenerationRequest) -> str:
        """Create prompt for architect node"""

        prompt = f"""
Create a detailed script structure for the following project:

Title: {getattr(request, 'title', 'Untitled')}
Description: {getattr(request, 'description', 'No description provided')}
Script Type: {getattr(request, 'script_type', 'Unknown')}

Please provide:
1. Three-act structure breakdown
2. Main character development arcs
3. Key scene outlines with purposes
4. Dialogue style and tone guidelines
5. Pacing and rhythm considerations

Focus on creating a solid structural foundation that will guide the writing process.
"""
        return prompt.strip()

    def _create_architect_prompt_with_rag(
        self, request: GenerationRequest, rag_context: str
    ) -> str:
        """Create enhanced architect prompt with RAG context"""

        base_prompt = f"""
Create a detailed script structure for the following project:

Title: {getattr(request, 'title', 'Untitled')}
Description: {getattr(request, 'description', 'No description provided')}
Script Type: {getattr(request, 'script_type', 'Unknown')}
"""

        if rag_context and len(rag_context.strip()) > 0:
            enhanced_prompt = f"""
{base_prompt}

RELEVANT CONTEXT FROM KNOWLEDGE BASE:
{rag_context}

Please provide:
1. Three-act structure breakdown
2. Main character development arcs
3. Key scene outlines with purposes
4. Dialogue style and tone guidelines
5. Pacing and rhythm considerations

Use the provided context to inform your architectural decisions where relevant, ensuring consistency with established world-building, character traits, and narrative patterns. However, maintain originality and coherence for this specific project.

Focus on creating a solid structural foundation that will guide the writing process.
"""
        else:
            enhanced_prompt = f"""
{base_prompt}

Please provide:
1. Three-act structure breakdown
2. Main character development arcs
3. Key scene outlines with purposes
4. Dialogue style and tone guidelines
5. Pacing and rhythm considerations

Focus on creating a solid structural foundation that will guide the writing process.
"""

        return enhanced_prompt.strip()

    def _create_stylist_prompt(self, request: GenerationRequest, structure: str) -> str:
        """Create prompt for stylist node"""

        prompt = f"""
Based on the following story structure, create an enhanced script with refined dialogue, improved pacing, and polished writing style:

ORIGINAL STRUCTURE:
{structure}

REQUIREMENTS:
- Enhance dialogue to be more natural and engaging
- Improve scene transitions and flow
- Maintain consistency in character voices
- Ensure proper script formatting
- Enhance emotional impact and readability

SCRIPT TYPE: {getattr(request, 'script_type', 'Unknown')}
TARGET AUDIENCE: Consider appropriate tone and content

Please create a full, polished script based on this structure.
"""
        return prompt.strip()

    def _create_special_agent_prompt(
        self, request: GenerationRequest, enhanced_script: str, requirements: list[str]
    ) -> str:
        """Create prompt for special agent node"""

        prompt = f"""
Apply specialized expertise to enhance this script:

SCRIPT CONTENT:
{enhanced_script}

SPECIAL REQUIREMENTS TO ADDRESS:
{chr(10).join([f'- {req}' for req in requirements])}

Please enhance the script by applying domain-specific knowledge for these requirements while maintaining the overall story integrity and script quality.

ORIGINAL REQUEST CONTEXT:
- Title: {getattr(request, 'title', 'Untitled')}
- Type: {getattr(request, 'script_type', 'Unknown')}
"""
        return prompt.strip()

    def _create_prompt_context(
        self, request: GenerationRequest, rag_context: str = ""
    ) -> PromptContext:
        """Create prompt context from generation request"""

        # Map script type to ScriptType enum
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

    def _identify_special_agent_type(
        self, request: GenerationRequest
    ) -> tuple[SpecialAgentType | None, list[str]]:
        """Identify special agent type and requirements based on request"""

        requirements = []
        agent_type = None

        # Check script type for special requirements
        script_type = getattr(request, "script_type", None)
        if script_type:
            script_type_str = (
                script_type.value
                if hasattr(script_type, "value")
                else str(script_type).lower()
            )

            if "technical" in script_type_str or "documentary" in script_type_str:
                requirements.append("technical")
                agent_type = SpecialAgentType.DIALOGUE_ENHANCER

            if "historical" in script_type_str:
                requirements.append("historical_accuracy")
                agent_type = SpecialAgentType.FLAW_GENERATOR

            if "medical" in script_type_str or "health" in script_type_str:
                requirements.append("medical_accuracy")
                agent_type = SpecialAgentType.DIALOGUE_ENHANCER

            if "legal" in script_type_str or "crime" in script_type_str:
                requirements.append("legal_accuracy")
                agent_type = SpecialAgentType.TENSION_BUILDER

            if "thriller" in script_type_str:
                requirements.append("plot_twists")
                agent_type = SpecialAgentType.PLOT_TWISTER

            if "comedy" in script_type_str:
                requirements.append("humor_enhancement")
                agent_type = SpecialAgentType.HUMOR_INJECTOR

            if "drama" in script_type_str:
                requirements.append("emotion_amplification")
                agent_type = SpecialAgentType.EMOTION_AMPLIFIER

        # Check description for keywords
        description = getattr(request, "description", "").lower()
        if "science" in description or "technology" in description:
            requirements.append("scientific_accuracy")
            agent_type = SpecialAgentType.DIALOGUE_ENHANCER

        if "period" in description or "historical" in description:
            requirements.append("historical_accuracy")
            agent_type = SpecialAgentType.FLAW_GENERATOR

        if "twist" in description or "surprise" in description:
            requirements.append("plot_twists")
            agent_type = SpecialAgentType.PLOT_TWISTER

        if "conflict" in description or "tension" in description:
            requirements.append("conflict_intensification")
            agent_type = SpecialAgentType.CONFLICT_INTENSIFIER

        # Default to dialogue enhancer if no specific requirements
        if not requirements:
            requirements.append("dialogue_enhancement")
            agent_type = SpecialAgentType.DIALOGUE_ENHANCER

        return agent_type, list(set(requirements))  # Remove duplicates

    def _identify_special_requirements(self, request: GenerationRequest) -> list[str]:
        """Legacy method - use _identify_special_agent_type instead"""
        _, requirements = self._identify_special_agent_type(request)
        return requirements

    def _evaluate_structure_quality(self, structure: str) -> float:
        """Evaluate quality of story structure"""

        if not structure:
            return 0.0

        score = 0.0

        # Check for key structural elements
        structure_lower = structure.lower()

        # Three-act structure indicators
        if "act" in structure_lower:
            score += 0.2

        # Character development
        if "character" in structure_lower:
            score += 0.2

        # Scene breakdown
        if "scene" in structure_lower:
            score += 0.2

        # Dialogue guidelines
        if "dialogue" in structure_lower:
            score += 0.2

        # Overall completeness (length and detail)
        if len(structure) > 500:
            score += 0.2

        return min(score, 1.0)

    def _evaluate_style_quality(self, content: str) -> float:
        """Evaluate quality of writing style"""

        if not content:
            return 0.0

        score = 0.0

        # Check for script formatting
        if "FADE IN" in content or "EXT." in content or "INT." in content:
            score += 0.3

        # Check for dialogue quality (balanced with action)
        lines = content.split("\\n")
        dialogue_lines = sum(
            1
            for line in lines
            if line.strip() and not line.strip().startswith(("EXT.", "INT.", "FADE"))
        )
        total_lines = len([line for line in lines if line.strip()])

        if total_lines > 0 and 0.3 <= dialogue_lines / total_lines <= 0.7:
            score += 0.3

        # Check for variety in sentence structure
        sentences = content.split(".")
        if (
            len(set(len(s.split()) for s in sentences[:10])) > 3
        ):  # Variety in sentence length
            score += 0.2

        # Overall length and completeness
        if len(content) > 1000:
            score += 0.2

        return min(score, 1.0)

    def _evaluate_specialist_quality(
        self, content: str, requirements: list[str]
    ) -> float:
        """Evaluate how well specialist requirements are met"""

        if not content or not requirements:
            return 0.5  # Neutral score if no requirements

        score = 0.0
        content_lower = content.lower()

        for req in requirements:
            if req == "technical":
                # Look for technical terminology
                tech_terms = ["system", "process", "method", "technology", "technical"]
                if any(term in content_lower for term in tech_terms):
                    score += 0.2

            elif req == "historical_accuracy":
                # Look for period-appropriate language
                if (
                    len(content) > 500
                ):  # Assume longer content has more opportunity for accuracy
                    score += 0.2

            elif req == "medical_accuracy":
                # Look for medical terminology
                med_terms = ["medical", "health", "patient", "treatment", "diagnosis"]
                if any(term in content_lower for term in med_terms):
                    score += 0.2

            elif req == "legal_accuracy":
                # Look for legal terminology
                legal_terms = ["legal", "court", "law", "evidence", "trial"]
                if any(term in content_lower for term in legal_terms):
                    score += 0.2

            elif req == "scientific_accuracy":
                # Look for scientific terminology
                sci_terms = ["research", "study", "analysis", "data", "experiment"]
                if any(term in content_lower for term in sci_terms):
                    score += 0.2

        return min(score / len(requirements) if requirements else 0.5, 1.0)

    # ========================================================================================
    # Quality Management Functions
    # ========================================================================================

    async def _check_format_quality(self, content: str) -> float:
        """Check script formatting quality"""

        if not content:
            return 0.0

        score = 0.0
        content_lines = content.split("\\n")

        # Check for standard script formatting elements
        formatting_elements = {
            "fade_in": any("FADE IN" in line.upper() for line in content_lines),
            "scene_headers": any(
                line.strip().startswith(("EXT.", "INT.")) for line in content_lines
            ),
            "character_names": any(
                line.strip().isupper() and len(line.strip().split()) <= 3
                for line in content_lines
            ),
            "dialogue": any(
                not line.strip().startswith(("EXT.", "INT.", "FADE"))
                and line.strip()
                and not line.strip().isupper()
                for line in content_lines
            ),
            "fade_out": any("FADE OUT" in line.upper() for line in content_lines),
        }

        # Score based on presence of formatting elements
        score += sum(0.2 for element in formatting_elements.values() if element)

        return min(score, 1.0)

    async def _check_content_quality(
        self, content: str, request: GenerationRequest
    ) -> float:
        """Check content quality against request requirements"""

        if not content:
            return 0.0

        score = 0.0
        content_lower = content.lower()

        # Check if title is referenced
        title = getattr(request, "title", "").lower()
        if title and title in content_lower:
            score += 0.2

        # Check if description elements are present
        description = getattr(request, "description", "").lower()
        if description:
            description_words = description.split()
            matching_words = sum(
                1
                for word in description_words
                if word in content_lower and len(word) > 3
            )
            if len(description_words) > 0:
                score += 0.3 * min(matching_words / len(description_words), 1.0)

        # Check content length appropriateness
        word_count = len(content.split())
        if 500 <= word_count <= 5000:  # Reasonable script length
            score += 0.3
        elif word_count > 100:  # At least some content
            score += 0.1

        # Check for narrative coherence (simple heuristic)
        if content.count(".") > 5:  # Multiple sentences
            score += 0.2

        return min(score, 1.0)

    async def _check_technical_quality(self, content: str) -> float:
        """Check technical writing quality"""

        if not content:
            return 0.0

        score = 0.0

        # Check for common technical issues
        lines = [line.strip() for line in content.split("\\n") if line.strip()]

        # Consistent formatting
        if len(lines) > 0:
            # Check for consistent capitalization in scene headers
            scene_headers = [
                line for line in lines if line.startswith(("EXT.", "INT."))
            ]
            if scene_headers:
                consistent_caps = all(
                    line.isupper() or line.istitle() for line in scene_headers
                )
                if consistent_caps:
                    score += 0.25

            # Check for proper dialogue attribution
            dialogue_blocks = 0
            for i, line in enumerate(lines):
                if line.isupper() and len(line.split()) <= 3:  # Character name
                    if (
                        i + 1 < len(lines) and not lines[i + 1].isupper()
                    ):  # Followed by dialogue
                        dialogue_blocks += 1

            if dialogue_blocks > 0:
                score += 0.25

            # Check for scene transitions
            transitions = sum(
                1
                for line in lines
                if any(word in line.upper() for word in ["CUT TO:", "DISSOLVE", "FADE"])
            )
            if transitions > 0:
                score += 0.25

            # Check spelling/grammar (basic check)
            common_errors = ["teh", "adn", "hte", "recieve", "seperate"]
            error_count = sum(content.lower().count(error) for error in common_errors)
            if error_count == 0:
                score += 0.25

        return min(score, 1.0)

    async def _generate_quality_recommendations(
        self, content: str, quality_results: dict[str, Any]
    ) -> list[str]:
        """Generate recommendations for improving quality"""

        recommendations = []

        if quality_results.get("format_score", 0) < 0.6:
            recommendations.append(
                "Improve script formatting: ensure proper scene headers, character names, and dialogue formatting"
            )

        if quality_results.get("content_score", 0) < 0.6:
            recommendations.append(
                "Enhance content relevance: better incorporate the title and description elements"
            )

        if quality_results.get("technical_score", 0) < 0.6:
            recommendations.append(
                "Fix technical issues: improve consistency in formatting and check for errors"
            )

        # Length-based recommendations
        word_count = len(content.split()) if content else 0
        if word_count < 500:
            recommendations.append(
                "Expand content: script appears too short for a complete narrative"
            )
        elif word_count > 5000:
            recommendations.append(
                "Consider condensing: script may be too long for the intended format"
            )

        # Structural recommendations
        if not any(word in content.upper() for word in ["FADE IN", "EXT.", "INT."]):
            recommendations.append(
                "Add proper script structure: include scene headers and transitions"
            )

        return recommendations

    async def _apply_quality_improvements(
        self, content: str, recommendations: list[str]
    ) -> str:
        """Apply basic quality improvements to content"""

        improved_content = content

        # Basic improvements that can be automated
        for recommendation in recommendations:
            if "script structure" in recommendation.lower():
                # Add basic structure if missing
                if not improved_content.strip().startswith("FADE IN"):
                    improved_content = "FADE IN:\\n\\n" + improved_content

                if not improved_content.strip().endswith("FADE OUT."):
                    improved_content = improved_content + "\\n\\nFADE OUT."

            elif "formatting" in recommendation.lower():
                # Fix basic formatting issues
                lines = improved_content.split("\\n")
                formatted_lines = []

                for line in lines:
                    stripped = line.strip()
                    if stripped.startswith(("EXT.", "INT.")):
                        # Ensure scene headers are uppercase
                        formatted_lines.append(stripped.upper())
                    else:
                        formatted_lines.append(line)

                improved_content = "\\n".join(formatted_lines)

        return improved_content

    async def get_generation_quality_metrics(
        self, generation_id: str
    ) -> dict[str, Any] | None:
        """Get quality metrics for a specific generation"""

        context = self._contexts.get(generation_id)
        if not context:
            return None

        quality_result = context.get_result(NodeType.QUALITY_REVIEWER.value)
        if not quality_result:
            return None

        return {
            "generation_id": generation_id,
            "overall_quality_score": context.get_overall_quality_score(),
            "quality_breakdown": {
                "format_score": quality_result.get("format_score", 0),
                "content_score": quality_result.get("content_score", 0),
                "technical_score": quality_result.get("technical_score", 0),
            },
            "quality_scores": dict(context.quality_scores),
            "recommendations": quality_result.get("recommendations", []),
            "workflow_execution_times": {
                key: value
                for key, value in context.metadata.items()
                if key.endswith("_execution_time")
            },
        }

    async def get_service_quality_statistics(self) -> dict[str, Any]:
        """Get overall service quality statistics"""

        completed_generations = [
            gen
            for gen in self._generations.values()
            if gen.status == GenerationStatus.COMPLETED
        ]

        if not completed_generations:
            return {
                "total_completed": 0,
                "average_quality_score": 0.0,
                "quality_distribution": {},
                "common_recommendations": [],
            }

        # Calculate quality statistics
        quality_scores = []
        all_recommendations = []

        for gen in completed_generations:
            context = self._contexts.get(gen.generation_id)
            if context:
                overall_score = context.get_overall_quality_score()
                quality_scores.append(overall_score)

                quality_result = context.get_result(NodeType.QUALITY_REVIEWER.value)
                if quality_result and quality_result.get("recommendations"):
                    all_recommendations.extend(quality_result["recommendations"])

        # Quality distribution
        quality_distribution = {
            "excellent": sum(1 for score in quality_scores if score >= 0.9),
            "good": sum(1 for score in quality_scores if 0.7 <= score < 0.9),
            "fair": sum(1 for score in quality_scores if 0.5 <= score < 0.7),
            "poor": sum(1 for score in quality_scores if score < 0.5),
        }

        # Common recommendations
        from collections import Counter

        recommendation_counts = Counter(all_recommendations)
        common_recommendations = [
            {"recommendation": rec, "frequency": count}
            for rec, count in recommendation_counts.most_common(5)
        ]

        return {
            "total_completed": len(completed_generations),
            "average_quality_score": (
                sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
            ),
            "quality_distribution": quality_distribution,
            "common_recommendations": common_recommendations,
            "quality_trend": {
                "improving": (
                    len([s for s in quality_scores[-10:] if s > 0.7])
                    > len([s for s in quality_scores[:10] if s > 0.7])
                    if len(quality_scores) > 10
                    else None
                )
            },
        }

    async def list_active_generations(self) -> list:
        """List all active generations"""
        active = []
        for gen_id, generation in self._generations.items():
            if generation.status in [
                GenerationStatus.PENDING,
                GenerationStatus.IN_PROGRESS,
            ]:
                active.append(
                    {
                        "generation_id": gen_id,
                        "project_id": generation.project_id,
                        "status": generation.status,
                        "created_at": generation.created_at,
                    }
                )
        return active

    async def get_generation_statistics(self) -> dict[str, Any]:
        """Get generation service statistics"""
        total = len(self._generations)

        stats = {
            "total_generations": total,
            "by_status": {status.value: 0 for status in GenerationStatus},
            "by_script_type": {},
        }

        for generation in self._generations.values():
            stats["by_status"][generation.status.value] += 1

            script_type = generation.script_type.value
            if script_type not in stats["by_script_type"]:
                stats["by_script_type"][script_type] = 0
            stats["by_script_type"][script_type] += 1

        return stats

    async def get_workflow_info(self) -> dict[str, Any]:
        """Get LangGraph workflow information"""
        return self.langgraph_workflow.get_workflow_info()

    async def is_langgraph_available(self) -> bool:
        """Check if LangGraph workflow is available and compiled"""
        workflow_info = await self.get_workflow_info()
        return (
            workflow_info["langgraph_available"] and workflow_info["workflow_compiled"]
        )

    # ========================================================================================
    # Hybrid Workflow API Methods
    # ========================================================================================

    async def execute_hybrid_workflow(
        self, request: ScriptGenerationRequest
    ) -> HybridWorkflowResponse:
        """Execute hybrid LangGraph workflow with real-time tracking"""

        # Generate workflow and generation IDs
        if CORE_AVAILABLE:
            workflow_id = generate_prefixed_id("workflow")
            generation_id = generate_prefixed_id("gen")
            start_time = utc_now()
        else:
            workflow_id = f"workflow_{uuid.uuid4().hex[:12]}"
            generation_id = f"gen_{uuid.uuid4().hex[:12]}"
            start_time = datetime.now()

        # Initialize workflow progress
        progress = WorkflowProgress(
            total_nodes=4,  # architect, stylist, special_agent, finalization
            completed_nodes=0,
            current_node=None,
            progress_percentage=0.0,
            estimated_completion=None,
        )

        # Create initial workflow response
        workflow_response = HybridWorkflowResponse(
            workflow_id=workflow_id,
            generation_id=generation_id,
            project_id=request.project_id,
            episode_id=request.episode_id,
            status=WorkflowStatus.PENDING,
            progress=progress,
            started_at=start_time,
            updated_at=start_time,
        )

        # Store workflow
        self._workflows[workflow_id] = workflow_response
        self._workflow_progress[workflow_id] = progress
        self._node_results[workflow_id] = []

        # Start background execution
        task = asyncio.create_task(
            self._execute_hybrid_workflow_background(workflow_id, request)
        )
        self._workflow_tasks[workflow_id] = task

        if CORE_AVAILABLE:
            logger.info(
                "Hybrid workflow started",
                extra={
                    "workflow_id": workflow_id,
                    "generation_id": generation_id,
                    "project_id": request.project_id,
                    "workflow_type": "hybrid",
                },
            )

        return workflow_response

    async def _execute_hybrid_workflow_background(
        self, workflow_id: str, request: ScriptGenerationRequest
    ):
        """Background execution of hybrid workflow"""

        workflow_response = self._workflows[workflow_id]

        try:
            # Update status to running
            workflow_response.status = WorkflowStatus.RUNNING
            workflow_response.updated_at = (
                utc_now() if CORE_AVAILABLE else datetime.now()
            )

            # Convert to standard GenerationRequest for workflow execution
            standard_request = self._convert_to_standard_request(request)

            # Execute LangGraph workflow with progress tracking
            langgraph_response = await self._execute_workflow_with_tracking(
                standard_request, workflow_response.generation_id, workflow_id
            )

            # Update workflow response with results
            await self._finalize_hybrid_workflow(workflow_id, langgraph_response)

        except Exception as e:
            logger.error(f"Hybrid workflow failed: {workflow_id}: {e}")

            # Update workflow with error
            workflow_response.status = WorkflowStatus.FAILED
            workflow_response.error_message = str(e)
            workflow_response.updated_at = (
                utc_now() if CORE_AVAILABLE else datetime.now()
            )

        finally:
            # Clean up task reference
            if workflow_id in self._workflow_tasks:
                del self._workflow_tasks[workflow_id]

    async def _execute_workflow_with_tracking(
        self, request: GenerationRequest, generation_id: str, workflow_id: str
    ):
        """Execute workflow with progress tracking"""

        # This would integrate with the LangGraph workflow to provide progress updates
        # For now, we'll simulate the execution and provide updates

        workflow_response = self._workflows[workflow_id]
        progress = self._workflow_progress[workflow_id]

        # Simulate node execution with progress updates
        nodes = [
            WorkflowNodeType.ARCHITECT,
            WorkflowNodeType.STYLIST,
            WorkflowNodeType.SPECIAL_AGENT,
            WorkflowNodeType.FINALIZATION,
        ]

        for i, node in enumerate(nodes):
            # Update current node
            progress.current_node = node
            progress.progress_percentage = (i / len(nodes)) * 100
            workflow_response.status = WorkflowStatus.NODE_EXECUTING
            workflow_response.updated_at = (
                utc_now() if CORE_AVAILABLE else datetime.now()
            )

            if CORE_AVAILABLE:
                logger.info(
                    "Executing workflow node",
                    extra={
                        "workflow_id": workflow_id,
                        "node": node.value,
                        "progress": progress.progress_percentage,
                    },
                )

            # Execute actual LangGraph workflow (delegate to existing method)
            if i == 0:  # First node - start the actual workflow
                langgraph_response = await self.langgraph_workflow.execute(
                    request, generation_id
                )

                # Extract node results from workflow metadata
                if (
                    hasattr(langgraph_response, "workflow_metadata")
                    and langgraph_response.workflow_metadata
                ):
                    await self._extract_node_results(
                        workflow_id, langgraph_response.workflow_metadata
                    )

                # Update progress to completion
                progress.completed_nodes = len(nodes)
                progress.current_node = None
                progress.progress_percentage = 100.0

                return langgraph_response

            # Simulate delay for other nodes (in real implementation, this would be actual node execution)
            await asyncio.sleep(0.1)

            # Create simulated node result
            node_result = NodeExecutionResult(
                node_type=node,
                status="completed",
                content=f"Simulated result from {node.value} node",
                quality_score=0.8,
                execution_time=1.5,
                tokens_used=100,
                model_used="simulated-model",
            )

            self._node_results[workflow_id].append(node_result)
            progress.completed_nodes = i + 1

        # This shouldn't be reached in normal execution
        raise RuntimeError("Workflow execution completed without LangGraph response")

    async def _extract_node_results(
        self, workflow_id: str, workflow_metadata: dict[str, Any]
    ):
        """Extract individual node results from workflow metadata"""

        # Extract results for each node from the workflow metadata
        node_mapping = {
            "architect": WorkflowNodeType.ARCHITECT,
            "stylist": WorkflowNodeType.STYLIST,
            "special_agent": WorkflowNodeType.SPECIAL_AGENT,
            "finalization": WorkflowNodeType.FINALIZATION,
        }

        for node_key, node_type in node_mapping.items():
            node_metadata = workflow_metadata.get(f"{node_key}_metadata", {})

            if node_metadata:
                node_result = NodeExecutionResult(
                    node_type=node_type,
                    status="completed",
                    content=node_metadata.get("result", ""),
                    quality_score=node_metadata.get("quality_score", 0.0),
                    execution_time=node_metadata.get("execution_time", 0.0),
                    tokens_used=node_metadata.get("tokens_used", 0),
                    model_used=node_metadata.get("model_used", "unknown"),
                    metadata=node_metadata,
                )

                self._node_results[workflow_id].append(node_result)

    async def _finalize_hybrid_workflow(
        self, workflow_id: str, langgraph_response: GenerationResponse
    ):
        """Finalize hybrid workflow with results"""

        workflow_response = self._workflows[workflow_id]

        # Update workflow response with final results
        workflow_response.status = WorkflowStatus.COMPLETED
        workflow_response.final_script = langgraph_response.generated_script
        workflow_response.partial_results = self._node_results[workflow_id]
        workflow_response.completed_at = utc_now() if CORE_AVAILABLE else datetime.now()
        workflow_response.updated_at = workflow_response.completed_at

        # Extract quality scores and metadata
        if (
            hasattr(langgraph_response, "quality_score")
            and langgraph_response.quality_score
        ):
            workflow_response.overall_quality_score = langgraph_response.quality_score

        if (
            hasattr(langgraph_response, "workflow_metadata")
            and langgraph_response.workflow_metadata
        ):
            workflow_response.execution_metadata = langgraph_response.workflow_metadata
            workflow_response.total_tokens_used = (
                langgraph_response.workflow_metadata.get("total_tokens", 0)
            )

        # Calculate total execution time
        if workflow_response.started_at and workflow_response.completed_at:
            total_time = (
                workflow_response.completed_at - workflow_response.started_at
            ).total_seconds()
            workflow_response.total_execution_time = total_time

        if CORE_AVAILABLE:
            logger.info(
                "Hybrid workflow completed",
                extra={
                    "workflow_id": workflow_id,
                    "generation_id": workflow_response.generation_id,
                    "total_time": workflow_response.total_execution_time,
                    "quality_score": workflow_response.overall_quality_score,
                    "final_script_length": len(workflow_response.final_script or ""),
                },
            )

    def _convert_to_standard_request(
        self, request: ScriptGenerationRequest
    ) -> GenerationRequest:
        """Convert ScriptGenerationRequest to standard GenerationRequest"""

        # Create standard request data
        request_data = {
            "project_id": request.project_id,
            "script_type": request.script_type,
            "title": request.title,
            "description": request.description,
        }

        # Add optional fields
        if request.episode_id:
            request_data["episode_id"] = request.episode_id
        if request.length_target:
            request_data["length_target"] = request.length_target
        if request.temperature:
            request_data["temperature"] = request.temperature

        return GenerationRequest(**request_data)

    async def get_workflow_status(
        self, workflow_id: str
    ) -> WorkflowStatusResponse | None:
        """Get current status of a workflow execution"""

        if workflow_id not in self._workflows:
            return None

        workflow = self._workflows[workflow_id]
        progress = self._workflow_progress[workflow_id]
        node_results = self._node_results[workflow_id]

        # Determine available results
        available_results = [result.node_type for result in node_results]

        # Get latest content
        latest_content = None
        if node_results:
            latest_result = node_results[-1]
            latest_content = latest_result.content
        elif workflow.final_script:
            latest_content = workflow.final_script

        # Create execution metrics
        execution_metrics = {
            "nodes_completed": progress.completed_nodes,
            "total_nodes": progress.total_nodes,
            "current_node": (
                progress.current_node.value if progress.current_node else None
            ),
            "progress_percentage": progress.progress_percentage,
        }

        # Resource usage metrics
        resource_usage = {
            "total_tokens": sum(result.tokens_used or 0 for result in node_results),
            "execution_time": workflow.total_execution_time,
            "memory_usage": "N/A",  # Would be implemented with actual monitoring
        }

        return WorkflowStatusResponse(
            workflow_id=workflow_id,
            status=workflow.status,
            progress=progress,
            current_node_details={
                "node": progress.current_node.value if progress.current_node else None,
                "estimated_time_remaining": None,  # Would be calculated based on historical data
            },
            last_update=workflow.updated_at,
            available_results=available_results,
            latest_content=latest_content,
            execution_metrics=execution_metrics,
            resource_usage=resource_usage,
        )

    async def execute_custom_workflow(
        self, request: CustomWorkflowRequest
    ) -> HybridWorkflowResponse:
        """Execute custom workflow with user-defined nodes and parameters"""

        # For now, delegate to standard hybrid workflow
        # In a full implementation, this would handle custom node configurations
        base_request = request.base_request

        # Apply custom parameters if specified
        if request.node_parameters:
            # Modify base request based on custom parameters
            pass

        # Execute with custom workflow path
        workflow_response = await self.execute_hybrid_workflow(base_request)

        # Add custom workflow metadata
        workflow_response.execution_metadata["custom_workflow"] = True
        workflow_response.execution_metadata["custom_nodes"] = [
            node.get("type") for node in request.custom_nodes
        ]
        workflow_response.execution_metadata["workflow_path"] = [
            node.value for node in request.workflow_path
        ]

        return workflow_response

    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running workflow"""

        if workflow_id not in self._workflows:
            return False

        workflow = self._workflows[workflow_id]

        # Can only cancel running workflows
        if workflow.status not in [
            WorkflowStatus.PENDING,
            WorkflowStatus.RUNNING,
            WorkflowStatus.NODE_EXECUTING,
        ]:
            return False

        # Cancel the background task
        if workflow_id in self._workflow_tasks:
            task = self._workflow_tasks[workflow_id]
            task.cancel()
            del self._workflow_tasks[workflow_id]

        # Update workflow status
        workflow.status = WorkflowStatus.CANCELLED
        workflow.updated_at = utc_now() if CORE_AVAILABLE else datetime.now()

        if CORE_AVAILABLE:
            logger.info(
                "Workflow cancelled",
                extra={
                    "workflow_id": workflow_id,
                    "generation_id": workflow.generation_id,
                },
            )

        return True

    async def list_active_workflows(self) -> list[dict[str, Any]]:
        """List all active workflows"""

        active_workflows = []

        for workflow_id, workflow in self._workflows.items():
            if workflow.status in [
                WorkflowStatus.PENDING,
                WorkflowStatus.RUNNING,
                WorkflowStatus.NODE_EXECUTING,
            ]:
                active_workflows.append(
                    {
                        "workflow_id": workflow_id,
                        "generation_id": workflow.generation_id,
                        "project_id": workflow.project_id,
                        "status": workflow.status.value,
                        "progress_percentage": self._workflow_progress[
                            workflow_id
                        ].progress_percentage,
                        "started_at": workflow.started_at,
                        "current_node": (
                            self._workflow_progress[workflow_id].current_node.value
                            if self._workflow_progress[workflow_id].current_node
                            else None
                        ),
                    }
                )

        return active_workflows
