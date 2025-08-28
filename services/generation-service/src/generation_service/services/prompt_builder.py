"""
Prompt builder with token budget management and memory integration.
Implements the specified prompt ordering and token allocation policies.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from ..models.memory import GenerationState, MemoryCompressionPolicy, ConversationTurn, EntityMemory
from ..models.generation import ScriptGenerationRequest

logger = logging.getLogger(__name__)


class TokenBudgetManager:
    """Manages token allocation across different prompt components"""
    
    def __init__(self, total_budget: int = 4000, policy: Optional[MemoryCompressionPolicy] = None):
        self.total_budget = total_budget
        self.policy = policy or MemoryCompressionPolicy()
        
        # Calculate allocations based on percentages
        self.memory_budget = int(self.total_budget * self.policy.memory_token_budget_pct / 100)
        self.rag_budget = int(self.total_budget * self.policy.rag_token_budget_pct / 100)
        self.user_min_budget = int(self.total_budget * self.policy.user_prompt_min_pct / 100)
        
        # Remaining budget for system prompt and other components
        self.system_budget = self.total_budget - self.memory_budget - self.rag_budget - self.user_min_budget
        
        logger.debug(f"Token budget allocation: memory={self.memory_budget}, rag={self.rag_budget}, "
                    f"user_min={self.user_min_budget}, system={self.system_budget}, total={self.total_budget}")
    
    def estimate_tokens(self, text: str) -> int:
        """Rough token estimation: ~4 chars per token"""
        if not text:
            return 0
        return len(text) // 4
    
    def fits_in_budget(self, text: str, budget: int) -> bool:
        """Check if text fits within token budget"""
        return self.estimate_tokens(text) <= budget
    
    def truncate_to_budget(self, text: str, budget: int) -> str:
        """Truncate text to fit within token budget"""
        if self.fits_in_budget(text, budget):
            return text
        
        # Simple truncation - could be improved with sentence boundaries
        target_chars = budget * 4
        if len(text) <= target_chars:
            return text
        
        truncated = text[:target_chars - 20] + "...[truncated]"
        logger.warning(f"Text truncated from {len(text)} to {len(truncated)} chars to fit {budget} token budget")
        return truncated


class MemoryPromptBuilder:
    """Builds memory-aware prompts from entity memory and conversation history"""
    
    def __init__(self, budget_manager: TokenBudgetManager):
        self.budget_manager = budget_manager
    
    def build_entity_memory_prompt(self, entity_memory: EntityMemory) -> str:
        """Build prompt section from structured entity memory"""
        if not entity_memory:
            return ""
        
        sections = []
        
        # Character rename mappings
        if entity_memory.rename_map:
            renames = [f"- {old} → {new}" for old, new in entity_memory.rename_map.items()]
            sections.append("Character Names:\n" + "\n".join(renames))
        
        # Style preferences
        if entity_memory.style_flags:
            sections.append("Style Guidelines:\n" + "\n".join(f"- {flag}" for flag in entity_memory.style_flags))
        
        # Important facts
        if entity_memory.facts:
            sections.append("Key Facts:\n" + "\n".join(f"- {fact}" for fact in entity_memory.facts))
        
        if not sections:
            return ""
        
        prompt = "=== CONTEXT MEMORY ===\n" + "\n\n".join(sections) + "\n"
        
        # Ensure it fits in memory budget
        return self.budget_manager.truncate_to_budget(prompt, self.budget_manager.memory_budget // 2)
    
    def build_conversation_summary(self, turns: List[ConversationTurn], preserve_count: int = 2) -> str:
        """Build conversation summary from turns, preserving recent ones"""
        if not turns:
            return ""
        
        # Sort by timestamp
        sorted_turns = sorted(turns, key=lambda t: t.created_at)
        
        # Separate recent turns from older ones
        recent_turns = sorted_turns[-preserve_count:] if preserve_count > 0 else []
        older_turns = sorted_turns[:-preserve_count] if preserve_count > 0 else sorted_turns
        
        sections = []
        
        # Summarize older turns as decisions/context
        if older_turns:
            decisions = []
            for turn in older_turns:
                # Extract key decisions and preferences
                content = turn.content.lower()
                if any(keyword in content for keyword in ['change', 'rename', 'call', 'should be']):
                    decisions.append(f"- {turn.content[:100]}...")
                elif any(keyword in content for keyword in ['style', 'tone', 'feel', 'mood']):
                    decisions.append(f"- Style: {turn.content[:80]}...")
                elif turn.source == 'ui' and turn.selection:
                    decisions.append(f"- Action: {turn.content[:80]}...")
            
            if decisions:
                sections.append("Previous Decisions:\n" + "\n".join(decisions[:5]))  # Max 5 decisions
        
        # Include recent turns verbatim
        if recent_turns:
            recent_content = []
            for turn in recent_turns:
                source_label = f"[{turn.source.upper()}]"
                recent_content.append(f"{source_label} {turn.content}")
            sections.append("Recent Context:\n" + "\n".join(recent_content))
        
        if not sections:
            return ""
        
        prompt = "=== CONVERSATION HISTORY ===\n" + "\n\n".join(sections) + "\n"
        
        # Fit in remaining memory budget
        remaining_memory_budget = self.budget_manager.memory_budget // 2
        return self.budget_manager.truncate_to_budget(prompt, remaining_memory_budget)


class RAGPromptBuilder:
    """Builds RAG context prompts with budget management"""
    
    def __init__(self, budget_manager: TokenBudgetManager):
        self.budget_manager = budget_manager
    
    def build_rag_context(self, rag_results: List[Dict[str, Any]], query: str) -> str:
        """Build RAG context from search results"""
        if not rag_results:
            return ""
        
        # Sort by relevance score if available
        sorted_results = sorted(rag_results, 
                              key=lambda x: x.get('score', 0.0), 
                              reverse=True)
        
        sections = []
        used_tokens = 0
        
        for i, result in enumerate(sorted_results):
            content = result.get('content', '')
            metadata = result.get('metadata', {})
            score = result.get('score', 0.0)
            
            # Format result
            section = f"Reference {i+1} (relevance: {score:.2f}):\n{content}\n"
            if metadata:
                section += f"Source: {metadata.get('source', 'Unknown')}\n"
            
            section_tokens = self.budget_manager.estimate_tokens(section)
            
            # Check if adding this section would exceed RAG budget
            if used_tokens + section_tokens > self.budget_manager.rag_budget:
                logger.info(f"RAG budget exhausted after {i} results ({used_tokens} tokens)")
                break
            
            sections.append(section)
            used_tokens += section_tokens
        
        if not sections:
            return ""
        
        prompt = f"=== RELEVANT CONTEXT ===\nQuery: {query}\n\n" + "\n".join(sections)
        
        return self.budget_manager.truncate_to_budget(prompt, self.budget_manager.rag_budget)


class SystemPromptBuilder:
    """Builds system prompts and user guidance"""
    
    def __init__(self, budget_manager: TokenBudgetManager):
        self.budget_manager = budget_manager
    
    def build_system_prompt(self, request: ScriptGenerationRequest) -> str:
        """Build system prompt with generation instructions"""
        
        # Base system prompt
        system_base = f"""You are an expert script writer specializing in {request.script_type.value} content.

