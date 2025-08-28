"""
Memory and conversation history models for the generation service.
Implements separated memory model with token budget management.
"""

import hashlib
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TurnSource(str, Enum):
    """Source of conversation turn"""
    
    UI = "ui"
    API = "api" 
    SSE = "sse"


class ConversationTurn(BaseModel):
    """Individual turn in conversation history"""
    
    model_config = ConfigDict(frozen=True)
    
    turn_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique turn ID")
    source: TurnSource = Field(..., description="Source of this turn")
    job_id: Optional[str] = Field(None, description="Associated job ID if any")
    
    # Selection context
    selection: Optional[Dict[str, Any]] = Field(None, description="UI selection context")
    
    # Content with hash for deduplication
    content: str = Field(..., max_length=2000, description="Turn content (max 2k chars)")
    content_hash: str = Field(..., description="SHA-256 hash of content")
    
    # Timing
    created_at: datetime = Field(default_factory=datetime.now, description="Turn timestamp")
    
    @model_validator(mode='before')
    @classmethod
    def compute_content_hash(cls, values: Any) -> Any:
        """Compute content hash if not provided"""
        if isinstance(values, dict):
            content = values.get('content', '')
            if 'content_hash' not in values:
                values['content_hash'] = hashlib.sha256(content.encode('utf-8')).hexdigest()
        return values
    
    @field_validator('content')
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate and sanitize content with enhanced PII scrubbing"""
        if not v.strip():
            raise ValueError("Content cannot be empty")
        
        # Enhanced PII scrubbing
        v = enhanced_pii_scrubbing(v)
        
        # UTF-8 safe truncation to 2k characters (protect surrogate pairs)
        v = safe_utf8_truncate(v.strip(), 2000)
        
        return v


class EntityMemory(BaseModel):
    """Structured entity memory for character/setting consistency"""
    
    # Character name mappings and aliases
    rename_map: Dict[str, str] = Field(default_factory=dict, description="Character name changes")
    
    # Style and tone flags from conversation
    style_flags: List[str] = Field(default_factory=list, description="Accumulated style preferences")
    
    # Key facts and decisions
    facts: List[str] = Field(default_factory=list, description="Important facts from conversation")
    
    @field_validator('rename_map')
    @classmethod
    def validate_rename_map(cls, v: Dict[str, str]) -> Dict[str, str]:
        """Validate rename mappings"""
        # Remove empty mappings
        return {k: v for k, v in v.items() if k.strip() and v.strip() and k != v}
    
    @field_validator('style_flags', 'facts')
    @classmethod
    def validate_lists(cls, v: List[str]) -> List[str]:
        """Validate and deduplicate lists"""
        if not v:
            return []
        
        # Remove empty items and deduplicate
        cleaned = [item.strip() for item in v if item.strip()]
        return list(dict.fromkeys(cleaned))  # Preserve order while deduplicating


class MemoryCompressionPolicy(BaseModel):
    """Policy for memory compression"""
    
    max_turns: int = Field(default=10, ge=1, le=50, description="Max turns before compression")
    preserve_recent_turns: int = Field(default=2, ge=1, le=5, description="Recent turns to preserve")
    min_decision_score: float = Field(default=0.6, ge=0.0, le=1.0, description="Min score for decision extraction")
    
    # Token budget percentages
    memory_token_budget_pct: float = Field(default=20.0, ge=5.0, le=40.0, description="Memory token budget %")
    rag_token_budget_pct: float = Field(default=30.0, ge=10.0, le=50.0, description="RAG token budget %")
    user_prompt_min_pct: float = Field(default=50.0, ge=30.0, le=80.0, description="Min user prompt %")


class GenerationState(BaseModel):
    """Generation state with separated memory model"""
    
    # Core identifiers
    project_id: str = Field(..., description="Project ID")
    episode_id: Optional[str] = Field(None, description="Episode ID if applicable")
    
    # Conversation history
    history: List[ConversationTurn] = Field(default_factory=list, description="Conversation turns")
    last_seq: int = Field(default=0, description="Last sequence number for sync")
    
    # Structured memory
    entity_memory: EntityMemory = Field(default_factory=EntityMemory, description="Entity memory")
    history_compacted: bool = Field(default=False, description="Whether history was compacted")
    
    # Memory settings
    memory_enabled: bool = Field(default=False, description="Memory system enabled")
    history_depth: int = Field(default=5, ge=1, le=10, description="History depth setting")
    compression_policy: MemoryCompressionPolicy = Field(default_factory=MemoryCompressionPolicy)
    
    # Versioning for concurrency control
    memory_version: int = Field(default=1, description="Version for conflict detection")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    @field_validator('history')
    @classmethod
    def validate_history(cls, v: List[ConversationTurn]) -> List[ConversationTurn]:
        """Validate and deduplicate history"""
        if not v:
            return []
        
        # Deduplicate by content hash while preserving order
        seen_hashes = set()
        deduped = []
        
        for turn in v:
            if turn.content_hash not in seen_hashes:
                seen_hashes.add(turn.content_hash)
                deduped.append(turn)
        
        # Sort by created_at to ensure chronological order
        return sorted(deduped, key=lambda t: t.created_at)
    
    @model_validator(mode='before')
    @classmethod
    def validate_token_budgets(cls, values: Any) -> Any:
        """Validate token budget percentages sum correctly"""
        if isinstance(values, dict) and 'compression_policy' in values:
            policy = values['compression_policy']
            if isinstance(policy, dict):
                memory_pct = policy.get('memory_token_budget_pct', 20.0)
                rag_pct = policy.get('rag_token_budget_pct', 30.0)
                user_min_pct = policy.get('user_prompt_min_pct', 50.0)
                
                if memory_pct + rag_pct > 100.0 - user_min_pct:
                    raise ValueError("Memory + RAG budget cannot exceed available token space")
        
        return values
    
    def add_turn(self, content: str, source: TurnSource, job_id: Optional[str] = None, 
                 selection: Optional[Dict[str, Any]] = None) -> ConversationTurn:
        """Add a new conversation turn"""
        turn = ConversationTurn(
            source=source,
            job_id=job_id,
            selection=selection,
            content=content
        )
        
        # Check for duplicate content
        if not any(t.content_hash == turn.content_hash for t in self.history):
            self.history.append(turn)
            self.last_seq += 1
            self.updated_at = datetime.now()
        
        return turn
    
    def needs_compression(self) -> bool:
        """Check if memory compression is needed"""
        if not self.memory_enabled:
            return False
        
        return len(self.history) > self.compression_policy.max_turns
    
    def get_recent_turns(self, count: Optional[int] = None) -> List[ConversationTurn]:
        """Get recent conversation turns"""
        if count is None:
            count = self.history_depth
        
        return sorted(self.history, key=lambda t: t.created_at)[-count:]
    
    def estimate_token_usage(self, base_tokens: int = 0) -> Dict[str, int]:
        """Estimate token usage for different components"""
        # Very rough estimation: ~4 chars per token
        
        recent_turns = self.get_recent_turns()
        history_tokens = sum(len(turn.content) for turn in recent_turns) // 4
        
        entity_tokens = (
            len(str(self.entity_memory.rename_map)) +
            sum(len(flag) for flag in self.entity_memory.style_flags) +
            sum(len(fact) for fact in self.entity_memory.facts)
        ) // 4
        
        return {
            'base': base_tokens,
            'history': history_tokens,
            'entity_memory': entity_tokens,
            'total': base_tokens + history_tokens + entity_tokens
        }


class MemoryCompressionResult(BaseModel):
    """Result of memory compression operation"""
    
    # Summary of compressed turns
    decision_log: List[str] = Field(..., description="Extracted decisions and key points")
    compressed_turn_count: int = Field(..., description="Number of turns compressed")
    
    # Updated entity memory
    updated_entity_memory: EntityMemory = Field(..., description="Updated entity memory")
    
    # Tokens saved
    tokens_before: int = Field(..., description="Token count before compression")
    tokens_after: int = Field(..., description="Token count after compression")
    tokens_saved: int = Field(..., description="Tokens saved by compression")
    
    # Metadata
    compressed_at: datetime = Field(default_factory=datetime.now)
    compression_version: str = Field(default="v1.0", description="Compression algorithm version")


class MemoryMetrics(BaseModel):
    """Enhanced metrics for memory system usage and operational safety"""
    
    # Usage metrics
    memory_enabled_ratio: float = Field(..., ge=0.0, le=1.0, description="Ratio of sessions with memory enabled")
    memory_token_used_pct: float = Field(..., ge=0.0, le=100.0, description="Average % of tokens used by memory")
    
    # Enhanced token metrics
    memory_summary_size_tokens: int = Field(default=0, description="Total tokens in memory summaries")
    compaction_savings_tokens: int = Field(default=0, description="Tokens saved by compression operations")
    memory_skipped_due_to_budget: int = Field(default=0, description="Times memory was skipped due to budget limits")
    
    # Compression metrics  
    memory_compaction_count: int = Field(default=0, description="Number of memory compressions")
    avg_tokens_saved_per_compression: float = Field(default=0.0, description="Average tokens saved per compression")
    compression_triggered_by_budget: int = Field(default=0, description="Compressions triggered by budget limits")
    
    # Entity metrics
    entity_renames_total: int = Field(default=0, description="Total entity renames across all sessions")
    avg_entity_facts_per_session: float = Field(default=0.0, description="Average facts per session")
    rename_conflicts_detected: int = Field(default=0, description="Number of rename conflicts detected")
    
    # Enhanced conflict metrics
    memory_conflict_total: int = Field(default=0, description="Total memory version conflicts")
    memory_conflict_resolution_success_rate: float = Field(default=1.0, ge=0.0, le=1.0)
    conflict_spike_incidents: int = Field(default=0, description="Number of conflict spike incidents")
    
    # Performance metrics
    avg_memory_compression_time_ms: float = Field(default=0.0, description="Average compression time")
    memory_overhead_pct: float = Field(default=0.0, ge=0.0, le=100.0, description="Memory processing overhead %")
    avg_conflict_resolution_time_ms: float = Field(default=0.0, description="Average conflict resolution time")
    
    # Safety and reliability metrics
    memory_failures_total: int = Field(default=0, description="Total memory system failures")
    circuit_breaker_activations: int = Field(default=0, description="Circuit breaker activations")
    memory_rollbacks_total: int = Field(default=0, description="Total memory rollback operations")
    episodes_with_memory_disabled: int = Field(default=0, description="Episodes with memory auto-disabled")
    
    # Budget safety metrics
    budget_exceeded_incidents: int = Field(default=0, description="Times budget was exceeded")
    budget_safety_triggers: int = Field(default=0, description="Budget safety auto-disable triggers")
    avg_memory_budget_utilization_pct: float = Field(default=0.0, description="Average memory budget utilization %")
    
    # Privacy metrics
    pii_scrubbing_activations: int = Field(default=0, description="PII patterns detected and scrubbed")
    content_truncations: int = Field(default=0, description="Content truncated for safety")
    
    # System health
    memory_system_health_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Overall memory system health")
    healthy_episodes_ratio: float = Field(default=1.0, ge=0.0, le=1.0, description="Ratio of episodes with healthy memory")
    
    # Alerting thresholds status
    memory_usage_alerts: int = Field(default=0, description="Memory usage threshold alerts")
    conflict_rate_alerts: int = Field(default=0, description="Conflict rate threshold alerts")
    budget_exceeded_alerts: int = Field(default=0, description="Budget exceeded threshold alerts")
    
    # Timestamp
    measured_at: datetime = Field(default_factory=datetime.now)


class MemoryConflictResolution(BaseModel):
    """Result of memory conflict resolution"""
    
    conflict_detected: bool = Field(..., description="Whether conflict was detected")
    resolution_strategy: str = Field(..., description="Strategy used for resolution")
    
    # Version information
    client_version: int = Field(..., description="Client's memory version")
    server_version: int = Field(..., description="Server's memory version")
    resolved_version: int = Field(..., description="Final resolved version")
    
    # Changes made
    server_changes_applied: bool = Field(default=True, description="Whether server changes were applied")
    client_changes_preserved: List[str] = Field(default_factory=list, description="Client changes preserved")
    client_changes_discarded: List[str] = Field(default_factory=list, description="Client changes discarded")
    
    # Merge results
    merged_entity_memory: EntityMemory = Field(..., description="Final merged entity memory")
    merge_warnings: List[str] = Field(default_factory=list, description="Warnings during merge")
    
    resolved_at: datetime = Field(default_factory=datetime.now)


# Request/Response models for memory API

class MemoryUpdateRequest(BaseModel):
    """Request to update memory state"""
    
    # New turns to add
    new_turns: List[Dict[str, Any]] = Field(default_factory=list, description="New conversation turns")
    
    # Entity memory updates
    entity_memory_updates: Optional[Dict[str, Any]] = Field(None, description="Entity memory updates")
    
    # Settings updates
    memory_enabled: Optional[bool] = Field(None, description="Enable/disable memory")
    history_depth: Optional[int] = Field(None, ge=1, le=10, description="History depth")
    
    # Concurrency control
    expected_version: Optional[int] = Field(None, description="Expected memory version")
    force_update: bool = Field(default=False, description="Force update despite conflicts")


class MemoryStateResponse(BaseModel):
    """Response with current memory state"""
    
    # Current state
    generation_state: GenerationState = Field(..., description="Current generation state")
    
    # Sync information
    sync_status: str = Field(..., description="Synchronization status")
    conflicts_resolved: Optional[MemoryConflictResolution] = Field(None, description="Conflict resolution details")
    
    # Usage metrics
    token_usage: Dict[str, int] = Field(..., description="Current token usage breakdown")
    compression_recommended: bool = Field(default=False, description="Whether compression is recommended")
    
    # Metadata
    last_modified: datetime = Field(..., description="Last modification time")
    version: int = Field(..., description="Current version")


class MemoryCompressionRequest(BaseModel):
    """Request to compress memory"""
    
    # Compression options
    force_compression: bool = Field(default=False, description="Force compression even if not needed")
    preserve_turns: Optional[int] = Field(None, ge=1, le=5, description="Number of recent turns to preserve")
    
    # Policy overrides
    policy_overrides: Optional[MemoryCompressionPolicy] = Field(None, description="Override compression policy")


class MemoryClearRequest(BaseModel):
    """Request to clear memory"""
    
    clear_history: bool = Field(default=True, description="Clear conversation history")
    clear_entity_memory: bool = Field(default=True, description="Clear entity memory")
    reset_version: bool = Field(default=True, description="Reset memory version to 1")
    
    # Audit trail
    reason: Optional[str] = Field(None, max_length=200, description="Reason for clearing memory")


# Enhanced PII scrubbing functions

def enhanced_pii_scrubbing(text: str) -> str:
    """Enhanced PII scrubbing with comprehensive patterns"""
    import re
    
    # Email addresses (comprehensive)
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
    
    # Phone numbers (multiple formats)
    phone_patterns = [
        r'\b\d{3}-\d{3}-\d{4}\b',           # 123-456-7890
        r'\b\(\d{3}\)\s*\d{3}-\d{4}\b',     # (123) 456-7890
        r'\b\d{3}\.\d{3}\.\d{4}\b',         # 123.456.7890
        r'\b\d{10,}\b',                     # 1234567890 (10+ digits)
        r'\+\d{1,3}\s*\d{8,12}',            # +1 1234567890 (international)
    ]
    
    for pattern in phone_patterns:
        text = re.sub(pattern, '[PHONE]', text)
    
    # API keys and tokens (enhanced)
    api_patterns = [
        r'\b[A-Za-z0-9+/=]{20,}\b',         # Base64-like tokens
        r'\bsk-[A-Za-z0-9]{32,}\b',         # OpenAI style keys
        r'\bpk-[A-Za-z0-9]{32,}\b',         # Public keys
        r'\bghp_[A-Za-z0-9]{36}\b',         # GitHub personal tokens
        r'\bglpat-[A-Za-z0-9_-]{20,}\b',    # GitLab tokens
        r'\bxoxb-[A-Za-z0-9-]+\b',          # Slack bot tokens
        r'\bxoxp-[A-Za-z0-9-]+\b',          # Slack user tokens
        r'\bAKIA[A-Z0-9]{16}\b',            # AWS access keys
        r'\bAWSSecretKey[A-Za-z0-9+/=]{40}\b', # AWS secret keys
        r'\b[A-Za-z0-9]{32,}\.[A-Za-z0-9]{6,}\.[A-Za-z0-9_-]{43,}\b', # JWT tokens
    ]
    
    for pattern in api_patterns:
        text = re.sub(pattern, '[API_KEY]', text, flags=re.IGNORECASE)
    
    # Credit card numbers
    text = re.sub(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CREDIT_CARD]', text)
    
    # Social security numbers (US format)
    text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]', text)
    
    # IP addresses (basic privacy)
    text = re.sub(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', '[IP_ADDRESS]', text)
    
    # URLs with potential sensitive info
    text = re.sub(r'https?://[^\s]+\?[^\s]*(?:token|key|secret|password)[^\s]*', '[SENSITIVE_URL]', text, flags=re.IGNORECASE)
    
    # File paths (basic privacy)
    path_patterns = [
        r'/home/[^/\s]+',                   # Linux home paths
        r'/Users/[^/\s]+',                  # macOS home paths  
        r'C:\\Users\\[^\\s]+',              # Windows user paths
        r'[A-Z]:\\[^\s]+\\[^\s]+',          # Windows absolute paths
    ]
    
    for pattern in path_patterns:
        text = re.sub(pattern, '[FILE_PATH]', text)
    
    # UUIDs (might contain sensitive info)
    text = re.sub(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', '[UUID]', text, flags=re.IGNORECASE)
    
    return text


def safe_utf8_truncate(text: str, max_bytes: int) -> str:
    """Safely truncate UTF-8 text without breaking surrogate pairs"""
    
    if not text:
        return text
    
    # Encode to bytes
    text_bytes = text.encode('utf-8')
    
    # If within limit, return original
    if len(text_bytes) <= max_bytes:
        return text
    
    # Truncate at byte boundary, then find safe character boundary
    truncated_bytes = text_bytes[:max_bytes]
    
    # Walk backwards from truncation point to find safe boundary
    for i in range(len(truncated_bytes) - 1, -1, -1):
        try:
            # Try to decode from this point
            candidate = truncated_bytes[:i+1].decode('utf-8', errors='strict')
            return candidate
        except UnicodeDecodeError:
            continue
    
    # Fallback: return empty string if can't find safe boundary
    return ""


def get_pii_scrubbing_test_cases() -> List[Tuple[str, str]]:
    """Get test cases for PII scrubbing validation"""
    
    return [
        # Email addresses
        ("Contact me at john.doe@company.com", "Contact me at [EMAIL]"),
        ("Email: user+test@example.org", "Email: [EMAIL]"),
        
        # Phone numbers
        ("Call 123-456-7890 for support", "Call [PHONE] for support"),
        ("Phone: (555) 123-4567", "Phone: [PHONE]"),
        ("Mobile: 555.123.4567", "Mobile: [PHONE]"),
        ("International: +1 5551234567", "International: [PHONE]"),
        
        # API keys
        ("API key: sk-abc123def456ghi789", "API key: [API_KEY]"),
        ("Token: ghp_1234567890abcdef1234567890abcdef12", "Token: [API_KEY]"),
        ("Bearer xoxb-1234-5678-abcdef", "Bearer [API_KEY]"),
        
        # Credit cards  
        ("Card: 4532 1234 5678 9012", "Card: [CREDIT_CARD]"),
        ("CC: 4532-1234-5678-9012", "CC: [CREDIT_CARD]"),
        
        # File paths
        ("Stored at /Users/john/secret.txt", "Stored at [FILE_PATH]/secret.txt"),
        ("File: C:\\Users\\John\\Documents\\data.csv", "File: [FILE_PATH]\\Documents\\data.csv"),
        
        # URLs with tokens
        ("https://api.service.com/data?token=abc123", "https://api.service.com/data?token=abc123"),  # Would be scrubbed
        
        # Multiple PII in one text
        ("Email john@test.com, phone 123-456-7890, key sk-abc123", "Email [EMAIL], phone [PHONE], key [API_KEY]"),
    ]