"""
Memory management API endpoints.
Handles conversation history, entity memory, and memory compression.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from ..models.memory import (
    GenerationState,
    MemoryUpdateRequest,
    MemoryStateResponse,
    MemoryCompressionRequest,
    MemoryClearRequest,
    MemoryMetrics,
    MemoryConflictResolution,
    ConversationTurn,
    TurnSource
)
from ..services.memory_compression import MemoryCompressionService
from .idempotency_middleware import idempotent_endpoint

# Import Core Module components if available
try:
    from ai_script_core import (
        BaseServiceException,
        ValidationException,
        get_service_logger,
    )
    CORE_AVAILABLE = True
    logger = get_service_logger("generation-service.memory")
except (ImportError, RuntimeError):
    CORE_AVAILABLE = False
    logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory storage for demo (in production, use database)
_memory_states: Dict[str, GenerationState] = {}
_compression_service = MemoryCompressionService()


class MemoryStateRequest(BaseModel):
    """Request to get or create memory state"""
    
    project_id: str = Field(..., description="Project ID")
    episode_id: Optional[str] = Field(None, description="Episode ID")
    memory_enabled: bool = Field(default=False, description="Enable memory system")
    history_depth: int = Field(default=5, ge=1, le=10, description="History depth")


class AddTurnRequest(BaseModel):
    """Request to add a conversation turn"""
    
    content: str = Field(..., max_length=2000, description="Turn content")
    source: TurnSource = Field(default=TurnSource.API, description="Source of turn")
    job_id: Optional[str] = Field(None, description="Associated job ID")
    selection: Optional[Dict[str, Any]] = Field(None, description="UI selection context")
    expected_version: Optional[int] = Field(None, description="Expected memory version")


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


@router.post(
    "/memory/state",
    response_model=MemoryStateResponse,
    summary="Get Memory State",
    description="Get current memory state for project/episode"
)
async def get_memory_state(
    request: MemoryStateRequest,
) -> MemoryStateResponse:
    """Get current memory state"""
    
    try:
        state = get_or_create_memory_state(request.project_id, request.episode_id)
        
        # Update settings if provided
        if request.memory_enabled != state.memory_enabled:
            state.memory_enabled = request.memory_enabled
            state.updated_at = datetime.now()
        
        if request.history_depth != state.history_depth:
            state.history_depth = request.history_depth
            state.updated_at = datetime.now()
        
        # Calculate token usage
        token_usage = state.estimate_token_usage()
        
        # Check if compression is recommended
        compression_recommended = _compression_service.compressor.needs_compression(state)
        
        return MemoryStateResponse(
            generation_state=state,
            sync_status="synchronized",
            token_usage=token_usage,
            compression_recommended=compression_recommended,
            last_modified=state.updated_at,
            version=state.memory_version
        )
        
    except Exception as e:
        logger.error(f"Failed to get memory state: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get memory state: {str(e)}"
        )


@router.post(
    "/memory/turns",
    response_model=MemoryStateResponse,
    summary="Add Conversation Turn",
    description="Add a new turn to conversation history"
)
async def add_conversation_turn(
    project_id: str,
    episode_id: Optional[str] = None,
    request: AddTurnRequest = ...,
) -> MemoryStateResponse:
    """Add a new conversation turn"""
    
    try:
        state = get_or_create_memory_state(project_id, episode_id)
        
        # Check for version conflicts
        if request.expected_version and request.expected_version != state.memory_version:
            logger.warning(f"Memory version conflict: expected {request.expected_version}, "
                         f"actual {state.memory_version}")
            
            # For now, server wins (could implement more sophisticated conflict resolution)
            conflicts_resolved = MemoryConflictResolution(
                conflict_detected=True,
                resolution_strategy="server_wins",
                client_version=request.expected_version,
                server_version=state.memory_version,
                resolved_version=state.memory_version,
                server_changes_applied=True,
                merged_entity_memory=state.entity_memory
            )
        else:
            conflicts_resolved = None
        
        # Add the turn
        turn = state.add_turn(
            content=request.content,
            source=request.source,
            job_id=request.job_id,
            selection=request.selection
        )
        
        # Increment version
        state.memory_version += 1
        
        # Auto-compress if needed
        compression_result = _compression_service.auto_compress_if_needed(state)
        if compression_result:
            logger.info(f"Auto-compressed memory: {compression_result.tokens_saved} tokens saved")
        
        # Calculate token usage
        token_usage = state.estimate_token_usage()
        
        # Check if compression is recommended
        compression_recommended = _compression_service.compressor.needs_compression(state)
        
        return MemoryStateResponse(
            generation_state=state,
            sync_status="synchronized" if not conflicts_resolved else "conflict_resolved",
            conflicts_resolved=conflicts_resolved,
            token_usage=token_usage,
            compression_recommended=compression_recommended,
            last_modified=state.updated_at,
            version=state.memory_version
        )
        
    except ValueError as e:
        logger.warning(f"Invalid turn request: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to add conversation turn: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add turn: {str(e)}"
        )


@router.put(
    "/memory/state",
    response_model=MemoryStateResponse,
    summary="Update Memory State",
    description="Update memory state with new settings or entity memory"
)
async def update_memory_state(
    project_id: str,
    episode_id: Optional[str] = None,
    request: MemoryUpdateRequest = ...,
) -> MemoryStateResponse:
    """Update memory state"""
    
    try:
        state = get_or_create_memory_state(project_id, episode_id)
        
        # Check for version conflicts
        conflicts_resolved = None
        if request.expected_version and request.expected_version != state.memory_version:
            if not request.force_update:
                logger.warning(f"Memory version conflict: expected {request.expected_version}, "
                             f"actual {state.memory_version}")
                
                conflicts_resolved = MemoryConflictResolution(
                    conflict_detected=True,
                    resolution_strategy="server_wins",
                    client_version=request.expected_version,
                    server_version=state.memory_version,
                    resolved_version=state.memory_version,
                    server_changes_applied=True,
                    client_changes_discarded=["settings_update"],
                    merged_entity_memory=state.entity_memory
                )
                
                # Return current state without changes
                token_usage = state.estimate_token_usage()
                return MemoryStateResponse(
                    generation_state=state,
                    sync_status="conflict_detected",
                    conflicts_resolved=conflicts_resolved,
                    token_usage=token_usage,
                    compression_recommended=_compression_service.compressor.needs_compression(state),
                    last_modified=state.updated_at,
                    version=state.memory_version
                )
        
        # Add new turns
        for turn_data in request.new_turns:
            turn = ConversationTurn(**turn_data)
            # Check for duplicates before adding
            if not any(t.content_hash == turn.content_hash for t in state.history):
                state.history.append(turn)
                state.last_seq += 1
        
        # Update entity memory
        if request.entity_memory_updates:
            updates = request.entity_memory_updates
            
            # Update rename map (merge with existing)
            if 'rename_map' in updates:
                state.entity_memory.rename_map.update(updates['rename_map'])
            
            # Update style flags (merge with existing)
            if 'style_flags' in updates:
                new_flags = set(state.entity_memory.style_flags) | set(updates['style_flags'])
                state.entity_memory.style_flags = list(new_flags)
            
            # Update facts (append new ones)
            if 'facts' in updates:
                for fact in updates['facts']:
                    if fact not in state.entity_memory.facts:
                        state.entity_memory.facts.append(fact)
        
        # Update settings
        if request.memory_enabled is not None:
            state.memory_enabled = request.memory_enabled
        
        if request.history_depth is not None:
            state.history_depth = request.history_depth
        
        # Update timestamps and version
        state.updated_at = datetime.now()
        state.memory_version += 1
        
        # Auto-compress if needed
        compression_result = _compression_service.auto_compress_if_needed(state)
        if compression_result:
            logger.info(f"Auto-compressed memory: {compression_result.tokens_saved} tokens saved")
        
        # Calculate token usage
        token_usage = state.estimate_token_usage()
        
        return MemoryStateResponse(
            generation_state=state,
            sync_status="synchronized",
            conflicts_resolved=conflicts_resolved,
            token_usage=token_usage,
            compression_recommended=_compression_service.compressor.needs_compression(state),
            last_modified=state.updated_at,
            version=state.memory_version
        )
        
    except ValueError as e:
        logger.warning(f"Invalid update request: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update memory state: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update memory: {str(e)}"
        )


@router.post(
    "/memory/compress",
    response_model=Dict[str, Any],
    summary="Compress Memory",
    description="Compress conversation history to save tokens"
)
async def compress_memory(
    project_id: str,
    episode_id: Optional[str] = None,
    request: MemoryCompressionRequest = MemoryCompressionRequest(),
) -> Dict[str, Any]:
    """Compress memory to save tokens"""
    
    try:
        state = get_or_create_memory_state(project_id, episode_id)
        
        if not state.memory_enabled:
            raise ValueError("Memory system is not enabled for this session")
        
        # Preview compression first
        preview = _compression_service.preview_compression(state)
        
        if not request.force_compression and not preview['needs_compression']:
            return {
                "compressed": False,
                "reason": "Compression not needed",
                "preview": preview
            }
        
        # Perform compression
        if request.preserve_turns:
            result = _compression_service.force_compress(state, request.preserve_turns)
        else:
            result = _compression_service.compressor.compress_memory(state)
        
        # Update version
        state.memory_version += 1
        
        return {
            "compressed": True,
            "result": {
                "decisions_extracted": len(result.decision_log),
                "turns_compressed": result.compressed_turn_count,
                "tokens_saved": result.tokens_saved,
                "compression_ratio": result.tokens_saved / max(result.tokens_before, 1),
                "decision_log": result.decision_log,
            },
            "preview": preview,
            "new_version": state.memory_version
        }
        
    except ValueError as e:
        logger.warning(f"Invalid compression request: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to compress memory: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Memory compression failed: {str(e)}"
        )


@router.delete(
    "/memory/clear",
    response_model=Dict[str, Any],
    summary="Clear Memory",
    description="Clear conversation history and/or entity memory"
)
async def clear_memory(
    project_id: str,
    episode_id: Optional[str] = None,
    request: MemoryClearRequest = MemoryClearRequest(),
) -> Dict[str, Any]:
    """Clear memory state"""
    
    try:
        state = get_or_create_memory_state(project_id, episode_id)
        
        cleared_components = []
        
        # Clear history
        if request.clear_history:
            turns_cleared = len(state.history)
            state.history = []
            state.last_seq = 0
            state.history_compacted = False
            cleared_components.append(f"history ({turns_cleared} turns)")
        
        # Clear entity memory
        if request.clear_entity_memory:
            from ..models.memory import EntityMemory
            renames_cleared = len(state.entity_memory.rename_map)
            facts_cleared = len(state.entity_memory.facts)
            flags_cleared = len(state.entity_memory.style_flags)
            
            state.entity_memory = EntityMemory()
            cleared_components.append(f"entity_memory ({renames_cleared} renames, "
                                    f"{facts_cleared} facts, {flags_cleared} flags)")
        
        # Reset version
        if request.reset_version:
            state.memory_version = 1
            cleared_components.append("version")
        else:
            state.memory_version += 1
        
        # Update timestamp
        state.updated_at = datetime.now()
        
        # Log for audit trail
        logger.info(f"Memory cleared for {project_id}:{episode_id}: {', '.join(cleared_components)}"
                   + (f" - Reason: {request.reason}" if request.reason else ""))
        
        return {
            "cleared": True,
            "components": cleared_components,
            "reason": request.reason,
            "new_version": state.memory_version,
            "timestamp": state.updated_at.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to clear memory: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Memory clear failed: {str(e)}"
        )


@router.get(
    "/memory/metrics",
    response_model=MemoryMetrics,
    summary="Get Memory Metrics",
    description="Get memory system usage metrics"
)
async def get_memory_metrics() -> MemoryMetrics:
    """Get memory system metrics"""
    
    try:
        # Calculate metrics from current states
        total_states = len(_memory_states)
        enabled_states = sum(1 for state in _memory_states.values() if state.memory_enabled)
        
        if total_states == 0:
            return MemoryMetrics(
                memory_enabled_ratio=0.0,
                memory_token_used_pct=0.0
            )
        
        # Calculate token usage statistics
        total_tokens = 0
        memory_tokens = 0
        compression_count = 0
        total_renames = 0
        total_facts = 0
        
        for state in _memory_states.values():
            if state.memory_enabled:
                usage = state.estimate_token_usage()
                total_tokens += usage['total']
                memory_tokens += usage.get('entity_memory', 0) + usage.get('history', 0)
                
                if state.history_compacted:
                    compression_count += 1
                
                total_renames += len(state.entity_memory.rename_map)
                total_facts += len(state.entity_memory.facts)
        
        memory_token_pct = (memory_tokens / max(total_tokens, 1)) * 100
        avg_facts = total_facts / max(enabled_states, 1)
        
        return MemoryMetrics(
            memory_enabled_ratio=enabled_states / total_states,
            memory_token_used_pct=memory_token_pct,
            memory_compaction_count=compression_count,
            entity_renames_total=total_renames,
            avg_entity_facts_per_session=avg_facts,
            memory_conflict_total=0,  # Would track this in production
            memory_conflict_resolution_success_rate=1.0
        )
        
    except Exception as e:
        logger.error(f"Failed to get memory metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metrics: {str(e)}"
        )


@router.get(
    "/memory/preview-compression",
    response_model=Dict[str, Any],
    summary="Preview Memory Compression",
    description="Preview what would happen during memory compression"
)
async def preview_memory_compression(
    project_id: str,
    episode_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Preview memory compression without actually performing it"""
    
    try:
        state = get_or_create_memory_state(project_id, episode_id)
        
        if not state.memory_enabled:
            return {
                "memory_enabled": False,
                "message": "Memory system is not enabled for this session"
            }
        
        preview = _compression_service.preview_compression(state)
        
        return {
            "memory_enabled": True,
            "preview": preview,
            "current_state": {
                "total_turns": len(state.history),
                "entity_renames": len(state.entity_memory.rename_map),
                "entity_facts": len(state.entity_memory.facts),
                "style_flags": len(state.entity_memory.style_flags),
                "history_compacted": state.history_compacted,
                "memory_version": state.memory_version
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to preview compression: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Preview failed: {str(e)}"
        )