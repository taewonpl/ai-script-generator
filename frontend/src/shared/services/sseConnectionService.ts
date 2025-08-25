/**
 * SSE Connection Management Service
 * Handles EventSource connections with reconnection logic and error handling
 */

import type {
  SSEEventData,
  SSEConnectionStatus,
  SSEEventHandlers,
  ProgressEventData,
  PreviewEventData,
  CompletedEventData,
  FailedEventData,
  HeartbeatEventData,
  SSEConnectionError,
} from '../types/generation'

export class SSEConnectionService {
  private eventSource: EventSource | null = null
  private connectionStatus: SSEConnectionStatus = {
    state: 'closed',
    retryCount: 0,
    maxRetries: 5,
  }
  private retryTimeoutId: number | null = null
  private heartbeatTimeoutId: number | null = null
  private handlers: SSEEventHandlers = {}
  private retryDelays = [1000, 2000, 5000] // Exponential backoff: 1s → 2s → 5s
  private heartbeatTimeout = 60000 // 60 seconds timeout for heartbeat
  private currentJobId: string | null = null
  private isIntentionallyClosed = false

  constructor(handlers: SSEEventHandlers = {}) {
    this.handlers = handlers
    this.bindMethods()
  }

  private bindMethods() {
    this.connect = this.connect.bind(this)
    this.disconnect = this.disconnect.bind(this)
    this.handleOpen = this.handleOpen.bind(this)
    this.handleError = this.handleError.bind(this)
    this.handleMessage = this.handleMessage.bind(this)
  }

  /**
   * Connect to SSE endpoint
   */
  public connect(sseUrl: string, jobId: string): void {
    this.currentJobId = jobId
    this.isIntentionallyClosed = false

    // Clean up existing connection
    this.cleanup()

    // Update connection status
    this.updateConnectionStatus({
      state: 'connecting',
      retryCount: this.connectionStatus.retryCount,
      maxRetries: this.connectionStatus.maxRetries,
    })

    try {
      this.eventSource = new EventSource(sseUrl)

      // Set up event listeners
      this.eventSource.onopen = this.handleOpen
      this.eventSource.onerror = this.handleError

      // Set up specific event type listeners
      this.setupEventTypeListeners()

      // Start heartbeat monitoring
      this.startHeartbeatMonitoring()
    } catch (error) {
      console.error('Failed to create EventSource:', error)
      this.handleConnectionError(error as Error)
    }
  }

  /**
   * Disconnect from SSE endpoint
   */
  public disconnect(): void {
    this.isIntentionallyClosed = true
    this.cleanup()

    this.updateConnectionStatus({
      state: 'closed',
      retryCount: 0,
      maxRetries: this.connectionStatus.maxRetries,
    })
  }

  /**
   * Get current connection status
   */
  public getConnectionStatus(): SSEConnectionStatus {
    return { ...this.connectionStatus }
  }

  /**
   * Update event handlers
   */
  public updateHandlers(handlers: Partial<SSEEventHandlers>): void {
    this.handlers = { ...this.handlers, ...handlers }
  }

  private setupEventTypeListeners(): void {
    if (!this.eventSource) return

    // Progress events
    this.eventSource.addEventListener('progress', (event: MessageEvent) => {
      try {
        const data: ProgressEventData = JSON.parse(event.data)
        this.handlers.onProgress?.(data)
      } catch (error) {
        console.error('Failed to parse progress event:', error)
      }
    })

    // Preview events
    this.eventSource.addEventListener('preview', (event: MessageEvent) => {
      try {
        const data: PreviewEventData = JSON.parse(event.data)
        this.handlers.onPreview?.(data)
      } catch (error) {
        console.error('Failed to parse preview event:', error)
      }
    })

    // Completed events
    this.eventSource.addEventListener('completed', (event: MessageEvent) => {
      try {
        const data: CompletedEventData = JSON.parse(event.data)
        this.handlers.onCompleted?.(data)
        // Connection will close naturally after completion
      } catch (error) {
        console.error('Failed to parse completed event:', error)
      }
    })

    // Failed events
    this.eventSource.addEventListener('failed', (event: MessageEvent) => {
      try {
        const data: FailedEventData = JSON.parse(event.data)
        this.handlers.onFailed?.(data)
        // Connection will close naturally after failure
      } catch (error) {
        console.error('Failed to parse failed event:', error)
      }
    })

    // Heartbeat events
    this.eventSource.addEventListener('heartbeat', (event: MessageEvent) => {
      try {
        const data: HeartbeatEventData = JSON.parse(event.data)
        this.handleHeartbeat(data)
        this.handlers.onHeartbeat?.(data)
      } catch (error) {
        console.error('Failed to parse heartbeat event:', error)
      }
    })
  }

  private handleOpen = (): void => {
    console.log('SSE connection opened')

    this.updateConnectionStatus({
      state: 'connected',
      retryCount: 0, // Reset retry count on successful connection
      maxRetries: this.connectionStatus.maxRetries,
      error: undefined,
    })

    // Clear any pending retry
    if (this.retryTimeoutId) {
      clearTimeout(this.retryTimeoutId)
      this.retryTimeoutId = null
    }
  }

  private handleError = (): void => {
    if (this.isIntentionallyClosed) {
      return // Don't handle errors if intentionally closed
    }

    console.warn('SSE connection error')

    const error = new Error('SSE connection error') as SSEConnectionError
    error.connectionState = 'error'
    error.retryCount = this.connectionStatus.retryCount
    error.canRetry =
      this.connectionStatus.retryCount < this.connectionStatus.maxRetries

    this.handleConnectionError(error)
  }

