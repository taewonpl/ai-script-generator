/**
 * SSE (Server-Sent Events) utilities for generation service
 * Handles dev/prod path consistency and request ID injection
 */

import { newRid } from '../api/clients'
import { globalSSECleanup } from '../../hooks/useSSECleanup'

/**
 * Build SSE URL with proper dev/prod routing and Last-Event-ID support
 * @param jobId - Generation job ID
 * @param params - Additional query parameters
 * @param lastEventId - Last Event ID for resuming connection
 * @returns Complete SSE URL for EventSource
 */
export const buildSSEUrl = (
  jobId: string, 
  params?: Record<string, string>,
  lastEventId?: string
): string => {
  // Dev uses proxy path, Prod uses direct path
  const base = import.meta.env.DEV ? '/api/generation/api/v1' : '/api/v1'
  
  // Build query parameters including request ID for tracing
  const queryParams = new URLSearchParams({
    rid: newRid(), // Request ID for SSE tracing (EventSource can't use custom headers)
    ...params,
  })
  
  // Add Last-Event-ID as query parameter for fallback support
  if (lastEventId) {
    queryParams.set('last-event-id', lastEventId)
  }
  
  const url = `${base}/generations/${jobId}/events`
  const fullUrl = `${url}?${queryParams.toString()}`
  
  if (import.meta.env.DEV) {
    console.log(`🔄 SSE URL built:`, fullUrl, { jobId, params, lastEventId })
  }
  
  return fullUrl
}

/**
 * Build WebSocket URL (for future use if needed)
 * @param jobId - Generation job ID
 * @param params - Additional query parameters
 * @returns WebSocket URL
 */
export const buildWebSocketUrl = (jobId: string, params?: Record<string, string>): string => {
  const base = import.meta.env.DEV ? '/api/generation/api/v1' : '/api/v1'
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const queryParams = new URLSearchParams({
    rid: newRid(),
    ...params,
  })
  
  const url = `${protocol}//${window.location.host}${base}/generations/${jobId}/ws`
  return `${url}?${queryParams.toString()}`
}

/**
 * Create EventSource with proper configuration
 * @param url - SSE URL (from buildSSEUrl)
 * @param options - EventSource options
 * @returns Configured EventSource instance
 */
export const createEventSource = (url: string, options?: EventSourceInit): EventSource => {
  // Extract request_id from URL for tracing
  const urlObj = new URL(url, window.location.origin)
  const requestId = urlObj.searchParams.get('rid') || 'unknown'
  const jobId = url.match(/generations\/([^\/]+)/)?.[1] || 'unknown'
  
  const eventSource = new EventSource(url, {
    withCredentials: true,
    ...options,
  })
  
  // Enhanced logging with ID tracing (always log for observability)
  const logData = {
    action: 'sse_connection',
    url,
    jobId,
    requestId,
    timestamp: new Date().toISOString(),
  }
  
  if (import.meta.env.DEV) {
    console.log(`📡 SSE EventSource created:`, logData)
  } else {
    console.log(JSON.stringify({
      level: 'info',
      event: 'sse_created',
      ...logData
    }))
  }
  
  eventSource.addEventListener('open', () => {
    const openLogData = {
      ...logData,
      action: 'sse_opened',
      readyState: eventSource.readyState,
    }
    
    if (import.meta.env.DEV) {
      console.log('✅ SSE Connection opened:', openLogData)
    } else {
      console.log(JSON.stringify({
        level: 'info',
        ...openLogData
      }))
    }
  })
  
  eventSource.addEventListener('error', (event) => {
    const errorLogData = {
      ...logData,
      action: 'sse_error',
      readyState: eventSource.readyState,
      error: 'EventSource error occurred',
    }
    
    if (import.meta.env.DEV) {
      console.error('❌ SSE Connection error:', errorLogData, event)
    } else {
      console.error(JSON.stringify({
        level: 'error',
        ...errorLogData
      }))
    }
  })
  
  eventSource.addEventListener('close', () => {
    const closeLogData = {
      ...logData,
      action: 'sse_closed',
      readyState: eventSource.readyState,
    }
    
    if (import.meta.env.DEV) {
      console.log('🔌 SSE Connection closed:', closeLogData)
    } else {
      console.log(JSON.stringify({
        level: 'info',
        ...closeLogData
      }))
    }
  })
  
  return eventSource
}

/**
 * Enhanced SSE connection helper with metrics, heartbeat timeout, and lifecycle management
 */
