"""
Failure recovery and auto-disable mechanisms for memory system.
Handles memory errors, circuit breaking, and recovery workflows.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class MemoryFailureType(str, Enum):
    """Types of memory failures"""
    
    COMPRESSION_ERROR = "compression_error"
    VALIDATION_ERROR = "validation_error"
    CONFLICT_RESOLUTION_ERROR = "conflict_resolution_error"
    BUDGET_EXCEEDED = "budget_exceeded"
    STORAGE_ERROR = "storage_error"
    NETWORK_ERROR = "network_error"
    TIMEOUT_ERROR = "timeout_error"


class CircuitBreakerState(str, Enum):
    """Circuit breaker states"""
    
    CLOSED = "closed"        # Normal operation
    OPEN = "open"           # Failures detected, memory disabled
    HALF_OPEN = "half_open" # Testing recovery


@dataclass
class MemoryFailure:
    """Record of a memory system failure"""
    
    project_id: str
    episode_id: Optional[str]
    failure_type: MemoryFailureType
    error_message: str
    timestamp: datetime
    stack_trace: Optional[str] = None
    context: Dict[str, any] = field(default_factory=dict)


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior"""
    
    failure_threshold: int = 3          # Failures within time window to trigger open
    time_window_minutes: int = 5        # Time window for counting failures
    recovery_timeout_minutes: int = 10  # Time to wait before trying recovery
    max_recovery_attempts: int = 3      # Max attempts before permanent disable
    
    # Failure type weights (some failures are more serious)
    failure_weights: Dict[MemoryFailureType, float] = field(default_factory=lambda: {
        MemoryFailureType.STORAGE_ERROR: 2.0,
        MemoryFailureType.COMPRESSION_ERROR: 1.5,
        MemoryFailureType.CONFLICT_RESOLUTION_ERROR: 1.5,
        MemoryFailureType.VALIDATION_ERROR: 1.0,
        MemoryFailureType.BUDGET_EXCEEDED: 0.5,
        MemoryFailureType.NETWORK_ERROR: 0.5,
        MemoryFailureType.TIMEOUT_ERROR: 0.5,
    })


class CircuitBreaker:
    """Circuit breaker for memory operations"""
    
    def __init__(self, config: Optional[CircuitBreakerConfig] = None):
        self.config = config or CircuitBreakerConfig()
        self.failures: deque = deque(maxlen=100)  # Keep last 100 failures
        self.state = CircuitBreakerState.CLOSED
        self.last_failure_time: Optional[datetime] = None
        self.recovery_attempts = 0
        self.disabled_until: Optional[datetime] = None
    
    def record_failure(self, failure: MemoryFailure) -> bool:
        """
        Record a failure and determine if circuit should open
        
        Returns True if circuit opened (memory should be disabled)
        """
        
        self.failures.append(failure)
        self.last_failure_time = failure.timestamp
        
        # Calculate weighted failure count in time window
        window_start = datetime.now() - timedelta(minutes=self.config.time_window_minutes)
        recent_failures = [f for f in self.failures if f.timestamp > window_start]
        
        weighted_failure_count = sum(
            self.config.failure_weights.get(f.failure_type, 1.0) 
            for f in recent_failures
        )
        
        logger.warning(f"Memory failure recorded: {failure.failure_type} for {failure.project_id}:{failure.episode_id}")
        logger.debug(f"Weighted failure count in window: {weighted_failure_count}/{self.config.failure_threshold}")
        
        # Check if should open circuit
        if weighted_failure_count >= self.config.failure_threshold and self.state == CircuitBreakerState.CLOSED:
            self._open_circuit()
            return True
        
        return self.state == CircuitBreakerState.OPEN
    
    def can_attempt_operation(self) -> Tuple[bool, str]:
        """Check if memory operations are allowed"""
        
        now = datetime.now()
        
        if self.state == CircuitBreakerState.CLOSED:
            return True, "Circuit closed, operations allowed"
        
        elif self.state == CircuitBreakerState.OPEN:
            # Check if recovery timeout has passed
            if (self.last_failure_time and 
                now - self.last_failure_time > timedelta(minutes=self.config.recovery_timeout_minutes)):
                
                # Check if permanently disabled
                if self.recovery_attempts >= self.config.max_recovery_attempts:
                    return False, "Memory permanently disabled due to repeated failures"
                
                # Try half-open state
                self.state = CircuitBreakerState.HALF_OPEN
                logger.info(f"Circuit breaker entering HALF_OPEN state (attempt {self.recovery_attempts + 1})")
                return True, "Circuit half-open, testing recovery"
            
            return False, f"Circuit open, disabled until {self.last_failure_time + timedelta(minutes=self.config.recovery_timeout_minutes)}"
        
        elif self.state == CircuitBreakerState.HALF_OPEN:
            # Allow limited operations to test recovery
            return True, "Circuit half-open, testing recovery"
        
        return False, "Unknown circuit state"
    
    def record_success(self):
        """Record successful operation (for recovery)"""
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            # Success in half-open state, close circuit
            self.state = CircuitBreakerState.CLOSED
            self.recovery_attempts = 0  # Reset recovery attempts
            logger.info("Circuit breaker closed after successful recovery")
        
        # Clear recent failures on success
        cutoff = datetime.now() - timedelta(minutes=self.config.time_window_minutes * 2)
        self.failures = deque([f for f in self.failures if f.timestamp > cutoff], maxlen=100)
    
    def _open_circuit(self):
        """Open the circuit due to failures"""
        
        self.state = CircuitBreakerState.OPEN
        self.recovery_attempts += 1
        
        logger.error(f"Circuit breaker OPENED due to failures (attempt {self.recovery_attempts}/{self.config.max_recovery_attempts})")
        
        # If max attempts reached, disable for longer
        if self.recovery_attempts >= self.config.max_recovery_attempts:
            self.disabled_until = datetime.now() + timedelta(hours=24)  # 24 hour cooldown
            logger.error("Memory system permanently disabled for this session due to repeated failures")
    
    def get_failure_summary(self) -> Dict[str, any]:
        """Get summary of recent failures"""
        
        if not self.failures:
            return {
                'total_failures': 0,
                'recent_failures': 0,
                'failure_types': {},
                'state': self.state.value
            }
        
        now = datetime.now()
        window_start = now - timedelta(minutes=self.config.time_window_minutes)
        recent_failures = [f for f in self.failures if f.timestamp > window_start]
        
        failure_types = defaultdict(int)
        for failure in recent_failures:
            failure_types[failure.failure_type.value] += 1
        
        return {
            'total_failures': len(self.failures),
            'recent_failures': len(recent_failures),
            'failure_types': dict(failure_types),
            'state': self.state.value,
            'recovery_attempts': self.recovery_attempts,
            'disabled_until': self.disabled_until.isoformat() if self.disabled_until else None,
            'last_failure': self.last_failure_time.isoformat() if self.last_failure_time else None
        }


