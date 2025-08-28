/**
 * Audit Trail System with PII Protection and Cross-Tenant Security
 * Provides structured logging for security events and user actions
 */

import { MetricsCollector } from '../metrics/collector'

export interface AuditEvent {
  eventType: 
    | 'user_login' 
    | 'user_logout' 
    | 'project_created' 
    | 'project_accessed' 
    | 'episode_created' 
    | 'episode_accessed' 
    | 'commit_submitted' 
    | 'sse_connection' 
    | 'security_violation'
    | 'data_export'
    | 'admin_action'
  timestamp: string
  userId?: string // Hashed or anonymized
  projectId?: string
  episodeId?: string
  sessionId: string
  requestId: string
  userAgent: string
  ipAddress?: string // Anonymized IP (e.g., 192.168.1.xxx)
  resource: string
  action: string
  outcome: 'success' | 'failure' | 'denied'
  metadata?: Record<string, any>
  securityLevel: 'low' | 'medium' | 'high' | 'critical'
  crossTenantRisk?: boolean
}

export interface SecurityViolation {
  type: 'unauthorized_access' | 'cross_tenant_breach' | 'data_leak' | 'suspicious_activity'
  severity: 'low' | 'medium' | 'high' | 'critical'
  description: string
  affectedResources: string[]
  mitigationApplied?: string
}

/**
 * PII-safe audit trail collector
 */
class AuditTrailService {
  private auditBuffer: AuditEvent[] = []
  private securityViolations: SecurityViolation[] = []
  private metrics = new MetricsCollector('audit')
  private readonly maxBufferSize = 100
  private readonly flushInterval = 10000 // 10 seconds for security events
  private flushTimer: NodeJS.Timeout | null = null
  
  constructor() {
    this.startFlushTimer()
    this.setupUnloadFlush()
  }
  
  /**
   * Record audit event with automatic PII scrubbing
   */
  recordEvent(event: Omit<AuditEvent, 'timestamp' | 'sessionId' | 'requestId' | 'userAgent'>): void {
    const sanitizedEvent: AuditEvent = {
      ...event,
      timestamp: new Date().toISOString(),
      sessionId: this.generateSessionId(),
      requestId: this.generateRequestId(),
      userAgent: this.sanitizeUserAgent(navigator.userAgent),
      userId: event.userId ? this.hashUserId(event.userId) : undefined,
      ipAddress: event.ipAddress ? this.anonymizeIP(event.ipAddress) : undefined,
      metadata: event.metadata ? this.sanitizeMetadata(event.metadata) : undefined,
    }
    
    // Cross-tenant security check
    if (this.detectCrossTenantRisk(sanitizedEvent)) {
      sanitizedEvent.crossTenantRisk = true
      sanitizedEvent.securityLevel = 'critical'
    }
    
    this.auditBuffer.push(sanitizedEvent)
    
    // Record metrics
    this.metrics.record('audit_event', 1, {
      eventType: sanitizedEvent.eventType,
      outcome: sanitizedEvent.outcome,
      securityLevel: sanitizedEvent.securityLevel,
    })
    
    // Auto-flush for critical events
    if (sanitizedEvent.securityLevel === 'critical' || sanitizedEvent.crossTenantRisk) {
      this.flush(true) // Immediate flush for critical events
    } else if (this.auditBuffer.length >= this.maxBufferSize) {
      this.flush()
    }
    
    if (import.meta.env.DEV) {
      console.log('🔒 Audit Event Recorded:', {
        type: sanitizedEvent.eventType,
        outcome: sanitizedEvent.outcome,
        securityLevel: sanitizedEvent.securityLevel,
        crossTenantRisk: sanitizedEvent.crossTenantRisk,
      })
    }
  }
  
  /**
   * Record security violation with immediate alert
   */
  recordSecurityViolation(violation: SecurityViolation): void {
    this.securityViolations.push(violation)
    
    // Create critical audit event
    this.recordEvent({
      eventType: 'security_violation',
      resource: violation.affectedResources.join(','),
      action: `security_violation_${violation.type}`,
      outcome: 'denied',
      securityLevel: 'critical',
      metadata: {
        violationType: violation.type,
        severity: violation.severity,
        description: this.sanitizeString(violation.description),
        mitigationApplied: violation.mitigationApplied || 'none',
      },
    })
    
    // Record violation metrics
    this.metrics.record('security_violation', 1, {
      type: violation.type,
      severity: violation.severity,
    })
    
    if (import.meta.env.DEV) {
      console.error('🚨 Security Violation Recorded:', {
        type: violation.type,
        severity: violation.severity,
        resources: violation.affectedResources,
      })
    }
  }
  