export class SSEConnection {
  private eventSource: EventSource | null = null
  private baseUrl: string
  private jobId: string
  private params?: Record<string, string>
  private lastEventId: string | null = null
  private retryCount = 0
  private maxRetries = 3
  private retryDelay = 1000
  private onMessage: (event: MessageEvent) => void
  private onError?: (error: Event) => void
  private connectionId: string
  private heartbeatTimeout: NodeJS.Timeout | null = null
  private lastHeartbeat = Date.now()
  private readonly HEARTBEAT_TIMEOUT_MS = 25000 // 25 seconds
  private isIntentionallyClosed = false
  private circuitBreakerUntil: number = 0
  private rapidReconnectCount = 0
  private readonly CIRCUIT_BREAKER_THRESHOLD = 5
  private readonly CIRCUIT_BREAKER_WINDOW_MS = 60000 // 1 minute
  private readonly CIRCUIT_BREAKER_DELAY_MS = 30000 // 30 seconds
  private scopeId: string
  
  constructor(
    jobId: string,
    onMessage: (event: MessageEvent) => void,
    onError?: (error: Event) => void,
    params?: Record<string, string>,
    scopeId?: string
  ) {
    this.jobId = jobId
    this.params = params
    this.onMessage = onMessage
    this.onError = onError
    this.connectionId = `${jobId}-${Date.now()}`
    this.scopeId = scopeId || 'default'
    
    // Register with global cleanup manager for route change handling
    globalSSECleanup.register(
      this.connectionId,
      () => this.disconnect(),
      `Generation SSE: ${jobId}`,
      { 
        scopeId: this.scopeId, 
        canContinueInBackground: true // Generation can continue in background
      }
    )
    
    // Import metrics dynamically to avoid circular dependencies
    import('@/shared/services/metrics/sseMetrics').then(({ sseMetrics }) => {
      this.recordMetrics = (action: string, ...args: any[]) => {
        switch (action) {
          case 'opened':
            sseMetrics.recordConnectionOpened(this.connectionId)
            break
          case 'closed':
            sseMetrics.recordConnectionClosed(this.connectionId)
            break
          case 'reconnect':
            sseMetrics.recordReconnection(this.connectionId, args[0])
            break
          case 'heartbeat_timeout':
            sseMetrics.recordHeartbeatTimeout(this.connectionId)
            break
          case 'circuit_breaker_activated':
            sseMetrics.recordCircuitBreakerActivated(this.connectionId, args[0])
            break
          case 'manual_retry':
            sseMetrics.recordManualRetry(this.connectionId)
            break
        }
      }
    }).catch(() => {
      // Graceful fallback if metrics module fails to load
      this.recordMetrics = () => {}
    })
  }
  
  private recordMetrics: (action: string, ...args: any[]) => void = () => {}
  
  connect(): void {
    try {
      // Check circuit breaker
      if (Date.now() < this.circuitBreakerUntil) {
        const remainingMs = this.circuitBreakerUntil - Date.now()
        console.warn(`🚫 Circuit breaker active. Manual retry available in ${Math.ceil(remainingMs / 1000)}s`)
        return
      }

      this.isIntentionallyClosed = false
      
      // Build URL with Last-Event-ID support
      const url = buildSSEUrl(this.jobId, this.params, this.lastEventId || undefined)
      this.eventSource = createEventSource(url)
      
      // Enhanced message handler with heartbeat tracking and event ID capture
      this.eventSource.onmessage = (event) => {
        this.lastHeartbeat = Date.now()
        this.resetHeartbeatTimeout()
        
        // Capture Last-Event-ID for resumption (actual implementation)
        if (event.lastEventId) {
          this.lastEventId = event.lastEventId
        }
        
        this.onMessage(event)
      }
      
      this.eventSource.onerror = (event) => {
        const now = Date.now()
        console.error(`SSE Error (attempt ${this.retryCount + 1}):`, event)
        this.clearHeartbeatTimeout()
        
        if (this.onError) {
          this.onError(event)
        }
        
        // Circuit breaker logic: track rapid reconnects
        if (now - this.lastHeartbeat < this.CIRCUIT_BREAKER_WINDOW_MS) {
          this.rapidReconnectCount++
          
          if (this.rapidReconnectCount >= this.CIRCUIT_BREAKER_THRESHOLD) {
            this.circuitBreakerUntil = now + this.CIRCUIT_BREAKER_DELAY_MS
            this.rapidReconnectCount = 0
            console.warn(`🚫 Circuit breaker activated: ${this.CIRCUIT_BREAKER_THRESHOLD} failures in ${this.CIRCUIT_BREAKER_WINDOW_MS/1000}s. Wait ${this.CIRCUIT_BREAKER_DELAY_MS/1000}s or manually retry.`)
            this.recordMetrics('circuit_breaker_activated', this.retryCount + 1)
            return
          }
        } else {
          // Reset counter if outside window
          this.rapidReconnectCount = 0
        }
        
        // Auto-retry with exponential backoff - removed Retry-After header check
        // (EventSource cannot read response headers)
        if (this.retryCount < this.maxRetries && !this.isIntentionallyClosed) {
          const baseDelay = this.retryDelay * Math.pow(2, this.retryCount)
          const jitter = Math.random() * 0.1 * baseDelay // Add jitter
          const retryDelay = Math.floor(baseDelay + jitter)
          
          console.log(`⏳ Retrying SSE connection in ${retryDelay}ms... (attempt ${this.retryCount + 1}/${this.maxRetries})`)
          this.recordMetrics('reconnect', this.retryCount + 1)
          
          setTimeout(() => {
            this.retryCount++
            this.disconnect()
            this.connect()
          }, retryDelay)
        } else if (!this.isIntentionallyClosed) {
          console.error('❌ SSE connection failed after maximum retries')
        }
      }
      
      this.eventSource.onopen = () => {
        console.log('✅ SSE Connection established')
        this.retryCount = 0 // Reset retry count on successful connection
        this.rapidReconnectCount = 0 // Reset circuit breaker counter
        this.lastHeartbeat = Date.now()
        this.resetHeartbeatTimeout()
        this.recordMetrics('opened')
      }
    } catch (error) {
      console.error('Failed to create SSE connection:', error)
      if (this.onError) {
        this.onError(error as Event)
      }
    }
  }
  
