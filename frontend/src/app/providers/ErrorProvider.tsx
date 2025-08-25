import { useCallback, useEffect } from 'react'
import type { ReactNode, ErrorInfo } from 'react'
import { ErrorBoundary } from 'react-error-boundary'
import { QueryErrorResetBoundary } from '@tanstack/react-query'
import {
  Box,
  Typography,
  Button,
  Card,
  CardContent,
  Stack,
  Alert,
} from '@mui/material'
import {
  Refresh as RefreshIcon,
  Home as HomeIcon,
  BugReport as BugIcon,
} from '@mui/icons-material'

import { ErrorClassifier } from '../../shared/lib/errors/errorClassifier'
import { SentryReporter } from '../../shared/lib/errors/sentryReporter'
import { useToastHelpers } from '@/shared/ui/components/toast'
import type { AppError } from '../../shared/lib/errors/types'
import { analytics } from '../../shared/lib/analytics'

interface ErrorFallbackProps {
  error: Error
  resetErrorBoundary: () => void
}

/**
 * Error fallback component for critical errors
 */
function ErrorFallback({ error, resetErrorBoundary }: ErrorFallbackProps) {
  const appError = ErrorClassifier.classify(error)
  const errorInfo = ErrorClassifier.getErrorInfo(appError)

  const handleGoHome = () => {
    window.location.href = '/'
  }

  const handleReload = () => {
    window.location.reload()
  }

  const handleReportBug = () => {
    const subject = `Bug Report: ${errorInfo.title}`
    const body = `
에러 정보:
- 카테고리: ${appError.category}
- 메시지: ${appError.userMessage}
- 시간: ${appError.timestamp.toISOString()}
- URL: ${window.location.href}
- 사용자 에이전트: ${navigator.userAgent}

추가 정보를 입력해주세요:
    `.trim()

    window.open(
      `mailto:support@example.com?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`,
    )
  }

  useEffect(() => {
    // Report error to Sentry
    SentryReporter.reportError(appError, {
      component: 'ErrorFallback',
      url: window.location.href,
      userAgent: navigator.userAgent,
    })

    // Track error in analytics
    analytics.trackError(error, {
      component: 'ErrorFallback',
      category: appError.category,
      severity: appError.severity,
      url: window.location.href,
    })
  }, [appError, error])

  return (
    <Box
      display="flex"
      justifyContent="center"
      alignItems="center"
      minHeight="100vh"
      bgcolor="background.default"
      p={3}
    >
      <Card sx={{ maxWidth: 600, width: '100%' }}>
        <CardContent>
          <Stack spacing={3} alignItems="center">
            {/* Error Icon */}
            <BugIcon sx={{ fontSize: 64, color: 'error.main' }} />

            {/* Error Title */}
            <Typography variant="h4" component="h1" textAlign="center">
              {errorInfo.title}
            </Typography>

            {/* Error Message */}
            <Typography
              variant="body1"
              textAlign="center"
              color="textSecondary"
            >
              {errorInfo.message}
            </Typography>

            {/* Additional Info */}
            {errorInfo.action && (
              <Alert severity="info" sx={{ width: '100%' }}>
                권장 조치: {errorInfo.action}
              </Alert>
            )}

            {/* Technical Details (Development) */}
            {import.meta.env.DEV && (
              <Alert severity="warning" sx={{ width: '100%' }}>
                <Typography variant="caption" component="div">
                  <strong>개발 모드 정보:</strong>
                  <br />
                  Category: {appError.category}
                  <br />
                  Severity: {appError.severity}
                  <br />
                  Retryable: {appError.retryable ? 'Yes' : 'No'}
                  <br />
                  Original: {error.message}
                </Typography>
              </Alert>
            )}

            {/* Action Buttons */}
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
              {errorInfo.retryable && (
                <Button
                  variant="contained"
                  startIcon={<RefreshIcon />}
                  onClick={resetErrorBoundary}
                >
                  다시 시도
                </Button>
              )}

              <Button
                variant="outlined"
                startIcon={<HomeIcon />}
                onClick={handleGoHome}
              >
                홈으로
              </Button>

              <Button
                variant="text"
                startIcon={<BugIcon />}
                onClick={handleReportBug}
                size="small"
              >
                버그 신고
              </Button>
            </Stack>

            {/* Reload Button (Last Resort) */}
            <Button
              variant="text"
              onClick={handleReload}
              size="small"
              sx={{ mt: 2 }}
            >
              페이지 새로고침
            </Button>
          </Stack>
        </CardContent>
      </Card>
    </Box>
  )
}

