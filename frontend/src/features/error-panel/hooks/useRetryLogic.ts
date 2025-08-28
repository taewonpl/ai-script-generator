/**
 * Hook for retry logic with exponential backoff and jitter
 */

import { useState, useCallback, useRef } from 'react'
import type { RetryConfig } from '../types'

const DEFAULT_RETRY_CONFIG: RetryConfig = {
  maxRetries: 3,
  baseDelay: 1000, // 1 second
  maxDelay: 10000, // 10 seconds
  exponentialBackoff: true,
  jitter: true,
}

export interface RetryState {
  isRetrying: boolean
  retryCount: number
  canRetry: boolean
  nextRetryDelay: number | null
  lastError: Error | null
}

export interface RetryActions {
  retry: () => Promise<void>
  reset: () => void
  cancel: () => void
}

export function useRetryLogic(
  retryFunction: () => Promise<void>,
  config: Partial<RetryConfig> = {}
): RetryState & RetryActions {
  const finalConfig = { ...DEFAULT_RETRY_CONFIG, ...config }
  const [state, setState] = useState<RetryState>({
    isRetrying: false,
    retryCount: 0,
    canRetry: true,
    nextRetryDelay: null,
    lastError: null,
  })
  
  const timeoutRef = useRef<NodeJS.Timeout | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  const calculateDelay = useCallback(
    (attempt: number): number => {
      let delay = finalConfig.baseDelay

      if (finalConfig.exponentialBackoff) {
        // Exponential backoff: baseDelay * (2 ^ attempt)
        delay = finalConfig.baseDelay * Math.pow(2, attempt)
      }

      // Cap at maxDelay
      delay = Math.min(delay, finalConfig.maxDelay)

      // Add jitter to prevent thundering herd
      if (finalConfig.jitter) {
        const jitterAmount = delay * 0.1 // 10% jitter
        delay += (Math.random() - 0.5) * jitterAmount * 2
      }

      return Math.floor(delay)
    },
    [finalConfig]
  )

  const retry = useCallback(async () => {
    if (!state.canRetry || state.isRetrying) {
      return
    }

    // Create new abort controller for this retry attempt
    abortControllerRef.current = new AbortController()

    setState(prev => ({
      ...prev,
      isRetrying: true,
      nextRetryDelay: null,
    }))

    try {
      await retryFunction()
      
      // Success - reset state
      setState(prev => ({
        ...prev,
        isRetrying: false,
        retryCount: 0,
        canRetry: true,
        lastError: null,
      }))
    } catch (error) {
      const newRetryCount = state.retryCount + 1
      const canRetryAgain = newRetryCount < finalConfig.maxRetries
      
      setState(prev => ({
        ...prev,
        isRetrying: false,
        retryCount: newRetryCount,
        canRetry: canRetryAgain,
        lastError: error instanceof Error ? error : new Error(String(error)),
        nextRetryDelay: canRetryAgain ? calculateDelay(newRetryCount) : null,
      }))

      // If we can retry again, schedule the next retry
      if (canRetryAgain) {
        const delay = calculateDelay(newRetryCount)
        
        timeoutRef.current = setTimeout(async () => {
          if (!abortControllerRef.current?.signal.aborted) {
            await retry()
          }
        }, delay)
      }
    }
  }, [
    state.canRetry,
    state.isRetrying,
    state.retryCount,
    retryFunction,
    finalConfig.maxRetries,
    calculateDelay,
  ])

  const reset = useCallback(() => {
    // Cancel any pending retries
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
      timeoutRef.current = null
    }

    // Cancel any ongoing request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }

    setState({
      isRetrying: false,
      retryCount: 0,
      canRetry: true,
      nextRetryDelay: null,
      lastError: null,
    })
  }, [])

  const cancel = useCallback(() => {
    // Cancel any pending retries
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
      timeoutRef.current = null
    }

    // Cancel any ongoing request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }

    setState(prev => ({
      ...prev,
      isRetrying: false,
      canRetry: false,
      nextRetryDelay: null,
    }))
  }, [])

  // Cleanup on unmount
  const cleanup = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
    }
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
  }, [])

  // Effect to cleanup on unmount
  useState(() => {
    return cleanup
  })

  return {
    ...state,
    retry,
    reset,
    cancel,
  }
}

/**
 * Utility to create a delay function that respects abort signals
 */
export function createCancellableDelay(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(resolve, ms)
    
    if (signal) {
      if (signal.aborted) {
        clearTimeout(timeout)
        reject(new Error('Aborted'))
        return
      }
      
      signal.addEventListener('abort', () => {
        clearTimeout(timeout)
        reject(new Error('Aborted'))
      })
    }
  })
}