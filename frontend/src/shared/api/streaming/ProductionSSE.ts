/**
 * Production-level SSE implementation with Last-Event-ID support,
 * jittered backoff, and distributed environment compatibility
 */

import type {
  SSEConnectionState,
  SSEOptions,
  SSEHookReturn,
  TypedSSEEventData,
  SSEEventData,
} from './types'

const DEFAULT_RETRY_DELAYS = [1000, 2000, 5000, 15000] // 1s, 2s, 5s, 15s
const DEFAULT_MAX_RETRIES = 10
const DEFAULT_HEARTBEAT_TIMEOUT = 45000 // 45 seconds (30s heartbeat + 15s grace)
const DEFAULT_MANUAL_RETRY_TIMEOUT = 60000 // 60 seconds before showing manual retry

interface ProductionSSEOptions extends SSEOptions {
  enableJitter?: boolean
  manualRetryTimeout?: number
  enableLastEventId?: boolean
}

interface SSEConnectionStats {
  totalReconnects: number
  lastReconnectAt: Date | null
  connectionDuration: number
  missedHeartbeats: number
}

/**
 * Production-ready SSE client with enterprise features
 */
export class ProductionSSEClient {
  private eventSource: EventSource | null = null
  private connectionState: SSEConnectionState = 'idle'
  private retryTimeoutId: NodeJS.Timeout | null = null
  private heartbeatTimeoutId: NodeJS.Timeout | null = null
  private manualRetryTimeoutId: NodeJS.Timeout | null = null

  // State tracking
  private events: TypedSSEEventData[] = []
  private latestEvent: TypedSSEEventData | null = null
  private error: Error | null = null
  private retryCount = 0
  private lastConnectedAt: Date | null = null
  private lastEventId: string | null = null
  private connectionStats: SSEConnectionStats = {
    totalReconnects: 0,
    lastReconnectAt: null,
    connectionDuration: 0,
    missedHeartbeats: 0,
  }

  // Event listeners
  private onStateChange?: (state: SSEConnectionState) => void
  private onEvent?: (event: TypedSSEEventData) => void
  private onError?: (error: Error) => void
  private onManualRetryAvailable?: () => void

  constructor(private options: ProductionSSEOptions) {
    const {
      maxRetries = DEFAULT_MAX_RETRIES,
      retryDelays = DEFAULT_RETRY_DELAYS,
      heartbeatTimeout = DEFAULT_HEARTBEAT_TIMEOUT,
      enableJitter = true,
      manualRetryTimeout = DEFAULT_MANUAL_RETRY_TIMEOUT,
      enableLastEventId = true,
    } = options

    this.options = {
      ...options,
      maxRetries,
      retryDelays,
      heartbeatTimeout,
      enableJitter,
      manualRetryTimeout,
      enableLastEventId,
    }
  }

  /**
   * Connect to SSE endpoint with Last-Event-ID support
   */
  connect(url: string): void {
    if (this.connectionState === 'open') {
      return // Already connected
    }

    console.log(
      `🔄 Connecting to SSE: ${url} (attempt ${this.retryCount + 1}/${this.options.maxRetries})`,
    )

    this.setConnectionState('connecting')
    this.clearTimeouts()

    try {
      // Close existing connection
      this.cleanup()

      // Build URL with Last-Event-ID support
      const eventSourceUrl = this.buildEventSourceUrl(url)

      // Create EventSource with Last-Event-ID header if supported
      this.eventSource = new EventSource(eventSourceUrl, {
        withCredentials: this.options.withCredentials,
      })

      this.setupEventListeners()
      this.startHeartbeatMonitoring()
    } catch (err) {
      console.error('❌ Failed to create SSE connection:', err)
      this.handleConnectionError(err as Error)
    }
  }

  /**
   * Disconnect and clean up
   */
  disconnect(): void {
    console.log('🔌 Disconnecting SSE')
    this.setConnectionState('closed')
    this.cleanup()
    this.retryCount = 0
  }