  /**
   * Record SSE connection audit trail
   */
  recordSSEConnection(
    connectionId: string,
    projectId: string,
    action: 'connect' | 'disconnect' | 'heartbeat_timeout' | 'circuit_breaker',
    metadata?: Record<string, any>
  ): void {
    this.recordEvent({
      eventType: 'sse_connection',
      projectId: projectId,
      resource: `sse_connection:${connectionId}`,
      action: `sse_${action}`,
      outcome: action === 'circuit_breaker' || action === 'heartbeat_timeout' ? 'failure' : 'success',
      securityLevel: action === 'circuit_breaker' ? 'medium' : 'low',
      metadata: metadata ? this.sanitizeMetadata(metadata) : undefined,
    })
  }
  
  /**
   * Record episode commit audit trail
   */
  recordCommitAudit(
    projectId: string,
    episodeId: string,
    commitId: string,
    outcome: 'success' | 'duplicate' | 'no_change' | 'hash_mismatch' | 'failure',
    metadata?: Record<string, any>
  ): void {
    this.recordEvent({
      eventType: 'commit_submitted',
      projectId: projectId,
      episodeId: episodeId,
      resource: `episode:${episodeId}`,
      action: `commit_${outcome}`,
      outcome: outcome === 'success' || outcome === 'duplicate' || outcome === 'no_change' ? 'success' : 'failure',
      securityLevel: outcome === 'hash_mismatch' ? 'medium' : 'low',
      metadata: {
        commitId: commitId,
        ...this.sanitizeMetadata(metadata || {}),
      },
    })
  }
  
  /**
   * Check for cross-tenant access risks
   */
  private detectCrossTenantRisk(event: AuditEvent): boolean {
    // Simple heuristics for cross-tenant risk detection
    // In production, this would involve more sophisticated analysis
    
    // Check for rapid project switching
    if (event.eventType === 'project_accessed') {
      const recentProjectAccess = this.auditBuffer
        .filter(e => 
          e.eventType === 'project_accessed' && 
          e.userId === event.userId &&
          Date.now() - new Date(e.timestamp).getTime() < 60000 // Last minute
        )
        .map(e => e.projectId)
      
      const uniqueProjects = new Set(recentProjectAccess)
      if (uniqueProjects.size > 3) {
        return true // Accessing multiple projects quickly
      }
    }
    
    // Check for unusual episode access patterns
    if (event.eventType === 'episode_accessed') {
      const recentEpisodeAccess = this.auditBuffer
        .filter(e => 
          e.eventType === 'episode_accessed' && 
          e.userId === event.userId &&
          Date.now() - new Date(e.timestamp).getTime() < 300000 // Last 5 minutes
        )
        .map(e => e.projectId)
      
      const uniqueProjects = new Set(recentEpisodeAccess)
      if (uniqueProjects.size > 5) {
        return true // Accessing episodes across many projects
      }
    }
    
    return false
  }
  
  /**
   * Sanitize metadata to remove PII
   */
  private sanitizeMetadata(metadata: Record<string, any>): Record<string, any> {
    const sanitized: Record<string, any> = {}
    
    for (const [key, value] of Object.entries(metadata)) {
      // Skip potentially sensitive fields
      if (this.isSensitiveField(key)) {
        sanitized[key] = '[REDACTED]'
        continue
      }
      
      if (typeof value === 'string') {
        sanitized[key] = this.sanitizeString(value)
      } else if (typeof value === 'object' && value !== null) {
        sanitized[key] = this.sanitizeMetadata(value)
      } else {
        sanitized[key] = value
      }
    }
    
    return sanitized
  }
  
  /**
   * Check if field name suggests sensitive data
   */
  private isSensitiveField(fieldName: string): boolean {
    const sensitivePatterns = [
      /password/i,
      /token/i,
      /secret/i,
      /key/i,
      /email/i,
      /phone/i,
      /ssn/i,
      /credit/i,
      /card/i,
      /address/i,
    ]
    
    return sensitivePatterns.some(pattern => pattern.test(fieldName))
  }
  
  /**
   * Sanitize string content to remove PII patterns
   */
  private sanitizeString(input: string): string {
    if (input.length > 500) {
      input = input.slice(0, 500) + '...[TRUNCATED]'
    }
    
    return input
      // Remove email patterns
      .replace(/\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g, '[EMAIL]')
      // Remove phone patterns
      .replace(/\b\d{3}[-.]?\d{3}[-.]?\d{4}\b/g, '[PHONE]')
      // Remove potential API keys/tokens
      .replace(/[A-Za-z0-9]{32,}/g, match => match.slice(0, 8) + '[REDACTED]')
  }
  
  /**
   * Hash user ID for privacy
   */
  private hashUserId(userId: string): string {
    // Simple hash for demo - in production use proper crypto
    let hash = 0
    for (let i = 0; i < userId.length; i++) {
      const char = userId.charCodeAt(i)
      hash = ((hash << 5) - hash) + char
      hash = hash & hash // Convert to 32-bit integer
    }
    return `user_${Math.abs(hash).toString(16)}`
  }
  
