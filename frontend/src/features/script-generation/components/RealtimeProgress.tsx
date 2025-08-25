import { useState, useEffect } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  LinearProgress,
  Stack,
  Chip,
  Alert,
  Button,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Collapse,
} from '@mui/material'
import {
  Cancel as CancelIcon,
  Refresh as RestartIcon,
  CheckCircle as CompleteIcon,
  Info as InfoIcon,
  ExpandMore as ExpandIcon,
  ExpandLess as CollapseIcon,
  Psychology as AIIcon,
  Edit as ProcessIcon,
  Save as SaveIcon,
  Create as EditIcon,
} from '@mui/icons-material'

import { useSSE } from '@/shared/api/streaming/useSSE'
import { useJobControl } from '@/shared/api/hooks'
import { useToastHelpers } from '@/shared/ui/components/toast'
import { env } from '@/shared/config/env'
import type { GenerationJob, GenerationConfig } from '../types'
import type { GenerationResult } from '@/shared/api/streaming/types'

interface RealtimeProgressProps {
  job: GenerationJob
  onCancel: () => void
  onRestart: () => void
  onComplete: (result: GenerationResult) => void
  onError: (error: string) => void
  showDetails?: boolean
  compact?: boolean
}

// Progress stages with descriptions
const PROGRESS_STAGES = {
  initializing: {
    label: '초기화 중',
    description: 'AI 모델을 준비하고 있습니다',
    icon: <AIIcon />,
  },
  analyzing: {
    label: '분석 중',
    description: '프롬프트를 분석하고 컨텍스트를 파악합니다',
    icon: <ProcessIcon />,
  },
  generating: {
    label: '생성 중',
    description: '스크립트를 생성하고 있습니다',
    icon: <EditIcon />,
  },
  reviewing: {
    label: '검토 중',
    description: '생성된 내용을 검토하고 최적화합니다',
    icon: <InfoIcon />,
  },
  finalizing: {
    label: '마무리 중',
    description: '최종 스크립트를 저장합니다',
    icon: <SaveIcon />,
  },
  completed: {
    label: '완료',
    description: '스크립트 생성이 완료되었습니다',
    icon: <CompleteIcon />,
  },
}

/**
 * Progress visualization component
 */
function ProgressVisualization({
  progress,
  stage,
  compact = false,
}: {
  progress: number
  stage: string
  compact?: boolean
}) {
  const stageInfo = PROGRESS_STAGES[stage as keyof typeof PROGRESS_STAGES] || {
    label: stage,
    description: '',
    icon: <ProcessIcon />,
  }

  const getProgressColor = () => {
    if (progress >= 100) return 'success'
    if (progress >= 75) return 'info'
    if (progress >= 50) return 'warning'
    return 'error'
  }

  return (
    <Box>
      <Box display="flex" alignItems="center" justifyContent="between" mb={1}>
        <Box display="flex" alignItems="center" gap={1}>
          {stageInfo.icon}
          <Typography
            variant={compact ? 'body2' : 'subtitle1'}
            fontWeight="medium"
          >
            {stageInfo.label}
          </Typography>
        </Box>
        <Typography
          variant={compact ? 'caption' : 'body2'}
          color="textSecondary"
        >
          {Math.round(progress)}%
        </Typography>
      </Box>

      <LinearProgress
        variant="determinate"
        value={Math.min(progress, 100)}
        color={getProgressColor() as any}
        sx={{
          height: compact ? 6 : 8,
          borderRadius: 4,
          mb: compact ? 1 : 2,
        }}
      />

      {!compact && stageInfo.description && (
        <Typography variant="body2" color="textSecondary">
          {stageInfo.description}
        </Typography>
      )}
    </Box>
  )
}

/**
 * Estimated time remaining display
 */
function TimeEstimate({
  estimatedTime,
  startTime,
}: {
  estimatedTime?: number
  startTime: Date
}) {
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    const interval = setInterval(() => {
      setElapsed(Date.now() - startTime.getTime())
    }, 1000)

    return () => clearInterval(interval)
  }, [startTime])

  const formatTime = (ms: number) => {
    const seconds = Math.floor(ms / 1000)
    if (seconds < 60) return `${seconds}초`
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    return `${minutes}분 ${remainingSeconds}초`
  }

  return (
    <Stack direction="row" spacing={2} alignItems="center">
      <Typography variant="body2" color="textSecondary">
        진행 시간: {formatTime(elapsed)}
      </Typography>
      {estimatedTime && estimatedTime > 0 && (
        <Typography variant="body2" color="textSecondary">
          예상 남은 시간: {formatTime(estimatedTime * 1000)}
        </Typography>
      )}
    </Stack>
  )
}

/**
 * Job configuration summary
 */
function JobConfigSummary({
  config,
  expanded,
  onToggle,
}: {
  config: GenerationConfig
  expanded: boolean
  onToggle: () => void
}) {
  return (
    <Card variant="outlined">
      <CardContent sx={{ pb: expanded ? 2 : '16px !important' }}>
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Typography variant="subtitle2">생성 설정</Typography>
          <IconButton onClick={onToggle} size="small">
            {expanded ? <CollapseIcon /> : <ExpandIcon />}
          </IconButton>
        </Box>

        <Collapse in={expanded}>
          <Stack spacing={1} mt={2}>
            <Stack direction="row" spacing={1} flexWrap="wrap">
              {config.aiModel && (
                <Chip label={`AI: ${config.aiModel}`} size="small" />
              )}
              {config.genre && (
                <Chip label={`장르: ${config.genre}`} size="small" />
              )}
              {config.tone && (
                <Chip label={`톤: ${config.tone}`} size="small" />
              )}
              {config.length && (
                <Chip label={`길이: ${config.length}`} size="small" />
              )}
              {config.language && (
                <Chip label={`언어: ${config.language}`} size="small" />
              )}
            </Stack>

            {config.characters && config.characters.length > 0 && (
              <Typography variant="body2" color="textSecondary">
                등장인물: {config.characters.join(', ')}
              </Typography>
            )}

            {config.themes && config.themes.length > 0 && (
              <Typography variant="body2" color="textSecondary">
                주제: {config.themes.join(', ')}
              </Typography>
            )}

            <Typography
              variant="body2"
              color="textSecondary"
              sx={{
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                display: '-webkit-box',
                WebkitLineClamp: 3,
                WebkitBoxOrient: 'vertical',
              }}
            >
              프롬프트: {config.prompt}
            </Typography>
          </Stack>
        </Collapse>
      </CardContent>
    </Card>
  )
}

/**
 * Real-time progress tracking component
 */
export function RealtimeProgress({
  job,
  onCancel,
  onRestart,
  onComplete,
  onError,
  showDetails = true,
  compact = false,
}: RealtimeProgressProps) {
  const [showCancelDialog, setShowCancelDialog] = useState(false)
  const [showConfigDetails, setShowConfigDetails] = useState(false)

  const { showSuccess, showError } = useToastHelpers()
  const { cancelJob, isCanceling } = useJobControl()

  // SSE connection for real-time updates
  const sseUrl = `${env.VITE_GENERATION_SERVICE_URL}/api/v1/jobs/${job.id}/stream`

  const {
    connectionState,
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

  // Handle SSE events
  useEffect(() => {
    if (!latestEvent || latestEvent.jobId !== job.id) return

    switch (latestEvent.type) {
      case 'progress':
        // Progress updates are handled by the parent component
        break

      case 'completed':
        showSuccess('스크립트 생성이 완료되었습니다!')
        // @ts-expect-error - Temporary workaround for GenerationResult type mismatch
        onComplete(latestEvent.result)
        disconnect()
        break

      case 'failed':
        showError('스크립트 생성 중 오류가 발생했습니다.')
        onError(latestEvent.error.message)
        disconnect()
        break

      // Note: 'canceled' event type removed as it's not in Python backend
    }
  }, [
    latestEvent,
    job.id,
    onComplete,
    onError,
    onCancel,
    disconnect,
    showSuccess,
    showError,
  ])

  // Handle job cancellation
  const handleCancel = async () => {
    try {
      await cancelJob(job.id, 'User requested cancellation')
      setShowCancelDialog(false)
    } catch (error) {
      console.error('Failed to cancel job:', error)
    }
  }

  const isActive = job.status === 'streaming' || job.status === 'queued'
  const isCompleted = job.status === 'completed'
  const isFailed = job.status === 'failed'
  const isCancelled = job.status === 'canceled'

  return (
    <Stack spacing={3}>
      {/* Main Progress Card */}
      <Card>
        <CardContent>
          <Box
            display="flex"
            alignItems="center"
            justifyContent="between"
            mb={3}
          >
            <Typography variant={compact ? 'h6' : 'h5'}>
              AI 스크립트 생성 진행상황
            </Typography>

            <Stack direction="row" spacing={1}>
              {/* Connection Status */}
              <Chip
                label={
                  connectionState === 'open' ? '실시간 연결됨' : '연결 중...'
                }
                color={connectionState === 'open' ? 'success' : 'warning'}
                size="small"
                variant="outlined"
              />

              {/* Action Buttons */}
              {isActive && (
                <>
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
                </>
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

          {/* Progress Visualization */}
          <ProgressVisualization
            progress={job.progress}
            stage={job.currentStep}
            compact={compact}
          />

          {/* Time Information */}
          {isActive && (
            <Box mt={2}>
              <TimeEstimate
                {...(job.estimatedTime !== undefined && {
                  estimatedTime: job.estimatedTime,
                })}
                startTime={job.createdAt}
              />
            </Box>
          )}

          {/* Status Messages */}
          {isFailed && (
            <Alert severity="error" sx={{ mt: 2 }}>
              생성 실패: {job.error || '알 수 없는 오류가 발생했습니다.'}
            </Alert>
          )}

          {isCancelled && (
            <Alert severity="warning" sx={{ mt: 2 }}>
              사용자에 의해 취소되었습니다.
            </Alert>
          )}

          {isCompleted && (
            <Alert severity="success" sx={{ mt: 2 }}>
              스크립트 생성이 성공적으로 완료되었습니다!
            </Alert>
          )}

          {sseError && (
            <Alert severity="error" sx={{ mt: 2 }}>
              실시간 연결 오류: {sseError.message}
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Configuration Details */}
      {showDetails && (
        <JobConfigSummary
          config={job.config}
          expanded={showConfigDetails}
          onToggle={() => setShowConfigDetails(!showConfigDetails)}
        />
      )}

      {/* Cancel Confirmation Dialog */}
      <Dialog
        open={showCancelDialog}
        onClose={() => setShowCancelDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>스크립트 생성 취소</DialogTitle>
        <DialogContent>
          <Typography>
            정말로 스크립트 생성을 취소하시겠습니까? 현재까지의 진행사항은
            저장되지 않습니다.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowCancelDialog(false)}>계속 진행</Button>
          <Button onClick={handleCancel} color="error" disabled={isCanceling}>
            {isCanceling ? '취소 중...' : '취소 확인'}
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  )
}
