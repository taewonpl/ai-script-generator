/**
 * User-friendly ErrorPanel component with copy functionality and retry logic
 */

import { useState, useCallback } from 'react'
import {
  Alert,
  AlertTitle,
  Box,
  Button,
  Chip,
  Collapse,
  IconButton,
  Stack,
  Typography,
  useTheme,
  Tooltip,
  CircularProgress,
} from '@mui/material'
import {
  ContentCopy as CopyIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Refresh as RefreshIcon,
  Close as CloseIcon,
  Schedule as ScheduleIcon,
} from '@mui/icons-material'

import { useToastHelpers } from '@/shared/ui/components/toast'
import { useRetryLogic } from '../hooks/useRetryLogic'
import { getErrorTranslation } from '../translations'
import { createCopyableErrorDetails } from '../utils/errorMapping'
import type { ErrorPanelProps } from '../types'

/**
 * ErrorPanel - A comprehensive error display component with user-friendly messaging,
 * copy functionality, retry logic, and technical details toggle
 */
export function ErrorPanel({
  error,
  onRetry,
  onDismiss,
  language = 'kr',
  compact = false,
  showTechnicalDetails = false,
  retryConfig,
}: ErrorPanelProps) {
  const theme = useTheme()
  const { showSuccess } = useToastHelpers()
  const [showDetails, setShowDetails] = useState(showTechnicalDetails)
  
  const translation = getErrorTranslation(error.error_type, language)
  
  // Retry logic
  const retryLogic = useRetryLogic(
    async () => {
      if (onRetry) {
        await onRetry()
      }
    },
    retryConfig
  )

  // Copy error details to clipboard
  const handleCopyDetails = useCallback(async () => {
    try {
      const errorDetails = createCopyableErrorDetails(error)
      await navigator.clipboard.writeText(errorDetails)
      showSuccess(translation.copySuccessText)
    } catch {
      // Fallback for older browsers
      const textArea = document.createElement('textarea')
      textArea.value = createCopyableErrorDetails(error)
      document.body.appendChild(textArea)
      textArea.select()
      document.execCommand('copy')
      document.body.removeChild(textArea)
      showSuccess(translation.copySuccessText)
    }
  }, [error, showSuccess, translation.copySuccessText])

  const handleRetry = useCallback(async () => {
    if (onRetry && !retryLogic.isRetrying) {
      await retryLogic.retry()
    }
  }, [onRetry, retryLogic])

  const toggleDetails = useCallback(() => {
    setShowDetails(prev => !prev)
  }, [])

  // Determine alert severity based on error type
  const severity = error.retryable ? 'warning' : 'error'

  const formatNextRetryTime = (delay: number) => {
    const seconds = Math.ceil(delay / 1000)
    return language === 'en' ? `${seconds}s` : `${seconds}초`
  }

  return (
    <Alert
      severity={severity}
      variant="filled"
      sx={{
        width: '100%',
        '& .MuiAlert-message': {
          width: '100%',
        },
      }}
    >
      <AlertTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        {translation.title}
        
        {/* Error type chip */}
        <Chip
          label={error.error_type.replace('_', ' ').toUpperCase()}
          size="small"
          color={error.retryable ? 'warning' : 'error'}
          variant="outlined"
          sx={{ ml: 'auto', fontSize: '0.7rem' }}
        />
        
        {/* Dismiss button */}
        {onDismiss && (
          <IconButton
            size="small"
            onClick={onDismiss}
            sx={{ color: 'inherit', ml: 1 }}
            aria-label={translation.dismissText}
          >
            <CloseIcon fontSize="small" />
          </IconButton>
        )}
      </AlertTitle>

      {/* Main error message */}
      <Typography variant="body2" sx={{ mb: 2 }}>
        {error.hint || translation.userMessage}
      </Typography>

      {/* Action hint */}
      {!compact && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {translation.actionHint}
        </Typography>
      )}

      {/* Retry progress indicator */}
      {retryLogic.isRetrying && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
          <CircularProgress size={16} color="inherit" />
          <Typography variant="body2">
            {language === 'en' ? 'Retrying...' : '재시도 중...'}
          </Typography>
        </Box>
      )}

      {/* Next retry countdown */}
      {retryLogic.nextRetryDelay && !retryLogic.isRetrying && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
          <ScheduleIcon fontSize="small" color="inherit" />
          <Typography variant="body2">
            {language === 'en' 
              ? `Next retry in ${formatNextRetryTime(retryLogic.nextRetryDelay)}`
              : `${formatNextRetryTime(retryLogic.nextRetryDelay)} 후 재시도`
            }
          </Typography>
        </Box>
      )}

      {/* Action buttons */}
      <Stack direction="row" spacing={1} sx={{ mb: showDetails ? 2 : 0 }}>
        {/* Retry button */}
        {error.retryable && onRetry && (
          <Button
            variant="outlined"
            size="small"
            startIcon={retryLogic.isRetrying ? <CircularProgress size={14} color="inherit" /> : <RefreshIcon />}
            onClick={handleRetry}
            disabled={!retryLogic.canRetry || retryLogic.isRetrying}
            sx={{ color: 'inherit', borderColor: 'currentColor' }}
          >
            {translation.retryButtonText}
            {retryLogic.retryCount > 0 && ` (${retryLogic.retryCount}/${retryConfig?.maxRetries || 3})`}
          </Button>
        )}

        {/* Copy details button */}
        <Tooltip title={translation.copyDetailsText}>
          <Button
            variant="outlined"
            size="small"
            startIcon={<CopyIcon />}
            onClick={handleCopyDetails}
            sx={{ color: 'inherit', borderColor: 'currentColor' }}
          >
            {compact ? '' : translation.copyDetailsText}
          </Button>
        </Tooltip>

        {/* Toggle details button */}
        {(error.technicalMessage || error.context) && (
          <Button
            variant="text"
            size="small"
            endIcon={showDetails ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            onClick={toggleDetails}
            sx={{ color: 'inherit' }}
          >
            {showDetails ? translation.hideDetailsText : translation.showDetailsText}
          </Button>
        )}
      </Stack>

      {/* Technical details collapse */}
      <Collapse in={showDetails}>
        <Box sx={{ 
          mt: 2, 
          p: 2, 
          bgcolor: theme.palette.action.hover,
          borderRadius: 1,
        }}>
          <Typography variant="subtitle2" gutterBottom>
            {language === 'en' ? 'Technical Details' : '기술적 세부사항'}
          </Typography>
          
          {/* Error IDs */}
          {(error.traceId || error.requestId) && (
            <Stack spacing={1} sx={{ mb: 2 }}>
              {error.traceId && (
                <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                  <strong>Trace ID:</strong> {error.traceId}
                </Typography>
              )}
              {error.requestId && (
                <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                  <strong>Request ID:</strong> {error.requestId}
                </Typography>
              )}
            </Stack>
          )}

          {/* Technical message */}
          {error.technicalMessage && error.technicalMessage !== error.userMessage && (
            <Typography variant="body2" sx={{ mb: 2 }}>
              <strong>
                {language === 'en' ? 'Technical Message:' : '기술적 메시지:'}
              </strong>
              <br />
              {error.technicalMessage}
            </Typography>
          )}

          {/* Context details */}
          {error.context && (
            <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
              <strong>
                {language === 'en' ? 'Context:' : '컨텍스트:'}
              </strong>
              <br />
              {JSON.stringify(error.context, null, 2)}
            </Typography>
          )}

          {/* Timestamp */}
          <Typography variant="body2" sx={{ mt: 2, fontSize: '0.75rem', color: 'text.secondary' }}>
            {error.timestamp}
          </Typography>
        </Box>
      </Collapse>
    </Alert>
  )
}

export default ErrorPanel