Generate a high-quality script based on the provided requirements and context.

Title: {request.title}
Description: {request.description}

Requirements:
- Type: {request.script_type.value}
- Target length: {request.length_target or 'flexible'} words
"""
        
        # Add context requirements if available
        if hasattr(request, 'context') and request.context:
            context_reqs = []
            context = request.context
            
            if hasattr(context, 'characters') and context.characters:
                context_reqs.append(f"Characters: {len(context.characters)} defined")
            
            if hasattr(context, 'mood') and context.mood:
                context_reqs.append(f"Mood: {context.mood}")
            
            if hasattr(context, 'themes') and context.themes:
                context_reqs.append(f"Themes: {', '.join(context.themes[:3])}")  # Max 3 themes
            
            if context_reqs:
                system_base += "\nContext Requirements:\n- " + "\n- ".join(context_reqs) + "\n"
        
        # Add quality instructions
        system_base += """
Quality Standards:
- Maintain character consistency throughout
- Use natural, engaging dialogue
- Follow proper script formatting
- Create clear scene transitions
- Ensure narrative coherence

Pay special attention to any context memory and previous decisions provided.
"""
        
        return self.budget_manager.truncate_to_budget(system_base, self.budget_manager.system_budget)
    
    def build_user_guidance(self, user_prompt: str, additional_instructions: Optional[str] = None) -> str:
        """Build final user prompt with guidance"""
        
        sections = []
        
        # Main user prompt (guaranteed minimum space)
        if user_prompt:
            sections.append(f"=== GENERATION REQUEST ===\n{user_prompt}")
        
        # Additional instructions
        if additional_instructions:
            sections.append(f"=== ADDITIONAL GUIDANCE ===\n{additional_instructions}")
        
        # Closing instruction
        sections.append("Please generate the script now, incorporating all provided context and requirements.")
        
        prompt = "\n\n".join(sections)
        
        # Ensure user prompt gets its minimum allocation
        available_budget = max(self.budget_manager.user_min_budget, 
                              self.budget_manager.total_budget - 
                              self.budget_manager.memory_budget - 
                              self.budget_manager.rag_budget - 
                              self.budget_manager.system_budget)
        
        if not self.budget_manager.fits_in_budget(prompt, available_budget):
            logger.warning(f"User prompt exceeds available budget ({available_budget} tokens)")
            # Preserve main prompt, truncate additional instructions
            if additional_instructions and len(sections) > 2:
                main_prompt = sections[0] + "\n\n" + sections[-1]  # Keep request and closing
                return self.budget_manager.truncate_to_budget(main_prompt, available_budget)
        
        return prompt


class EnhancedPromptBuilder:
    """Main prompt builder that orchestrates all components"""
    
    # Token budget safety thresholds
    MEMORY_DISABLE_THRESHOLD = 0.35  # 35% of total budget
    MEMORY_WARNING_THRESHOLD = 0.25  # 25% of total budget
    
    def __init__(self, total_budget: int = 4000, policy: Optional[MemoryCompressionPolicy] = None):
        self.budget_manager = TokenBudgetManager(total_budget, policy)
        self.memory_builder = MemoryPromptBuilder(self.budget_manager)
        self.rag_builder = RAGPromptBuilder(self.budget_manager)
        self.system_builder = SystemPromptBuilder(self.budget_manager)
        
        # Safety tracking
        self.memory_auto_disabled = False
        self.budget_safety_triggered = False
    
    def check_memory_budget_safety(self, generation_state: Optional[GenerationState]) -> Tuple[bool, str]:
        """Check if memory usage would exceed safety thresholds"""
        
        if not generation_state or not generation_state.memory_enabled:
            return True, "Memory disabled"
        
        # Estimate memory token usage
        memory_usage = generation_state.estimate_token_usage()
        total_memory_tokens = memory_usage.get('entity_memory', 0) + memory_usage.get('history', 0)
        
        # Calculate percentage of total budget
        memory_percentage = total_memory_tokens / self.budget_manager.total_budget
        
        if memory_percentage > self.MEMORY_DISABLE_THRESHOLD:
            self.memory_auto_disabled = True
            self.budget_safety_triggered = True
            
            logger.warning(f"Memory auto-disabled: {memory_percentage:.1%} exceeds {self.MEMORY_DISABLE_THRESHOLD:.1%} threshold")
            return False, f"memory_skipped_due_to_budget (usage: {memory_percentage:.1%})"
        
        elif memory_percentage > self.MEMORY_WARNING_THRESHOLD:
            logger.info(f"Memory usage warning: {memory_percentage:.1%} approaching threshold")
            return True, f"memory_usage_high (usage: {memory_percentage:.1%})"
        
        return True, "memory_usage_normal"
    
    def build_complete_prompt(self, 
                            request: ScriptGenerationRequest,
                            generation_state: Optional[GenerationState] = None,
                            rag_results: Optional[List[Dict[str, Any]]] = None,
                            user_prompt: str = "",
                            additional_instructions: Optional[str] = None) -> Tuple[str, Dict[str, int]]:
        """
        Build complete prompt following the specified order:
        System → Entity Memory → RAG → Conversation Summary → Last N turns → User Guidance
        """
        
        components = []
        token_usage = {}
        
        # Check memory budget safety first
        memory_safe, safety_status = self.check_memory_budget_safety(generation_state)
        if not memory_safe and generation_state:
            # Temporarily disable memory for this request
            generation_state_copy = generation_state.model_copy()
            generation_state_copy.memory_enabled = False
            generation_state = generation_state_copy
            
            # Add safety event to token usage for tracking
            token_usage['memory_safety_event'] = safety_status
        
        # 1. System Prompt
        system_prompt = self.system_builder.build_system_prompt(request)
        if system_prompt:
            components.append(system_prompt)
            token_usage['system'] = self.budget_manager.estimate_tokens(system_prompt)
        
        # 2. Entity Memory (if memory enabled and safe)
        if generation_state and generation_state.memory_enabled and memory_safe:
            entity_prompt = self.memory_builder.build_entity_memory_prompt(generation_state.entity_memory)
            if entity_prompt:
                components.append(entity_prompt)
                token_usage['entity_memory'] = self.budget_manager.estimate_tokens(entity_prompt)
        
        # 3. RAG Context
        if rag_results:
            query = f"{request.title} {request.description} {user_prompt}"
            rag_prompt = self.rag_builder.build_rag_context(rag_results, query)
            if rag_prompt:
                components.append(rag_prompt)
                token_usage['rag'] = self.budget_manager.estimate_tokens(rag_prompt)
        
        # 4. Conversation Summary + Recent Turns (if memory enabled and safe)
        if generation_state and generation_state.memory_enabled and memory_safe and generation_state.history:
            conversation_prompt = self.memory_builder.build_conversation_summary(
                generation_state.history,
                preserve_count=generation_state.compression_policy.preserve_recent_turns
            )
            if conversation_prompt:
                components.append(conversation_prompt)
                token_usage['conversation'] = self.budget_manager.estimate_tokens(conversation_prompt)
        
        # 5. User Guidance (always last and guaranteed space)
        if user_prompt:
            guidance_prompt = self.system_builder.build_user_guidance(user_prompt, additional_instructions)
            components.append(guidance_prompt)
            token_usage['user_guidance'] = self.budget_manager.estimate_tokens(guidance_prompt)
        
        # Combine all components
        complete_prompt = "\n\n" + "="*50 + "\n\n".join(components)
        
        # Final token count
        total_tokens = sum(token_usage.values())
        token_usage['total'] = total_tokens
        token_usage['budget'] = self.budget_manager.total_budget
        token_usage['remaining'] = max(0, self.budget_manager.total_budget - total_tokens)
        
        # Log usage statistics
        logger.info(f"Prompt built: {total_tokens}/{self.budget_manager.total_budget} tokens "
                   f"({total_tokens/self.budget_manager.total_budget*100:.1f}%)")
        
        # Log memory safety events
        if 'memory_safety_event' in token_usage:
            logger.warning(f"Memory safety event: {token_usage['memory_safety_event']}")
        
        for component, tokens in token_usage.items():
            if component not in ['total', 'budget', 'remaining', 'memory_safety_event']:
                logger.debug(f"  {component}: {tokens} tokens")
        
        # Add enhanced metrics
        token_usage.update({
            'memory_summary_size_tokens': token_usage.get('entity_memory', 0) + token_usage.get('conversation', 0),
            'memory_budget_utilization_pct': (token_usage.get('entity_memory', 0) + token_usage.get('conversation', 0)) / self.budget_manager.total_budget * 100,
            'budget_safety_triggered': self.budget_safety_triggered,
        })
        
        return complete_prompt, token_usage
    
    def check_budget_exceeded(self, token_usage: Dict[str, int]) -> bool:
        """Check if token budget is exceeded"""
        return token_usage.get('total', 0) > self.budget_manager.total_budget
    
    def suggest_budget_adjustments(self, token_usage: Dict[str, int]) -> List[str]:
        """Suggest adjustments when budget is exceeded"""
        suggestions = []
        
        if not self.check_budget_exceeded(token_usage):
            return suggestions
        
        exceeded_by = token_usage.get('total', 0) - self.budget_manager.total_budget
        
        # Suggest compression if memory is using too much
        memory_tokens = token_usage.get('entity_memory', 0) + token_usage.get('conversation', 0)
        if memory_tokens > self.budget_manager.memory_budget:
            suggestions.append(f"Compress memory (currently {memory_tokens} tokens, "
                             f"budget {self.budget_manager.memory_budget})")
        
        # Suggest reducing RAG results
        rag_tokens = token_usage.get('rag', 0)
        if rag_tokens > self.budget_manager.rag_budget:
            suggestions.append(f"Reduce RAG context (currently {rag_tokens} tokens, "
                             f"budget {self.budget_manager.rag_budget})")
        
        # General suggestion
        suggestions.append(f"Budget exceeded by {exceeded_by} tokens ({exceeded_by/self.budget_manager.total_budget*100:.1f}%)")
        
        return suggestions