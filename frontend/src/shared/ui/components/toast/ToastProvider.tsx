import { createContext, useContext, useCallback, useState } from 'react'
import type { ReactNode } from 'react'
import {
  Snackbar,
  Alert,
  AlertTitle,
  IconButton,
  Stack,
  Slide,
} from '@mui/material'
import type { SlideProps } from '@mui/material/Slide'
import { Close as CloseIcon } from '@mui/icons-material'

export type ToastSeverity = 'success' | 'error' | 'warning' | 'info'

export interface ToastOptions {
  severity: ToastSeverity
  title?: string
  message: string
  duration?: number
  persistent?: boolean
  action?: {
    label: string
    onClick: () => void
  }
}

export interface Toast extends ToastOptions {
  id: string
  createdAt: Date
}

interface ToastContextValue {
  showToast: (options: ToastOptions) => string
  hideToast: (id: string) => void
  clearAllToasts: () => void
  toasts: Toast[]
}

const ToastContext = createContext<ToastContextValue | undefined>(undefined)

// Slide transition component
function SlideTransition(props: SlideProps) {
  return <Slide {...props} direction="up" />
}

interface ToastProviderProps {
  children: ReactNode
  maxToasts?: number
  defaultDuration?: number
  anchorOrigin?: {
    vertical: 'top' | 'bottom'
    horizontal: 'left' | 'center' | 'right'
  }
}

/**
 * Global toast notification system
 *
 * Features:
 * - Multiple toast types (success, error, warning, info)
 * - Auto-dismiss with configurable duration
 * - Manual dismiss
 * - Persistent toasts
 * - Action buttons
 * - Stack management (max toasts)
 * - Accessibility support
 */
export function ToastProvider({
  children,
  maxToasts = 3,
  defaultDuration = 6000,
  anchorOrigin = { vertical: 'top', horizontal: 'right' },
}: ToastProviderProps) {
  const [toasts, setToasts] = useState<Toast[]>([])

  // Generate unique ID for toasts
  const generateId = useCallback(() => {
    return `toast-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`
  }, [])

  // Show a new toast
  const showToast = useCallback(
    (options: ToastOptions): string => {
      const id = generateId()
      const toast: Toast = {
        ...options,
        id,
        createdAt: new Date(),
        duration: options.duration ?? defaultDuration,
      }

      setToasts(prev => {
        const newToasts = [toast, ...prev]

        // Limit number of toasts
        if (newToasts.length > maxToasts) {
          return newToasts.slice(0, maxToasts)
        }

        return newToasts
      })

      // Auto-dismiss after duration (unless persistent)
      if (!options.persistent && toast.duration > 0) {
        setTimeout(() => {
          hideToast(id)
        }, toast.duration)
      }

      return id
    },
    [generateId, defaultDuration, maxToasts],
  )

  // Hide a specific toast
  const hideToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(toast => toast.id !== id))
  }, [])

  // Clear all toasts
  const clearAllToasts = useCallback(() => {
    setToasts([])
  }, [])

  const contextValue: ToastContextValue = {
    showToast,
    hideToast,
    clearAllToasts,
    toasts,
  }

  return (
    <ToastContext.Provider value={contextValue}>
      {children}

      {/* Render toasts */}
      <Stack
        spacing={1}
        sx={{
          position: 'fixed',
          top: anchorOrigin.vertical === 'top' ? 24 : 'auto',
          bottom: anchorOrigin.vertical === 'bottom' ? 24 : 'auto',
          left: anchorOrigin.horizontal === 'left' ? 24 : 'auto',
          right: anchorOrigin.horizontal === 'right' ? 24 : 'auto',
          zIndex: theme => theme.zIndex.snackbar,
          maxWidth: 400,
          width: '100%',
        }}
      >
        {toasts.map(toast => (
          <Snackbar
            key={toast.id}
            open={true}
            TransitionComponent={SlideTransition}
            sx={{
              position: 'static',
              transform: 'none',
              width: '100%',
            }}
          >
            <Alert
              severity={toast.severity}
              onClose={() => hideToast(toast.id)}
              action={
                <Stack direction="row" spacing={1} alignItems="center">
                  {/* Custom action button */}
                  {toast.action && (
                    <IconButton
                      size="small"
                      onClick={toast.action.onClick}
                      sx={{ color: 'inherit' }}
                    >
                      {toast.action.label}
                    </IconButton>
                  )}

                  {/* Close button */}
                  <IconButton
                    size="small"
                    onClick={() => hideToast(toast.id)}
                    sx={{ color: 'inherit' }}
                  >
                    <CloseIcon fontSize="small" />
                  </IconButton>
                </Stack>
              }
              sx={{ width: '100%' }}
            >
              {toast.title && <AlertTitle>{toast.title}</AlertTitle>}
              {toast.message}
            </Alert>
          </Snackbar>
        ))}
      </Stack>
    </ToastContext.Provider>
  )
}

/**
 * Hook to access toast functionality
 */
export function useToast(): ToastContextValue {
  const context = useContext(ToastContext)

  if (!context) {
    throw new Error('useToast must be used within a ToastProvider')
  }

  return context
}

/**
 * Convenience hook with predefined toast methods
 */
export function useToastHelpers() {
  const { showToast } = useToast()

  const showSuccess = useCallback(
    (message: string, title?: string) => {
      return showToast({ severity: 'success', message, title })
    },
    [showToast],
  )

  const showError = useCallback(
    (message: string, title?: string, persistent = false) => {
      return showToast({ severity: 'error', message, title, persistent })
    },
    [showToast],
  )

  const showWarning = useCallback(
    (message: string, title?: string) => {
      return showToast({ severity: 'warning', message, title })
    },
    [showToast],
  )

  const showInfo = useCallback(
    (message: string, title?: string) => {
      return showToast({ severity: 'info', message, title })
    },
    [showToast],
  )

  const showRetryableError = useCallback(
    (message: string, onRetry: () => void, title = '오류 발생') => {
      return showToast({
        severity: 'error',
        title,
        message,
        persistent: true,
        action: {
          label: '다시 시도',
          onClick: onRetry,
        },
      })
    },
    [showToast],
  )

  return {
    showSuccess,
    showError,
    showWarning,
    showInfo,
    showRetryableError,
  }
}
