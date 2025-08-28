"""
Enhanced conflict resolution for multi-tab memory synchronization.
Implements deterministic merging based on episode_id, last_seq, and timestamp.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from collections import deque

from ..models.memory import GenerationState, ConversationTurn, EntityMemory, MemoryConflictResolution

logger = logging.getLogger(__name__)


@dataclass 
class ConflictEvent:
    """Record of a conflict event for tracking"""
    
    project_id: str
    episode_id: Optional[str]
    conflict_type: str
    client_version: int
    server_version: int
    resolution_strategy: str
    timestamp: datetime
    details: Dict[str, Any]


class WriteThrottler:
    """Throttles write operations to prevent excessive updates"""
    
    def __init__(self, min_interval_ms: int = 300, max_interval_ms: int = 500):
        self.min_interval = timedelta(milliseconds=min_interval_ms)
        self.max_interval = timedelta(milliseconds=max_interval_ms)
        self.pending_writes: Dict[str, datetime] = {}
        self.last_writes: Dict[str, datetime] = {}
        
    def can_write(self, key: str) -> bool:
        """Check if write is allowed for the given key"""
        now = datetime.now()
        
        # Check if minimum interval has passed since last write
        last_write = self.last_writes.get(key)
        if last_write and (now - last_write) < self.min_interval:
            # Schedule pending write
            self.pending_writes[key] = now + self.min_interval
            return False
        
        return True
    
    def mark_write(self, key: str):
        """Mark that a write has occurred"""
        self.last_writes[key] = datetime.now()
        # Remove from pending if it was scheduled
        self.pending_writes.pop(key, None)
    
    def get_pending_writes(self) -> List[str]:
        """Get keys that have pending writes ready to execute"""
        now = datetime.now()
        ready_keys = []
        
        for key, scheduled_time in list(self.pending_writes.items()):
            if now >= scheduled_time:
                ready_keys.append(key)
                del self.pending_writes[key]
        
        return ready_keys


class DeterministicMerger:
    """Handles deterministic merging of memory states"""
    
    def __init__(self):
        self.conflict_history: deque = deque(maxlen=100)  # Keep last 100 conflicts
    
    def merge_conversation_histories(self, 
                                   local_state: GenerationState,
                                   remote_state: GenerationState) -> Tuple[List[ConversationTurn], List[str]]:
        """
        Merge conversation histories using deterministic ordering
        
        Priority: episode_id, last_seq, turn_timestamp, content_hash
        """
        
        warnings = []
        
        # Combine all turns from both states
        all_turns = list(local_state.history) + list(remote_state.history)
        
        # Remove duplicates based on content_hash
        unique_turns = {}
        for turn in all_turns:
            if turn.content_hash not in unique_turns:
                unique_turns[turn.content_hash] = turn
            else:
                # If same content_hash but different metadata, use the one with latest created_at
                existing = unique_turns[turn.content_hash]
                if turn.created_at > existing.created_at:
                    unique_turns[turn.content_hash] = turn
                    warnings.append(f"Duplicate turn content, kept latest version: {turn.turn_id}")
        
        # Sort by deterministic criteria
        sorted_turns = sorted(unique_turns.values(), key=self._get_turn_sort_key)
        
        return sorted_turns, warnings
    
    def merge_entity_memories(self, 
                            local_memory: EntityMemory,
                            remote_memory: EntityMemory) -> Tuple[EntityMemory, List[str]]:
        """
        Merge entity memories with conflict resolution
        
        Strategy: Server wins for conflicts, but merge non-conflicting additions
        """
        
        warnings = []
        
        # Merge rename maps (remote/server wins on conflicts)
        merged_renames = dict(remote_memory.rename_map)  # Start with server state
        
        for local_key, local_value in local_memory.rename_map.items():
            if local_key not in merged_renames:
                # New rename from local, add it
                merged_renames[local_key] = local_value
            elif merged_renames[local_key] != local_value:
                # Conflict: server wins, but log it
                warnings.append(f"Rename conflict for '{local_key}': server '{merged_renames[local_key]}' vs local '{local_value}', kept server")
        
        # Merge style flags (combine unique values)
        merged_style_flags = list(remote_memory.style_flags)
        for flag in local_memory.style_flags:
            if flag not in merged_style_flags:
                merged_style_flags.append(flag)
        
        # Merge facts (combine unique values, server order preferred)
        merged_facts = list(remote_memory.facts)
        for fact in local_memory.facts:
            if fact not in merged_facts:
                merged_facts.append(fact)
        
        # Limit merged data to prevent unbounded growth
        if len(merged_style_flags) > 15:
            merged_style_flags = merged_style_flags[-15:]
            warnings.append("Style flags truncated to last 15 entries")
        
        if len(merged_facts) > 25:
            merged_facts = merged_facts[-25:]
            warnings.append("Facts truncated to last 25 entries")
        
        merged_memory = EntityMemory(
            rename_map=merged_renames,
            style_flags=merged_style_flags,
            facts=merged_facts
        )
        
        return merged_memory, warnings
    
    def resolve_version_conflict(self,
                               local_state: GenerationState,
                               remote_state: GenerationState) -> MemoryConflictResolution:
        """
        Resolve version conflicts between local and remote states
        
        Strategy: Merge content but use remote version as baseline
        """
        
        resolution_start = datetime.now()
        
        # Merge conversation histories
        merged_history, history_warnings = self.merge_conversation_histories(local_state, remote_state)
        
        # Merge entity memories  
        merged_entity_memory, memory_warnings = self.merge_entity_memories(
            local_state.entity_memory, 
            remote_state.entity_memory
        )
        
        # Determine preserved and discarded changes
        preserved_changes = []
        discarded_changes = []
        
        # Check for local changes that were preserved
        local_turn_hashes = {turn.content_hash for turn in local_state.history}
        merged_turn_hashes = {turn.content_hash for turn in merged_history}
        
        local_only_turns = local_turn_hashes - merged_turn_hashes
        if local_only_turns:
            discarded_changes.extend([f"turn_{hash[:8]}" for hash in local_only_turns])
        
        preserved_local_turns = local_turn_hashes & merged_turn_hashes
        if preserved_local_turns:
            preserved_changes.extend([f"turn_{hash[:8]}" for hash in preserved_local_turns])
        
        # Check entity memory changes
        local_renames = set(local_state.entity_memory.rename_map.items())
        merged_renames = set(merged_entity_memory.rename_map.items())
        
        if local_renames - merged_renames:
            discarded_changes.append("entity_renames")
        if local_renames & merged_renames:
            preserved_changes.append("entity_renames")
        
        # Create resolution result
        resolution = MemoryConflictResolution(
            conflict_detected=True,
            resolution_strategy="deterministic_merge",
            client_version=local_state.memory_version,
            server_version=remote_state.memory_version,
            resolved_version=remote_state.memory_version + 1,  # Increment for merge
            server_changes_applied=True,
            client_changes_preserved=preserved_changes,
            client_changes_discarded=discarded_changes,
            merged_entity_memory=merged_entity_memory,
            merge_warnings=history_warnings + memory_warnings,
            resolved_at=datetime.now()
        )
        
        # Update remote state with merged content
        remote_state.history = merged_history
        remote_state.entity_memory = merged_entity_memory
        remote_state.memory_version = resolution.resolved_version
        remote_state.updated_at = datetime.now()
        
        # Log conflict for tracking
        conflict_event = ConflictEvent(
            project_id=local_state.project_id,
            episode_id=local_state.episode_id,
            conflict_type="version_conflict",
            client_version=local_state.memory_version,
            server_version=remote_state.memory_version,
            resolution_strategy="deterministic_merge",
            timestamp=resolution_start,
            details={
                'merge_warnings': len(history_warnings + memory_warnings),
                'preserved_changes': len(preserved_changes),
                'discarded_changes': len(discarded_changes),
                'resolution_time_ms': (datetime.now() - resolution_start).total_seconds() * 1000
            }
        )
        
        self.conflict_history.append(conflict_event)
        
        logger.info(f"Resolved version conflict for {local_state.project_id}:{local_state.episode_id}: "
                   f"{len(preserved_changes)} preserved, {len(discarded_changes)} discarded")
        
        return resolution
    
    def _get_turn_sort_key(self, turn: ConversationTurn) -> Tuple:
        """Get sort key for deterministic turn ordering"""
        return (
            turn.created_at.timestamp(),  # Primary: timestamp
            turn.source.value,             # Secondary: source type  
            turn.turn_id                   # Tertiary: unique ID for determinism
        )
    
    def get_conflict_statistics(self) -> Dict[str, Any]:
        """Get statistics about recent conflicts"""
        
        if not self.conflict_history:
            return {
                'total_conflicts': 0,
                'recent_conflicts_1h': 0,
                'recent_conflicts_24h': 0,
                'avg_resolution_time_ms': 0,
                'most_common_type': None
            }
        
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(hours=24)
        
        recent_1h = [c for c in self.conflict_history if c.timestamp > hour_ago]
        recent_24h = [c for c in self.conflict_history if c.timestamp > day_ago]
        
        # Calculate average resolution time
        resolution_times = [c.details.get('resolution_time_ms', 0) for c in self.conflict_history]
        avg_resolution_time = sum(resolution_times) / len(resolution_times) if resolution_times else 0
        
        # Most common conflict type
        conflict_types = [c.conflict_type for c in self.conflict_history]
        most_common_type = max(set(conflict_types), key=conflict_types.count) if conflict_types else None
        
        return {
            'total_conflicts': len(self.conflict_history),
            'recent_conflicts_1h': len(recent_1h),
            'recent_conflicts_24h': len(recent_24h),
            'avg_resolution_time_ms': avg_resolution_time,
            'most_common_type': most_common_type,
            'conflict_types': {t: conflict_types.count(t) for t in set(conflict_types)}
        }


class EnhancedConflictResolver:
    """Enhanced conflict resolver with throttling and deterministic merging"""
    
    def __init__(self):
        self.throttler = WriteThrottler()
        self.merger = DeterministicMerger()
        
        # Track conflict patterns for alerting
        self.conflict_spike_threshold = 10  # conflicts per hour
        self.last_spike_alert = datetime.min
        self.spike_alert_cooldown = timedelta(hours=1)
    
    def can_perform_write(self, project_id: str, episode_id: Optional[str] = None) -> bool:
        """Check if write operation can proceed (not throttled)"""
        key = f"{project_id}:{episode_id or 'default'}"
        return self.throttler.can_write(key)
    
    def mark_write_performed(self, project_id: str, episode_id: Optional[str] = None):
        """Mark that a write operation was performed"""
        key = f"{project_id}:{episode_id or 'default'}"
        self.throttler.mark_write(key)
    
    def resolve_memory_conflict(self,
                              local_state: GenerationState,
                              remote_state: GenerationState) -> MemoryConflictResolution:
        """
        Resolve memory conflict using enhanced deterministic merging
        """
        
        # Use deterministic merger
        resolution = self.merger.resolve_version_conflict(local_state, remote_state)
        
        # Check for conflict spikes and alert if needed
        self._check_conflict_spike()
        
        return resolution
    
    def get_pending_writes(self) -> List[str]:
        """Get memory keys that have pending writes ready to execute"""
        return self.throttler.get_pending_writes()
    
    def batch_merge_writes(self, pending_operations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Merge multiple pending write operations for efficiency
        
        Groups operations by memory key and merges them into single operations
        """
        
        # Group by memory key
        grouped_ops = {}
        for op in pending_operations:
            key = f"{op['project_id']}:{op.get('episode_id', 'default')}"
            if key not in grouped_ops:
                grouped_ops[key] = []
            grouped_ops[key].append(op)
        
        # Merge operations for each key
        merged_ops = []
        for key, ops in grouped_ops.items():
            if len(ops) == 1:
                merged_ops.append(ops[0])
            else:
                # Merge multiple operations
                merged_op = self._merge_write_operations(ops)
                merged_ops.append(merged_op)
                
                logger.info(f"Merged {len(ops)} write operations for {key}")
        
        return merged_ops
    
    def _merge_write_operations(self, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge multiple write operations into a single operation"""
        
        if not operations:
            return {}
        
        # Start with the latest operation as base
        merged = operations[-1].copy()
        
        # Merge turns from all operations
        all_turns = []
        for op in operations:
            turns = op.get('turns', [])
            all_turns.extend(turns)
        
        # Remove duplicate turns by content hash
        unique_turns = {}
        for turn in all_turns:
            content_hash = turn.get('content_hash')
            if content_hash and content_hash not in unique_turns:
                unique_turns[content_hash] = turn
        
        merged['turns'] = list(unique_turns.values())
        
        # Merge entity memory updates (latest wins)
        entity_updates = {}
        for op in operations:
            if 'entity_memory' in op:
                entity_updates.update(op['entity_memory'])
        
        if entity_updates:
            merged['entity_memory'] = entity_updates
        
        # Use latest timestamp
        merged['timestamp'] = max(op.get('timestamp', datetime.min) for op in operations)
        
        return merged
    
    def _check_conflict_spike(self):
        """Check for conflict spikes and trigger alerts if needed"""
        
        now = datetime.now()
        
        # Skip if we recently sent an alert
        if now - self.last_spike_alert < self.spike_alert_cooldown:
            return
        
        # Get recent conflict statistics
        stats = self.merger.get_conflict_statistics()
        recent_conflicts = stats['recent_conflicts_1h']
        
        if recent_conflicts >= self.conflict_spike_threshold:
            logger.warning(f"Memory conflict spike detected: {recent_conflicts} conflicts in last hour "
                          f"(threshold: {self.conflict_spike_threshold})")
            
            self.last_spike_alert = now
            
            # Could trigger external alerting here
            # e.g., send to monitoring system, Slack webhook, etc.
    
    def get_system_health_status(self) -> Dict[str, Any]:
        """Get overall system health status related to conflicts"""
        
        conflict_stats = self.merger.get_conflict_statistics()
        
        # Determine health status
        recent_conflicts = conflict_stats['recent_conflicts_1h']
        
        if recent_conflicts >= self.conflict_spike_threshold:
            health_status = 'warning'
            health_message = f"High conflict rate: {recent_conflicts}/hour"
        elif recent_conflicts >= self.conflict_spike_threshold // 2:
            health_status = 'degraded'
            health_message = f"Elevated conflict rate: {recent_conflicts}/hour"
        else:
            health_status = 'healthy'
            health_message = "Conflict rate normal"
        
        return {
            'status': health_status,
            'message': health_message,
            'metrics': conflict_stats,
            'throttling': {
                'pending_writes': len(self.throttler.pending_writes),
                'min_interval_ms': self.throttler.min_interval.total_seconds() * 1000,
                'max_interval_ms': self.throttler.max_interval.total_seconds() * 1000,
            }
        }


# Global instance for reuse
_conflict_resolver = EnhancedConflictResolver()


def resolve_memory_conflict(local_state: GenerationState, remote_state: GenerationState) -> MemoryConflictResolution:
    """Convenience function for conflict resolution"""
    return _conflict_resolver.resolve_memory_conflict(local_state, remote_state)


def can_write_memory(project_id: str, episode_id: Optional[str] = None) -> bool:
    """Convenience function to check if memory write is throttled"""
    return _conflict_resolver.can_perform_write(project_id, episode_id)


def mark_memory_write(project_id: str, episode_id: Optional[str] = None):
    """Convenience function to mark memory write performed"""
    _conflict_resolver.mark_write_performed(project_id, episode_id)


def get_conflict_health_status() -> Dict[str, Any]:
    """Convenience function to get conflict resolution health status"""
    return _conflict_resolver.get_system_health_status()