  private handleMessage = (event: MessageEvent): void => {
    try {
      const data: SSEEventData = JSON.parse(event.data)
      console.log('SSE message received:', data)
    } catch (error) {
      console.error('Failed to parse SSE message:', error)
    }
  }

  private handleHeartbeat(data: HeartbeatEventData): void {
    this.updateConnectionStatus({
      ...this.connectionStatus,
      lastHeartbeat: data.timestamp,
    })

    // Reset heartbeat timeout
    this.startHeartbeatMonitoring()
  }

  private startHeartbeatMonitoring(): void {
    // Clear existing timeout
    if (this.heartbeatTimeoutId) {
      clearTimeout(this.heartbeatTimeoutId)
    }

    // Set new timeout
    this.heartbeatTimeoutId = window.setTimeout(() => {
      console.warn('Heartbeat timeout - connection may be dead')

      if (
        !this.isIntentionallyClosed &&
        this.connectionStatus.state === 'connected'
      ) {
        this.handleConnectionError(new Error('Heartbeat timeout'))
      }
    }, this.heartbeatTimeout)
  }

  private handleConnectionError(error: Error): void {
    console.error('SSE connection error:', error)

    this.updateConnectionStatus({
      state: 'error',
      retryCount: this.connectionStatus.retryCount,
      maxRetries: this.connectionStatus.maxRetries,
      error: error.message,
    })

    // Notify error handler
    this.handlers.onError?.(error)

    // Attempt reconnection if retries are available
    if (!this.isIntentionallyClosed && this.canRetry()) {
      this.scheduleReconnection()
    }
  }

  private canRetry(): boolean {
    return this.connectionStatus.retryCount < this.connectionStatus.maxRetries
  }

  private scheduleReconnection(): void {
    const retryCount = this.connectionStatus.retryCount
    const delayIndex = Math.min(retryCount, this.retryDelays.length - 1)
    const delay = this.retryDelays[delayIndex]

    console.log(
      `Scheduling reconnection attempt ${retryCount + 1}/${this.connectionStatus.maxRetries} in ${delay}ms`,
    )

    this.updateConnectionStatus({
      ...this.connectionStatus,
      retryCount: retryCount + 1,
      nextRetryIn: delay / 1000,
    })

    // Update countdown
    this.startRetryCountdown(delay)

    this.retryTimeoutId = window.setTimeout(() => {
      if (!this.isIntentionallyClosed && this.currentJobId) {
        console.log(
          `Attempting reconnection ${retryCount + 1}/${this.connectionStatus.maxRetries}`,
        )
        this.reconnect()
      }
    }, delay)
  }

  private startRetryCountdown(totalDelay: number): void {
    const startTime = Date.now()
    const updateInterval = 1000 // Update every second

    const updateCountdown = () => {
      if (
        this.isIntentionallyClosed ||
        this.connectionStatus.state === 'connected'
      ) {
        return // Stop countdown if connection is restored or closed
      }

      const elapsed = Date.now() - startTime
      const remaining = Math.max(0, totalDelay - elapsed)
      const secondsRemaining = Math.ceil(remaining / 1000)

      this.updateConnectionStatus({
        ...this.connectionStatus,
        nextRetryIn: secondsRemaining,
      })

      if (remaining > 0) {
        setTimeout(updateCountdown, updateInterval)
      }
    }

    updateCountdown()
  }

  private reconnect(): void {
    if (!this.currentJobId) {
      console.error('Cannot reconnect: no job ID available')
      return
    }

    // Clean up current connection
    this.cleanup()

    // Reconstruct SSE URL (assuming the original pattern)
    const baseUrl = import.meta.env.PROD
      ? '/api/v1'
      : 'http://localhost:8000/api/v1'
    const sseUrl = `${baseUrl}/generations/${this.currentJobId}/events`

    // Reconnect
    this.connect(sseUrl, this.currentJobId)
  }

  private updateConnectionStatus(status: Partial<SSEConnectionStatus>): void {
    this.connectionStatus = { ...this.connectionStatus, ...status }
    this.handlers.onConnectionChange?.(this.connectionStatus)
  }

  private cleanup(): void {
    // Close EventSource
    if (this.eventSource) {
      this.eventSource.close()
      this.eventSource = null
    }

    // Clear timeouts
    if (this.retryTimeoutId) {
      clearTimeout(this.retryTimeoutId)
      this.retryTimeoutId = null
    }

    if (this.heartbeatTimeoutId) {
      clearTimeout(this.heartbeatTimeoutId)
      this.heartbeatTimeoutId = null
    }
  }

  /**
   * Force a manual retry attempt with improved error recovery
   */
  public forceRetry(): boolean {
    if (!this.currentJobId) {
      console.error('Cannot retry: no job ID available')
      return false
    }

    console.log('Forcing manual retry with connection recovery')

    // Reset retry count to allow fresh attempts
    this.connectionStatus.retryCount = 0

    // Clear any existing timeouts
    this.cleanup()

    // Update status to show manual retry is happening
    this.updateConnectionStatus({
      state: 'connecting',
      retryCount: 0,
      maxRetries: this.connectionStatus.maxRetries,
      error: undefined,
      nextRetryIn: undefined,
    })

    this.reconnect()
    return true
  }

  /**
   * Check if manual retry is possible
   */
  public canManualRetry(): boolean {
    return (
      this.connectionStatus.state === 'error' &&
      this.currentJobId !== null &&
      !this.isIntentionallyClosed
    )
  }

  /**
   * Destroy the service and clean up all resources
   */
  public destroy(): void {
    this.disconnect()
    this.handlers = {}
    this.currentJobId = null
  }
}
