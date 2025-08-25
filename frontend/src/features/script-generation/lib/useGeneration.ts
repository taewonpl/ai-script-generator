import { useState, useEffect, useCallback, useRef } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { GenerationRequest } from '@/shared/types/project'
import type {
  GenerationState,
  UseSSEResult,
  ProgressEventData,
  PreviewEventData,
  FailedEventData,
  HeartbeatEventData,
  AppEvent,
} from '../types/sse'
import { previewConcat } from '@/shared/utils/scriptUtils'

// 백오프 재연결 설정
const RECONNECT_DELAYS = [1000, 2000, 5000, 15000] // 1s → 2s → 5s → 15s
const MAX_RETRIES = 10
const HEARTBEAT_TIMEOUT = 30000 // 30초

/**
 * SSE 이벤트 파싱 함수 - 백엔드 format_sse() 출력 형식에 맞춤
 * Backend sends: event: {type}\ndata: {AppEvent JSON}\n\n
 */
const parseSSEEvent = (event: MessageEvent): AppEvent | null => {
  try {
    // event.data는 AppEvent JSON 구조
    const eventData = JSON.parse(event.data) as AppEvent
    return eventData
  } catch (error) {
    console.error('Failed to parse SSE event:', error)
    return null
  }
}

/**
 * SSE 연결을 관리하는 훅
 */
const useSSE = (jobId: string | null): UseSSEResult => {
  const [state, setState] = useState<GenerationState>('idle')
  const [progress, setProgress] = useState(0)
  const [preview, setPreview] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [retryCount, setRetryCount] = useState(0)
  const [isConnected, setIsConnected] = useState(false)
  const [lastHeartbeat, setLastHeartbeat] = useState<string | null>(null)

  const eventSourceRef = useRef<EventSource | null>(null)
  const heartbeatTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  // Heartbeat 타임아웃 설정
  const resetHeartbeatTimeout = useCallback(() => {
    if (heartbeatTimeoutRef.current) {
      clearTimeout(heartbeatTimeoutRef.current)
    }

    heartbeatTimeoutRef.current = setTimeout(() => {
      console.warn('SSE heartbeat timeout - connection may be lost')
      setIsConnected(false)
    }, HEARTBEAT_TIMEOUT)
  }, [])

  // 재연결 로직
  const reconnect = useCallback(() => {
    if (!jobId || retryCount >= MAX_RETRIES) {
      setState('failed')
      setError('Maximum retry attempts reached')
      return
    }

    const delay =
      RECONNECT_DELAYS[Math.min(retryCount, RECONNECT_DELAYS.length - 1)]

    console.log(
      `Reconnecting SSE in ${delay}ms (attempt ${retryCount + 1}/${MAX_RETRIES})`,
    )

    reconnectTimeoutRef.current = setTimeout(() => {
      setRetryCount(prev => prev + 1)
      // connect 함수는 useEffect에서 jobId 변경으로 자동 호출됨
    }, delay)
  }, [jobId, retryCount])

  // SSE 연결 함수
  const connect = useCallback(() => {
    if (!jobId) return

    // 기존 연결 정리
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
    }

    const url = `/api/generations/${jobId}/events`
    const eventSource = new EventSource(url)
    eventSourceRef.current = eventSource

    eventSource.onopen = () => {
      console.log('SSE connection opened')
      setIsConnected(true)
      setError(null)
      resetHeartbeatTimeout()
    }

    // 특정 이벤트 타입별 핸들러 등록 (백엔드에서 event: {type} 전송)
    eventSource.addEventListener('progress', event => {
      const eventData = parseSSEEvent(event as MessageEvent)
      if (!eventData || eventData.type !== 'progress') return

      const data = eventData as ProgressEventData
      setProgress(data.value)
      setState('generating')
      resetHeartbeatTimeout()
    })

    eventSource.addEventListener('preview', event => {
      const eventData = parseSSEEvent(event as MessageEvent)
      if (!eventData || eventData.type !== 'preview') return

      const data = eventData as PreviewEventData
      setPreview(prev => previewConcat(prev, data.markdown))
      resetHeartbeatTimeout()
    })

    eventSource.addEventListener('completed', event => {
      const eventData = parseSSEEvent(event as MessageEvent)
      if (!eventData || eventData.type !== 'completed') return

      setState('completed')
      setProgress(100)
      console.log('Script generation completed')
    })

    eventSource.addEventListener('failed', event => {
      const eventData = parseSSEEvent(event as MessageEvent)
      if (!eventData || eventData.type !== 'failed') return

      const data = eventData as FailedEventData
      setState('failed')
      setError(data.error.message)
      console.error('Script generation failed:', data)
    })

    eventSource.addEventListener('heartbeat', event => {
      const eventData = parseSSEEvent(event as MessageEvent)
      if (!eventData || eventData.type !== 'heartbeat') return

      const data = eventData as HeartbeatEventData
      setLastHeartbeat(data.timestamp)
      setIsConnected(true)
      resetHeartbeatTimeout()
    })

    eventSource.onerror = event => {
      console.error('SSE connection error:', event)
      setIsConnected(false)

      if (eventSource.readyState === EventSource.CLOSED) {
        console.log('SSE connection closed, attempting to reconnect...')
        reconnect()
      }
    }
  }, [jobId, resetHeartbeatTimeout, reconnect])

  // jobId 변경 시 연결
  useEffect(() => {
    if (jobId) {
      setState('starting')
      setProgress(0)
      setPreview('')
      setError(null)
      connect()
    }

    // 클린업
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
        eventSourceRef.current = null
      }
      if (heartbeatTimeoutRef.current) {
        clearTimeout(heartbeatTimeoutRef.current)
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
    }
  }, [jobId, connect])

  return {
    state,
    progress,
    preview,
    error,
    retryCount,
    isConnected,
    lastHeartbeat,
  }
}

