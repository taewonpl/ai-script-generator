import { useEffect, useRef, useState, useCallback } from 'react'
import type {
  // GenerationUpdate,
  // SystemUpdate,
  WebSocketMessage,
} from '@/shared/types/api'

interface UseWebSocketOptions {
  onMessage?: (data: WebSocketMessage) => void
  onConnect?: () => void
  onDisconnect?: () => void
  onError?: (error: Event) => void
  reconnectInterval?: number
  maxReconnectAttempts?: number
}

interface UseWebSocketReturn {
  isConnected: boolean
  lastMessage: WebSocketMessage | null
  sendMessage: (message: WebSocketMessage) => void
  disconnect: () => void
  reconnect: () => void
}

export function useWebSocket(
  url: string,
  options: UseWebSocketOptions = {},
): UseWebSocketReturn {
  const {
    onMessage,
    onConnect,
    onDisconnect,
    onError,
    reconnectInterval = 3000,
    maxReconnectAttempts = 5,
  } = options

  const ws = useRef<WebSocket | null>(null)
  const reconnectAttempts = useRef(0)
  const reconnectTimeoutRef = useRef<any>(null)

  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null)

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      return
    }

    try {
      ws.current = new WebSocket(url)

      ws.current.onopen = () => {
        setIsConnected(true)
        reconnectAttempts.current = 0
        onConnect?.()
      }

      ws.current.onmessage = event => {
        try {
          const data = JSON.parse(event.data)
          setLastMessage(data)
          onMessage?.(data)
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }

      ws.current.onclose = () => {
        setIsConnected(false)
        onDisconnect?.()

        // Attempt reconnection
        if (reconnectAttempts.current < maxReconnectAttempts) {
          reconnectAttempts.current++
          reconnectTimeoutRef.current = setTimeout(() => {
            connect()
          }, reconnectInterval)
        }
      }

      ws.current.onerror = error => {
        onError?.(error)
      }
    } catch (error) {
      console.error('Failed to connect WebSocket:', error)
    }
  }, [
    url,
    onMessage,
    onConnect,
    onDisconnect,
    onError,
    reconnectInterval,
    maxReconnectAttempts,
  ])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }

    if (ws.current) {
      ws.current.close()
    }
  }, [])

  const sendMessage = useCallback((message: WebSocketMessage) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message))
    }
  }, [])

  const reconnect = useCallback(() => {
    disconnect()
    reconnectAttempts.current = 0
    connect()
  }, [connect, disconnect])

  useEffect(() => {
    connect()

    return () => {
      disconnect()
    }
  }, [connect, disconnect])

  return {
    isConnected,
    lastMessage,
    sendMessage,
    disconnect,
    reconnect,
  }
}

// Generation-specific WebSocket hook
export function useGenerationWebSocket(generationId: string) {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { generationService } = require('@/shared/api/services')

  return useWebSocket(
    generationService.createGenerationSocket(generationId).url,
    {
      onMessage: (data: any) => {
        console.log('Generation update:', data)
      },
    },
  )
}

// System status WebSocket hook
export function useSystemWebSocket() {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { coreService } = require('@/shared/api/services')

  return useWebSocket(coreService.createSystemSocket().url, {
    onMessage: (data: any) => {
      console.log('System update:', data)
    },
  })
}

// Project updates WebSocket hook
export function useProjectWebSocket(projectId: string) {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { projectService } = require('@/shared/api/services')

  return useWebSocket(projectService.createProjectSocket(projectId).url, {
    onMessage: (data: WebSocketMessage) => {
      console.log('Project update:', data)
    },
  })
}