class MemoryRecoveryManager:
    """Manages memory failure recovery and auto-disable mechanisms"""
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}  # Per episode circuit breaker
        self.global_circuit_breaker = CircuitBreaker()
        
        # Rollback support
        self.memory_snapshots: Dict[str, Tuple[datetime, any]] = {}  # Recent memory states
        self.rollback_enabled = True
        self.rollback_timeout = timedelta(seconds=60)  # 60 second rollback window
    
    def get_episode_key(self, project_id: str, episode_id: Optional[str]) -> str:
        """Get key for episode-specific circuit breaker"""
        return f"{project_id}:{episode_id or 'default'}"
    
    def record_memory_failure(self, 
                            project_id: str,
                            episode_id: Optional[str],
                            failure_type: MemoryFailureType,
                            error_message: str,
                            context: Optional[Dict] = None,
                            stack_trace: Optional[str] = None) -> bool:
        """
        Record a memory failure and determine if memory should be disabled
        
        Returns True if memory should be disabled for this episode
        """
        
        failure = MemoryFailure(
            project_id=project_id,
            episode_id=episode_id,
            failure_type=failure_type,
            error_message=error_message,
            timestamp=datetime.now(),
            stack_trace=stack_trace,
            context=context or {}
        )
        
        # Record in episode-specific circuit breaker
        episode_key = self.get_episode_key(project_id, episode_id)
        if episode_key not in self.circuit_breakers:
            self.circuit_breakers[episode_key] = CircuitBreaker()
        
        episode_disabled = self.circuit_breakers[episode_key].record_failure(failure)
        
        # Also record in global circuit breaker for system-wide issues
        global_disabled = self.global_circuit_breaker.record_failure(failure)
        
        # Log the incident
        severity = "ERROR" if episode_disabled or global_disabled else "WARNING"
        logger.log(
            logging.ERROR if episode_disabled else logging.WARNING,
            f"Memory failure ({severity}): {failure_type.value} - {error_message}"
        )
        
        return episode_disabled or global_disabled
    
    def can_use_memory(self, project_id: str, episode_id: Optional[str]) -> Tuple[bool, str]:
        """Check if memory can be used for this episode"""
        
        # Check global circuit breaker first
        global_allowed, global_reason = self.global_circuit_breaker.can_attempt_operation()
        if not global_allowed:
            return False, f"Global: {global_reason}"
        
        # Check episode-specific circuit breaker
        episode_key = self.get_episode_key(project_id, episode_id)
        if episode_key in self.circuit_breakers:
            episode_allowed, episode_reason = self.circuit_breakers[episode_key].can_attempt_operation()
            if not episode_allowed:
                return False, f"Episode: {episode_reason}"
        
        return True, "Memory available"
    
    def record_memory_success(self, project_id: str, episode_id: Optional[str]):
        """Record successful memory operation"""
        
        # Record success in both circuit breakers
        self.global_circuit_breaker.record_success()
        
        episode_key = self.get_episode_key(project_id, episode_id)
        if episode_key in self.circuit_breakers:
            self.circuit_breakers[episode_key].record_success()
    
    def create_memory_snapshot(self, 
                             project_id: str, 
                             episode_id: Optional[str], 
                             memory_state: any) -> str:
        """Create a rollback snapshot of memory state"""
        
        if not self.rollback_enabled:
            return ""
        
        snapshot_key = f"{project_id}:{episode_id or 'default'}:{datetime.now().isoformat()}"
        self.memory_snapshots[snapshot_key] = (datetime.now(), memory_state)
        
        # Clean old snapshots
        self._cleanup_old_snapshots()
        
        return snapshot_key
    
    def can_rollback(self, snapshot_key: str) -> bool:
        """Check if rollback is possible for snapshot"""
        
        if not self.rollback_enabled or snapshot_key not in self.memory_snapshots:
            return False
        
        snapshot_time, _ = self.memory_snapshots[snapshot_key]
        return datetime.now() - snapshot_time <= self.rollback_timeout
    
    def rollback_memory(self, snapshot_key: str) -> Tuple[bool, any]:
        """Rollback memory to snapshot state"""
        
        if not self.can_rollback(snapshot_key):
            return False, None
        
        _, memory_state = self.memory_snapshots[snapshot_key]
        
        logger.info(f"Rolling back memory to snapshot: {snapshot_key}")
        return True, memory_state
    
    def _cleanup_old_snapshots(self):
        """Clean up expired snapshots"""
        
        cutoff = datetime.now() - self.rollback_timeout * 2  # Keep some extra for safety
        expired_keys = []
        
        for key, (timestamp, _) in self.memory_snapshots.items():
            if timestamp < cutoff:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.memory_snapshots[key]
    
    def get_system_health(self) -> Dict[str, any]:
        """Get overall system health status"""
        
        global_health = self.global_circuit_breaker.get_failure_summary()
        
        episode_healths = {}
        total_episodes = len(self.circuit_breakers)
        healthy_episodes = 0
        
        for episode_key, breaker in self.circuit_breakers.items():
            health = breaker.get_failure_summary()
            episode_healths[episode_key] = health
            
            if health['state'] == 'closed':
                healthy_episodes += 1
        
        health_percentage = (healthy_episodes / total_episodes * 100) if total_episodes > 0 else 100
        
        # Determine overall status
        if global_health['state'] == 'open':
            status = 'critical'
            message = 'Global memory system disabled'
        elif health_percentage < 50:
            status = 'degraded'
            message = f'Memory issues in {total_episodes - healthy_episodes} episodes'
        elif health_percentage < 80:
            status = 'warning'
            message = f'Memory issues in {total_episodes - healthy_episodes} episodes'
        else:
            status = 'healthy'
            message = 'Memory system operational'
        
        return {
            'status': status,
            'message': message,
            'health_percentage': health_percentage,
            'global_health': global_health,
            'episode_count': total_episodes,
            'healthy_episodes': healthy_episodes,
            'rollback_enabled': self.rollback_enabled,
            'active_snapshots': len(self.memory_snapshots),
        }
    
    def force_reset_episode(self, project_id: str, episode_id: Optional[str]) -> bool:
        """Force reset circuit breaker for episode (admin function)"""
        
        episode_key = self.get_episode_key(project_id, episode_id)
        if episode_key in self.circuit_breakers:
            del self.circuit_breakers[episode_key]
            logger.info(f"Force reset memory circuit breaker for {episode_key}")
            return True
        
        return False


