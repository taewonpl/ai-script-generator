import { useState, useEffect } from 'react'
import {
  Box,
  LinearProgress,
  Typography,
  Chip,
  IconButton,
  Card,
  CardContent,
  Alert,
  Stack,
  Tooltip,
} from '@mui/material'
import {
  Cancel as CancelIcon,
  CheckCircle as CompletedIcon,
  Error as ErrorIcon,
  Pause as PauseIcon,
  PlayArrow as RunningIcon,
  Schedule as QueuedIcon,
  Wifi as ConnectedIcon,
  SignalWifiOff as DisconnectedIcon,
  Refresh as RetryingIcon,
} from '@mui/icons-material'

import { useSSE } from '@/shared/api/streaming/useSSE'
import { useJobControl } from '@/shared/api/hooks/useJobControl'
import type { ProgressEventData } from '@/shared/api/streaming/types'

export interface JobProgressIndicatorProps {
  jobId: string
  sseUrl: string
  title?: string
  onComplete?: (result: unknown) => void
  onError?: (error: string) => void
  onCancel?: () => void
  showConnectionStatus?: boolean
  autoConnect?: boolean
}

/**
 * Real-time job progress indicator with SSE connection
 *
 * Features:
 * - Real-time progress updates via SSE
 * - Connection status indicator
 * - Job cancellation
 * - Auto-reconnection
 * - Error handling
 */
