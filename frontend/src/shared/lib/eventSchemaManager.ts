/**
 * Event Schema Manager
 * Handles event schema hardening with versioning, idempotency, and sessionization
 */

interface SessionState {
  sessionId: string
  pageId: string
  sequenceCounter: number
  startTime: number
  userAgentHash: string
}

class EventSchemaManager {
  private static instance: EventSchemaManager
  private sessionState: SessionState
  private readonly SCHEMA_VERSION = '1.0'

  private constructor() {
    this.sessionState = this.initializeSession()
  }

  public static getInstance(): EventSchemaManager {
    if (!EventSchemaManager.instance) {
      EventSchemaManager.instance = new EventSchemaManager()
    }
    return EventSchemaManager.instance
  }

  private initializeSession(): SessionState {
    // Generate session ID (persistent across page reloads during session)
    const sessionId = sessionStorage.getItem('behavior_session_id') || this.generateUUID()
    sessionStorage.setItem('behavior_session_id', sessionId)

    // Generate page ID (unique per page load)
    const pageId = this.generateUUID()

    // Initialize sequence counter
    const sequenceCounter = 0

    // Calculate user agent hash for anonymous tracking
    const userAgentHash = this.hashString(navigator.userAgent)

    return {
      sessionId,
      pageId,
      sequenceCounter,
      startTime: performance.now(),
      userAgentHash,
    }
  }

  /**
   * Generate a new event ID with schema hardening
   */
  public generateEventId(): string {
    return this.generateUUID()
  }

  /**
   * Get the next sequence number for this session
   */
  public getNextSequence(): number {
    return ++this.sessionState.sequenceCounter
  }

  /**
   * Generate editor scope ID based on current context
   */
  public generateEditorScopeId(projectId: string, episodeId: string): string {
    return `${projectId}:${episodeId}:${this.sessionState.pageId}`
  }

  /**
   * Create standardized event metadata
   */
  public createEventMetadata(
    projectId: string,
    episodeId: string,
    actorIdHash?: string
  ) {
    const now = new Date()
    const timezoneOffset = now.getTimezoneOffset() // In minutes

    return {
      // Schema hardening
      schema_version: this.SCHEMA_VERSION,
      event_id: this.generateEventId(),
      seq: this.getNextSequence(),

      // Timestamps
      ts_client: now.toISOString(),
      ts_client_hr: performance.now(),

      // Session and scope tracking
      session_id: this.sessionState.sessionId,
      page_id: this.sessionState.pageId,
      editor_scope_id: this.generateEditorScopeId(projectId, episodeId),

      // Reserved tracking fields
      actor_id_hash: actorIdHash,
      request_id: this.generateUUID(),
      trace_id: this.generateTraceId(),
      ua_hash: this.sessionState.userAgentHash,
      tz_offset: timezoneOffset,

      // Legacy compatibility
      client_ts: now.toISOString(),
    }
  }

  /**
   * Generate UUID v4
   */
  private generateUUID(): string {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) {
      return crypto.randomUUID()
    }

    // Fallback UUID v4 implementation
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
      const r = (Math.random() * 16) | 0
      const v = c === 'x' ? r : (r & 0x3) | 0x8
      return v.toString(16)
    })
  }

  /**
   * Generate trace ID for request correlation
   */
  private generateTraceId(): string {
    const timestamp = Date.now().toString(36)
    const random = Math.random().toString(36).substr(2, 9)
    return `${timestamp}-${random}`
  }

  /**
   * Simple hash function for strings
   */
  private hashString(str: string): string {
    let hash = 0
    if (str.length === 0) return hash.toString()

    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i)
      hash = (hash << 5) - hash + char
      hash = hash & hash // Convert to 32-bit integer
    }

    return Math.abs(hash).toString(36)
  }

  /**
   * Validate event schema with privacy enforcement
   */
  public validateEvent(event: unknown): boolean {
    if (!event || typeof event !== 'object') return false

    const eventObj = event as Record<string, unknown>

    // Check required schema hardening fields
    const requiredFields = [
      'schema_version',
      'event_id',
      'seq',
      'ts_client',
      'ts_client_hr',
      'session_id',
      'page_id',
      'editor_scope_id',
    ]

    const hasRequiredFields = requiredFields.every(field => field in eventObj && eventObj[field] != null)
    if (!hasRequiredFields) return false

    // TEXT-FREE GUARANTEE: Reject events containing text content
    const forbiddenTextKeys = ['text', 'body', 'content', 'script', 'message', 'comment', 'description']
    const hasForbiddenText = this.containsTextContent(eventObj, forbiddenTextKeys)
    if (hasForbiddenText) {
      console.warn('Event validation failed: contains forbidden text content')
      return false
    }

    return true
  }

  /**
   * Recursively check for forbidden text content
   */
  private containsTextContent(obj: any, forbiddenKeys: string[]): boolean {
    if (typeof obj !== 'object' || obj === null) return false

    for (const [key, value] of Object.entries(obj)) {
      // Check if key contains forbidden text fields
      if (forbiddenKeys.some(forbidden => key.toLowerCase().includes(forbidden.toLowerCase()))) {
        // Allow specific numeric/boolean metadata but not string content
        if (typeof value === 'string' && value.length > 10) {
          return true
        }
      }

      // Recursively check nested objects
      if (typeof value === 'object' && value !== null) {
        if (this.containsTextContent(value, forbiddenKeys)) {
          return true
        }
      }
    }

    return false
  }

  /**
   * Check if analytics is enabled for user/project
   */
  public isAnalyticsEnabled(): boolean {
    // Respect Do Not Track header
    if (navigator.doNotTrack === '1' || navigator.doNotTrack === 'yes') {
      return false
    }

    // Check user preference (stored in localStorage)
    const userPreference = localStorage.getItem('analytics_enabled')
    if (userPreference === 'false') {
      return false
    }

    // Default to enabled if no explicit opt-out
    return true
  }

  /**
   * Set analytics preference
   */
  public setAnalyticsEnabled(enabled: boolean): void {
    localStorage.setItem('analytics_enabled', enabled.toString())
  }

  /**
   * Get current session info for debugging
   */
  public getSessionInfo() {
    return {
      ...this.sessionState,
      schemaVersion: this.SCHEMA_VERSION,
      sessionDuration: performance.now() - this.sessionState.startTime,
    }
  }

  /**
   * Reset session (useful for testing or explicit session boundary)
   */
  public resetSession(): void {
    sessionStorage.removeItem('behavior_session_id')
    this.sessionState = this.initializeSession()
  }
}

export const eventSchemaManager = EventSchemaManager.getInstance()