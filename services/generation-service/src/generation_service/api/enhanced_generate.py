"""
Enhanced generation endpoints with memory integration.
Extends the basic generation API with conversation memory and token budget management.
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from ..models.generation import GenerationRequest, GenerationResponse, ScriptGenerationRequest
from ..models.memory import GenerationState, TurnSource, MemoryCompressionPolicy
from ..services.generation_service import GenerationService
from ..services.memory_compression import MemoryCompressionService
from ..services.prompt_builder import EnhancedPromptBuilder
from .idempotency_middleware import idempotent_endpoint

# Import Core Module components if available
try:
    from ai_script_core import (
        BaseServiceException,
        ValidationException,
        get_service_logger,
    )
    CORE_AVAILABLE = True
    logger = get_service_logger("generation-service.enhanced")
except (ImportError, RuntimeError):
    CORE_AVAILABLE = False
    logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory storage for demo (in production, use database)
_memory_states: Dict[str, GenerationState] = {}
_compression_service = MemoryCompressionService()


class EnhancedGenerationRequest(BaseModel):
    """Enhanced generation request with memory parameters"""
    
    # Base generation parameters
    base_request: ScriptGenerationRequest = Field(..., description="Base generation request")
    
    # Memory parameters
    memory_enabled: bool = Field(default=False, description="Enable conversation memory")
    history_depth: int = Field(default=5, ge=1, le=10, description="Number of turns to keep in history")
    use_entity_memory: bool = Field(default=True, description="Use entity memory for consistency")
    
    # Memory policy overrides
    memory_token_budget_pct: Optional[float] = Field(None, ge=5.0, le=40.0, description="Memory token budget %")
    rag_token_budget_pct: Optional[float] = Field(None, ge=10.0, le=50.0, description="RAG token budget %")
    user_prompt_min_pct: Optional[float] = Field(None, ge=30.0, le=80.0, description="Min user prompt %")
    
    # Conversation context
    user_prompt: str = Field(..., description="User's generation prompt")
    additional_instructions: Optional[str] = Field(None, description="Additional generation instructions")
    
    # RAG parameters
    enable_rag: bool = Field(default=False, description="Enable RAG context")
    rag_query: Optional[str] = Field(None, description="Custom RAG query (defaults to prompt)")
    max_rag_results: Optional[int] = Field(default=5, ge=1, le=20, description="Max RAG results")
    
    # Token management
    total_token_budget: Optional[int] = Field(default=4000, ge=1000, le=8000, description="Total token budget")
    
    # History synchronization
    expected_memory_version: Optional[int] = Field(None, description="Expected memory version for conflict detection")
    client_turns: List[Dict[str, Any]] = Field(default_factory=list, description="Client-side conversation turns")


class EnhancedGenerationResponse(BaseModel):
    """Enhanced generation response with memory information"""
    
    # Base generation response
    generation_response: GenerationResponse = Field(..., description="Base generation response")
    
    # Memory state
    memory_state: Optional[GenerationState] = Field(None, description="Updated memory state")
    memory_synchronized: bool = Field(default=True, description="Whether memory is synchronized")
    memory_conflicts_resolved: Optional[Dict[str, Any]] = Field(None, description="Conflict resolution details")
    
    # Token usage breakdown
    token_usage: Dict[str, int] = Field(..., description="Token usage by component")
    budget_exceeded: bool = Field(default=False, description="Whether token budget was exceeded")
    budget_adjustments: List[str] = Field(default_factory=list, description="Suggested budget adjustments")
    
    # Memory compression info
    memory_compressed: bool = Field(default=False, description="Whether memory was compressed")
    compression_details: Optional[Dict[str, Any]] = Field(None, description="Compression details")
    
    # Performance metrics
    prompt_build_time_ms: float = Field(..., description="Time to build prompt")
    generation_time_ms: float = Field(..., description="Generation time")
    total_time_ms: float = Field(..., description="Total request time")


def get_memory_key(project_id: str, episode_id: Optional[str] = None) -> str:
    """Generate memory state key"""
    return f"{project_id}:{episode_id or 'default'}"


def get_or_create_memory_state(project_id: str, episode_id: Optional[str] = None) -> GenerationState:
    """Get existing or create new memory state"""
    key = get_memory_key(project_id, episode_id)
    
    if key not in _memory_states:
        _memory_states[key] = GenerationState(
            project_id=project_id,
            episode_id=episode_id
        )
        logger.info(f"Created new memory state for {key}")
    
    return _memory_states[key]


def get_generation_service() -> GenerationService:
    """Dependency to get generation service instance"""
    # In production, this would be properly managed
    return GenerationService()


@router.post(
    "/generate/enhanced",
    response_model=EnhancedGenerationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enhanced Script Generation",
    description="Generate script with memory integration and token budget management"
)
@idempotent_endpoint(ttl_seconds=24 * 3600)
async def enhanced_generate_script(
    request: EnhancedGenerationRequest,
    http_request: Request,
    service: GenerationService = Depends(get_generation_service),
) -> EnhancedGenerationResponse:
    """Generate script with enhanced memory and budget management"""
    
    start_time = datetime.now()
    
    try:
        # Get or create memory state
        memory_state = None
        memory_synchronized = True
        memory_conflicts_resolved = None
        
        if request.memory_enabled:
            memory_state = get_or_create_memory_state(
                request.base_request.project_id,
                request.base_request.episode_id
            )
            
            # Update memory settings
            memory_state.memory_enabled = request.memory_enabled
            memory_state.history_depth = request.history_depth
            
            # Synchronize client turns
            if request.client_turns:
                # Check for version conflicts
                if (request.expected_memory_version and 
                    request.expected_memory_version != memory_state.memory_version):
                    
                    logger.warning(f"Memory version conflict: expected {request.expected_memory_version}, "
                                 f"actual {memory_state.memory_version}")
                    
                    # Simple conflict resolution: server wins, but report conflict
                    memory_synchronized = False
                    memory_conflicts_resolved = {
                        "strategy": "server_wins",
                        "client_version": request.expected_memory_version,
                        "server_version": memory_state.memory_version,
                        "client_changes_discarded": len(request.client_turns)
                    }
                else:
                    # Add client turns to history
                    from ..models.memory import ConversationTurn
                    for turn_data in request.client_turns:
                        turn = ConversationTurn(**turn_data)
                        # Check for duplicates
                        if not any(t.content_hash == turn.content_hash for t in memory_state.history):
                            memory_state.history.append(turn)
                            memory_state.last_seq += 1
        
        # Build memory compression policy with any overrides
        compression_policy = MemoryCompressionPolicy()
        if request.memory_token_budget_pct:
            compression_policy.memory_token_budget_pct = request.memory_token_budget_pct
        if request.rag_token_budget_pct:
            compression_policy.rag_token_budget_pct = request.rag_token_budget_pct
        if request.user_prompt_min_pct:
            compression_policy.user_prompt_min_pct = request.user_prompt_min_pct
        
        # Create enhanced prompt builder
        prompt_start = datetime.now()
        prompt_builder = EnhancedPromptBuilder(
            total_budget=request.total_token_budget or 4000,
            policy=compression_policy
        )
        
        # Auto-compress memory if needed
        memory_compressed = False
        compression_details = None
        if memory_state and request.memory_enabled:
            compression_result = _compression_service.auto_compress_if_needed(memory_state)
            if compression_result:
                memory_compressed = True
                compression_details = {
                    "decisions_extracted": len(compression_result.decision_log),
                    "turns_compressed": compression_result.compressed_turn_count,
                    "tokens_saved": compression_result.tokens_saved,
                    "sample_decisions": compression_result.decision_log[:3]
                }
                logger.info(f"Auto-compressed memory: {compression_result.tokens_saved} tokens saved")
        
        # Build RAG context if enabled
        rag_results = []
        if request.enable_rag:
            # TODO: Integrate with actual RAG service
            # For now, return empty results
            logger.info("RAG enabled but not implemented yet")
        
        # Build complete prompt
        complete_prompt, token_usage = prompt_builder.build_complete_prompt(
            request=request.base_request,
            generation_state=memory_state if request.memory_enabled else None,
            rag_results=rag_results if request.enable_rag else None,
            user_prompt=request.user_prompt,
            additional_instructions=request.additional_instructions
        )
        
        prompt_build_time = (datetime.now() - prompt_start).total_seconds() * 1000
        
        # Check budget and get suggestions
        budget_exceeded = prompt_builder.check_budget_exceeded(token_usage)
        budget_adjustments = []
        if budget_exceeded:
            budget_adjustments = prompt_builder.suggest_budget_adjustments(token_usage)
            logger.warning(f"Token budget exceeded: {budget_adjustments}")
        
        # Add conversation turn for the current generation
        if memory_state and request.memory_enabled:
            memory_state.add_turn(
                content=request.user_prompt,
                source=TurnSource.API,
                job_id=None  # Will be filled after generation
            )
            memory_state.memory_version += 1
        
        # Perform actual generation
        generation_start = datetime.now()
        
        # Create modified request with enhanced prompt
        modified_request = GenerationRequest(
            project_id=request.base_request.project_id,
            episode_id=request.base_request.episode_id,
            script_type=request.base_request.script_type,
            title=request.base_request.title,
            description=complete_prompt,  # Use enhanced prompt as description
            length_target=request.base_request.length_target,
            model=getattr(request.base_request, 'model_preferences', {}).get('default'),
            temperature=request.base_request.temperature,
        )
        
        generation_response = await service.generate_script(modified_request)
        generation_time = (datetime.now() - generation_start).total_seconds() * 1000
        
        # Update memory with generation result
        if memory_state and request.memory_enabled and generation_response.generation_id:
            # Find the last turn and update it with job_id
            if memory_state.history:
                memory_state.history[-1] = memory_state.history[-1].model_copy(
                    update={"job_id": generation_response.generation_id}
                )
            
            # Add generation result as system turn
            if hasattr(generation_response, 'generated_script') and generation_response.generated_script:
                memory_state.add_turn(
                    content=f"Generated: {generation_response.generated_script[:200]}...",
                    source=TurnSource.SSE,
                    job_id=generation_response.generation_id
                )
        
        total_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return EnhancedGenerationResponse(
            generation_response=generation_response,
            memory_state=memory_state,
            memory_synchronized=memory_synchronized,
            memory_conflicts_resolved=memory_conflicts_resolved,
            token_usage=token_usage,
            budget_exceeded=budget_exceeded,
            budget_adjustments=budget_adjustments,
            memory_compressed=memory_compressed,
            compression_details=compression_details,
            prompt_build_time_ms=prompt_build_time,
            generation_time_ms=generation_time,
            total_time_ms=total_time
        )
        
    except ValidationException as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ValueError as e:
        logger.warning(f"Invalid request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Enhanced generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Enhanced generation failed: {str(e)}"
        )


@router.get(
    "/generate/{generation_id}/memory-context",
    response_model=Dict[str, Any],
    summary="Get Generation Memory Context",
    description="Get the memory context used for a specific generation"
)
async def get_generation_memory_context(
    generation_id: str,
    project_id: str,
    episode_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Get memory context for a generation"""
    
    try:
        memory_state = get_or_create_memory_state(project_id, episode_id)
        
        # Find turns related to this generation
        related_turns = [
            turn for turn in memory_state.history 
            if turn.job_id == generation_id
        ]
        
        # Get recent context around the generation
        generation_turn_index = None
        for i, turn in enumerate(memory_state.history):
            if turn.job_id == generation_id:
                generation_turn_index = i
                break
        
        context_turns = []
        if generation_turn_index is not None:
            # Get 3 turns before and after the generation
            start_idx = max(0, generation_turn_index - 3)
            end_idx = min(len(memory_state.history), generation_turn_index + 4)
            context_turns = memory_state.history[start_idx:end_idx]
        
        return {
            "generation_id": generation_id,
            "memory_enabled": memory_state.memory_enabled,
            "memory_version": memory_state.memory_version,
            "related_turns": [
                {
                    "turn_id": turn.turn_id,
                    "source": turn.source,
                    "content": turn.content[:100] + "..." if len(turn.content) > 100 else turn.content,
                    "created_at": turn.created_at.isoformat(),
                }
                for turn in related_turns
            ],
            "context_turns": [
                {
                    "turn_id": turn.turn_id,
                    "source": turn.source,
                    "content": turn.content[:100] + "..." if len(turn.content) > 100 else turn.content,
                    "created_at": turn.created_at.isoformat(),
                }
                for turn in context_turns
            ],
            "entity_memory": {
                "renames": memory_state.entity_memory.rename_map,
                "style_flags": memory_state.entity_memory.style_flags,
                "facts_count": len(memory_state.entity_memory.facts),
            },
            "history_stats": {
                "total_turns": len(memory_state.history),
                "history_compacted": memory_state.history_compacted,
                "last_seq": memory_state.last_seq,
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get memory context: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get memory context: {str(e)}"
        )


@router.post(
    "/generate/validate-prompt",
    response_model=Dict[str, Any],
    summary="Validate Enhanced Prompt",
    description="Validate and preview prompt building without actual generation"
)
async def validate_enhanced_prompt(
    request: EnhancedGenerationRequest,
) -> Dict[str, Any]:
    """Validate and preview enhanced prompt building"""
    
    try:
        # Get memory state for validation
        memory_state = None
        if request.memory_enabled:
            memory_state = get_or_create_memory_state(
                request.base_request.project_id,
                request.base_request.episode_id
            )
        
        # Build compression policy
        compression_policy = MemoryCompressionPolicy()
        if request.memory_token_budget_pct:
            compression_policy.memory_token_budget_pct = request.memory_token_budget_pct
        if request.rag_token_budget_pct:
            compression_policy.rag_token_budget_pct = request.rag_token_budget_pct
        if request.user_prompt_min_pct:
            compression_policy.user_prompt_min_pct = request.user_prompt_min_pct
        
        # Create prompt builder
        prompt_builder = EnhancedPromptBuilder(
            total_budget=request.total_token_budget or 4000,
            policy=compression_policy
        )
        
        # Build prompt
        complete_prompt, token_usage = prompt_builder.build_complete_prompt(
            request=request.base_request,
            generation_state=memory_state if request.memory_enabled else None,
            rag_results=[],  # Empty for validation
            user_prompt=request.user_prompt,
            additional_instructions=request.additional_instructions
        )
        
        # Check budget
        budget_exceeded = prompt_builder.check_budget_exceeded(token_usage)
        budget_adjustments = []
        if budget_exceeded:
            budget_adjustments = prompt_builder.suggest_budget_adjustments(token_usage)
        
        # Preview memory compression if needed
        compression_preview = None
        if memory_state and request.memory_enabled:
            compression_preview = _compression_service.preview_compression(memory_state)
        
        return {
            "valid": not budget_exceeded,
            "prompt_length": len(complete_prompt),
            "token_usage": token_usage,
            "budget_exceeded": budget_exceeded,
            "budget_adjustments": budget_adjustments,
            "compression_preview": compression_preview,
            "memory_state": {
                "enabled": request.memory_enabled,
                "turns_count": len(memory_state.history) if memory_state else 0,
                "entity_renames": len(memory_state.entity_memory.rename_map) if memory_state else 0,
                "entity_facts": len(memory_state.entity_memory.facts) if memory_state else 0,
            },
            "prompt_preview": {
                "first_500_chars": complete_prompt[:500],
                "last_500_chars": complete_prompt[-500:] if len(complete_prompt) > 1000 else "",
            }
        }
        
    except Exception as e:
        logger.error(f"Prompt validation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Prompt validation failed: {str(e)}"
        )