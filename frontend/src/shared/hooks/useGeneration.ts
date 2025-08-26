/**
 * useGeneration Hook
 * Complete state management for SSE-based script generation
 */

import { useState, useCallback, useRef, useEffect } from 'react'
import type {
  GenerationState,
  GenerationJobRequest,
  UseGenerationResult,
  ProgressEventData,
  PreviewEventData,
  CompletedEventData,
  FailedEventData,
  HeartbeatEventData,
  SSEConnectionStatus,
  GenerationJobStatus,
} from '../types/generation'
import { SSEConnectionService } from '../services/sseConnectionService'
import { GenerationService } from '../services/generationService'
import { GenerationError } from '../types/generation'

const initialState: GenerationState = {
  status: 'queued',
  progress: 0,
  currentStep: '대기 중',
  previewContent: '',
  wordCount: 0,
  tokens: 0,
  connectionStatus: {
    state: 'closed',
    retryCount: 0,
    maxRetries: 5,
  },
  savedToEpisode: false,
  isStarting: false,
  isCancelling: false,
  canRetry: false,
  canSave: false,
}

export function useGeneration(): UseGenerationResult {
  const [state, setState] = useState<GenerationState>(initialState)
  const sseServiceRef = useRef<SSEConnectionService | null>(null)
  const currentRequestRef = useRef<GenerationJobRequest | null>(null)

  // Initialize SSE service
  useEffect(() => {
    sseServiceRef.current = new SSEConnectionService({
      onProgress: handleProgressEvent,
      onPreview: handlePreviewEvent,
      onCompleted: handleCompletedEvent,
      onFailed: handleFailedEvent,
      onHeartbeat: handleHeartbeatEvent,
      onConnectionChange: handleConnectionChange,
      onError: handleConnectionError,
    })

    return () => {
      sseServiceRef.current?.destroy()
    }
  }, [])

  // Event handlers
  const handleProgressEvent = useCallback((data: ProgressEventData) => {
    setState(prev => ({
      ...prev,
      progress: data.value,
      currentStep: data.currentStep,
      estimatedRemainingTime: data.estimatedTime,
      status: 'streaming' as GenerationJobStatus,
    }))
  }, [])

  const handlePreviewEvent = useCallback((data: PreviewEventData) => {
    setState(prev => ({
      ...prev,
      previewContent: data.markdown,
      wordCount: data.wordCount || 0,
      tokens: data.estimatedTokens || 0,
    }))
  }, [])

  const handleCompletedEvent = useCallback((data: CompletedEventData) => {
    setState(prev => ({
      ...prev,
      status: 'completed',
      progress: 100,
      currentStep: '완료',
      finalContent: data.result.markdown,
      previewContent: data.result.markdown,
      wordCount: data.result.wordCount || 0,
      tokens: data.result.tokens,
      episodeId: data.result.episodeId,
      savedToEpisode: data.result.savedToEpisode || false,
      canSave: true,
      canRetry: true,
      estimatedRemainingTime: 0,
    }))
  }, [])

  const handleFailedEvent = useCallback((data: FailedEventData) => {
    setState(prev => ({
      ...prev,
      status: 'failed',
      currentStep: '실패',
      error: {
        code: data.error.code,
        message: data.error.message,
        retryable: data.error.retryable,
      },
      canRetry: data.error.retryable,
      canSave: false,
    }))
  }, [])

  const handleHeartbeatEvent = useCallback((_data: HeartbeatEventData) => {
    // Heartbeat is handled internally by SSE service
    // Could be used for additional UI indicators if needed
  }, [])

  const handleConnectionChange = useCallback(
    (connectionStatus: SSEConnectionStatus) => {
      setState(prev => ({
        ...prev,
        connectionStatus,
      }))
    },
    [],
  )

  const handleConnectionError = useCallback((error: Error) => {
    console.error('Generation connection error:', error)

    setState(prev => ({
      ...prev,
      error: {
        code: 'CONNECTION_ERROR',
        message: '연결에 문제가 발생했습니다.',
        retryable: true,
      },
      canRetry: true,
    }))
  }, [])

  // Actions
  const startGeneration = useCallback(
    async (request: GenerationJobRequest): Promise<boolean> => {
      try {
        // Validate request
        const validationErrors =
          GenerationService.validateGenerationRequest(request)
        if (validationErrors.length > 0) {
          setState(prev => ({
            ...prev,
            error: {
              code: 'VALIDATION_ERROR',
              message: validationErrors.join(' '),
              retryable: false,
            },
          }))
          return false
        }

        setState(prev => ({ ...prev, isStarting: true, error: undefined }))

        // Store request for potential retry
        currentRequestRef.current = request

        // Start generation
        const jobResponse = await GenerationService.startGeneration(request)

        setState(prev => ({
          ...prev,
          jobId: jobResponse.jobId,
          status: jobResponse.status,
          isStarting: false,
        }))

        // Connect to SSE stream
        sseServiceRef.current?.connect(jobResponse.sseUrl, jobResponse.jobId)

        return true
      } catch (error) {
        console.error('Failed to start generation:', error)

        const errorMessage =
          error instanceof GenerationError
            ? (error as any).message
            : '생성을 시작할 수 없습니다.'

        const retryable =
          error instanceof GenerationError ? (error as any).retryable : true

        setState(prev => ({
          ...prev,
          isStarting: false,
          error: {
            code:
              error instanceof GenerationError
                ? (error as any).code
                : 'UNKNOWN_ERROR',
            message: errorMessage,
            retryable,
          },
          canRetry: retryable,
        }))

        return false
      }
    },
    [],
  )

  const cancelGeneration = useCallback(async (): Promise<boolean> => {
    if (!state.jobId) {
      console.warn('Cannot cancel: no job ID available')
      return false
    }

    try {
      setState(prev => ({ ...prev, isCancelling: true }))

      // Cancel via API (idempotent)
      await GenerationService.cancelGeneration(state.jobId)

      // Disconnect SSE
      sseServiceRef.current?.disconnect()

      setState(prev => ({
        ...prev,
        status: 'canceled',
        currentStep: '취소됨',
        isCancelling: false,
        canRetry: true,
      }))

      return true
    } catch (error) {
      console.error('Failed to cancel generation:', error)

      setState(prev => ({
        ...prev,
        isCancelling: false,
        error: {
          code: 'CANCEL_ERROR',
          message: '취소 중 오류가 발생했습니다.',
          retryable: false,
        },
      }))

      return false
    }
  }, [state.jobId])

  const retryGeneration = useCallback(async (): Promise<boolean> => {
    if (!currentRequestRef.current) {
      console.error('Cannot retry: no previous request available')
      return false
    }

    // Reset state
    setState(prev => ({
      ...initialState,
      connectionStatus: prev.connectionStatus,
    }))

    // Disconnect current SSE connection
    sseServiceRef.current?.disconnect()

    // Start new generation with same parameters
    return startGeneration(currentRequestRef.current)
  }, [startGeneration])

  const reset = useCallback(() => {
    // Disconnect SSE
    sseServiceRef.current?.disconnect()

    // Reset state
    setState(initialState)
    currentRequestRef.current = null
  }, [])

  // Helper functions
  const getProgressMessage = useCallback((): string => {
    if (state.error) {
      return `오류: ${state.error.message}`
    }

    if (state.connectionStatus.state === 'connecting') {
      return '서버에 연결 중...'
    }

    if (state.connectionStatus.state === 'error') {
      const retryInfo = state.connectionStatus.nextRetryIn
        ? ` (${state.connectionStatus.nextRetryIn}초 후 재시도)`
        : ''
      return `연결 문제가 발생했습니다${retryInfo}`
    }

    if (state.status === 'completed') {
      return `완료! ${state.tokens}개 토큰, ${state.wordCount}개 단어`
    }

    if (state.status === 'failed') {
      return (state as any).error?.message || '생성에 실패했습니다'
    }

    if (state.status === 'canceled') {
      return '생성이 취소되었습니다'
    }

    return state.currentStep
  }, [state])

  const getEstimatedTimeString = useCallback((): string => {
    if (!state.estimatedRemainingTime) {
      return ''
    }

    const minutes = Math.floor(state.estimatedRemainingTime / 60)
    const seconds = state.estimatedRemainingTime % 60

    if (minutes > 0) {
      return `약 ${minutes}분 ${seconds}초 남음`
    } else {
      return `약 ${seconds}초 남음`
    }
  }, [state.estimatedRemainingTime])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      sseServiceRef.current?.destroy()
    }
  }, [])

  return {
    state,
    startGeneration,
    cancelGeneration,
    retryGeneration,
    reset,
    getProgressMessage,
    getEstimatedTimeString,
  }
}