  /**
   * Manual retry with connection recovery
   */
  manualRetry(): boolean {
    if (!this.canManualRetry()) {
      return false
    }

    console.log('🔄 Manual retry initiated')

    // Reset retry count for fresh attempts
    this.retryCount = 0
    this.error = null

    // Reconnect with original URL
    this.connect(this.options.url!)
    return true
  }

  /**
   * Check if manual retry is available
   */
  canManualRetry(): boolean {
    return this.connectionState === 'closed' && this.error !== null
  }

  /**
   * Get connection statistics
   */
  getConnectionStats(): SSEConnectionStats {
    return { ...this.connectionStats }
  }

  /**
   * Set event listeners
   */
  setEventListeners(listeners: {
    onStateChange?: (state: SSEConnectionState) => void
    onEvent?: (event: TypedSSEEventData) => void
    onError?: (error: Error) => void
    onManualRetryAvailable?: () => void
  }): void {
    this.onStateChange = listeners.onStateChange
    this.onEvent = listeners.onEvent
    this.onError = listeners.onError
    this.onManualRetryAvailable = listeners.onManualRetryAvailable
  }

  // Private methods

  private buildEventSourceUrl(url: string): string {
    // For browsers that don't support Last-Event-ID header in EventSource constructor,
    // we can append it as a query parameter
    if (this.options.enableLastEventId && this.lastEventId) {
      const urlObj = new URL(url)
      urlObj.searchParams.set('lastEventId', this.lastEventId)
      return urlObj.toString()
    }
    return url
  }

  private setupEventListeners(): void {
    if (!this.eventSource) return

    // Connection opened
    this.eventSource.onopen = () => {
      console.log('✅ SSE connection opened')
      this.setConnectionState('open')
      this.retryCount = 0
      this.lastConnectedAt = new Date()

      // Update connection stats
      if (this.connectionStats.lastReconnectAt) {
        this.connectionStats.totalReconnects++
      }
      this.connectionStats.lastReconnectAt = new Date()
    }

    // Connection error
    this.eventSource.onerror = error => {
      console.error('❌ SSE connection error:', error)

      if (this.eventSource?.readyState === EventSource.CLOSED) {
        this.setConnectionState('closed')
      } else if (this.canRetry()) {
        this.setConnectionState('retrying')
        this.scheduleRetry()
      } else {
        this.setConnectionState('closed')
        this.error = new Error(
          `SSE connection failed after ${this.options.maxRetries} retries`,
        )
        this.scheduleManualRetry()
      }
    }

    // Set up event type listeners
    this.setupEventTypeListeners()
  }

  private setupEventTypeListeners(): void {
    if (!this.eventSource) return

    const eventTypes = [
      'progress',
      'preview',
      'completed',
      'failed',
      'heartbeat',
    ]

    eventTypes.forEach(eventType => {
      this.eventSource!.addEventListener(eventType, (event: MessageEvent) => {
        try {
          const eventData: SSEEventData = JSON.parse(event.data)
          const typedEvent = eventData as TypedSSEEventData

          console.log('📡 SSE Event received:', typedEvent)

          // Store Last-Event-ID if available
          if (this.options.enableLastEventId && event.lastEventId) {
            this.lastEventId = event.lastEventId
          }

          // Update events
          this.events.push(typedEvent)
          this.latestEvent = typedEvent

          // Handle heartbeat
          if (typedEvent.type === 'heartbeat') {
            this.handleHeartbeat()
          }

          // Notify listener
          this.onEvent?.(typedEvent)
        } catch (err) {
          console.error('❌ Failed to parse SSE event:', err)
          this.error = new Error('Failed to parse SSE event data')
          this.onError?.(this.error)
        }
      })
    })
  }

  private handleHeartbeat(): void {
    this.startHeartbeatMonitoring() // Reset timeout
    this.connectionStats.missedHeartbeats = 0
  }

