"""
Memory compression service with decision log extraction.
Implements policies for compressing conversation history while preserving key decisions.
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from ..models.memory import (
    ConversationTurn, 
    EntityMemory, 
    GenerationState, 
    MemoryCompressionResult,
    MemoryCompressionPolicy
)

logger = logging.getLogger(__name__)


class DecisionExtractor:
    """Extracts key decisions and preferences from conversation turns"""
    
    # Patterns for identifying different types of decisions
    RENAME_PATTERNS = [
        r"(?:change|rename|call)\s+(?:the\s+)?(\w+)\s+(?:to|as)\s+(\w+)",
        r"(\w+)\s+(?:should be|is now)\s+(?:called|named)\s+(\w+)",
        r"let'?s\s+(?:call|name)\s+(\w+)\s+(\w+)",
    ]
    
    STYLE_PATTERNS = [
        r"(?:make it|should be|write in a?)\s+(more\s+)?(\w+(?:\s+\w+)*)\s+(?:style|tone|way)",
        r"(?:tone|style|mood|feel)(?:\s+should)?\s+(?:be|is)\s+((?:\w+\s*){1,3})",
        r"(?:more|less|very)\s+(\w+(?:\s+\w+)*)",
    ]
    
    CHARACTER_PATTERNS = [
        r"(\w+)\s+(?:is|should be)\s+(?:a|an|the)\s+((?:\w+\s*){1,4})",
        r"(\w+)'?s?\s+(?:character|personality|trait)s?\s+(?:is|are|should be)\s+((?:\w+\s*){1,4})",
    ]
    
    SETTING_PATTERNS = [
        r"(?:set in|takes? place in|located in|happening in)\s+((?:\w+\s*){1,5})",
        r"(?:the\s+)?(?:setting|location|scene)\s+(?:is|should be)\s+((?:\w+\s*){1,5})",
    ]
    
    def __init__(self, min_decision_score: float = 0.6):
        self.min_decision_score = min_decision_score
        
        # Compile patterns for performance
        self.rename_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.RENAME_PATTERNS]
        self.style_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.STYLE_PATTERNS]
        self.character_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.CHARACTER_PATTERNS]
        self.setting_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.SETTING_PATTERNS]
    
    def extract_renames(self, text: str) -> List[Tuple[str, str]]:
        """Extract character/entity rename decisions"""
        renames = []
        
        for pattern in self.rename_regex:
            matches = pattern.findall(text)
            for match in matches:
                if isinstance(match, tuple) and len(match) == 2:
                    old_name, new_name = match
                    if old_name.lower() != new_name.lower():
                        renames.append((old_name.strip(), new_name.strip()))
        
        return renames
    
    def extract_style_preferences(self, text: str) -> List[str]:
        """Extract style and tone preferences"""
        preferences = []
        
        for pattern in self.style_regex:
            matches = pattern.findall(text)
            for match in matches:
                if isinstance(match, tuple):
                    # Take the non-empty part of the match
                    style = next((part for part in match if part.strip()), "")
                else:
                    style = match
                
                if style and len(style.strip()) > 2:
                    preferences.append(style.strip().lower())
        
        return preferences
    
    def extract_character_facts(self, text: str) -> List[str]:
        """Extract character-related facts"""
        facts = []
        
        for pattern in self.character_regex:
            matches = pattern.findall(text)
            for match in matches:
                if isinstance(match, tuple) and len(match) == 2:
                    character, trait = match
                    fact = f"{character.strip()} is {trait.strip()}"
                    facts.append(fact)
        
        return facts
    
    def extract_setting_facts(self, text: str) -> List[str]:
        """Extract setting-related facts"""
        facts = []
        
        for pattern in self.setting_regex:
            matches = pattern.findall(text)
            for match in matches:
                setting = match if isinstance(match, str) else match[0] if match else ""
                if setting and len(setting.strip()) > 3:
                    facts.append(f"Setting: {setting.strip()}")
        
        return facts
    
    def calculate_decision_score(self, turn: ConversationTurn) -> float:
        """Calculate importance score for a conversation turn"""
        content = turn.content.lower()
        score = 0.0
        
        # Source weight (UI interactions typically more important)
        if turn.source.value == 'ui':
            score += 0.3
        elif turn.source.value == 'api':
            score += 0.2
        
        # Decision keywords
        decision_keywords = [
            'change', 'rename', 'call', 'should be', 'make it', 'instead',
            'replace', 'update', 'modify', 'adjust', 'fix'
        ]
        
        for keyword in decision_keywords:
            if keyword in content:
                score += 0.2
        
        # Style keywords
        style_keywords = [
            'tone', 'style', 'mood', 'feel', 'atmosphere', 'dramatic', 
            'comedic', 'serious', 'lighthearted', 'formal', 'casual'
        ]
        
        for keyword in style_keywords:
            if keyword in content:
                score += 0.15
        
        # Character/entity keywords
        entity_keywords = [
            'character', 'protagonist', 'antagonist', 'narrator', 'voice'
        ]
        
        for keyword in entity_keywords:
            if keyword in content:
                score += 0.1
        
        # Length factor (longer content might be more important)
        if len(content) > 100:
            score += 0.1
        elif len(content) > 50:
            score += 0.05
        
        # Selection context (UI selections are important)
        if turn.selection:
            score += 0.2
        
        return min(score, 1.0)
    
    def extract_all_decisions(self, turns: List[ConversationTurn]) -> Tuple[List[str], Dict[str, str], List[str]]:
        """Extract all decisions from turns, returning (decisions, renames, style_flags)"""
        decisions = []
        rename_map = {}
        style_flags = set()
        
        for turn in turns:
            score = self.calculate_decision_score(turn)
            
            if score >= self.min_decision_score:
                # Extract specific decision types
                renames = self.extract_renames(turn.content)
                styles = self.extract_style_preferences(turn.content)
                char_facts = self.extract_character_facts(turn.content)
                setting_facts = self.extract_setting_facts(turn.content)
                
                # Add to accumulated data
                for old_name, new_name in renames:
                    rename_map[old_name] = new_name
                    decisions.append(f"Rename: {old_name} → {new_name}")
                
                for style in styles:
                    style_flags.add(style)
                    decisions.append(f"Style: {style}")
                
                for fact in char_facts + setting_facts:
                    decisions.append(fact)
                
                # General decision if no specific patterns matched
                if not (renames or styles or char_facts or setting_facts):
                    decisions.append(f"Decision: {turn.content[:80]}...")
        
        return decisions, rename_map, list(style_flags)


class MemoryCompressor:
    """Compresses conversation history using decision extraction"""
    
    def __init__(self, policy: Optional[MemoryCompressionPolicy] = None):
        self.policy = policy or MemoryCompressionPolicy()
        self.extractor = DecisionExtractor(self.policy.min_decision_score)
    
    def needs_compression(self, state: GenerationState) -> bool:
        """Check if state needs compression"""
        if not state.memory_enabled:
            return False
        
        return len(state.history) > self.policy.max_turns
    
    def compress_memory(self, state: GenerationState) -> MemoryCompressionResult:
        """Compress memory state and return result"""
        
        if not self.needs_compression(state):
            logger.info("Memory compression not needed")
            return MemoryCompressionResult(
                decision_log=[],
                compressed_turn_count=0,
                updated_entity_memory=state.entity_memory,
                tokens_before=0,
                tokens_after=0,
                tokens_saved=0
            )
        
        logger.info(f"Starting memory compression for {len(state.history)} turns")
        
        # Sort turns by timestamp
        sorted_turns = sorted(state.history, key=lambda t: t.created_at)
        
        # Separate recent turns from older ones
        recent_turns = sorted_turns[-self.policy.preserve_recent_turns:]
        older_turns = sorted_turns[:-self.policy.preserve_recent_turns]
        
        # Calculate tokens before compression
        tokens_before = self._estimate_history_tokens(state.history)
        
        # Extract decisions from older turns
        decisions, new_renames, new_style_flags = self.extractor.extract_all_decisions(older_turns)
        
        # Update entity memory
        updated_entity_memory = self._merge_entity_memory(
            state.entity_memory,
            new_renames,
            new_style_flags,
            decisions
        )
        
        # Update state with compressed history
        state.history = recent_turns
        state.entity_memory = updated_entity_memory
        state.history_compacted = True
        state.updated_at = datetime.now()
        
        # Calculate tokens after compression
        tokens_after = self._estimate_history_tokens(recent_turns)
        tokens_saved = tokens_before - tokens_after
        
        result = MemoryCompressionResult(
            decision_log=decisions,
            compressed_turn_count=len(older_turns),
            updated_entity_memory=updated_entity_memory,
            tokens_before=tokens_before,
            tokens_after=tokens_after,
            tokens_saved=tokens_saved
        )
        
        logger.info(f"Memory compression completed: {len(older_turns)} turns → "
                   f"{len(decisions)} decisions, {tokens_saved} tokens saved")
        
        return result
    
    def _estimate_history_tokens(self, turns: List[ConversationTurn]) -> int:
        """Estimate token count for conversation turns"""
        total_chars = sum(len(turn.content) for turn in turns)
        return total_chars // 4  # Rough estimation
    
    def _merge_entity_memory(self, 
                           existing_memory: EntityMemory,
                           new_renames: Dict[str, str],
                           new_style_flags: List[str],
                           decisions: List[str]) -> EntityMemory:
        """Merge new information into existing entity memory"""
        
        # Start with existing memory
        updated_rename_map = dict(existing_memory.rename_map)
        updated_style_flags = list(existing_memory.style_flags)
        updated_facts = list(existing_memory.facts)
        
        # Add new renames (newer takes precedence)
        for old_name, new_name in new_renames.items():
            updated_rename_map[old_name] = new_name
        
        # Add new style flags (deduplicate)
        for flag in new_style_flags:
            if flag not in updated_style_flags:
                updated_style_flags.append(flag)
        
        # Add decision-based facts (deduplicate and limit)
        decision_facts = [d for d in decisions if not d.startswith(('Rename:', 'Style:'))]
        for fact in decision_facts:
            if fact not in updated_facts:
                updated_facts.append(fact)
        
        # Limit facts to prevent unbounded growth
        MAX_FACTS = 20
        if len(updated_facts) > MAX_FACTS:
            # Keep most recent facts
            updated_facts = updated_facts[-MAX_FACTS:]
        
        # Limit style flags
        MAX_STYLE_FLAGS = 10
        if len(updated_style_flags) > MAX_STYLE_FLAGS:
            updated_style_flags = updated_style_flags[-MAX_STYLE_FLAGS:]
        
        return EntityMemory(
            rename_map=updated_rename_map,
            style_flags=updated_style_flags,
            facts=updated_facts
        )


class MemoryCompressionService:
    """High-level service for managing memory compression"""
    
    def __init__(self):
        self.compressor = MemoryCompressor()
    
    def auto_compress_if_needed(self, state: GenerationState) -> Optional[MemoryCompressionResult]:
        """Automatically compress memory if needed"""
        if not self.compressor.needs_compression(state):
            return None
        
        try:
            return self.compressor.compress_memory(state)
        except Exception as e:
            logger.error(f"Memory compression failed: {e}", exc_info=True)
            return None
    
    def force_compress(self, state: GenerationState, 
                      preserve_turns: Optional[int] = None) -> MemoryCompressionResult:
        """Force memory compression regardless of policy"""
        
        # Temporarily override policy if needed
        original_preserve = self.compressor.policy.preserve_recent_turns
        if preserve_turns is not None:
            self.compressor.policy.preserve_recent_turns = preserve_turns
        
        try:
            # Temporarily force compression by setting max_turns to 0
            original_max = self.compressor.policy.max_turns
            self.compressor.policy.max_turns = preserve_turns or original_preserve
            
            result = self.compressor.compress_memory(state)
            
            # Restore original policy
            self.compressor.policy.max_turns = original_max
            
            return result
            
        except Exception as e:
            logger.error(f"Forced memory compression failed: {e}", exc_info=True)
            raise
        finally:
            # Restore original preserve count
            self.compressor.policy.preserve_recent_turns = original_preserve
    
    def preview_compression(self, state: GenerationState) -> Dict[str, Any]:
        """Preview what would happen during compression without actually doing it"""
        
        if not self.compressor.needs_compression(state):
            return {
                'needs_compression': False,
                'current_turns': len(state.history),
                'max_allowed': self.compressor.policy.max_turns
            }
        
        # Sort turns by timestamp
        sorted_turns = sorted(state.history, key=lambda t: t.created_at)
        
        # Separate recent turns from older ones
        recent_turns = sorted_turns[-self.compressor.policy.preserve_recent_turns:]
        older_turns = sorted_turns[:-self.compressor.policy.preserve_recent_turns]
        
        # Extract decisions from older turns (without modifying state)
        decisions, new_renames, new_style_flags = self.compressor.extractor.extract_all_decisions(older_turns)
        
        # Calculate potential token savings
        tokens_before = self.compressor._estimate_history_tokens(state.history)
        tokens_after = self.compressor._estimate_history_tokens(recent_turns)
        tokens_saved = tokens_before - tokens_after
        
        return {
            'needs_compression': True,
            'current_turns': len(state.history),
            'turns_to_compress': len(older_turns),
            'turns_to_preserve': len(recent_turns),
            'decisions_extracted': len(decisions),
            'new_renames': len(new_renames),
            'new_style_flags': len(new_style_flags),
            'tokens_before': tokens_before,
            'tokens_after': tokens_after,
            'tokens_saved': tokens_saved,
            'sample_decisions': decisions[:5]  # First 5 decisions as preview
        }