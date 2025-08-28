/**
 * Standardized ErrorPanel with all DoD requirements
 * - Copy functionality with request_id/trace_id/endpoint/method/http_status/timestamp
 * - Manual retry with backoff counter reset
 * - Collapsible technical details (default collapsed)
 * - Consistent i18n (EN/KR)
 * - A11y support with role="alert" and keyboard navigation
 */

import { useState, useCallback, useEffect, useRef } from 'react'
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
  Paper,
} from '@mui/material'
import {
  ContentCopy as CopyIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Refresh as RefreshIcon,
  Close as CloseIcon,
  Schedule as ScheduleIcon,
  WifiOff as OfflineIcon,
} from '@mui/icons-material'

import { useToastHelpers } from '@/shared/ui/components/toast'
import type { StandardErrorFormat, StandardRetryConfig } from '../types/standardError'
import { DEFAULT_RETRY_CONFIG, addJitter } from '../types/standardError'
import { getMessage, getMessageWithVars } from '../i18n/errorMessages'
import { createCopyableErrorText } from '../adapters/errorAdapter'
import type { Language } from '../i18n/errorMessages'

interface StandardErrorPanelProps {
  error: StandardErrorFormat
  onRetry?: () => Promise<void>
  onDismiss?: () => void
  language?: Language
  compact?: boolean
  retryConfig?: Partial<StandardRetryConfig>
  className?: string
}

/**
 * Standardized ErrorPanel component
 */
