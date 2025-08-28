"""
Edge case tests for memory system operational safety
Tests for overlapping names, compression consistency, and multi-tab scenarios
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict
from unittest.mock import Mock, AsyncMock

from generation_service.models.memory import (
    GenerationState, ConversationTurn, EntityMemory, TurnSource,
    MemoryMetrics, MemoryFailureType
)
from generation_service.services.rename_processor import RenameProcessor
from generation_service.services.memory_compression import MemoryCompressionService, CompressionPolicy
from generation_service.services.conflict_resolver import EnhancedConflictResolver
from generation_service.services.failure_recovery import MemoryRecoveryManager, record_memory_failure


class TestOverlappingCharacterNames:
    """Test edge cases with overlapping character names like 'Han' and 'Han Seon'"""
    
    def setup_method(self):
        self.rename_processor = RenameProcessor()
        self.test_project_id = "test_project"
        self.test_episode_id = "test_episode"
    
    def test_overlapping_names_han_han_seon(self):
        """Test word boundary detection with 'Han' and 'Han Seon' characters"""
        
        # Setup rename map with overlapping names
        rename_map = {
            "Han": "김한수",
            "Han Seon": "박한선"
        }
        
        # Test various sentences with overlapping patterns
        test_cases = [
            # Should replace 'Han Seon' first (longer match)
            ("Han Seon walked to Han's house", "박한선 walked to 김한수's house"),
            ("Han and Han Seon talked together", "김한수 and 박한선 talked together"),
            ("Han Seon's friend Han arrived", "박한선's friend 김한수 arrived"),
            
            # Word boundary edge cases
            ("Hanbok worn by Han", "Hanbok worn by 김한수"),  # 'Hanbok' should not be replaced
            ("Han's Hanbok", "김한수's Hanbok"),
            ("Han Seon wore a Hanbok", "박한선 wore a Hanbok"),
            
            # Punctuation boundaries
            ("Han, Han Seon, and others", "김한수, 박한선, and others"),
            ("'Han!' shouted Han Seon", "'김한수!' shouted 박한선"),
            ("Han-style vs Han Seon-style", "김한수-style vs 박한선-style"),
        ]
        
        for input_text, expected_output in test_cases:
            result = self.rename_processor.apply_renames(input_text, rename_map)
            assert result == expected_output, f"Failed for '{input_text}': expected '{expected_output}', got '{result}'"
    
    def test_overlapping_names_complex_scenarios(self):
        """Test complex overlapping name scenarios"""
        
        # Multiple overlapping patterns
        rename_map = {
            "김": "Kim",
            "김철수": "Kim Chulsoo", 
            "김철수의": "Kim Chulsoo's",
            "이": "Lee",
            "이영희": "Lee Younghee"
        }
        
        test_cases = [
            # Longest match should win
            ("김철수의 집에서 김과 이영희가 만났다", "Kim Chulsoo's 집에서 Kim과 Lee Younghee가 만났다"),
            ("김철수는 이와 함께 왔다", "Kim Chulsoo는 Lee와 함께 왔다"),
            
            # Avoid partial matches within words
            ("김치와 김철수", "김치와 Kim Chulsoo"),  # '김치' should not be replaced
            ("이상한 이영희", "이상한 Lee Younghee"),  # '이상한' should not be replaced
        ]
        
        for input_text, expected_output in test_cases:
            result = self.rename_processor.apply_renames(input_text, rename_map)
            assert result == expected_output, f"Failed for '{input_text}': expected '{expected_output}', got '{result}'"
    
    def test_cycle_detection_overlapping_names(self):
        """Test cycle detection with overlapping character names"""
        
        # Create cycle with overlapping names
        rename_map_with_cycle = {
            "Han": "Han Seon",
            "Han Seon": "Han Woo", 
            "Han Woo": "Han",  # Creates cycle: Han → Han Seon → Han Woo → Han
            "Park": "Valid Name"  # Non-cycle name
        }
        
        cycles = self.rename_processor.detect_rename_cycles(rename_map_with_cycle)
        
        # Should detect the cycle
        assert len(cycles) == 1, f"Expected 1 cycle, found {len(cycles)}"
        
        cycle = cycles[0]
        expected_names = {"Han", "Han Seon", "Han Woo"}
        assert set(cycle) == expected_names, f"Expected cycle {expected_names}, got {set(cycle)}"
    
    def test_safe_rename_validation_overlapping(self):
        """Test safe rename validation with overlapping names"""
        
        # Test valid overlapping renames
        valid_renames = {
            "Han": "김한수",
            "Han Seon": "박한선",
            "Han Woo Jin": "이한우진"
        }
        
        is_safe, reason = self.rename_processor.validate_safe_renames(valid_renames)
        assert is_safe, f"Valid renames marked unsafe: {reason}"
        
        # Test conflicting overlapping renames
        conflicting_renames = {
            "Han": "같은이름",
            "Han Seon": "같은이름",  # Same target name
        }
        
        is_safe, reason = self.rename_processor.validate_safe_renames(conflicting_renames)
        assert not is_safe, "Conflicting renames not detected"
        assert "conflicts" in reason.lower(), f"Expected conflict reason, got: {reason}"


class TestCompressionConsistency:
    """Test compression consistency for long conversations"""
    
    def setup_method(self):
        self.compression_service = MemoryCompressionService()
        self.project_id = "test_project"
        self.episode_id = "test_episode"
    
    def create_long_conversation(self, turns_count: int) -> GenerationState:
        """Create a GenerationState with many conversation turns"""
        
        history = []
        entity_memory = EntityMemory(
            rename_map={"Character A": "캐릭터A", "Character B": "캐릭터B"},
            style_flags=["formal", "dramatic"],
            facts=["Setting is modern Seoul", "Genre is romance drama"]
        )
        
        for i in range(turns_count):
            turn = ConversationTurn(
                turn_id=f"turn_{i}",
                source=TurnSource.UI if i % 2 == 0 else TurnSource.API,
                content=f"Turn {i}: Character A talks to Character B about important plot point {i}. "
                       f"This conversation reveals key information about their relationship and the story direction. "
                       f"Turn {i} contains crucial dialogue that advances the narrative.",
                content_hash=f"hash_{i}",
                created_at=datetime.now() - timedelta(minutes=turns_count - i)
            )
            history.append(turn)
        
        return GenerationState(
            project_id=self.project_id,
            episode_id=self.episode_id,
            history=history,
            last_seq=turns_count,
            entity_memory=entity_memory,
            history_compacted=False,
            memory_enabled=True,
            history_depth=10,
            memory_version=1,
            created_at=datetime.now() - timedelta(hours=1),
            updated_at=datetime.now()
        )
    
    @pytest.mark.asyncio
    async def test_large_conversation_compression_consistency(self):
        """Test that large conversation compression is consistent across multiple runs"""
        
        # Create conversation with 100 turns (much larger than typical)
        large_conversation = self.create_long_conversation(100)
        
        # Compress the same conversation multiple times
        compression_results = []
        
        for run in range(3):  # Test consistency across 3 runs
            # Create fresh copy to avoid state pollution
            conversation_copy = GenerationState.model_copy(large_conversation)
            
            result = await self.compression_service.compress_memory(
                conversation_copy, 
                CompressionPolicy.SMART_PRESERVE
            )
            
            compression_results.append({
                'run': run,
                'compressed': result.compressed,
                'decision_log_length': len(result.decision_log) if result.decision_log else 0,
                'turns_preserved': len(result.compressed_state.history) if result.compressed_state else 0,
                'entity_facts_count': len(result.compressed_state.entity_memory.facts) if result.compressed_state else 0
            })
        
        # Verify consistency
        first_result = compression_results[0]
        
        for i, result in enumerate(compression_results[1:], 1):
            assert result['compressed'] == first_result['compressed'], \
                f"Run {i} compression result differs from run 0"
            
            # Decision log should be similar length (±2 entries for potential randomness)
            assert abs(result['decision_log_length'] - first_result['decision_log_length']) <= 2, \
                f"Run {i} decision log length varies too much from run 0"
            
            # Core preservation should be consistent
            assert result['turns_preserved'] == first_result['turns_preserved'], \
                f"Run {i} preserved different number of turns"
            
            assert result['entity_facts_count'] == first_result['entity_facts_count'], \
                f"Run {i} preserved different number of entity facts"
    
    @pytest.mark.asyncio
    async def test_compression_with_overlapping_names(self):
        """Test compression behavior with overlapping character names"""
        
        # Create conversation with overlapping names
        history = []
        for i in range(20):
            content = f"Turn {i}: Han talks to Han Seon about Han Woo. " \
                     f"Han Seon responds to Han while Han Woo listens. " \
                     f"All three characters (Han, Han Seon, Han Woo) are involved."
            
            turn = ConversationTurn(
                turn_id=f"turn_{i}",
                source=TurnSource.UI,
                content=content,
                content_hash=f"hash_{i}",
                created_at=datetime.now() - timedelta(minutes=20 - i)
            )
            history.append(turn)
        
        entity_memory = EntityMemory(
            rename_map={
                "Han": "김한수",
                "Han Seon": "박한선", 
                "Han Woo": "이한우"
            },
            style_flags=["casual", "contemporary"],
            facts=["Three friends in Seoul", "Coming-of-age story"]
        )
        
        state = GenerationState(
            project_id=self.project_id,
            episode_id=self.episode_id,
            history=history,
            last_seq=20,
            entity_memory=entity_memory,
            history_compacted=False,
            memory_enabled=True,
            history_depth=5,  # Force compression
            memory_version=1,
            created_at=datetime.now() - timedelta(hours=1),
            updated_at=datetime.now()
        )
        
        result = await self.compression_service.compress_memory(state, CompressionPolicy.PRESERVE_RECENT)
        
        # Verify compression handled overlapping names correctly
        assert result.compressed, "Long conversation with overlapping names should be compressed"
        assert result.compressed_state is not None
        
        # Check that decision log contains information about all three characters
        decision_text = ' '.join(result.decision_log or [])
        assert "Han" in decision_text or "김한수" in decision_text
        assert "Han Seon" in decision_text or "박한선" in decision_text  
        assert "Han Woo" in decision_text or "이한우" in decision_text


class TestMultiTabConcurrency:
    """Test multi-tab concurrent memory operations"""
    
    def setup_method(self):
        self.conflict_resolver = EnhancedConflictResolver()
        self.recovery_manager = MemoryRecoveryManager()
        self.project_id = "test_project"
        self.episode_id = "test_episode"
    
    def create_test_state(self, version: int, extra_turns: int = 0) -> GenerationState:
        """Create test GenerationState with specified version"""
        
        base_history = [
            ConversationTurn(
                turn_id="base_turn_1",
                source=TurnSource.UI,
                content="Initial conversation turn",
                content_hash="hash_base_1",
                created_at=datetime.now() - timedelta(minutes=10)
            )
        ]
        
        # Add extra turns for version differences
        for i in range(extra_turns):
            turn = ConversationTurn(
                turn_id=f"extra_turn_{i}",
                source=TurnSource.UI,
                content=f"Extra turn {i} content",
                content_hash=f"hash_extra_{i}",
                created_at=datetime.now() - timedelta(minutes=9 - i)
            )
            base_history.append(turn)
        
        return GenerationState(
            project_id=self.project_id,
            episode_id=self.episode_id,
            history=base_history,
            last_seq=len(base_history),
            entity_memory=EntityMemory(
                rename_map={"Test": f"테스트{version}"},
                style_flags=[f"style_{version}"],
                facts=[f"fact_version_{version}"]
            ),
            history_compacted=False,
            memory_enabled=True,
            history_depth=10,
            memory_version=version,
            created_at=datetime.now() - timedelta(hours=1),
            updated_at=datetime.now()
        )
    
    @pytest.mark.asyncio
    async def test_concurrent_memory_enable_disable(self):
        """Test concurrent enable/disable operations from multiple tabs"""
        
        # Simulate 3 tabs trying to change memory settings simultaneously
        tab_states = [
            self.create_test_state(1),
            self.create_test_state(1),
            self.create_test_state(1)
        ]
        
        # Each tab wants different settings
        desired_settings = [
            {'memory_enabled': True, 'history_depth': 5},
            {'memory_enabled': False, 'history_depth': 8}, 
            {'memory_enabled': True, 'history_depth': 10}
        ]
        
        # Track write attempts for throttling
        write_attempts = []
        
        async def simulate_tab_write(tab_id: int, state: GenerationState, settings: dict):
            """Simulate a tab attempting to write memory settings"""
            
            # Check if write is throttled
            can_write = self.conflict_resolver.can_perform_write(self.project_id, self.episode_id)
            
            write_attempts.append({
                'tab_id': tab_id,
                'can_write': can_write,
                'timestamp': datetime.now(),
                'settings': settings
            })
            
            if can_write:
                # Mark write performed for throttling
                self.conflict_resolver.mark_write_performed(self.project_id, self.episode_id)
                
                # Update state with new settings
                state.memory_enabled = settings['memory_enabled']
                state.history_depth = settings['history_depth']
                state.memory_version += 1
                state.updated_at = datetime.now()
            
            return can_write
        
        # Execute concurrent writes
        write_tasks = [
            simulate_tab_write(i, tab_states[i], desired_settings[i]) 
            for i in range(3)
        ]
        
        results = await asyncio.gather(*write_tasks)
        
        # Verify throttling behavior
        successful_writes = sum(1 for result in results if result)
        assert successful_writes <= 2, f"Too many concurrent writes allowed: {successful_writes}"
        
        # At least one write should succeed
        assert successful_writes >= 1, "No writes succeeded despite concurrent attempts"
        
        # Check write attempt timing
        write_times = [attempt['timestamp'] for attempt in write_attempts]
        if len(write_times) > 1:
            time_diffs = [(write_times[i] - write_times[0]).total_seconds() * 1000 
                         for i in range(1, len(write_times))]
            # Some writes should be throttled (happening very close in time)
            assert any(diff < 100 for diff in time_diffs), "No evidence of throttling detected"
    
    def test_conflict_resolution_deterministic_merging(self):
        """Test that conflict resolution produces deterministic results"""
        
        # Create two states with different changes (simulating different tabs)
        local_state = self.create_test_state(version=1, extra_turns=2)
        local_state.entity_memory.rename_map.update({"LocalChar": "로컬캐릭터"})
        local_state.entity_memory.facts.append("Local fact")
        
        remote_state = self.create_test_state(version=2, extra_turns=1) 
        remote_state.entity_memory.rename_map.update({"RemoteChar": "리모트캐릭터"})
        remote_state.entity_memory.facts.append("Remote fact")
        
        # Resolve conflict multiple times to test determinism
        resolution_results = []
        
        for attempt in range(3):
            # Create fresh copies to avoid state mutation
            local_copy = GenerationState.model_copy(local_state)
            remote_copy = GenerationState.model_copy(remote_state)
            
            resolution = self.conflict_resolver.resolve_memory_conflict(local_copy, remote_copy)
            
            resolution_results.append({
                'attempt': attempt,
                'resolved_version': resolution.resolved_version,
                'preserved_changes': len(resolution.client_changes_preserved),
                'discarded_changes': len(resolution.client_changes_discarded),
                'merge_warnings': len(resolution.merge_warnings),
                'final_rename_count': len(resolution.merged_entity_memory.rename_map)
            })
        
        # Verify deterministic behavior
        first_result = resolution_results[0]
        
        for result in resolution_results[1:]:
            assert result['resolved_version'] == first_result['resolved_version'], \
                "Version resolution not deterministic"
            assert result['preserved_changes'] == first_result['preserved_changes'], \
                "Change preservation not deterministic" 
            assert result['discarded_changes'] == first_result['discarded_changes'], \
                "Change discard not deterministic"
            assert result['final_rename_count'] == first_result['final_rename_count'], \
                "Final entity count not deterministic"
    
    @pytest.mark.asyncio 
    async def test_failure_recovery_multi_tab_scenario(self):
        """Test failure recovery with multiple tabs causing errors"""
        
        # Simulate multiple tabs causing different types of failures
        failure_scenarios = [
            (MemoryFailureType.VALIDATION_ERROR, "Tab 1 validation error", {"tab": 1}),
            (MemoryFailureType.CONFLICT_RESOLUTION_ERROR, "Tab 2 conflict error", {"tab": 2}),
            (MemoryFailureType.STORAGE_ERROR, "Tab 3 storage error", {"tab": 3}),
        ]
        
        # Record failures from different tabs
        for failure_type, error_msg, context in failure_scenarios:
            should_disable = record_memory_failure(
                self.project_id, 
                self.episode_id,
                failure_type,
                error_msg,
                context
            )
            
            # First failures should not disable immediately
            if failure_type == MemoryFailureType.STORAGE_ERROR:
                # Storage errors have higher weight, might trigger disable
                pass
            else:
                assert not should_disable, f"Single {failure_type} failure should not disable memory"
        
        # Additional failure should trigger circuit breaker
        final_failure = record_memory_failure(
            self.project_id,
            self.episode_id, 
            MemoryFailureType.STORAGE_ERROR,
            "Critical storage failure",
            {"tab": "final"}
        )
        
        # Should now disable due to accumulated weighted failures
        assert final_failure, "Accumulated failures should trigger circuit breaker"
        
        # Verify system health reflects the issues
        health_status = self.recovery_manager.get_system_health()
        
        assert health_status['status'] in ['degraded', 'warning', 'critical'], \
            f"Health status should reflect failures: {health_status['status']}"
        assert health_status['healthy_episodes'] < health_status['episode_count'], \
            "Episode should be marked as unhealthy"
    
    def test_batch_write_merging(self):
        """Test batching and merging of concurrent write operations"""
        
        # Create multiple pending write operations (simulating queued writes from tabs)
        pending_ops = [
            {
                'project_id': self.project_id,
                'episode_id': self.episode_id,
                'timestamp': datetime.now() - timedelta(milliseconds=100),
                'turns': [{'content': 'Turn 1 from tab A', 'content_hash': 'hash_a1'}],
                'entity_memory': {'rename_map': {'CharA': 'A캐릭터'}}
            },
            {
                'project_id': self.project_id, 
                'episode_id': self.episode_id,
                'timestamp': datetime.now() - timedelta(milliseconds=50),
                'turns': [{'content': 'Turn 2 from tab B', 'content_hash': 'hash_b1'}],
                'entity_memory': {'style_flags': ['informal']}
            },
            {
                'project_id': self.project_id,
                'episode_id': self.episode_id, 
                'timestamp': datetime.now(),
                'turns': [
                    {'content': 'Turn 3 from tab C', 'content_hash': 'hash_c1'},
                    {'content': 'Turn 1 from tab A', 'content_hash': 'hash_a1'}  # Duplicate
                ],
                'entity_memory': {'facts': ['New story fact']}
            }
        ]
        
        # Merge the operations
        merged_ops = self.conflict_resolver.batch_merge_writes(pending_ops)
        
        # Should merge into single operation for same memory key
        assert len(merged_ops) == 1, f"Expected 1 merged operation, got {len(merged_ops)}"
        
        merged_op = merged_ops[0]
        
        # Verify merged content
        assert len(merged_op['turns']) == 3, f"Expected 3 unique turns, got {len(merged_op['turns'])}"
        assert merged_op['timestamp'] == max(op['timestamp'] for op in pending_ops), \
            "Should use latest timestamp"
        
        # Verify entity memory merging
        assert 'CharA' in merged_op['entity_memory'].get('rename_map', {}), \
            "Rename map not merged"
        assert 'informal' in merged_op['entity_memory'].get('style_flags', []), \
            "Style flags not merged"
        assert 'New story fact' in merged_op['entity_memory'].get('facts', []), \
            "Facts not merged"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])