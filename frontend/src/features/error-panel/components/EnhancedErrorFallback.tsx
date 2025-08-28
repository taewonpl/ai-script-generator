/**
 * Enhanced ErrorFallback component using ErrorPanel
 * This can be used to upgrade the existing ErrorProvider fallback
 */

import { useCallback, useEffect } from 'react'
import { Box } from '@mui/material'

import { ErrorClassifier } from '@/shared/lib/errors/errorClassifier'
import { SentryReporter } from '@/shared/lib/errors/sentryReporter'
import { analytics } from '@/shared/lib/analytics'
import { ErrorPanel } from './ErrorPanel'
import { fromAppError } from '../utils/errorMapping'

interface EnhancedErrorFallbackProps {
  error: Error
  resetErrorBoundary: () => void
}

/**
 * Enhanced error fallback component using the new ErrorPanel
 * This provides a more user-friendly error experience than the original
 */
export function EnhancedErrorFallback({ error, resetErrorBoundary }: EnhancedErrorFallbackProps) {
  const appError = ErrorClassifier.classify(error)
  const detailedError = fromAppError(appError)

  const handleGoHome = useCallback(() => {
    window.location.href = '/'
  }, [])

  const handleReload = useCallback(() => {
    window.location.reload()
  }, [])

  const handleReportBug = useCallback(() => {
    const subject = `Bug Report: ${detailedError.error_type}`
    const body = `
에러 정보:
- 유형: ${detailedError.error_type}
- HTTP 상태: ${detailedError.http_status}
- 메시지: ${detailedError.userMessage}
- 시간: ${detailedError.timestamp}
- URL: ${window.location.href}
- 사용자 에이전트: ${navigator.userAgent}

${detailedError.traceId ? `Trace ID: ${detailedError.traceId}` : ''}
${detailedError.requestId ? `Request ID: ${detailedError.requestId}` : ''}

기술적 세부사항:
${detailedError.technicalMessage}

추가 정보를 입력해주세요:
    `.trim()

    window.open(
      `mailto:support@example.com?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`
    )
  }, [detailedError])

  const handleRetry = useCallback(async () => {
    try {
      resetErrorBoundary()
    } catch (retryError) {
      console.error('Retry failed:', retryError)
      // Could show additional error handling here
    }
  }, [resetErrorBoundary])

  const handleDismiss = useCallback(() => {
    // For critical errors, we might want to navigate away or reload
    handleGoHome()
  }, [handleGoHome])

  useEffect(() => {
    // Report error to Sentry
    SentryReporter.reportError(appError, {
      component: 'EnhancedErrorFallback',
      url: window.location.href,
      userAgent: navigator.userAgent,
    })

    // Track error in analytics
    analytics.trackError(error, {
      component: 'EnhancedErrorFallback',
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
      <Box sx={{ maxWidth: 600, width: '100%' }}>
        <ErrorPanel
          error={detailedError}
          onRetry={detailedError.retryable ? handleRetry : undefined}
          onDismiss={handleDismiss}
          language="kr" // Could be made configurable
          showTechnicalDetails={import.meta.env.DEV} // Show in development mode
          retryConfig={{
            maxRetries: 1, // Limited retries for critical errors
            baseDelay: 1000,
            exponentialBackoff: false,
          }}
        />

        {/* Additional fallback actions */}
        <Box sx={{ mt: 3, display: 'flex', justifyContent: 'center', gap: 2 }}>
          <button
            onClick={handleGoHome}
            style={{
              padding: '8px 16px',
              backgroundColor: '#1976d2',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            홈으로 이동
          </button>
          <button
            onClick={handleReportBug}
            style={{
              padding: '8px 16px',
              backgroundColor: '#f57c00',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            버그 신고
          </button>
          <button
            onClick={handleReload}
            style={{
              padding: '8px 16px',
              backgroundColor: '#388e3c',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            페이지 새로고침
          </button>
        </Box>
      </Box>
    </Box>
  )
}

export default EnhancedErrorFallback