/**
 * 스크립트 생성을 관리하는 메인 훅
 */
export function useGeneration(projectId: string) {
  const [currentJobId, setCurrentJobId] = useState<string | null>(null)
  const [lastGenerationParams, setLastGenerationParams] =
    useState<GenerationRequest | null>(null)
  const queryClient = useQueryClient()

  // 생성 시작 mutation
  const startMutation = useMutation({
    mutationFn: async (request: GenerationRequest) => {
      const idempotencyKey = `gen_${projectId}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`

      const response = await fetch(`/api/projects/${projectId}/generations`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Idempotency-Key': idempotencyKey,
        },
        body: JSON.stringify(request),
      })

      if (!response.ok) {
        throw new Error(`Generation failed: ${response.statusText}`)
      }

      const result = await response.json()
      return { jobId: result.data.jobId }
    },
    onSuccess: (data, variables) => {
      setCurrentJobId(data.jobId)
      setLastGenerationParams(variables)
      console.log('Generation started:', data.jobId)
    },
    onError: error => {
      console.error('Failed to start generation:', error)
    },
  })

  // 생성 취소 mutation
  const cancelMutation = useMutation({
    mutationFn: async (jobId: string) => {
      const response = await fetch(`/api/generations/${jobId}`, {
        method: 'DELETE',
      })

      if (!response.ok) {
        throw new Error(`Cancellation failed: ${response.statusText}`)
      }

      return { success: true }
    },
    onSuccess: () => {
      setCurrentJobId(null)
      console.log('Generation cancelled')
    },
    onError: error => {
      console.error('Failed to cancel generation:', error)
    },
  })

  // SSE 이벤트 구독
  const sseResult = useSSE(currentJobId)

  // 생성 완료 시 쿼리 무효화
  useEffect(() => {
    if (sseResult.state === 'completed') {
      // 에피소드 목록 갱신
      queryClient.invalidateQueries({ queryKey: ['episodes', projectId] })
      // 프로젝트 정보 갱신 (진행률 등)
      queryClient.invalidateQueries({ queryKey: ['project', projectId] })

      // 작업 완료 후 정리
      setCurrentJobId(null)
      setLastGenerationParams(null)
    }
  }, [sseResult.state, projectId, queryClient])

  // API 함수들
  const start = useCallback(
    async (request: GenerationRequest) => {
      return startMutation.mutateAsync(request)
    },
    [startMutation],
  )

  const cancel = useCallback(async () => {
    if (currentJobId) {
      return cancelMutation.mutateAsync(currentJobId)
    }
    throw new Error('No active generation to cancel')
  }, [currentJobId, cancelMutation])

  const restart = useCallback(async () => {
    if (!lastGenerationParams) {
      throw new Error('No previous generation parameters to restart')
    }

    // 현재 작업이 있으면 취소
    if (currentJobId) {
      await cancel()
    }

    // 동일한 파라미터로 재시작
    return start(lastGenerationParams)
  }, [lastGenerationParams, currentJobId, cancel, start])

  return {
    // API 함수들
    start,
    cancel,
    restart,

    // 상태
    isGenerating: !!currentJobId,
    jobId: currentJobId,
    lastParams: lastGenerationParams,

    // SSE 이벤트 결과
    ...sseResult,

    // Mutation 상태
    isStarting: startMutation.isPending,
    isCancelling: cancelMutation.isPending,
    startError: startMutation.error?.message || null,
    cancelError: cancelMutation.error?.message || null,
  }
}