export function JobProgressIndicator({
  jobId,
  sseUrl,
  title = 'Job Progress',
  onComplete,
  onError,
  onCancel,
  showConnectionStatus = true,
  autoConnect = true,
}: JobProgressIndicatorProps) {
  const [currentProgress, setCurrentProgress] = useState(0)
  const [currentStage, setCurrentStage] = useState<string>('')
  const [currentMessage, setCurrentMessage] = useState<string>('')
  const [jobStatus, setJobStatus] = useState<string>('pending')
  const [estimatedTimeRemaining, setEstimatedTimeRemaining] = useState<
    number | null
  >(null)

  // SSE connection
  const {
    connectionState,
    latestEvent,
    error: sseError,
    connect,
    disconnect,
    retryCount,
  } = useSSE({
    url: sseUrl,
    maxRetries: 5,
    retryDelays: [1000, 2000, 5000, 15000],
    heartbeatTimeout: 30000,
  })

  // Job control
  const { cancelJob, isCanceling, cancelError, canCancelJob } = useJobControl()

  // Auto-connect on mount
  useEffect(() => {
    if (autoConnect) {
      connect()
    }
    return () => disconnect()
  }, [autoConnect, connect, disconnect])

  // Handle SSE events
  useEffect(() => {
    if (!latestEvent || latestEvent.jobId !== jobId) return

    switch (latestEvent.type) {
      case 'progress': {
        const progressData = latestEvent as ProgressEventData
        setCurrentProgress(progressData.data.progress)
        setCurrentStage(progressData.data.stage)
        setCurrentMessage(progressData.data.message || '')
        setEstimatedTimeRemaining(
          progressData.data.estimatedTimeRemaining || null,
        )
        setJobStatus('running')
        break
      }

      case 'completed':
        setCurrentProgress(100)
        setJobStatus('completed')
        onComplete?.(latestEvent.data.result)
        break

      case 'failed':
        setJobStatus('failed')
        onError?.(latestEvent.data.error)
        break

      case 'canceled':
        setJobStatus('canceled')
        onCancel?.()
        break
    }
  }, [latestEvent, jobId, onComplete, onError, onCancel])

  // Handle job cancellation
  const handleCancel = async () => {
    try {
      await cancelJob(jobId, 'User requested cancellation')
      setJobStatus('canceling')
    } catch (error) {
      console.error('Failed to cancel job:', error)
    }
  }

  // Get connection status info
  const getConnectionStatusInfo = () => {
    switch (connectionState) {
      case 'idle':
        return {
          icon: <DisconnectedIcon />,
          color: 'default',
          text: 'Not Connected',
        }
      case 'connecting':
        return { icon: <RetryingIcon />, color: 'info', text: 'Connecting...' }
      case 'open':
        return { icon: <ConnectedIcon />, color: 'success', text: 'Connected' }
      case 'retrying':
        return {
          icon: <RetryingIcon />,
          color: 'warning',
          text: `Retrying (${retryCount})`,
        }
      case 'closed':
        return {
          icon: <DisconnectedIcon />,
          color: 'error',
          text: 'Disconnected',
        }
    }
  }

  // Get job status info
  const getJobStatusInfo = () => {
    switch (jobStatus) {
      case 'pending':
        return { icon: <QueuedIcon />, color: 'default', text: 'Pending' }
      case 'running':
        return { icon: <RunningIcon />, color: 'info', text: 'Running' }
      case 'canceling':
        return { icon: <PauseIcon />, color: 'warning', text: 'Canceling...' }
      case 'completed':
        return { icon: <CompletedIcon />, color: 'success', text: 'Completed' }
      case 'failed':
        return { icon: <ErrorIcon />, color: 'error', text: 'Failed' }
      case 'canceled':
        return { icon: <CancelIcon />, color: 'warning', text: 'Canceled' }
      default:
        return { icon: <QueuedIcon />, color: 'default', text: jobStatus }
    }
  }

  // Format time remaining
  const formatTimeRemaining = (seconds: number): string => {
    if (seconds < 60) return `${Math.round(seconds)}s`
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = Math.round(seconds % 60)
    return `${minutes}m ${remainingSeconds}s`
  }

  const connectionStatus = getConnectionStatusInfo()
  const jobStatusInfo = getJobStatusInfo()
  const showCancelButton = canCancelJob(jobStatus) && !isCanceling
  const isActive = ['pending', 'running'].includes(jobStatus)

  return (
    <Card variant="outlined">
      <CardContent>
        <Stack spacing={2}>
          {/* Header */}
          <Box
            display="flex"
            alignItems="center"
            justifyContent="space-between"
          >
            <Typography variant="h6" component="h3">
              {title}
            </Typography>

            <Stack direction="row" spacing={1} alignItems="center">
              {/* Connection Status */}
              {showConnectionStatus && (
                <Tooltip title={connectionStatus.text}>
                  <Chip
                    icon={connectionStatus.icon}
                    label={connectionStatus.text}
                    color={connectionStatus.color as any}
                    size="small"
                    variant="outlined"
                  />
                </Tooltip>
              )}

              {/* Job Status */}
              <Chip
                icon={jobStatusInfo.icon}
                label={jobStatusInfo.text}
                color={jobStatusInfo.color as any}
                size="small"
              />

              {/* Cancel Button */}
              {showCancelButton && (
                <Tooltip title="Cancel Job">
                  <IconButton
                    onClick={handleCancel}
                    disabled={isCanceling}
                    color="error"
                    size="small"
                  >
                    <CancelIcon />
                  </IconButton>
                </Tooltip>
              )}
            </Stack>
          </Box>

          {/* Progress Bar */}
          {isActive && (
            <Box>
              <LinearProgress
                variant="determinate"
                value={currentProgress}
                sx={{ height: 8, borderRadius: 4 }}
              />
              <Box display="flex" justifyContent="space-between" mt={1}>
                <Typography variant="body2" color="textSecondary">
                  {currentProgress.toFixed(1)}%
                </Typography>
                {estimatedTimeRemaining && (
                  <Typography variant="body2" color="textSecondary">
                    ~{formatTimeRemaining(estimatedTimeRemaining)} remaining
                  </Typography>
                )}
              </Box>
            </Box>
          )}

          {/* Current Stage and Message */}
          {(currentStage || currentMessage) && (
            <Box>
              {currentStage && (
                <Typography variant="subtitle2" color="primary">
                  {currentStage}
                </Typography>
              )}
              {currentMessage && (
                <Typography variant="body2" color="textSecondary">
                  {currentMessage}
                </Typography>
              )}
            </Box>
          )}

          {/* Error Messages */}
          {sseError && (
            <Alert severity="error">Connection Error: {sseError.message}</Alert>
          )}

          {cancelError && (
            <Alert severity="error">Cancel Error: {cancelError.message}</Alert>
          )}

          {/* Job ID (for debugging) */}
          <Typography variant="caption" color="textSecondary">
            Job ID: {jobId}
          </Typography>
        </Stack>
      </CardContent>
    </Card>
  )
}
