"""
Enhanced metrics collection and alerting for memory system.
Implements comprehensive monitoring with threshold-based alerting.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict, deque
from dataclasses import dataclass, field

from ..models.memory import MemoryMetrics, GenerationState
from ..services.failure_recovery import get_memory_health_status
from ..services.conflict_resolver import get_conflict_health_status

logger = logging.getLogger(__name__)


@dataclass
class AlertThresholds:
    """Alerting thresholds for memory system metrics"""
    
    # Usage thresholds
    memory_usage_warning: float = 0.25    # 25% of token budget
    memory_usage_critical: float = 0.35   # 35% of token budget
    
    # Conflict thresholds
    conflict_rate_warning: int = 5        # conflicts per hour
    conflict_rate_critical: int = 10      # conflicts per hour
    
    # Budget thresholds
    budget_exceeded_warning: int = 3      # budget exceeded events per hour
    budget_exceeded_critical: int = 10    # budget exceeded events per hour
    
    # Failure thresholds
    failure_rate_warning: int = 2         # failures per hour per episode
    failure_rate_critical: int = 5        # failures per hour per episode
    
    # Performance thresholds
    compression_time_warning: float = 5000.0  # 5s compression time
    conflict_resolution_time_warning: float = 2000.0  # 2s resolution time
    
    # Health thresholds
    system_health_warning: float = 0.8    # 80% system health
    system_health_critical: float = 0.6   # 60% system health


@dataclass
class Alert:
    """Alert record"""
    
    alert_type: str
    severity: str  # 'warning', 'critical'
    message: str
    metric_name: str
    current_value: float
    threshold_value: float
    timestamp: datetime
    episode_id: Optional[str] = None
    project_id: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)


class MetricsCollector:
    """Collects and aggregates memory system metrics"""
    
    def __init__(self, alert_thresholds: Optional[AlertThresholds] = None):
        self.thresholds = alert_thresholds or AlertThresholds()
        
        # Metrics storage (in production, would use proper metrics store)
        self.metrics_history: deque = deque(maxlen=1000)
        self.alerts_history: deque = deque(maxlen=500)
        
        # Counters and accumulators
        self.counters = defaultdict(int)
        self.timers = defaultdict(list)
        self.gauges = defaultdict(float)
        
        # Episode-specific tracking
        self.episode_metrics: Dict[str, Dict] = {}
        
        # Alert state tracking
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_cooldowns: Dict[str, datetime] = {}
        self.alert_cooldown_duration = timedelta(minutes=15)  # 15 minute cooldown
    
    def increment_counter(self, metric_name: str, value: int = 1, 
                         episode_key: Optional[str] = None, context: Dict = None):
        """Increment a counter metric"""
        
        self.counters[metric_name] += value
        
        # Track per-episode if specified
        if episode_key:
            if episode_key not in self.episode_metrics:
                self.episode_metrics[episode_key] = defaultdict(int)
            self.episode_metrics[episode_key][metric_name] += value
        
        logger.debug(f"Counter incremented: {metric_name} += {value}")
    
    def record_timer(self, metric_name: str, duration_ms: float,
                    episode_key: Optional[str] = None):
        """Record a timing metric"""
        
        self.timers[metric_name].append(duration_ms)
        
        # Keep only recent timings (last 100)
        if len(self.timers[metric_name]) > 100:
            self.timers[metric_name] = self.timers[metric_name][-100:]
        
        # Track per-episode
        if episode_key:
            if episode_key not in self.episode_metrics:
                self.episode_metrics[episode_key] = defaultdict(list)
            
            episode_timers = self.episode_metrics[episode_key].get(metric_name, [])
            episode_timers.append(duration_ms)
            if len(episode_timers) > 50:  # Smaller limit per episode
                episode_timers = episode_timers[-50:]
            self.episode_metrics[episode_key][metric_name] = episode_timers
        
        logger.debug(f"Timer recorded: {metric_name} = {duration_ms}ms")
    
    def set_gauge(self, metric_name: str, value: float, 
                  episode_key: Optional[str] = None):
        """Set a gauge metric"""
        
        self.gauges[metric_name] = value
        
        if episode_key:
            if episode_key not in self.episode_metrics:
                self.episode_metrics[episode_key] = {}
            self.episode_metrics[episode_key][metric_name] = value
        
        logger.debug(f"Gauge set: {metric_name} = {value}")
    
    def record_memory_operation(self, operation_type: str, duration_ms: float,
                              tokens_used: int = 0, success: bool = True,
                              episode_key: Optional[str] = None):
        """Record a memory operation with multiple metrics"""
        
        # Record timing
        self.record_timer(f"memory_{operation_type}_time_ms", duration_ms, episode_key)
        
        # Record tokens if applicable
        if tokens_used > 0:
            self.increment_counter(f"memory_{operation_type}_tokens", tokens_used, episode_key)
        
        # Record success/failure
        if success:
            self.increment_counter(f"memory_{operation_type}_success", 1, episode_key)
        else:
            self.increment_counter(f"memory_{operation_type}_failure", 1, episode_key)
    
    def check_alert_thresholds(self) -> List[Alert]:
        """Check current metrics against thresholds and generate alerts"""
        
        alerts = []
        now = datetime.now()
        
        # Check memory usage alerts
        current_usage = self.gauges.get('memory_budget_utilization_pct', 0.0)
        if current_usage > self.thresholds.memory_usage_critical:
            alert = self._create_alert(
                'memory_usage_critical',
                'critical',
                f'Memory usage at {current_usage:.1f}% exceeds critical threshold',
                'memory_budget_utilization_pct',
                current_usage,
                self.thresholds.memory_usage_critical
            )
            alerts.append(alert)
        elif current_usage > self.thresholds.memory_usage_warning:
            alert = self._create_alert(
                'memory_usage_warning', 
                'warning',
                f'Memory usage at {current_usage:.1f}% exceeds warning threshold',
                'memory_budget_utilization_pct',
                current_usage,
                self.thresholds.memory_usage_warning
            )
            alerts.append(alert)
        
        # Check conflict rate alerts (per hour)
        hour_ago = now - timedelta(hours=1)
        recent_conflicts = self.counters.get('memory_conflict_total', 0)  # Would need time windowing
        
        if recent_conflicts > self.thresholds.conflict_rate_critical:
            alert = self._create_alert(
                'conflict_rate_critical',
                'critical', 
                f'Conflict rate at {recent_conflicts}/hour exceeds critical threshold',
                'conflict_rate_per_hour',
                recent_conflicts,
                self.thresholds.conflict_rate_critical
            )
            alerts.append(alert)
        
        # Check budget exceeded alerts
        budget_exceeded = self.counters.get('budget_exceeded_incidents', 0)
        if budget_exceeded > self.thresholds.budget_exceeded_critical:
            alert = self._create_alert(
                'budget_exceeded_critical',
                'critical',
                f'Budget exceeded {budget_exceeded} times exceeds critical threshold',
                'budget_exceeded_incidents',
                budget_exceeded,
                self.thresholds.budget_exceeded_critical
            )
            alerts.append(alert)
        
        # Check system health alerts
        health_score = self.gauges.get('memory_system_health_score', 1.0)
        if health_score < self.thresholds.system_health_critical:
            alert = self._create_alert(
                'system_health_critical',
                'critical',
                f'System health at {health_score:.1%} below critical threshold',
                'memory_system_health_score',
                health_score,
                self.thresholds.system_health_critical
            )
            alerts.append(alert)
        elif health_score < self.thresholds.system_health_warning:
            alert = self._create_alert(
                'system_health_warning',
                'warning',
                f'System health at {health_score:.1%} below warning threshold',
                'memory_system_health_score',
                health_score,
                self.thresholds.system_health_warning
            )
            alerts.append(alert)
        
        # Process alerts (deduplicate, apply cooldowns)
        processed_alerts = self._process_alerts(alerts)
        
        return processed_alerts
    
    def _create_alert(self, alert_type: str, severity: str, message: str,
                     metric_name: str, current_value: float, threshold_value: float,
                     episode_key: Optional[str] = None) -> Alert:
        """Create an alert record"""
        
        project_id = None
        episode_id = None
        
        if episode_key:
            parts = episode_key.split(':', 1)
            project_id = parts[0] if parts else None
            episode_id = parts[1] if len(parts) > 1 and parts[1] != 'default' else None
        
        return Alert(
            alert_type=alert_type,
            severity=severity,
            message=message,
            metric_name=metric_name,
            current_value=current_value,
            threshold_value=threshold_value,
            timestamp=datetime.now(),
            project_id=project_id,
            episode_id=episode_id
        )
    
    def _process_alerts(self, alerts: List[Alert]) -> List[Alert]:
        """Process alerts with deduplication and cooldowns"""
        
        processed = []
        now = datetime.now()
        
        for alert in alerts:
            alert_key = f"{alert.alert_type}:{alert.project_id or ''}:{alert.episode_id or ''}"
            
            # Check cooldown
            last_alert_time = self.alert_cooldowns.get(alert_key)
            if last_alert_time and now - last_alert_time < self.alert_cooldown_duration:
                continue  # Skip due to cooldown
            
            # Check if this is a new alert or value changed significantly
            existing_alert = self.active_alerts.get(alert_key)
            if existing_alert:
                value_change = abs(alert.current_value - existing_alert.current_value)
                if value_change < alert.threshold_value * 0.1:  # Less than 10% threshold change
                    continue  # Skip, not significant enough change
            
            # Process the alert
            processed.append(alert)
            self.active_alerts[alert_key] = alert
            self.alert_cooldowns[alert_key] = now
            self.alerts_history.append(alert)
            
            # Log the alert
            logger.log(
                logging.ERROR if alert.severity == 'critical' else logging.WARNING,
                f"ALERT [{alert.severity.upper()}] {alert.alert_type}: {alert.message}"
            )
        
        return processed
    
    def generate_comprehensive_metrics(self, memory_states: List[GenerationState]) -> MemoryMetrics:
        """Generate comprehensive metrics from current state"""
        
        now = datetime.now()
        
        # Calculate basic usage metrics
        total_states = len(memory_states)
        enabled_states = sum(1 for state in memory_states if state.memory_enabled)
        memory_enabled_ratio = enabled_states / total_states if total_states > 0 else 0.0
        
        # Calculate token metrics
        total_tokens = 0
        memory_tokens = 0
        summary_tokens = 0
        
        for state in memory_states:
            if state.memory_enabled:
                usage = state.estimate_token_usage()
                total_tokens += usage.get('total', 0)
                memory_tokens += usage.get('entity_memory', 0) + usage.get('history', 0)
                summary_tokens += usage.get('entity_memory', 0)
        
        memory_token_pct = (memory_tokens / max(total_tokens, 1)) * 100
        
        # Get timing averages
        compression_times = self.timers.get('memory_compression_time_ms', [])
        avg_compression_time = sum(compression_times) / len(compression_times) if compression_times else 0.0
        
        resolution_times = self.timers.get('memory_conflict_resolution_time_ms', [])
        avg_resolution_time = sum(resolution_times) / len(resolution_times) if resolution_times else 0.0
        
        # Get health status
        health_status = get_memory_health_status()
        conflict_status = get_conflict_health_status()
        
        # Calculate system health score
        health_factors = [
            1.0 - (self.counters.get('memory_failures_total', 0) / max(total_states * 10, 1)),  # Failure rate
            1.0 - (self.counters.get('budget_exceeded_incidents', 0) / max(total_states * 5, 1)),  # Budget issues
            health_status.get('health_percentage', 100) / 100,  # Episode health
            conflict_status.get('metrics', {}).get('recent_conflicts_1h', 0) <= 5,  # Low conflict rate
        ]
        
        system_health_score = sum(health_factors) / len(health_factors)
        
        # Build comprehensive metrics
        metrics = MemoryMetrics(
            # Basic usage
            memory_enabled_ratio=memory_enabled_ratio,
            memory_token_used_pct=memory_token_pct,
            
            # Enhanced token metrics
            memory_summary_size_tokens=summary_tokens,
            compaction_savings_tokens=self.counters.get('compaction_savings_tokens', 0),
            memory_skipped_due_to_budget=self.counters.get('memory_skipped_due_to_budget', 0),
            
            # Compression metrics
            memory_compaction_count=self.counters.get('memory_compaction_count', 0),
            avg_tokens_saved_per_compression=self.gauges.get('avg_tokens_saved_per_compression', 0.0),
            compression_triggered_by_budget=self.counters.get('compression_triggered_by_budget', 0),
            
            # Entity metrics
            entity_renames_total=sum(len(state.entity_memory.rename_map) for state in memory_states),
            avg_entity_facts_per_session=sum(len(state.entity_memory.facts) for state in memory_states) / max(enabled_states, 1),
            rename_conflicts_detected=self.counters.get('rename_conflicts_detected', 0),
            
            # Conflict metrics
            memory_conflict_total=self.counters.get('memory_conflict_total', 0),
            memory_conflict_resolution_success_rate=self.gauges.get('memory_conflict_resolution_success_rate', 1.0),
            conflict_spike_incidents=self.counters.get('conflict_spike_incidents', 0),
            
            # Performance metrics
            avg_memory_compression_time_ms=avg_compression_time,
            memory_overhead_pct=self.gauges.get('memory_overhead_pct', 0.0),
            avg_conflict_resolution_time_ms=avg_resolution_time,
            
            # Safety metrics
            memory_failures_total=self.counters.get('memory_failures_total', 0),
            circuit_breaker_activations=self.counters.get('circuit_breaker_activations', 0),
            memory_rollbacks_total=self.counters.get('memory_rollbacks_total', 0),
            episodes_with_memory_disabled=self.counters.get('episodes_with_memory_disabled', 0),
            
            # Budget safety
            budget_exceeded_incidents=self.counters.get('budget_exceeded_incidents', 0),
            budget_safety_triggers=self.counters.get('budget_safety_triggers', 0),
            avg_memory_budget_utilization_pct=self.gauges.get('avg_memory_budget_utilization_pct', 0.0),
            
            # Privacy metrics
            pii_scrubbing_activations=self.counters.get('pii_scrubbing_activations', 0),
            content_truncations=self.counters.get('content_truncations', 0),
            
            # System health
            memory_system_health_score=system_health_score,
            healthy_episodes_ratio=health_status.get('health_percentage', 100) / 100,
            
            # Alerting status
            memory_usage_alerts=len([a for a in self.active_alerts.values() if 'memory_usage' in a.alert_type]),
            conflict_rate_alerts=len([a for a in self.active_alerts.values() if 'conflict_rate' in a.alert_type]),
            budget_exceeded_alerts=len([a for a in self.active_alerts.values() if 'budget_exceeded' in a.alert_type]),
        )
        
        # Store in history
        self.metrics_history.append(metrics)
        
        return metrics
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of current alerts and alert history"""
        
        active_by_severity = defaultdict(int)
        for alert in self.active_alerts.values():
            active_by_severity[alert.severity] += 1
        
        recent_alerts = [a for a in self.alerts_history 
                        if datetime.now() - a.timestamp < timedelta(hours=24)]
        
        return {
            'active_alerts': len(self.active_alerts),
            'active_by_severity': dict(active_by_severity),
            'recent_24h': len(recent_alerts),
            'alert_types_24h': list(set(a.alert_type for a in recent_alerts)),
            'cooldown_duration_minutes': self.alert_cooldown_duration.total_seconds() / 60,
        }
    
    def reset_episode_metrics(self, episode_key: str):
        """Reset metrics for a specific episode (after recovery)"""
        
        if episode_key in self.episode_metrics:
            del self.episode_metrics[episode_key]
        
        # Clear related alerts
        to_clear = [k for k in self.active_alerts.keys() if episode_key in k]
        for key in to_clear:
            del self.active_alerts[key]
            del self.alert_cooldowns[key]
        
        logger.info(f"Reset metrics for episode: {episode_key}")


# Global metrics collector instance
_metrics_collector = MetricsCollector()


def increment_memory_counter(metric_name: str, value: int = 1, 
                           episode_key: Optional[str] = None, context: Dict = None):
    """Convenience function to increment memory counter"""
    _metrics_collector.increment_counter(metric_name, value, episode_key, context)


def record_memory_timer(metric_name: str, duration_ms: float, episode_key: Optional[str] = None):
    """Convenience function to record memory timer"""
    _metrics_collector.record_timer(metric_name, duration_ms, episode_key)


def set_memory_gauge(metric_name: str, value: float, episode_key: Optional[str] = None):
    """Convenience function to set memory gauge"""
    _metrics_collector.set_gauge(metric_name, value, episode_key)


def generate_memory_metrics(memory_states: List[GenerationState]) -> MemoryMetrics:
    """Convenience function to generate comprehensive metrics"""
    return _metrics_collector.generate_comprehensive_metrics(memory_states)


def check_memory_alerts() -> List[Alert]:
    """Convenience function to check alert thresholds"""
    return _metrics_collector.check_alert_thresholds()


def get_alert_status() -> Dict[str, Any]:
    """Convenience function to get alert summary"""
    return _metrics_collector.get_alert_summary()