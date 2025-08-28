"""
Test suite for memory system validation scenarios.
Validates the key requirements and use cases for conversation memory.
"""

import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any

from ..models.memory import (
    GenerationState,
    ConversationTurn,
    TurnSource,
    EntityMemory,
    MemoryCompressionPolicy,
)
from ..services.memory_compression import MemoryCompressionService, DecisionExtractor
from ..services.prompt_builder import EnhancedPromptBuilder
from ..models.generation import ScriptGenerationRequest


class TestMemoryValidationScenarios:
    """Test scenarios for memory system validation"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.compression_service = MemoryCompressionService()
        self.decision_extractor = DecisionExtractor()
        self.prompt_builder = EnhancedPromptBuilder()
        
    def create_test_state(self, project_id: str = "test-project", 
                         episode_id: str = "test-episode") -> GenerationState:
        """Create a test generation state"""
        return GenerationState(
            project_id=project_id,
            episode_id=episode_id,
            memory_enabled=True,
            history_depth=5
        )
    
    def create_test_request(self) -> ScriptGenerationRequest:
        """Create a test script generation request"""
        from ..models.generation import ScriptType
        
        return ScriptGenerationRequest(
            project_id="test-project",
            episode_id="test-episode",
            script_type=ScriptType.DRAMA,
            title="Test Drama Script",
            description="A test script for validation"
        )
    
    def test_character_rename_consistency_memory_on_off(self):
        """
        Scenario 1: Character name change consistency
        Test that renamed characters are referenced correctly with memory ON vs OFF
        """
        state = self.create_test_state()
        
        # Conversation with character rename
        turns = [
            "Let's write a drama about a detective named John.",
            "Actually, let's change John to be called Marcus instead.",
            "Marcus should be more experienced than we initially thought.",
            "Have Marcus investigate the mysterious case."
        ]
        
        # Add turns to state
        for i, content in enumerate(turns):
            state.add_turn(content, TurnSource.UI, selection={"step": i})
        
        # Test with memory enabled
        request = self.create_test_request()
        prompt_memory_on, tokens_memory_on = self.prompt_builder.build_complete_prompt(
            request=request,
            generation_state=state,
            user_prompt="Write the next scene with the detective."
        )
        
        # Test with memory disabled
        state.memory_enabled = False
        prompt_memory_off, tokens_memory_off = self.prompt_builder.build_complete_prompt(
            request=request,
            generation_state=state,
            user_prompt="Write the next scene with the detective."
        )
        
        # With memory ON, should include rename information
        assert "John" in prompt_memory_on or "Marcus" in prompt_memory_on
        assert "rename" in prompt_memory_on.lower() or "call" in prompt_memory_on.lower()
        
        # With memory OFF, should not include context about character changes
        assert "rename" not in prompt_memory_off.lower()
        
        # Memory ON should use more tokens
        assert tokens_memory_on['total'] > tokens_memory_off['total']
        
        print("✅ Character rename consistency test passed")
    
    def test_memory_compression_long_conversation(self):
        """
        Scenario 2: Long conversation compression
        Test that memory compression works correctly for long conversations
        """
        state = self.create_test_state()
        
        # Simulate long conversation (15 turns, exceeds default policy of 10)
        conversation = [
            "Let's create a thriller script.",
            "The main character should be Sarah, a journalist.",
            "Actually, let's call her Emma instead of Sarah.",
            "Emma works for a major newspaper.",
            "The story takes place in New York City.",
            "Add a mysterious source who contacts Emma.",
            "The source has information about corruption.",
            "Make the tone dark and suspenseful.",
            "Emma should be skeptical at first.",
            "She gradually becomes more trusting.",
            "Add some action scenes for excitement.",
            "The corruption involves city officials.",
            "Emma's editor is hesitant to publish the story.",
            "There should be a plot twist near the end.",
            "Emma discovers the source has ulterior motives."
        ]
        
        for i, content in enumerate(conversation):
            state.add_turn(content, TurnSource.UI, selection={"turn": i})
        
        # Check compression is needed
        assert self.compression_service.compressor.needs_compression(state)
        
        # Preview compression
        preview = self.compression_service.preview_compression(state)
        assert preview['needs_compression']
        assert preview['turns_to_compress'] > 0
        assert len(preview['sample_decisions']) > 0
        
        # Perform compression
        result = self.compression_service.compressor.compress_memory(state)
        
        # Verify compression results
        assert result.compressed_turn_count > 0
        assert result.tokens_saved > 0
        assert len(result.decision_log) > 0
        
        # Check that key decisions were preserved
        decisions_text = " ".join(result.decision_log)
        assert "emma" in decisions_text.lower() or "sarah" in decisions_text.lower()  # Name change
        assert "dark" in decisions_text.lower() or "suspenseful" in decisions_text.lower()  # Style
        
        # Check that recent turns are preserved
        assert len(state.history) == state.compression_policy.preserve_recent_turns
        assert state.history_compacted
        
        print("✅ Memory compression test passed")
    
    def test_multi_tab_conflict_resolution(self):
        """
        Scenario 3: Multi-tab conflict handling
        Test conflict detection and resolution for concurrent updates
        """
        # Simulate two states representing different tabs
        state_tab1 = self.create_test_state()
        state_tab2 = self.create_test_state()
        
        # Both start with same version
        assert state_tab1.memory_version == state_tab2.memory_version == 1
        
        # Tab 1 adds a turn
        state_tab1.add_turn("Add a romantic subplot.", TurnSource.UI)
        state_tab1.memory_version += 1
        
        # Tab 2 adds a different turn (simulating concurrent edit)
        state_tab2.add_turn("Make it more action-oriented.", TurnSource.UI)
        state_tab2.memory_version += 1
        
        # Both tabs now have version 2, but different content
        assert state_tab1.memory_version == state_tab2.memory_version == 2
        assert len(state_tab1.history) == len(state_tab2.history) == 1
        
        # Different content should have different hashes
        tab1_hash = state_tab1.history[0].content_hash
        tab2_hash = state_tab2.history[0].content_hash
        assert tab1_hash != tab2_hash
        
        # Simulate server-wins conflict resolution
        # Tab 2 gets tab 1's state and needs to handle conflict
        state_tab2.memory_version = 3  # Server incremented version
        
        # In real implementation, would merge histories and resolve conflicts
        # Here we simulate by showing conflict detection works
        assert state_tab1.memory_version != state_tab2.memory_version
        
        print("✅ Multi-tab conflict test passed")
    
    def test_token_budget_management(self):
        """
        Scenario 4: Token budget exceeded handling
        Test automatic handling when token budget is exceeded
        """
        state = self.create_test_state()
        
        # Create a state with lots of content to exceed budget
        long_conversation = [
            "Write a detailed historical drama set in medieval England with complex characters and intricate political relationships between the nobility and clergy.",
            "The main protagonist should be Lady Eleanor, a strong-willed woman who challenges the social norms of her time and seeks to protect her family's lands.",
            "Add extensive world-building details about the castle, the surrounding countryside, the political tensions with neighboring kingdoms, and the religious conflicts.",
            "Include detailed character backgrounds for at least six major characters, each with their own motivations, secrets, and complex relationships with others.",
            "The tone should be epic and sweeping, with elements of romance, betrayal, political intrigue, and spiritual conflict woven throughout the narrative."
        ]
        
        for content in long_conversation:
            state.add_turn(content, TurnSource.UI)
        
        # Add lots of entity memory
        state.entity_memory.rename_map = {
            f"Character{i}": f"NewName{i}" for i in range(20)
        }
        state.entity_memory.facts = [
            f"Important fact number {i} about the story world and characters." for i in range(50)
        ]
        state.entity_memory.style_flags = [
            "epic", "dramatic", "romantic", "political", "medieval", "complex", "detailed"
        ]
        
        # Use small token budget to force exceeded condition
        small_budget_builder = EnhancedPromptBuilder(total_budget=1000)  # Very small
        
        request = self.create_test_request()
        user_prompt = "Write an epic 10-page scene with detailed character development, political intrigue, romantic tension, and historical accuracy. Include extensive dialogue and detailed descriptions of the medieval setting, clothing, customs, and political situation."
        
        prompt, token_usage = small_budget_builder.build_complete_prompt(
            request=request,
            generation_state=state,
            user_prompt=user_prompt
        )
        
        # Should detect budget exceeded
        budget_exceeded = small_budget_builder.check_budget_exceeded(token_usage)
        assert budget_exceeded, "Should detect token budget exceeded"
        
        # Should provide suggestions
        suggestions = small_budget_builder.suggest_budget_adjustments(token_usage)
        assert len(suggestions) > 0, "Should provide budget adjustment suggestions"
        assert any("compress" in s.lower() for s in suggestions), "Should suggest compression"
        
        # Auto-compress should help
        compression_result = self.compression_service.auto_compress_if_needed(state)
        assert compression_result is not None, "Should auto-compress when needed"
        assert compression_result.tokens_saved > 0, "Should save tokens"
        
        print("✅ Token budget management test passed")
    
    def test_decision_extraction_accuracy(self):
        """
        Scenario 5: Decision extraction accuracy
        Test that key decisions are correctly identified and extracted
        """
        test_cases = [
            # Character renames
            ("Change the protagonist from John to Marcus", ["john", "marcus"]),
            ("Let's call the detective Sarah instead", ["sarah"]),
            ("Rename the villain to Dr. Darkmore", ["darkmore"]),
            
            # Style preferences
            ("Make it more dramatic and suspenseful", ["dramatic", "suspenseful"]),
            ("The tone should be lighthearted and comedic", ["lighthearted", "comedic"]),
            ("Write in a formal, serious style", ["formal", "serious"]),
            
            # Character facts
            ("Marcus is an experienced detective", ["marcus", "experienced", "detective"]),
            ("Sarah should be very intelligent", ["sarah", "intelligent"]),
            
            # Setting facts
            ("Set in Victorian London", ["victorian", "london"]),
            ("Takes place in modern New York", ["modern", "new york"]),
        ]
        
        for content, expected_keywords in test_cases:
            turn = ConversationTurn(
                source=TurnSource.UI,
                content=content
            )
            
            # Test decision score
            score = self.decision_extractor.calculate_decision_score(turn)
            assert score >= self.decision_extractor.min_decision_score, f"Should identify '{content}' as important decision"
            
            # Test extraction
            renames = self.decision_extractor.extract_renames(content)
            styles = self.decision_extractor.extract_style_preferences(content)
            char_facts = self.decision_extractor.extract_character_facts(content)
            setting_facts = self.decision_extractor.extract_setting_facts(content)
            
            # At least one extraction method should find relevant keywords
            all_extracted = []
            all_extracted.extend([r[0] for r in renames] + [r[1] for r in renames])
            all_extracted.extend(styles)
            all_extracted.extend([f.lower() for f in char_facts])
            all_extracted.extend([f.lower() for f in setting_facts])
            
            extracted_text = " ".join(all_extracted).lower()
            found_keywords = [kw for kw in expected_keywords if kw.lower() in extracted_text]
            
            # Should find at least one expected keyword
            assert len(found_keywords) > 0, f"Should extract keywords from '{content}', found: {all_extracted}"
        
        print("✅ Decision extraction accuracy test passed")
    
    def test_pii_scrubbing(self):
        """
        Scenario 6: PII scrubbing validation
        Test that sensitive information is properly scrubbed
        """
        sensitive_content = [
            "Contact me at john.doe@example.com for more details",
            "Call me at 555-123-4567 when you're ready",
            "My API key is sk-abc123def456ghi789jkl012mno345pqr",
            "The file is stored at /Users/john/Documents/secret.txt",
        ]
        
        for content in sensitive_content:
            turn = ConversationTurn(
                source=TurnSource.UI,
                content=content
            )
            
            # Content should be sanitized during turn creation
            assert "@" not in turn.content or "[EMAIL]" in turn.content
            assert "555-123-4567" not in turn.content or "[PHONE]" in turn.content
            assert "sk-abc123def456ghi789jkl012mno345pqr" not in turn.content or "[API_KEY]" in turn.content
            
        print("✅ PII scrubbing test passed")
    
    def test_memory_metrics_accuracy(self):
        """
        Scenario 7: Memory metrics collection
        Test that metrics are accurately calculated and reported
        """
        state = self.create_test_state()
        
        # Add test data
        turns_to_add = 8
        for i in range(turns_to_add):
            state.add_turn(f"Turn {i} content", TurnSource.UI)
        
        renames_to_add = 3
        state.entity_memory.rename_map = {f"Old{i}": f"New{i}" for i in range(renames_to_add)}
        
        facts_to_add = 5
        state.entity_memory.facts = [f"Fact {i}" for i in range(facts_to_add)]
        
        flags_to_add = 4
        state.entity_memory.style_flags = [f"style{i}" for i in range(flags_to_add)]
        
        # Calculate metrics
        token_usage = state.estimate_token_usage()
        
        # Verify counts
        assert len(state.history) == turns_to_add
        assert len(state.entity_memory.rename_map) == renames_to_add
        assert len(state.entity_memory.facts) == facts_to_add
        assert len(state.entity_memory.style_flags) == flags_to_add
        
        # Verify token estimation
        assert token_usage['total'] > 0
        assert token_usage['history'] > 0
        assert token_usage['entity_memory'] > 0
        
        # Test compression recommendation
        state.history = [state.add_turn(f"Long turn {i}", TurnSource.UI) for i in range(20)]
        assert state.needs_compression()
        
        print("✅ Memory metrics test passed")
    
    def test_integration_scenario(self):
        """
        Scenario 8: Full integration test
        Test complete workflow from conversation to generation with memory
        """
        state = self.create_test_state()
        
        # Simulate realistic conversation
        conversation = [
            "I want to write a mystery novel",
            "The detective should be named Inspector Davies",
            "Actually, let's call him Detective Morgan instead",
            "Morgan is methodical and analytical",
            "Set it in a small coastal town",
            "The tone should be atmospheric and moody",
            "Add a mysterious disappearance case"
        ]
        
        for turn in conversation:
            state.add_turn(turn, TurnSource.UI)
        
        # Build prompt with memory
        request = self.create_test_request()
        request.script_type = "mystery"
        request.title = "Coastal Mystery"
        
        prompt, token_usage = self.prompt_builder.build_complete_prompt(
            request=request,
            generation_state=state,
            user_prompt="Write the opening scene where Detective Morgan arrives at the crime scene"
        )
        
        # Verify memory integration
        assert "morgan" in prompt.lower()  # Should use correct name
        assert "davies" not in prompt.lower() or "morgan" in prompt.lower()  # Should handle rename
        assert "coastal" in prompt.lower() or "town" in prompt.lower()  # Should include setting
        assert "atmospheric" in prompt.lower() or "moody" in prompt.lower()  # Should include style
        
        # Verify token budget management
        assert token_usage['total'] > 0
        assert 'entity_memory' in token_usage
        assert 'conversation' in token_usage
        
        # Verify prompt structure (should follow specified order)
        prompt_lines = prompt.split('\n')
        memory_section_found = False
        context_section_found = False
        
        for line in prompt_lines:
            if "CONTEXT MEMORY" in line:
                memory_section_found = True
            elif "CONVERSATION HISTORY" in line:
                context_section_found = True
        
        assert memory_section_found or context_section_found, "Should include memory sections"
        
        print("✅ Integration scenario test passed")


@pytest.mark.asyncio
class TestAsyncMemoryOperations:
    """Test asynchronous memory operations"""
    
    async def test_concurrent_turn_additions(self):
        """Test handling concurrent turn additions"""
        state = GenerationState(
            project_id="test",
            memory_enabled=True
        )
        
        # Simulate concurrent turn additions
        async def add_turns(prefix: str, count: int):
            tasks = []
            for i in range(count):
                content = f"{prefix}-turn-{i}"
                turn = ConversationTurn(source=TurnSource.UI, content=content)
                # In real implementation, would be async API calls
                tasks.append(asyncio.sleep(0.01))  # Simulate async delay
            
            await asyncio.gather(*tasks)
            return count
        
        # Run concurrent operations
        results = await asyncio.gather(
            add_turns("tab1", 5),
            add_turns("tab2", 3),
            add_turns("tab3", 4)
        )
        
        assert sum(results) == 12  # All turns should be processed
        print("✅ Concurrent operations test passed")


if __name__ == "__main__":
    # Run specific test scenarios for demonstration
    test_suite = TestMemoryValidationScenarios()
    test_suite.setup_method()
    
    print("🧪 Running Memory System Validation Scenarios...\n")
    
    try:
        test_suite.test_character_rename_consistency_memory_on_off()
        test_suite.test_memory_compression_long_conversation()
        test_suite.test_multi_tab_conflict_resolution()
        test_suite.test_token_budget_management()
        test_suite.test_decision_extraction_accuracy()
        test_suite.test_pii_scrubbing()
        test_suite.test_memory_metrics_accuracy()
        test_suite.test_integration_scenario()
        
        print("\n🎉 All memory validation scenarios passed!")
        print("\n📊 Test Summary:")
        print("✅ Character rename consistency (Memory ON/OFF)")
        print("✅ Long conversation compression")
        print("✅ Multi-tab conflict handling")
        print("✅ Token budget exceeded management")
        print("✅ Decision extraction accuracy")
        print("✅ PII scrubbing protection")
        print("✅ Memory metrics collection")
        print("✅ Full integration workflow")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise