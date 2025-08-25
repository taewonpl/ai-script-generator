import React from 'react'
import { Button, Alert, CircularProgress, Typography, Box } from '@mui/material'
import {
  Refresh as RefreshIcon,
  Warning as WarningIcon,
} from '@mui/icons-material'

interface SSERetryButtonProps {
  /**
   * Whether manual retry is available
   */
  canRetry: boolean

  /**
   * Current connection state
   */
  connectionState: 'idle' | 'connecting' | 'open' | 'retrying' | 'closed'

  /**
   * Number of automatic retry attempts made
   */
  retryCount: number

  /**
   * Maximum number of automatic retries
   */
  maxRetries: number

  /**
   * Current error message, if any
   */
  error: string | null

  /**
   * Callback for manual retry attempt
   */
  onRetry: () => void

  /**
   * Whether to show detailed connection info
   */
  showDetails?: boolean

  /**
   * Custom styling
   */
  variant?: 'outlined' | 'contained' | 'text'
}

/**
 * Manual retry button for SSE connections with connection status display
 */
export const SSERetryButton: React.FC<SSERetryButtonProps> = ({
  canRetry,
  connectionState,
  retryCount,
  maxRetries,
  error,
  onRetry,
  showDetails = true,
  variant = 'outlined',
}) => {
  const getStatusDisplay = () => {
    switch (connectionState) {
      case 'idle':
        return { text: 'Not connected', color: 'info', icon: null }
      case 'connecting':
        return {
          text: 'Connecting...',
          color: 'info',
          icon: <CircularProgress size={16} />,
        }
      case 'open':
        return { text: 'Connected', color: 'success', icon: null }
      case 'retrying':
        return {
          text: `Reconnecting... (${retryCount}/${maxRetries})`,
          color: 'warning',
          icon: <CircularProgress size={16} />,
        }
      case 'closed':
        return {
          text: 'Connection lost',
          color: 'error',
          icon: <WarningIcon fontSize="small" />,
        }
      default:
        return { text: 'Unknown', color: 'info', icon: null }
    }
  }

  const status = getStatusDisplay()
  const isConnecting =
    connectionState === 'connecting' || connectionState === 'retrying'

  return (
    <Box>
      {/* Connection Status Display */}
      {showDetails && (
        <Alert
          severity={status.color as any}
          variant="outlined"
          sx={{ mb: 2 }}
          icon={status.icon || undefined}
        >
          <Typography variant="body2" component="div">
            <strong>Connection Status:</strong> {status.text}
            {retryCount > 0 && connectionState !== 'open' && (
              <div>
                Automatic retries: {retryCount}/{maxRetries}
              </div>
            )}
            {error && (
              <div style={{ marginTop: 8 }}>
                <strong>Error:</strong> {error}
              </div>
            )}
          </Typography>
        </Alert>
      )}

      {/* Manual Retry Button */}
      {canRetry && (
        <Box textAlign="center">
          <Button
            variant={variant}
            color="primary"
            size="large"
            onClick={onRetry}
            disabled={isConnecting}
            startIcon={
              isConnecting ? <CircularProgress size={20} /> : <RefreshIcon />
            }
            sx={{
              minWidth: 200,
              minHeight: 48,
              fontWeight: 'bold',
            }}
          >
            {isConnecting ? 'Reconnecting...' : 'Retry Connection'}
          </Button>

          <Typography
            variant="caption"
            display="block"
            sx={{ mt: 1, color: 'text.secondary' }}
          >
            {retryCount >= maxRetries
              ? 'Automatic retries exhausted. Click to retry manually.'
              : 'Connection failed. Click to retry immediately.'}
          </Typography>
        </Box>
      )}

      {/* Connection Recovery Tips */}
      {connectionState === 'closed' && error && showDetails && (
        <Alert severity="info" sx={{ mt: 2 }}>
          <Typography variant="body2">
            <strong>Connection Recovery Tips:</strong>
            <ul style={{ margin: '8px 0', paddingLeft: '16px' }}>
              <li>Check your internet connection</li>
              <li>Try refreshing the page if the issue persists</li>
              <li>Contact support if problems continue</li>
            </ul>
          </Typography>
        </Alert>
      )}
    </Box>
  )
}

/**
 * Compact version of the retry button for inline use
 */
export const CompactSSERetryButton: React.FC<
  Omit<SSERetryButtonProps, 'showDetails'>
> = props => {
  const isConnecting =
    props.connectionState === 'connecting' ||
    props.connectionState === 'retrying'

  if (!props.canRetry) {
    return null
  }

  return (
    <Button
      variant={props.variant || 'text'}
      size="small"
      onClick={props.onRetry}
      disabled={isConnecting}
      startIcon={
        isConnecting ? <CircularProgress size={16} /> : <RefreshIcon />
      }
      sx={{ textTransform: 'none' }}
    >
      {isConnecting ? 'Retrying...' : 'Retry'}
    </Button>
  )
}

export default SSERetryButton
