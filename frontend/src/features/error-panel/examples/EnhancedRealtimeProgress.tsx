/**
 * Example integration: Enhanced RealtimeProgress with ErrorPanel
 * This demonstrates how to integrate ErrorPanel into existing components
 */

import { useState, useEffect } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Stack,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
} from '@mui/material'
import {
  Cancel as CancelIcon,
  Refresh as RestartIcon,
} from '@mui/icons-material'

import { useSSE } from '@/shared/api/streaming/useSSE'
import { useJobControl } from '@/shared/api/hooks'
import { useToastHelpers } from '@/shared/ui/components/toast'
import { ErrorPanel } from '../components/ErrorPanel'
import { useErrorPanel } from '../hooks/useErrorPanel'
import { env } from '@/shared/config/env'

// Import types (these would come from the actual component)
interface GenerationJob {
  id: string
  status: 'streaming' | 'queued' | 'completed' | 'failed' | 'canceled'
  progress: number
  currentStep: string
  error?: string
  createdAt: string
  estimatedTime?: number
}

interface GenerationResult {
  content: string
  metadata: Record<string, any>
}

interface EnhancedRealtimeProgressProps {
  job: GenerationJob
  onRestart: () => void
  onComplete: (result: GenerationResult) => void
  onError: (error: string) => void
  showDetails?: boolean
  compact?: boolean
}

/**
 * Enhanced version of RealtimeProgress with ErrorPanel integration
 */