  private resetHeartbeatTimeout(): void {
    this.clearHeartbeatTimeout()
    
    this.heartbeatTimeout = setTimeout(() => {
      const timeSinceLastHeartbeat = Date.now() - this.lastHeartbeat
      console.warn(`💓 SSE Heartbeat timeout after ${timeSinceLastHeartbeat}ms (threshold: ${this.HEARTBEAT_TIMEOUT_MS}ms)`)
      
      this.recordMetrics('heartbeat_timeout')
      
      // Force reconnection on heartbeat timeout
      if (!this.isIntentionallyClosed) {
        console.log('🔄 Attempting reconnection due to heartbeat timeout...')
        this.disconnect()
        this.connect()
      }
    }, this.HEARTBEAT_TIMEOUT_MS)
  }
  
  /**
   * Manual retry method to bypass circuit breaker
   */
  manualRetry(): void {
    console.log('🔄 Manual retry requested - bypassing circuit breaker')
    this.circuitBreakerUntil = 0
    this.rapidReconnectCount = 0
    this.retryCount = 0
    this.recordMetrics('manual_retry')
    this.disconnect()
    this.connect()
  }
  
  /**
   * Check if circuit breaker is active
   */
  isCircuitBreakerActive(): boolean {
    return Date.now() < this.circuitBreakerUntil
  }
  
  /**
   * Get remaining circuit breaker time in seconds
   */
  getCircuitBreakerRemainingSeconds(): number {
    if (!this.isCircuitBreakerActive()) return 0
    return Math.ceil((this.circuitBreakerUntil - Date.now()) / 1000)
  }
  
  /**
   * Get actual time since last heartbeat in milliseconds
   */
  getTimeSinceLastHeartbeat(): number {
    return Date.now() - this.lastHeartbeat
  }
  
  /**
   * Get scope ID for this connection
   */
  getScopeId(): string {
    return this.scopeId
  }
  
  private clearHeartbeatTimeout(): void {
    if (this.heartbeatTimeout) {
      clearTimeout(this.heartbeatTimeout)
      this.heartbeatTimeout = null
    }
  }
  
  disconnect(): void {
    this.isIntentionallyClosed = true
    this.clearHeartbeatTimeout()
    
    if (this.eventSource) {
      this.eventSource.close()
      this.eventSource = null
      this.recordMetrics('closed')
      console.log(`🔌 SSE Connection closed (scope: ${this.scopeId})`)
    }
    
    // Unregister from global cleanup manager
    globalSSECleanup.unregister(this.connectionId)
  }
  
  isConnected(): boolean {
    return this.eventSource?.readyState === EventSource.OPEN
  }
}

/**
 * Export for easy testing and debugging
 */
export const SSE_CONFIG = {
  DEV_BASE: '/api/generation/api/v1',
  PROD_BASE: '/api/v1',
  CURRENT_BASE: import.meta.env.DEV ? '/api/generation/api/v1' : '/api/v1',
} as const