interface ErrorProviderProps {
  children: ReactNode
}

/**
 * Global error handling provider
 *
 * Features:
 * - React Error Boundary integration
 * - TanStack Query error boundary integration
 * - Automatic error classification
 * - Sentry error reporting
 * - User-friendly error messages
 * - 401 auto-redirect to login
 * - Network error retry UI
 */
export function ErrorProvider({ children }: ErrorProviderProps) {
  const { showError, showRetryableError, showWarning } = useToastHelpers()

  // Handle global errors
  const handleError = useCallback(
    (error: Error, errorInfo?: ErrorInfo) => {
      const appError = ErrorClassifier.classify(error)

      console.error('🚨 Global error caught:', appError, errorInfo)

      // Report to Sentry
      SentryReporter.reportError(appError, {
        componentStack: errorInfo?.componentStack || '',
        url: window.location.href,
      })

      // Track in analytics
      analytics.trackError(error, {
        category: appError.category,
        severity: appError.severity,
        statusCode: appError.statusCode,
        retryable: appError.retryable,
        componentStack: errorInfo?.componentStack || '',
      })

      // Handle 401 errors - redirect to login
      if (
        appError.category === 'authorization' &&
        appError.statusCode === 401
      ) {
        // Clear any stored auth data
        localStorage.removeItem('token')
        localStorage.removeItem('user')

        // Show warning before redirect
        showWarning('로그인이 만료되었습니다. 로그인 페이지로 이동합니다.')

        // Redirect after a short delay
        setTimeout(() => {
          window.location.href = '/login'
        }, 2000)

        return
      }

      // Handle retryable errors with retry UI
      if (appError.retryable) {
        showRetryableError(
          appError.userMessage || '오류가 발생했습니다.',
          () => window.location.reload(),
          ErrorClassifier.getErrorInfo(appError).title,
        )
      } else {
        // Non-retryable errors
        showError(
          appError.userMessage || '오류가 발생했습니다.',
          ErrorClassifier.getErrorInfo(appError).title,
        )
      }
    },
    [showError, showRetryableError, showWarning],
  )

  // Global error event listener
  useEffect(() => {
    const handleGlobalError = (event: ErrorEvent) => {
      handleError(event.error)
    }

    const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
      const error =
        event.reason instanceof Error
          ? event.reason
          : new Error(`Unhandled promise rejection: ${event.reason}`)

      handleError(error)
    }

    window.addEventListener('error', handleGlobalError)
    window.addEventListener('unhandledrejection', handleUnhandledRejection)

    return () => {
      window.removeEventListener('error', handleGlobalError)
      window.removeEventListener('unhandledrejection', handleUnhandledRejection)
    }
  }, [handleError])

  return (
    <QueryErrorResetBoundary>
      {({ reset }) => (
        <ErrorBoundary
          FallbackComponent={ErrorFallback}
          onError={handleError}
          onReset={reset}
        >
          {children}
        </ErrorBoundary>
      )}
    </QueryErrorResetBoundary>
  )
}

/**
 * Hook to manually report errors
 */
export function useErrorReporting() {
  const { showError, showRetryableError } = useToastHelpers()

  const reportError = useCallback(
    (error: Error | string, context?: Record<string, any>) => {
      const appError =
        typeof error === 'string'
          ? new Error(error)
          : ErrorClassifier.classify(error)

      // Report to Sentry
      if (appError instanceof Error) {
        SentryReporter.reportError(appError as AppError, context)
      }

      // Show user notification
      const errorInfo = ErrorClassifier.getErrorInfo(appError as AppError)

      if (errorInfo.retryable) {
        showRetryableError(
          errorInfo.message,
          () => window.location.reload(),
          errorInfo.title,
        )
      } else {
        showError(errorInfo.message, errorInfo.title)
      }
    },
    [showError, showRetryableError],
  )

  return { reportError }
}