  private startHeartbeatMonitoring(): void {
    this.clearHeartbeatTimeout()

    this.heartbeatTimeoutId = setTimeout(() => {
      console.warn('⚠️ SSE heartbeat timeout - connection may be stale')
      this.connectionStats.missedHeartbeats++

      if (this.connectionState === 'open') {
        this.setConnectionState('retrying')
        this.scheduleRetry()
      }
    }, this.options.heartbeatTimeout!)
  }

  private canRetry(): boolean {
    return this.retryCount < this.options.maxRetries!
  }

  private scheduleRetry(): void {
    const delayIndex = Math.min(
      this.retryCount,
      this.options.retryDelays!.length - 1,
    )
    let delay = this.options.retryDelays![delayIndex]

    // Add jitter to prevent thundering herd
    if (this.options.enableJitter) {
      const jitter = delay * 0.1 * (Math.random() * 2 - 1) // ±10% jitter
      delay = Math.max(100, delay + jitter) // Minimum 100ms
    }

    console.log(
      `⏱️ Scheduling SSE retry in ${Math.round(delay)}ms (attempt ${this.retryCount + 1}/${this.options.maxRetries})`,
    )

    this.retryTimeoutId = setTimeout(() => {
      this.retryCount++
      this.connect(this.options.url!)
    }, delay)
  }

  private scheduleManualRetry(): void {
    console.log(
      `⏳ Manual retry will be available in ${this.options.manualRetryTimeout! / 1000}s`,
    )

    this.manualRetryTimeoutId = setTimeout(() => {
      console.log('🔄 Manual retry now available')
      this.onManualRetryAvailable?.()
    }, this.options.manualRetryTimeout!)
  }

  private handleConnectionError(error: Error): void {
    console.error('SSE connection error:', error)
    this.error = error
    this.onError?.(error)

    if (this.canRetry()) {
      this.setConnectionState('retrying')
      this.scheduleRetry()
    } else {
      this.setConnectionState('closed')
      this.scheduleManualRetry()
    }
  }

  private setConnectionState(state: SSEConnectionState): void {
    if (this.connectionState !== state) {
      this.connectionState = state
      console.log(`🔄 SSE State: ${state}`)
      this.onStateChange?.(state)
    }
  }

  private clearTimeouts(): void {
    if (this.retryTimeoutId) {
      clearTimeout(this.retryTimeoutId)
      this.retryTimeoutId = null
    }
    this.clearHeartbeatTimeout()
    this.clearManualRetryTimeout()
  }

  private clearHeartbeatTimeout(): void {
    if (this.heartbeatTimeoutId) {
      clearTimeout(this.heartbeatTimeoutId)
      this.heartbeatTimeoutId = null
    }
  }

  private clearManualRetryTimeout(): void {
    if (this.manualRetryTimeoutId) {
      clearTimeout(this.manualRetryTimeoutId)
      this.manualRetryTimeoutId = null
    }
  }

  private cleanup(): void {
    if (this.eventSource) {
      this.eventSource.close()
      this.eventSource = null
    }
    this.clearTimeouts()
  }

  // Public getters
  get state(): SSEConnectionState {
    return this.connectionState
  }

  get allEvents(): TypedSSEEventData[] {
    return [...this.events]
  }

  get lastEvent(): TypedSSEEventData | null {
    return this.latestEvent
  }

  get currentError(): Error | null {
    return this.error
  }

  get reconnectCount(): number {
    return this.connectionStats.totalReconnects
  }
}

/**
 * Production SSE Hook with enhanced features
 */
export function useProductionSSE(
  options: ProductionSSEOptions,
): SSEHookReturn & {
  manualRetry: () => boolean
  canManualRetry: boolean
  connectionStats: SSEConnectionStats
} {
  // Implementation would use the ProductionSSEClient
  // This is a placeholder showing the enhanced interface
  throw new Error(
    'Implementation needed - use ProductionSSEClient directly for now',
  )
}