# Global recovery manager instance
_recovery_manager = MemoryRecoveryManager()


def record_memory_failure(project_id: str, episode_id: Optional[str], 
                         failure_type: MemoryFailureType, error_message: str,
                         context: Optional[Dict] = None) -> bool:
    """Convenience function to record memory failure"""
    return _recovery_manager.record_memory_failure(
        project_id, episode_id, failure_type, error_message, context
    )


def can_use_memory_safely(project_id: str, episode_id: Optional[str]) -> Tuple[bool, str]:
    """Convenience function to check if memory can be used safely"""
    return _recovery_manager.can_use_memory(project_id, episode_id)


def record_memory_operation_success(project_id: str, episode_id: Optional[str]):
    """Convenience function to record successful memory operation"""
    _recovery_manager.record_memory_success(project_id, episode_id)


def create_rollback_snapshot(project_id: str, episode_id: Optional[str], memory_state: any) -> str:
    """Convenience function to create rollback snapshot"""
    return _recovery_manager.create_memory_snapshot(project_id, episode_id, memory_state)


def attempt_memory_rollback(snapshot_key: str) -> Tuple[bool, any]:
    """Convenience function to attempt memory rollback"""
    return _recovery_manager.rollback_memory(snapshot_key)


def get_memory_health_status() -> Dict[str, any]:
    """Convenience function to get memory system health"""
    return _recovery_manager.get_system_health()