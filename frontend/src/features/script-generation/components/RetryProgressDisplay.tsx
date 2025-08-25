/**
 * Real-time retry progress display
 */

import React, { useState, useEffect } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  LinearProgress,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Chip,
  Collapse,
  IconButton,
  Alert,
} from '@mui/material'
import {
  Schedule,
  CheckCircle,
  Error,
  ExpandMore,
  ExpandLess,
  Refresh,
} from '@mui/icons-material'

export interface RetryAttempt {
  attempt: number
  timestamp: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  error?: string
  nextRetryAt?: string
}

export interface RetryProgress {
  jobId: string
  generationId: string
  currentAttempt: number
  maxAttempts: number
  attempts: RetryAttempt[]
  status: 'processing' | 'completed' | 'failed' | 'dead'
  createdAt: string
  lastError?: string
}

interface RetryProgressDisplayProps {
  retryProgress: RetryProgress
  onRefresh?: () => void
}

export const RetryProgressDisplay: React.FC<RetryProgressDisplayProps> = ({
  retryProgress,
  onRefresh,
}) => {
  const [expanded, setExpanded] = useState(false)
  const [countdown, setCountdown] = useState<number | null>(null)

  // Find next retry time
  const nextRetry = retryProgress.attempts.find(
    attempt => attempt.status === 'pending' && attempt.nextRetryAt,
  )

  useEffect(() => {
    if (nextRetry?.nextRetryAt) {
      const calculateCountdown = () => {
        const now = new Date().getTime()
        const retryTime = new Date(nextRetry.nextRetryAt!).getTime()
        const difference = retryTime - now

        return difference > 0 ? Math.ceil(difference / 1000) : 0
      }

      const timer = setInterval(() => {
        const timeLeft = calculateCountdown()
        setCountdown(timeLeft)

        if (timeLeft <= 0) {
          clearInterval(timer)
          setCountdown(null)
        }
      }, 1000)

      return () => clearInterval(timer)
    }

    return () => {} // cleanup function for when condition is not met
  }, [nextRetry?.nextRetryAt])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success'
      case 'failed':
      case 'dead':
        return 'error'
      case 'processing':
        return 'info'
      case 'pending':
      default:
        return 'warning'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle color="success" />
      case 'failed':
      case 'dead':
        return <Error color="error" />
      case 'processing':
        return <Refresh color="info" />
      case 'pending':
      default:
        return <Schedule color="warning" />
    }
  }

  const progressPercentage =
    (retryProgress.currentAttempt / retryProgress.maxAttempts) * 100

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('ko-KR')
  }

  return (
    <Card variant="outlined">
      <CardContent>
        <Box
          display="flex"
          justifyContent="space-between"
          alignItems="center"
          mb={2}
        >
          <Typography variant="h6" component="h3">
            저장 재시도 진행 상황
          </Typography>
          <Box display="flex" alignItems="center" gap={1}>
            <Chip
              label={`${retryProgress.currentAttempt}/${retryProgress.maxAttempts}`}
              color={getStatusColor(retryProgress.status) as any}
              size="small"
            />
            {onRefresh && (
              <IconButton size="small" onClick={onRefresh}>
                <Refresh />
              </IconButton>
            )}
          </Box>
        </Box>

        {/* Progress bar */}
        <Box mb={2}>
          <LinearProgress
            variant="determinate"
            value={progressPercentage}
            color={getStatusColor(retryProgress.status) as any}
          />
          <Typography variant="caption" color="text.secondary" mt={0.5}>
            진행률: {progressPercentage.toFixed(0)}%
          </Typography>
        </Box>

        {/* Current status */}
        <Box display="flex" alignItems="center" gap={1} mb={1}>
          {getStatusIcon(retryProgress.status)}
          <Typography variant="body2">
            {retryProgress.status === 'processing' && '처리 중...'}
            {retryProgress.status === 'completed' && '저장 완료'}
            {retryProgress.status === 'failed' && '재시도 대기 중...'}
            {retryProgress.status === 'dead' && '최대 재시도 횟수 초과'}
          </Typography>
        </Box>

        {/* Countdown */}
        {countdown !== null && countdown > 0 && (
          <Alert severity="info" sx={{ mb: 2 }}>
            다음 재시도까지: {countdown}초
          </Alert>
        )}

        {/* Last error */}
        {retryProgress.lastError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            <Typography variant="body2">
              최근 오류: {retryProgress.lastError}
            </Typography>
          </Alert>
        )}

        {/* Attempts list toggle */}
        <Box display="flex" alignItems="center" gap={1} mb={1}>
          <IconButton size="small" onClick={() => setExpanded(!expanded)}>
            {expanded ? <ExpandLess /> : <ExpandMore />}
          </IconButton>
          <Typography variant="body2">
            재시도 내역 ({retryProgress.attempts.length}개)
          </Typography>
        </Box>

        {/* Attempts list */}
        <Collapse in={expanded}>
          <List dense>
            {retryProgress.attempts.map(attempt => (
              <ListItem key={attempt.attempt} divider>
                <ListItemIcon>{getStatusIcon(attempt.status)}</ListItemIcon>
                <ListItemText
                  primary={`시도 ${attempt.attempt}`}
                  secondary={
                    <Box>
                      <Typography variant="caption" display="block">
                        시간: {formatTime(attempt.timestamp)}
                      </Typography>
                      {attempt.error && (
                        <Typography
                          variant="caption"
                          color="error"
                          display="block"
                        >
                          오류: {attempt.error}
                        </Typography>
                      )}
                      {attempt.nextRetryAt && (
                        <Typography
                          variant="caption"
                          color="text.secondary"
                          display="block"
                        >
                          다음 재시도: {formatTime(attempt.nextRetryAt)}
                        </Typography>
                      )}
                    </Box>
                  }
                />
                <Chip
                  label={attempt.status}
                  size="small"
                  color={getStatusColor(attempt.status) as any}
                  variant="outlined"
                />
              </ListItem>
            ))}
          </List>
        </Collapse>

        {/* Job info */}
        <Box mt={2} pt={2} borderTop={1} borderColor="divider">
          <Typography variant="caption" color="text.secondary" display="block">
            작업 ID: {retryProgress.jobId}
          </Typography>
          <Typography variant="caption" color="text.secondary" display="block">
            생성 시간: {formatTime(retryProgress.createdAt)}
          </Typography>
        </Box>
      </CardContent>
    </Card>
  )
}