export function StandardErrorPanel({
  error,
  onRetry,
  onDismiss,
  language = 'ko',
  compact = false,
  retryConfig = {},
  className,
}: StandardErrorPanelProps) {
  const theme = useTheme()
  const { showSuccess } = useToastHelpers()
  const [showDetails, setShowDetails] = useState(false)
  const [retryCount, setRetryCount] = useState(0)
  const [isRetrying, setIsRetrying] = useState(false)
  const [nextRetryIn, setNextRetryIn] = useState<number | null>(null)
  const alertRef = useRef<HTMLDivElement>(null)
  const retryTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  const config = { ...DEFAULT_RETRY_CONFIG, ...retryConfig }

  // Focus alert on mount for a11y
  useEffect(() => {
    if (alertRef.current) {
      alertRef.current.focus()
    }
  }, [])

  // Auto retry logic
  useEffect(() => {
    if (retryCount < config.maxAutoRetries && onRetry && !isRetrying) {
      const delay = addJitter(config.autoDelays[retryCount] || 0, config.jitterRange)
      
      if (delay === 0) {
        // Immediate retry
        handleAutoRetry()
      } else {
        // Delayed retry with countdown
        setNextRetryIn(delay)
        retryTimeoutRef.current = setTimeout(() => {
          handleAutoRetry()
        }, delay)
      }
    }

    return () => {
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current)
        retryTimeoutRef.current = null
      }
    }
  }, [retryCount, config.maxAutoRetries, config.autoDelays, config.jitterRange, onRetry, isRetrying])

  // Countdown timer for next retry
  useEffect(() => {
    if (nextRetryIn === null) return

    const interval = setInterval(() => {
      setNextRetryIn(prev => {
        if (prev === null || prev <= 100) {
          return null
        }
        return prev - 100
      })
    }, 100)

    return () => clearInterval(interval)
  }, [nextRetryIn])

  // Online/offline detection with auto retry
  useEffect(() => {
    if (!config.offlineRetry || !onRetry) return

    const handleOnline = () => {
      if (error.is_offline) {
        // Auto retry once when coming back online
        handleManualRetry()
      }
    }

    window.addEventListener('online', handleOnline)
    return () => window.removeEventListener('online', handleOnline)
  }, [config.offlineRetry, onRetry, error.is_offline])

  const handleAutoRetry = useCallback(async () => {
    if (!onRetry || isRetrying) return

    setIsRetrying(true)
    setNextRetryIn(null)

    try {
      await onRetry()
      // Success - don't increment retry count as this will be handled by parent
    } catch {
      setRetryCount(prev => prev + 1)
    } finally {
      setIsRetrying(false)
    }
  }, [onRetry, isRetrying])

  const handleManualRetry = useCallback(async () => {
    if (!onRetry || isRetrying) return

    setIsRetrying(true)
    setNextRetryIn(null)
    
    // Reset counter on manual retry
    if (config.resetOnManual) {
      setRetryCount(0)
    }

    try {
      await onRetry()
    } catch (retryError) {
      console.error('Manual retry failed:', retryError)
    } finally {
      setIsRetrying(false)
    }
  }, [onRetry, isRetrying, config.resetOnManual])

  const handleCopyDetails = useCallback(async () => {
    try {
      const copyText = createCopyableErrorText(error)
      await navigator.clipboard.writeText(copyText)
      showSuccess(getMessage('error.details.copied', language))
    } catch {
      // Fallback for older browsers
      const textArea = document.createElement('textarea')
      textArea.value = createCopyableErrorText(error)
      document.body.appendChild(textArea)
      textArea.select()
      document.execCommand('copy')
      document.body.removeChild(textArea)
      showSuccess(getMessage('error.details.copied', language))
    }
  }, [error, showSuccess, language])

  const handleKeyDown = useCallback((event: React.KeyboardEvent) => {
    if (event.key === 'Enter' && onRetry) {
      handleManualRetry()
    } else if ((event.metaKey || event.ctrlKey) && event.key === 'c') {
      event.preventDefault()
      handleCopyDetails()
    }
  }, [onRetry, handleManualRetry, handleCopyDetails])

  const toggleDetails = useCallback(() => {
    setShowDetails(prev => !prev)
  }, [])

  // Determine alert severity
  const severity = error.is_offline ? 'warning' : 
                  error.http_status >= 500 ? 'error' : 
                  error.http_status >= 400 ? 'warning' : 'error'

  const headlineKey = error.is_offline ? 'error.headline.offline' :
                      `error.headline.${error.error_type}` as keyof typeof getMessage
  const hintKey = error.is_offline ? 'error.hint.offline' :
                  `error.hint.${error.error_type}` as keyof typeof getMessage

  const headline = getMessage(headlineKey, language) || getMessage('error.headline.generic', language)
  const hint = error.hint || getMessage(hintKey, language) || getMessage('error.hint.generic', language)

  const canRetry = onRetry && (retryCount < config.maxAutoRetries || !isRetrying)
  const showRetryCount = retryCount > 0 || isRetrying

  return (
    <Box className={className}>
      <Alert
        ref={alertRef}
        severity={severity}
        variant="filled"
        role="alert"
        tabIndex={0}
        onKeyDown={handleKeyDown}
        sx={{
          width: '100%',
          '& .MuiAlert-message': {
            width: '100%',
          },
        }}
      >
        <AlertTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {error.is_offline && <OfflineIcon fontSize="small" />}
          {headline}
          
          {/* Error type chip */}
          <Chip
            label={error.error_type.replace('_', ' ').toUpperCase()}
            size="small"
            color={severity}
            variant="outlined"
            sx={{ ml: 'auto', fontSize: '0.7rem' }}
          />
          
          {/* HTTP Status */}
          {error.http_status > 0 && (
            <Chip
              label={error.http_status}
              size="small"
              variant="outlined"
              sx={{ fontSize: '0.7rem' }}
            />
          )}
          
          {/* Dismiss button */}
          {onDismiss && (
            <IconButton
              size="small"
              onClick={onDismiss}
              sx={{ color: 'inherit', ml: 1 }}
              aria-label={getMessage('error.button.dismiss', language)}
            >
              <CloseIcon fontSize="small" />
            </IconButton>
          )}
        </AlertTitle>

        {/* Main error message */}
        <Typography variant="body2" sx={{ mb: 2 }}>
          {hint}
        </Typography>

        {/* Retry status */}
        {isRetrying && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
            <CircularProgress size={16} color="inherit" />
            <Typography variant="body2">
              {getMessage('error.retrying', language)}
            </Typography>
            {showRetryCount && (
              <Typography variant="caption">
                {getMessageWithVars('error.retry_count', language, {
                  count: retryCount + 1,
                  max: config.maxAutoRetries,
                })}
              </Typography>
            )}
          </Box>
        )}

        {/* Next retry countdown */}
        {nextRetryIn && !isRetrying && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
            <ScheduleIcon fontSize="small" color="inherit" />
            <Typography variant="body2">
              {language === 'en' 
                ? `Next retry in ${Math.ceil(nextRetryIn / 1000)}s`
                : `${Math.ceil(nextRetryIn / 1000)}초 후 재시도`
              }
            </Typography>
          </Box>
        )}

        {/* Action buttons */}
        <Stack direction="row" spacing={1} sx={{ mb: showDetails ? 2 : 0 }}>
          {/* Retry button */}
          {canRetry && (
            <Button
              variant="outlined"
              size="small"
              startIcon={isRetrying ? <CircularProgress size={14} color="inherit" /> : <RefreshIcon />}
              onClick={handleManualRetry}
              disabled={isRetrying}
              sx={{ color: 'inherit', borderColor: 'currentColor' }}
            >
              {getMessage('error.button.retry', language)}
              {showRetryCount && !compact && (
                <Typography component="span" variant="inherit" sx={{ ml: 0.5 }}>
                  ({retryCount}/{config.maxAutoRetries})
                </Typography>
              )}
            </Button>
          )}

          {/* Copy details button */}
          <Tooltip title={getMessage('error.details.copy', language)}>
            <Button
              variant="outlined"
              size="small"
              startIcon={<CopyIcon />}
              onClick={handleCopyDetails}
              sx={{ color: 'inherit', borderColor: 'currentColor' }}
            >
              {compact ? '' : getMessage('error.details.copy', language)}
            </Button>
          </Tooltip>

          {/* Toggle details button */}
          <Button
            variant="text"
            size="small"
            endIcon={showDetails ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            onClick={toggleDetails}
            sx={{ color: 'inherit' }}
          >
            {showDetails 
              ? getMessage('error.details.hide', language)
              : getMessage('error.details.show', language)
            }
          </Button>
        </Stack>

        {/* Technical details collapse */}
        <Collapse in={showDetails}>
          <Paper sx={{ 
            mt: 2, 
            p: 2, 
            bgcolor: theme.palette.action.hover,
            borderRadius: 1,
          }}>
            <Typography variant="subtitle2" gutterBottom>
              {getMessage('error.details.title', language)}
            </Typography>
            
            {/* Error IDs and metadata */}
            <Stack spacing={1} sx={{ mb: 2 }}>
              {error.request_id && (
                <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                  <strong>Request ID:</strong> {error.request_id}
                </Typography>
              )}
              {error.trace_id && (
                <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                  <strong>Trace ID:</strong> {error.trace_id}
                </Typography>
              )}
              {error.endpoint && (
                <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                  <strong>Endpoint:</strong> {error.method || 'GET'} {error.endpoint}
                </Typography>
              )}
            </Stack>

            {/* Raw message */}
            {error.raw_message && (
              <Typography 
                variant="body2" 
                sx={{ 
                  fontFamily: 'monospace', 
                  fontSize: '0.75rem',
                  whiteSpace: 'pre-wrap',
                  bgcolor: theme.palette.background.paper,
                  p: 1,
                  borderRadius: 1,
                  mb: 2,
                }}
              >
                {error.raw_message}
              </Typography>
            )}

            {/* Technical data */}
            {error.masked_data && (
              <Typography 
                variant="body2" 
                sx={{ 
                  fontFamily: 'monospace', 
                  fontSize: '0.75rem',
                  whiteSpace: 'pre-wrap',
                  bgcolor: theme.palette.background.paper,
                  p: 1,
                  borderRadius: 1,
                }}
              >
                {typeof error.masked_data === 'string' 
                  ? error.masked_data 
                  : JSON.stringify(error.masked_data, null, 2)
                }
              </Typography>
            )}

            {/* Timestamp */}
            <Typography variant="body2" sx={{ mt: 2, fontSize: '0.75rem', color: 'text.secondary' }}>
              {error.timestamp}
            </Typography>
          </Paper>
        </Collapse>
      </Alert>
    </Box>
  )
}

export default StandardErrorPanel