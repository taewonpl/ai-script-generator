import { useState, useEffect, useRef, useCallback } from 'react'
import type {
  SSEConnectionState,
  SSEOptions,
  SSEHookReturn,
  TypedSSEEventData,
} from './types'

const DEFAULT_RETRY_DELAYS = [1000, 2000, 5000, 15000] // 1s, 2s, 5s, 15s
const DEFAULT_MAX_RETRIES = 5
const DEFAULT_HEARTBEAT_TIMEOUT = 30000 // 30 seconds

/**
 * Custom hook for Server-Sent Events with auto-reconnection
 *
 * Features:
 * - Connection state management
 * - Auto-reconnection with exponential backoff
 * - Event type safety
 * - Heartbeat detection
 * - Manual connection control
 */
export function useSSE(options: SSEOptions): SSEHookReturn {
  const {
    url,
    maxRetries = DEFAULT_MAX_RETRIES,
    retryDelays = DEFAULT_RETRY_DELAYS,
    heartbeatTimeout = DEFAULT_HEARTBEAT_TIMEOUT,
    withCredentials = true,
  } = options

  // State
  const [connectionState, setConnectionState] =
    useState<SSEConnectionState>('idle')
  const [events, setEvents] = useState<TypedSSEEventData[]>([])
  const [latestEvent, setLatestEvent] = useState<TypedSSEEventData | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const [retryCount, setRetryCount] = useState(0)
  const [lastConnectedAt, setLastConnectedAt] = useState<Date | null>(null)

  // Refs for cleanup
  const eventSourceRef = useRef<EventSource | null>(null)
  const retryTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const heartbeatTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  // Clear all timeouts
  const clearTimeouts = useCallback(() => {
    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current)
      retryTimeoutRef.current = null
    }
    if (heartbeatTimeoutRef.current) {
      clearTimeout(heartbeatTimeoutRef.current)
      heartbeatTimeoutRef.current = null
    }
  }, [])

  // Process incoming SSE event
  const processEvent = useCallback((event: MessageEvent) => {
    try {
      // Python backend sends data in format: data: {json_object}
      const eventData = JSON.parse(event.data) as TypedSSEEventData

      console.log('📡 SSE Event received:', eventData)

      // Update events list
      setEvents(prev => [...prev, eventData])
      setLatestEvent(eventData)

      // Handle heartbeat
      if (eventData.type === 'heartbeat') {
        resetHeartbeatTimeout()
      }
    } catch (err) {
      console.error('❌ Failed to parse SSE event:', err, event.data)
      setError(new Error('Failed to parse SSE event data'))
    }
  }, [])

  // Reset heartbeat timeout
  const resetHeartbeatTimeout = useCallback(() => {
    if (heartbeatTimeoutRef.current) {
      clearTimeout(heartbeatTimeoutRef.current)
    }

    heartbeatTimeoutRef.current = setTimeout(() => {
      console.warn('⚠️ SSE heartbeat timeout - connection may be stale')
      if (connectionState === 'open') {
        setConnectionState('retrying')
        connect()
      }
    }, heartbeatTimeout)
  }, [connectionState, heartbeatTimeout])

  // Connect to SSE
  const connect = useCallback(() => {
    // Don't connect if already connected or retries exceeded
    if (connectionState === 'open' || retryCount >= maxRetries) {
      return
    }

    console.log(
      `🔄 Connecting to SSE: ${url} (attempt ${retryCount + 1}/${maxRetries})`,
    )

    setConnectionState('connecting')
    setError(null)
    clearTimeouts()

    try {
      // Close existing connection
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }

      // Create new EventSource
      const eventSource = new EventSource(url, { withCredentials })
      eventSourceRef.current = eventSource

      // Connection opened
      eventSource.onopen = () => {
        console.log('✅ SSE connection opened')
        setConnectionState('open')
        setRetryCount(0)
        setLastConnectedAt(new Date())
        resetHeartbeatTimeout()
      }

      // Message received (default event type)
      eventSource.onmessage = processEvent

      // Specific event type listeners (matching Python backend)
      eventSource.addEventListener('progress', processEvent)
      eventSource.addEventListener('preview', processEvent)
      eventSource.addEventListener('completed', processEvent)
      eventSource.addEventListener('failed', processEvent)
      eventSource.addEventListener('heartbeat', processEvent)

      // Connection error
      eventSource.onerror = error => {
        console.error('❌ SSE connection error:', error)

        if (eventSource.readyState === EventSource.CLOSED) {
          setConnectionState('closed')
        } else if (retryCount < maxRetries) {
          setConnectionState('retrying')
          scheduleRetry()
        } else {
          setConnectionState('closed')
          setError(
            new Error(`SSE connection failed after ${maxRetries} retries`),
          )
        }

        clearTimeouts()
      }
    } catch (err) {
      console.error('❌ Failed to create SSE connection:', err)
      setError(err as Error)
      setConnectionState('closed')
    }
  }, [
    url,
    withCredentials,
    retryCount,
    maxRetries,
    connectionState,
    processEvent,
    resetHeartbeatTimeout,
  ])

  // Schedule retry with exponential backoff
  const scheduleRetry = useCallback(() => {
    const delayIndex = Math.min(retryCount, retryDelays.length - 1)
    const delay = retryDelays[delayIndex]

    console.log(
      `⏱️ Scheduling SSE retry in ${delay}ms (attempt ${retryCount + 1}/${maxRetries})`,
    )

    retryTimeoutRef.current = setTimeout(() => {
      setRetryCount(prev => prev + 1)
      connect()
    }, delay)
  }, [retryCount, retryDelays, maxRetries, connect])

  // Disconnect from SSE
  const disconnect = useCallback(() => {
    console.log('🔌 Disconnecting SSE')

    setConnectionState('closed')
    clearTimeouts()

    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }

    setRetryCount(0)
  }, [clearTimeouts])

  // Clear events history
  const clearEvents = useCallback(() => {
    setEvents([])
    setLatestEvent(null)
  }, [])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect()
    }
  }, [disconnect])

  // Auto-reconnect when connection is lost (if not manually closed)
  useEffect(() => {
    if (connectionState === 'retrying' && retryCount < maxRetries) {
      scheduleRetry()
    }
  }, [connectionState, retryCount, maxRetries, scheduleRetry])

  return {
    connectionState,
    events,
    latestEvent,
    error,
    connect,
    disconnect,
    clearEvents,
    retryCount,
    lastConnectedAt,
  }
}
