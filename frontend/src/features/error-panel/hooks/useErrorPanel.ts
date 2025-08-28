/**
 * Hook to integrate ErrorPanel with existing error handling system
 */

import { useCallback, useState } from 'react'
import { useToastHelpers } from '@/shared/ui/components/toast'
import { toDetailedError } from '../utils/errorMapping'
import type { DetailedError, Language, RetryConfig } from '../types'

export interface ErrorPanelState {
  error: DetailedError | null
  isVisible: boolean
}

export interface UseErrorPanelOptions {
  language?: Language
  retryConfig?: Partial<RetryConfig>
  autoShow?: boolean
  showInToast?: boolean
}

export interface UseErrorPanelReturn {
  error: DetailedError | null
  isVisible: boolean
  showError: (error: unknown, onRetry?: () => Promise<void>) => void
  hideError: () => void
  retryError: () => Promise<void>
  currentRetryFn?: () => Promise<void>
}

/**
 * useErrorPanel - Hook to manage error display with ErrorPanel component
 */
export function useErrorPanel(options: UseErrorPanelOptions = {}): UseErrorPanelReturn {
  const {
    autoShow = true,
    showInToast = true,
  } = options

  const { showError: showToastError, showRetryableError } = useToastHelpers()
  const [state, setState] = useState<ErrorPanelState>({
    error: null,
    isVisible: false,
  })
  const [currentRetryFn, setCurrentRetryFn] = useState<(() => Promise<void>) | undefined>()

  const showError = useCallback(
    (error: unknown, onRetry?: () => Promise<void>) => {
      const detailedError = toDetailedError(error)
      
      setState({
        error: detailedError,
        isVisible: autoShow,
      })

      setCurrentRetryFn(onRetry ? () => onRetry : undefined)

      // Also show in toast system for immediate feedback
      if (showInToast) {
        if (detailedError.retryable && onRetry) {
          showRetryableError(
            detailedError.userMessage,
            onRetry,
            detailedError.error_type.replace('_', ' ').toUpperCase()
          )
        } else {
          showToastError(
            detailedError.userMessage,
            detailedError.error_type.replace('_', ' ').toUpperCase()
          )
        }
      }
    },
    [autoShow, showInToast, showToastError, showRetryableError]
  )

  const hideError = useCallback(() => {
    setState(prev => ({
      ...prev,
      isVisible: false,
    }))
    setCurrentRetryFn(undefined)
  }, [])

  const retryError = useCallback(async () => {
    if (currentRetryFn) {
      await currentRetryFn()
    }
  }, [currentRetryFn])

  return {
    error: state.error,
    isVisible: state.isVisible,
    showError,
    hideError,
    retryError,
    currentRetryFn,
  }
}

/**
 * useErrorPanelWithQuery - Hook specifically for React Query errors
 */
export function useErrorPanelWithQuery(options: UseErrorPanelOptions = {}) {
  const errorPanel = useErrorPanel(options)

  const handleQueryError = useCallback(
    (error: unknown, retry?: () => void) => {
      const retryFn = retry ? async () => {
        retry()
      } : undefined

      errorPanel.showError(error, retryFn)
    },
    [errorPanel]
  )

  return {
    ...errorPanel,
    handleQueryError,
  }
}