  /**
   * Anonymize IP address
   */
  private anonymizeIP(ip: string): string {
    const parts = ip.split('.')
    if (parts.length === 4) {
      return `${parts[0]}.${parts[1]}.${parts[2]}.xxx`
    }
    return 'xxx.xxx.xxx.xxx'
  }
  
  /**
   * Sanitize user agent string
   */
  private sanitizeUserAgent(userAgent: string): string {
    // Remove potentially identifying information while keeping browser/OS info
    return userAgent
      .replace(/\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b/g, '[IP]') // Remove IPs
      .slice(0, 200) // Limit length
  }
  
  /**
   * Generate session ID
   */
  private generateSessionId(): string {
    return `sess_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
  }
  
  /**
   * Generate request ID
   */
  private generateRequestId(): string {
    return `req_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
  }
  
  /**
   * Flush audit events to backend
   */
  private flush(immediate: boolean = false): void {
    if (this.auditBuffer.length === 0) {
      return
    }
    
    const events = [...this.auditBuffer]
    this.auditBuffer = []
    
    const payload = {
      timestamp: new Date().toISOString(),
      events,
      immediate,
      source: 'frontend_audit',
    }
    
    try {
      const data = JSON.stringify(payload)
      
      // Use sendBeacon for reliability, especially on page unload
      if (navigator.sendBeacon && (immediate || document.visibilityState === 'hidden')) {
        const sent = navigator.sendBeacon('/api/audit', data)
        
        if (import.meta.env.DEV) {
          console.log(`🔒 Audit events sent via sendBeacon: ${events.length} events, immediate: ${immediate}`)
        }
        
        if (!sent) {
          // Fallback if sendBeacon fails
          this.sendViaFetch(data)
        }
      } else {
        this.sendViaFetch(data)
      }
      
    } catch (error) {
      if (import.meta.env.DEV) {
        console.error('🔒 Failed to flush audit events:', error)
      }
      
      // Re-queue events if flush fails (with limit)
      if (this.auditBuffer.length < this.maxBufferSize * 2) {
        this.auditBuffer.unshift(...events)
      }
    }
  }
  
  /**
   * Send audit data via fetch
   */
  private sendViaFetch(data: string): void {
    fetch('/api/audit', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: data,
      keepalive: true, // Important for page unload
    }).catch(error => {
      if (import.meta.env.DEV) {
        console.error('🔒 Fetch audit send failed:', error)
      }
    })
  }
  
  /**
   * Start periodic flush timer
   */
  private startFlushTimer(): void {
    this.flushTimer = setInterval(() => {
      this.flush()
    }, this.flushInterval)
  }
  
  /**
   * Setup flush on page unload
   */
  private setupUnloadFlush(): void {
    const flushOnUnload = () => {
      this.flush(true) // Immediate flush with sendBeacon
    }
    
    window.addEventListener('beforeunload', flushOnUnload)
    window.addEventListener('pagehide', flushOnUnload)
    
    // Flush on visibility change
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'hidden') {
        this.flush(true)
      }
    })
  }
  
  /**
   * Get audit statistics
   */
  getAuditStats(): {
    bufferedEvents: number
    securityViolations: number
    recentEventTypes: Record<string, number>
  } {
    const recentEventTypes: Record<string, number> = {}
    
    this.auditBuffer.forEach(event => {
      recentEventTypes[event.eventType] = (recentEventTypes[event.eventType] || 0) + 1
    })
    
    return {
      bufferedEvents: this.auditBuffer.length,
      securityViolations: this.securityViolations.length,
      recentEventTypes,
    }
  }
  
  /**
   * Export audit trail in structured format (for debugging)
   */
  exportAuditTrail(): {
    events: AuditEvent[]
    violations: SecurityViolation[]
    stats: any
  } {
    return {
      events: [...this.auditBuffer], // Copy to prevent mutation
      violations: [...this.securityViolations],
      stats: this.getAuditStats(),
    }
  }
  
  /**
   * Clear audit buffer (for testing)
   */
  clearBuffer(): void {
    this.auditBuffer = []
    this.securityViolations = []
    
    if (import.meta.env.DEV) {
      console.log('🔒 Audit buffer cleared')
    }
  }
  
  /**
   * Cleanup and stop timers
   */
  destroy(): void {
    if (this.flushTimer) {
      clearInterval(this.flushTimer)
      this.flushTimer = null
    }
    
    // Final flush
    this.flush(true)
  }
}

// Global audit trail service
export const auditTrail = new AuditTrailService()

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
  auditTrail.destroy()
})

// Global debugging helper
if (import.meta.env.DEV) {
  // @ts-expect-error - Global debugging helper
  window.auditTrail = auditTrail
}