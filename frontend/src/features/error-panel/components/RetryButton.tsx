/**
 * Standalone retry button component with backoff logic
 */

import { Button, CircularProgress, Tooltip, Typography, Box } from '@mui/material'
import { Refresh as RefreshIcon, Schedule as ScheduleIcon } from '@mui/icons-material'

import { useRetryLogic } from '../hooks/useRetryLogic'
import type { RetryConfig, Language } from '../types'

interface RetryButtonProps {
  onRetry: () => Promise<void>
  retryConfig?: Partial<RetryConfig>
  language?: Language
  variant?: 'text' | 'outlined' | 'contained'
  size?: 'small' | 'medium' | 'large'
  disabled?: boolean
  showProgress?: boolean
  showCountdown?: boolean
}

/**
 * RetryButton - A button with built-in retry logic and exponential backoff
 */
export function RetryButton({
  onRetry,
  retryConfig,
  language = 'kr',
  variant = 'outlined',
  size = 'small',
  disabled = false,
  showProgress = true,
  showCountdown = true,
}: RetryButtonProps) {
  const retryLogic = useRetryLogic(onRetry, retryConfig)

  const retryText = language === 'en' ? 'Retry' : '다시 시도'
  const retryingText = language === 'en' ? 'Retrying...' : '재시도 중...'

  const formatNextRetryTime = (delay: number) => {
    const seconds = Math.ceil(delay / 1000)
    return language === 'en' ? `${seconds}s` : `${seconds}초`
  }

  const buttonText = retryLogic.isRetrying ? retryingText : retryText
  const maxRetries = retryConfig?.maxRetries || 3

  return (
    <Box>
      <Tooltip
        title={
          !retryLogic.canRetry
            ? language === 'en'
              ? 'Maximum retry attempts reached'
              : '최대 재시도 횟수에 도달했습니다'
            : ''
        }
      >
        <span>
          <Button
            variant={variant}
            size={size}
            startIcon={
              retryLogic.isRetrying && showProgress ? (
                <CircularProgress size={14} color="inherit" />
              ) : (
                <RefreshIcon />
              )
            }
            onClick={retryLogic.retry}
            disabled={
              disabled || !retryLogic.canRetry || retryLogic.isRetrying
            }
          >
            {buttonText}
            {retryLogic.retryCount > 0 && (
              <Typography component="span" variant="inherit" sx={{ ml: 0.5 }}>
                ({retryLogic.retryCount}/{maxRetries})
              </Typography>
            )}
          </Button>
        </span>
      </Tooltip>

      {/* Countdown display */}
      {showCountdown &&
        retryLogic.nextRetryDelay &&
        !retryLogic.isRetrying && (
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 0.5,
              mt: 1,
              fontSize: '0.75rem',
              color: 'text.secondary',
            }}
          >
            <ScheduleIcon fontSize="inherit" />
            <Typography variant="caption">
              {language === 'en'
                ? `Next retry in ${formatNextRetryTime(retryLogic.nextRetryDelay)}`
                : `${formatNextRetryTime(retryLogic.nextRetryDelay)} 후 재시도`}
            </Typography>
          </Box>
        )}
    </Box>
  )
}

export default RetryButton