export function EnhancedRealtimeProgress({
  job,
  onRestart,
  onComplete,
  onError,
  showDetails = true,
  compact = false,
}: EnhancedRealtimeProgressProps) {
  const [showCancelDialog, setShowCancelDialog] = useState(false)
  const { showSuccess } = useToastHelpers()
  const { cancelJob, isCanceling } = useJobControl()

  // Initialize ErrorPanel hook
  const errorPanel = useErrorPanel({
    language: 'kr', // Can be made configurable
    autoShow: true,
    showInToast: false, // Let ErrorPanel handle the display
    retryConfig: {
      maxRetries: 3,
      baseDelay: 2000,
      exponentialBackoff: true,
      jitter: true,
    },
  })

  // SSE connection for real-time updates
  const sseUrl = `${env.VITE_GENERATION_SERVICE_URL}/api/v1/jobs/${job.id}/stream`

  const {
    latestEvent,
    error: sseError,
    connect,
    disconnect,
  } = useSSE({
    url: sseUrl,
    maxRetries: 5,
    retryDelays: [1000, 2000, 5000, 15000],
  })

  // Auto-connect on mount
  useEffect(() => {
    if (job.status === 'streaming' || job.status === 'queued') {
      connect()
    }
    return () => disconnect()
  }, [job.id, job.status, connect, disconnect])

  // Handle SSE connection errors
  useEffect(() => {
    if (sseError) {
      errorPanel.showError(sseError, async () => {
        // Retry logic for SSE connection by reconnecting
        connect()
      })
    }
  }, [sseError, errorPanel, connect])

  // Handle SSE events
  useEffect(() => {
    if (!latestEvent || latestEvent.jobId !== job.id) return

    switch (latestEvent.type) {
      case 'progress':
        // Hide any previous errors on successful progress
        if (errorPanel.isVisible) {
          errorPanel.hideError()
        }
        break

      case 'completed':
        showSuccess('스크립트 생성이 완료되었습니다!')
        errorPanel.hideError() // Clear any errors
        // @ts-expect-error - Temporary workaround for GenerationResult type mismatch
        onComplete(latestEvent.result)
        disconnect()
        break

      case 'failed': {
        // Use ErrorPanel instead of simple toast
        const errorDetails = {
          error_type: 'server_unavailable' as const,
          http_status: 500,
          hint: '스크립트 생성 중 서버에서 오류가 발생했습니다.',
          timestamp: new Date().toISOString(),
          userMessage: latestEvent.error.message || '스크립트 생성 중 오류가 발생했습니다.',
          technicalMessage: latestEvent.error.message,
          retryable: true,
          context: {
            jobId: job.id,
            step: job.currentStep,
            progress: job.progress,
            eventData: latestEvent,
          },
        }

        errorPanel.showError(errorDetails, async () => {
          // Retry generation by restarting the job
          onRestart()
        })

        onError(latestEvent.error.message)
        disconnect()
        break
      }
      
      default:
        // Production safety: Legacy component graceful handling
        // For legacy components that only handle core events, we can log and ignore unknown types
        // In development, this will still show a warning in the console
        console.debug('Ignoring unknown event type in legacy component:', (latestEvent as any).type)
        if (import.meta.env.DEV) {
          console.warn('Legacy component missing handler for:', latestEvent)
        }
    }
  }, [
    latestEvent,
    job.id,
    job.currentStep,
    job.progress,
    onComplete,
    onError,
    onRestart,
    disconnect,
    showSuccess,
    errorPanel,
  ])

  // Handle job cancellation
  const handleCancel = async () => {
    try {
      await cancelJob(job.id, 'User requested cancellation')
      setShowCancelDialog(false)
      errorPanel.hideError() // Clear any errors when canceling
    } catch (error) {
      errorPanel.showError(error, async () => {
        // Retry cancellation
        await handleCancel()
      })
    }
  }

  const isActive = job.status === 'streaming' || job.status === 'queued'
  const isCompleted = job.status === 'completed'
  const isFailed = job.status === 'failed'
  const isCancelled = job.status === 'canceled'

  return (
    <Stack spacing={3}>
      {/* Error Panel - shows when there are errors */}
      {errorPanel.isVisible && errorPanel.error && (
        <ErrorPanel
          error={errorPanel.error}
          onRetry={errorPanel.currentRetryFn}
          onDismiss={errorPanel.hideError}
          language="kr"
          compact={compact}
          showTechnicalDetails={showDetails}
        />
      )}

      {/* Main Progress Card */}
      <Card>
        <CardContent>
          <Box display="flex" alignItems="center" justifyContent="space-between" mb={3}>
            <Typography variant={compact ? 'h6' : 'h5'}>
              AI 스크립트 생성 진행상황
            </Typography>

            <Stack direction="row" spacing={1}>
              {/* Action Buttons */}
              {isActive && (
                <Button
                  variant="outlined"
                  color="error"
                  startIcon={<CancelIcon />}
                  onClick={() => setShowCancelDialog(true)}
                  disabled={isCanceling}
                  size="small"
                >
                  {isCanceling ? '취소 중...' : '취소'}
                </Button>
              )}

              {(isFailed || isCancelled) && (
                <Button
                  variant="outlined"
                  startIcon={<RestartIcon />}
                  onClick={onRestart}
                  size="small"
                >
                  다시 시작
                </Button>
              )}
            </Stack>
          </Box>

          {/* Progress and Status Information */}
          <Typography variant="body1">진행률: {Math.round(job.progress * 100)}%</Typography>
          <Typography variant="body2" color="textSecondary">
            현재 단계: {job.currentStep}
          </Typography>

          {/* Success/Warning Alerts (Error is handled by ErrorPanel above) */}
          {isCompleted && (
            <Alert severity="success" sx={{ mt: 2 }}>
              스크립트 생성이 성공적으로 완료되었습니다!
            </Alert>
          )}

          {isCancelled && (
            <Alert severity="warning" sx={{ mt: 2 }}>
              사용자에 의해 취소되었습니다.
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Cancel Confirmation Dialog */}
      <Dialog
        open={showCancelDialog}
        onClose={() => setShowCancelDialog(false)}
      >
        <DialogTitle>생성 취소</DialogTitle>
        <DialogContent>
          <Typography>
            정말로 스크립트 생성을 취소하시겠습니까?
            <br />
            지금까지의 진행상황이 모두 사라집니다.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowCancelDialog(false)}>아니오</Button>
          <Button
            onClick={handleCancel}
            color="error"
            disabled={isCanceling}
          >
            {isCanceling ? '취소 중...' : '예, 취소합니다'}
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  )
}

export default EnhancedRealtimeProgress