// Hook for real-time retry progress updates
export const useRetryProgress = (generationId: string) => {
  const [retryProgress, setRetryProgress] = useState<RetryProgress | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchRetryProgress = async () => {
    try {
      setLoading(true)
      const response = await fetch(
        `/api/v1/generations/${generationId}/retry-progress`,
      )

      if (response.ok) {
        const data = await response.json()
        setRetryProgress(data.data)
        setError(null)
      } else if (response.status === 404) {
        // No retry progress found (normal case)
        setRetryProgress(null)
        setError(null)
      } else {
        // @ts-expect-error - Temporary workaround for Error constructor type issue
        throw new Error('Failed to fetch retry progress')
      }
    } catch (err) {
      // @ts-expect-error - Temporary workaround for error message property access
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchRetryProgress()

    // Poll for updates every 5 seconds if there's active retry progress
    const interval = setInterval(() => {
      if (retryProgress && retryProgress.status === 'processing') {
        fetchRetryProgress()
      }
    }, 5000)

    return () => clearInterval(interval)
  }, [generationId, retryProgress?.status])

  return {
    retryProgress,
    loading,
    error,
    refresh: fetchRetryProgress,
  }
}

// Combined component for save progress and retry display
export const SaveAndRetryProgress: React.FC<{ generationId: string }> = ({
  generationId,
}) => {
  const { retryProgress, loading, error, refresh } =
    useRetryProgress(generationId)

  if (loading) return <LinearProgress />
  if (error) return <Alert severity="error">오류: {error}</Alert>
  if (!retryProgress) return null

  return (
    <RetryProgressDisplay retryProgress={retryProgress} onRefresh={refresh} />
  )
}
