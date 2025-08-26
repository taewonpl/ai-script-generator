/**
 * Save progress indicator for generation save states
 */

import React, { useState, useEffect } from 'react'
import {
  Box,
  Button,
  CircularProgress,
  Typography,
  Alert,
  Chip,
} from '@mui/material'
import { CheckCircle, Error, Save, Replay, Schedule } from '@mui/icons-material'

export interface SaveState {
  status:
    | 'saving'
    | 'completed_pending_save'
    | 'save_failed'
    | 'completed'
    | 'failed'
  saveJobId?: string
  retryCount?: number
  maxRetries?: number
  lastError?: string
  nextRetryAt?: string
}

interface SaveProgressIndicatorProps {
  saveState: SaveState
  onManualSave?: () => void
  generationId: string
}

export const SaveProgressIndicator: React.FC<SaveProgressIndicatorProps> = ({
  saveState,
  onManualSave,
  generationId: _generationId,
}) => {
  const [timeUntilRetry, setTimeUntilRetry] = useState<number | null>(null)

  useEffect(() => {
    if (saveState.nextRetryAt) {
      const calculateTimeLeft = () => {
        const now = new Date().getTime()
        const retryTime = new Date(saveState.nextRetryAt!).getTime()
        const difference = retryTime - now

        return difference > 0 ? Math.ceil(difference / 1000) : 0
      }

      const timer = setInterval(() => {
        const timeLeft = calculateTimeLeft()
        setTimeUntilRetry(timeLeft)

        if (timeLeft <= 0) {
          clearInterval(timer)
          setTimeUntilRetry(null)
        }
      }, 1000)

      return () => clearInterval(timer)
    }

    return () => {} // cleanup function for when condition is not met
  }, [saveState.nextRetryAt])

  const renderSaveStatus = () => {
    switch (saveState.status) {
      case 'saving':
        return (
          <Box display="flex" alignItems="center" gap={1}>
            <CircularProgress size={20} />
            <Typography variant="body2" color="primary">
              저장 중...
            </Typography>
          </Box>
        )

      case 'completed_pending_save':
        return (
          <Box display="flex" flexDirection="column" gap={1}>
            <Box display="flex" alignItems="center" gap={1}>
              <Schedule color="warning" />
              <Typography variant="body2" color="warning.main">
                대본 생성 완료, 저장 중...
              </Typography>
              {saveState.retryCount && saveState.maxRetries && (
                <Chip
                  label={`재시도 ${saveState.retryCount}/${saveState.maxRetries}`}
                  size="small"
                  color="warning"
                  variant="outlined"
                />
              )}
            </Box>

            {timeUntilRetry && (
              <Typography variant="caption" color="text.secondary">
                다음 재시도까지: {timeUntilRetry}초
              </Typography>
            )}
          </Box>
        )

      case 'save_failed':
        return (
          <Box display="flex" flexDirection="column" gap={1}>
            <Alert severity="error" variant="outlined">
              <Typography variant="body2">저장에 실패했습니다</Typography>
              {saveState.lastError && (
                <Typography variant="caption" color="text.secondary">
                  오류: {saveState.lastError}
                </Typography>
              )}
            </Alert>

            <Box display="flex" gap={1}>
              {onManualSave && (
                <Button
                  variant="contained"
                  size="small"
                  startIcon={<Save />}
                  onClick={onManualSave}
                  color="primary"
                >
                  수동 저장
                </Button>
              )}

              <Button
                variant="outlined"
                size="small"
                startIcon={<Replay />}
                onClick={() => window.location.reload()}
              >
                새로고침
              </Button>
            </Box>
          </Box>
        )

      case 'completed':
        return (
          <Box display="flex" alignItems="center" gap={1}>
            <CheckCircle color="success" />
            <Typography variant="body2" color="success.main">
              저장 완료
            </Typography>
          </Box>
        )

      case 'failed':
        return (
          <Box display="flex" alignItems="center" gap={1}>
            <Error color="error" />
            <Typography variant="body2" color="error.main">
              생성 실패
            </Typography>
          </Box>
        )

      default:
        return null
    }
  }

  const getProgressColor = () => {
    switch (saveState.status) {
      case 'saving':
      case 'completed_pending_save':
        return 'warning'
      case 'save_failed':
      case 'failed':
        return 'error'
      case 'completed':
        return 'success'
      default:
        return 'primary'
    }
  }

  return (
    <Box
      sx={{
        p: 2,
        borderRadius: 1,
        border: 1,
        borderColor: `${getProgressColor()}.main`,
        backgroundColor: `${getProgressColor()}.50`,
      }}
    >
      {renderSaveStatus()}
    </Box>
  )
}

// Hook for managing save state
// eslint-disable-next-line react-refresh/only-export-components
export const useSaveProgress = (generationId: string) => {
  const [saveState, setSaveState] = useState<SaveState>({
    status: 'saving',
  })

  const updateSaveState = (newState: Partial<SaveState>) => {
    setSaveState(prev => ({ ...prev, ...newState }))
  }

  const handleManualSave = async () => {
    try {
      setSaveState(prev => ({ ...prev, status: 'saving' }))

      // Call manual save API
      const response = await fetch(
        `/api/v1/generations/${generationId}/manual-save`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
        },
      )

      if (response.ok) {
        setSaveState(prev => ({ ...prev, status: 'completed' }))
      } else {
        // @ts-expect-error - Temporary workaround for Error constructor type issue
        throw new Error('Manual save failed')
      }
    } catch (error) {
      setSaveState(prev => ({
        ...prev,
        status: 'save_failed',
        // @ts-expect-error - Temporary workaround for error message property access
        lastError: error instanceof Error ? error.message : 'Unknown error',
      }))
    }
  }

  return {
    saveState,
    updateSaveState,
    handleManualSave,
  }
}
