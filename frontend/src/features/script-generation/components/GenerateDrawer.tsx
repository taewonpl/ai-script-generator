import { useState, useEffect, useCallback } from 'react'
import {
  Drawer,
  Box,
  Typography,
  Button,
  TextField,
  Alert,
  LinearProgress,
  Card,
  CardContent,
  Stack,
  IconButton,
  Chip,
  Fade,
  CircularProgress,
  Snackbar,
  AlertTitle,
  Tooltip,
  Skeleton,
} from '@mui/material'
import {
  Close as CloseIcon,
  PlayArrow as PlayArrowIcon,
  Stop as StopIcon,
  RestartAlt as RestartAltIcon,
  Save as SaveIcon,
  SignalWifiOff as DisconnectedIcon,
  Wifi as ConnectedIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  Refresh as RefreshIcon,
  WifiOff as OfflineIcon,
  CheckCircle as SuccessIcon,
} from '@mui/icons-material'

// Import new SSE-based hooks and types
import { useGeneration } from '@/shared/hooks/useGeneration'
import { useEpisodes } from '@/shared/hooks/api/useEpisodes'
import type { GenerationJobRequest } from '@/shared/types/generation'
import type { Project } from '@/shared/types/project'

interface GenerateDrawerProps {
  isOpen: boolean
  onClose: () => void
  project: Project
  projectName: string
  initialEpisodeNumber?: number
  onEpisodeCreated?: (episodeId: string, episodeNumber: number) => void
}

export function GenerateDrawer({
  isOpen,
  onClose,
  project,
  projectName,
  initialEpisodeNumber,
  onEpisodeCreated,
}: GenerateDrawerProps) {
  // Form state
  const [episodeTitle, setEpisodeTitle] = useState('')
  const [episodeDescription, setEpisodeDescription] = useState('')
  const [customPrompt, setCustomPrompt] = useState('')
  const [scriptType, setScriptType] = useState<
    'drama' | 'comedy' | 'documentary'
  >('drama')
  const [lengthTarget, setLengthTarget] = useState<number>(1000)

  // User experience state
  const [isOnline, setIsOnline] = useState(navigator.onLine)
  const [saveSuccessSnackbar, setSaveSuccessSnackbar] = useState(false)
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)

  // SSE-based generation hook
  const generation = useGeneration(project.id)

  // Episodes hook for episode management
  // @ts-expect-error - Temporary workaround for missing createEpisode, isCreating properties
  const { createEpisode, isCreating } = useEpisodes(project.id)

  // Network status monitoring
  useEffect(() => {
    const handleOnline = () => setIsOnline(true)
    const handleOffline = () => setIsOnline(false)

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  // Track unsaved changes
  useEffect(() => {
    const hasChanges =
      episodeDescription.trim() !== '' ||
      customPrompt.trim() !== '' ||
      episodeTitle.trim() !==
        `${projectName} - Ep. ${initialEpisodeNumber || 1}`
    setHasUnsavedChanges(hasChanges)
  }, [
    episodeDescription,
    customPrompt,
    episodeTitle,
    projectName,
    initialEpisodeNumber,
  ])

  // Auto-generate episode title
  useEffect(() => {
    if (!episodeTitle && projectName) {
      const episodeNumber = initialEpisodeNumber || 1
      setEpisodeTitle(`${projectName} - Ep. ${episodeNumber}`)
    }
  }, [projectName, initialEpisodeNumber, episodeTitle])

  // Reset form when drawer closes
  useEffect(() => {
    if (!isOpen) {
      generation.reset()
      setEpisodeTitle('')
      setEpisodeDescription('')
      setCustomPrompt('')
    }
  }, [isOpen, generation])

  // Handle generation start
  const handleStart = useCallback(async () => {
    const request: GenerationJobRequest = {
      projectId: project.id,
      episodeNumber: initialEpisodeNumber,
      title: episodeTitle.trim() || undefined,
      description: episodeDescription.trim() || customPrompt.trim(),
      scriptType,
      lengthTarget,
      temperature: 0.7,
    }

    await generation.startGeneration(request)
  }, [
    project.id,
    initialEpisodeNumber,
    episodeTitle,
    episodeDescription,
    customPrompt,
    scriptType,
    lengthTarget,
    generation,
  ])

  // Handle generation cancellation
  const handleCancel = useCallback(async () => {
    await generation.cancelGeneration()
  }, [generation])

  // Handle retry
  const handleRetry = useCallback(async () => {
    await generation.retryGeneration()
  }, [generation])

  // Handle save to episode with enhanced error handling
  const handleSave = useCallback(async () => {
    if (!generation.state.finalContent) {
      return
    }

    // Check network connectivity first
    if (!isOnline) {
      console.warn('Cannot save while offline')
      return
    }

    try {
      // If generation was automatically saved to episode, just close
      if (generation.state.savedToEpisode && generation.state.episodeId) {
        setSaveSuccessSnackbar(true)
        onEpisodeCreated?.(
          generation.state.episodeId,
          initialEpisodeNumber || 1,
        )
        setTimeout(() => onClose(), 1500) // Delay for user to see success message
        return
      }

      // Manually create episode if auto-save failed
      const episode = await createEpisode({
        title:
          episodeTitle.trim() ||
          `${projectName} - Ep. ${initialEpisodeNumber || 1}`,
        script: {
          markdown: generation.state.finalContent,
          tokens: generation.state.tokens,
        },
        promptSnapshot: episodeDescription.trim() || customPrompt.trim(),
      })

      if (episode) {
        setSaveSuccessSnackbar(true)
        onEpisodeCreated?.(episode.id, episode.number)
        setTimeout(() => onClose(), 1500) // Delay for user to see success message
      }
    } catch (error) {
      console.error('Failed to save episode:', error)

      // Enhanced error reporting for user
      const errorMessage =
        error instanceof Error
          ? error.message
          : '알 수 없는 오류가 발생했습니다.'
      console.error('Episode save error details:', errorMessage)
    }
  }, [
    generation.state.finalContent,
    generation.state.savedToEpisode,
    generation.state.episodeId,
    generation.state.tokens,
    isOnline,
    createEpisode,
    episodeTitle,
    projectName,
    initialEpisodeNumber,
    episodeDescription,
    customPrompt,
    onEpisodeCreated,
    onClose,
  ])

  // Enhanced connection status indicator with offline detection
  const getConnectionStatusChip = () => {
    const { connectionStatus } = generation.state

    // Show offline status first if detected
    if (!isOnline) {
      return (
        <Tooltip title="네트워크 연결을 확인하고 다시 시도해주세요" arrow>
          <Chip
            icon={<OfflineIcon />}
            label="오프라인"
            color="error"
            size="small"
          />
        </Tooltip>
      )
    }

    switch (connectionStatus.state) {
      case 'connecting':
        return (
          <Tooltip title="서버에 연결하고 있습니다" arrow>
            <Chip
              icon={<CircularProgress size={16} />}
              label="연결 중..."
              color="warning"
              size="small"
            />
          </Tooltip>
        )
      case 'connected':
        return (
          <Tooltip title="서버와 정상적으로 연결되었습니다" arrow>
            <Chip
              icon={<ConnectedIcon />}
              label="연결됨"
              color="success"
              size="small"
            />
          </Tooltip>
        )
      case 'error': {
        const errorMessage = connectionStatus.nextRetryIn
          ? `${connectionStatus.nextRetryIn}초 후 자동 재시도됩니다`
          : '연결 문제가 발생했습니다. 수동으로 재시도하거나 잠시 후 다시 시도해주세요'

        return (
          <Tooltip title={errorMessage} arrow>
            <Chip
              icon={<DisconnectedIcon />}
              label={`연결 문제 ${connectionStatus.nextRetryIn ? `(${connectionStatus.nextRetryIn}초 후 재시도)` : ''}`}
              color="error"
              size="small"
            />
          </Tooltip>
        )
      }
      default:
        return null
    }
  }

  // Enhanced error message with actionable suggestions
  const getErrorMessage = () => {
    const { error } = generation.state
    if (!error) return null

    const actionableMessage = error.message
    let suggestions: string[] = []

    // Provide specific suggestions based on error code
    switch (error.code) {
      case 'CONNECTION_ERROR':
        suggestions = [
          '네트워크 연결 상태를 확인해주세요',
          '잠시 후 다시 시도해주세요',
          'VPN을 사용 중이라면 연결을 확인해주세요',
        ]
        break
      case 'VALIDATION_ERROR':
        suggestions = [
          '입력한 내용을 다시 확인해주세요',
          '필수 항목이 모두 작성되었는지 확인해주세요',
        ]
        break
      case 'GENERATION_START_FAILED':
        suggestions = ['서버 상태를 확인 중입니다', '잠시 후 다시 시도해주세요']
        break
      default:
        suggestions = [
          '페이지를 새로고침 후 다시 시도해주세요',
          '문제가 계속되면 고객지원팀에 문의해주세요',
        ]
    }

    return {
      message: actionableMessage,
      suggestions,
      retryable: error.retryable,
    }
  }

  // Enhanced action buttons with better accessibility and offline handling
  const renderActionButtons = () => {
    const { status, canRetry, canSave } = generation.state
    const isOffline = !isOnline

    if (status === 'streaming') {
      return (
        <Stack direction="row" spacing={2}>
          <Button
            variant="outlined"
            color="error"
            startIcon={<StopIcon />}
            onClick={handleCancel}
            disabled={generation.state.isCancelling || isOffline}
            fullWidth
            aria-describedby="cancel-help-text"
          >
            {generation.state.isCancelling ? '취소 중...' : '생성 취소'}
          </Button>
          <Typography
            id="cancel-help-text"
            variant="caption"
            color="textSecondary"
            sx={{ display: 'none' }}
          >
            현재 진행 중인 스크립트 생성을 중단합니다
          </Typography>
        </Stack>
      )
    }

    if (status === 'failed' || status === 'canceled') {
      return (
        <Stack direction="row" spacing={2}>
          {canRetry && (
            <Tooltip
              title={
                isOffline
                  ? '오프라인 상태에서는 재시도할 수 없습니다'
                  : '동일한 설정으로 다시 시도'
              }
              arrow
            >
              <span>
                <Button
                  variant="outlined"
                  startIcon={<RestartAltIcon />}
                  onClick={handleRetry}
                  disabled={generation.state.isStarting || isOffline}
                  aria-describedby="retry-help-text"
                >
                  재시도
                </Button>
              </span>
            </Tooltip>
          )}
          <Tooltip
            title={
              isOffline
                ? '오프라인 상태에서는 새로 시작할 수 없습니다'
                : '새로운 설정으로 다시 시작'
            }
            arrow
          >
            <span>
              <Button
                variant="contained"
                startIcon={<PlayArrowIcon />}
                onClick={handleStart}
                disabled={
                  generation.state.isStarting ||
                  isOffline ||
                  !episodeDescription.trim()
                }
                aria-describedby="restart-help-text"
              >
                다시 시작
              </Button>
            </span>
          </Tooltip>
        </Stack>
      )
    }

    if (status === 'completed') {
      return (
        <Stack direction="row" spacing={2}>
          <Tooltip
            title={
              isOffline
                ? '오프라인 상태에서는 재생성할 수 없습니다'
                : '동일한 설정으로 새로운 스크립트 생성'
            }
            arrow
          >
            <span>
              <Button
                variant="outlined"
                startIcon={<RestartAltIcon />}
                onClick={handleRetry}
                disabled={generation.state.isStarting || isOffline}
              >
                다시 생성
              </Button>
            </span>
          </Tooltip>
          {canSave && (
            <Tooltip
              title={
                isOffline
                  ? '오프라인 상태에서는 저장할 수 없습니다'
                  : '완성된 스크립트를 에피소드로 저장'
              }
              arrow
            >
              <span>
                <Button
                  variant="contained"
                  color="success"
                  startIcon={
                    generation.state.savedToEpisode ? (
                      <SuccessIcon />
                    ) : (
                      <SaveIcon />
                    )
                  }
                  onClick={handleSave}
                  disabled={isCreating || isOffline}
                  aria-describedby="save-help-text"
                >
                  {isCreating
                    ? '저장 중...'
                    : generation.state.savedToEpisode
                      ? '저장 완료'
                      : '에피소드로 저장'}
                </Button>
              </span>
            </Tooltip>
          )}
        </Stack>
      )
    }

    // Default state (queued or idle)
    const isStartDisabled =
      generation.state.isStarting || !episodeDescription.trim() || isOffline

    return (
      <Tooltip
        title={
          isOffline
            ? '오프라인 상태에서는 생성할 수 없습니다'
            : !episodeDescription.trim()
              ? '스크립트 설명을 입력해주세요'
              : 'AI가 설명을 바탕으로 스크립트를 생성합니다'
        }
        arrow
      >
        <span>
          <Button
            variant="contained"
            startIcon={
              generation.state.isStarting ? (
                <CircularProgress size={20} />
              ) : (
                <PlayArrowIcon />
              )
            }
            onClick={handleStart}
            disabled={isStartDisabled}
            fullWidth
            aria-describedby="start-help-text"
          >
            {generation.state.isStarting ? '시작 중...' : '스크립트 생성 시작'}
          </Button>
        </span>
      </Tooltip>
    )
  }

  return (
    <Drawer
      anchor="right"
      open={isOpen}
      onClose={onClose}
      sx={{
        '& .MuiDrawer-paper': {
          width: { xs: '100%', sm: 700, md: 800 },
          maxWidth: '100vw',
        },
      }}
      role="dialog"
      aria-labelledby="generate-drawer-title"
      aria-modal="true"
    >
      <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
        {/* Header */}
        <Box
          sx={{
            p: 3,
            borderBottom: 1,
            borderColor: 'divider',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <Typography variant="h5" id="generate-drawer-title" fontWeight="bold">
            🎬 스크립트 생성
          </Typography>
          <IconButton onClick={onClose} aria-label="생성 창 닫기" size="small">
            <CloseIcon />
          </IconButton>
        </Box>

        {/* Content */}
        <Box sx={{ flex: 1, overflow: 'auto', p: 3 }}>
          {/* Connection Status with manual retry option */}
          {(generation.state.status === 'streaming' ||
            generation.state.connectionStatus.state !== 'closed') && (
            <Fade in timeout={300}>
              <Box sx={{ mb: 3 }}>
                <Stack
                  direction="row"
                  spacing={1}
                  alignItems="center"
                  justifyContent="space-between"
                >
                  <Stack direction="row" spacing={1} alignItems="center">
                    {getConnectionStatusChip()}
                    {generation.state.connectionStatus.retryCount > 0 && (
                      <Chip
                        label={`재시도 ${generation.state.connectionStatus.retryCount}/${generation.state.connectionStatus.maxRetries}`}
                        color="info"
                        size="small"
                      />
                    )}
                  </Stack>

                  {/* Manual retry button when connection fails */}
                  {generation.state.connectionStatus.state === 'error' &&
                    generation.state.connectionStatus.retryCount >=
                      generation.state.connectionStatus.maxRetries && (
                      <Tooltip title="연결을 수동으로 다시 시도합니다" arrow>
                        <Button
                          variant="outlined"
                          size="small"
                          startIcon={<RefreshIcon />}
                          onClick={() => {
                            // Force manual retry through SSE service
                            console.log(
                              'Manual connection retry requested by user',
                            )
                            generation.state.connectionStatus.retryCount = 0 // Reset for manual retry
                            generation.retryGeneration()
                          }}
                          disabled={!isOnline || generation.state.isStarting}
                        >
                          연결 재시도
                        </Button>
                      </Tooltip>
                    )}
                </Stack>
              </Box>
            </Fade>
          )}

          {/* Episode Information */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                에피소드 정보
              </Typography>

              <TextField
                label="에피소드 제목"
                value={episodeTitle}
                onChange={e => setEpisodeTitle(e.target.value)}
                fullWidth
                margin="normal"
                disabled={generation.state.status === 'streaming'}
                helperText="비워두면 자동으로 생성됩니다"
                inputProps={{
                  'aria-describedby': 'title-helper-text',
                  maxLength: 200,
                }}
                onKeyDown={e => {
                  if (e.key === 'Enter') {
                    e.preventDefault()
                    document.getElementById('episode-description')?.focus()
                  }
                }}
              />

              <TextField
                id="episode-description"
                label="스크립트 설명 / 프롬프트"
                value={episodeDescription}
                onChange={e => setEpisodeDescription(e.target.value)}
                fullWidth
                multiline
                rows={4}
                margin="normal"
                disabled={generation.state.status === 'streaming'}
                required
                placeholder="어떤 스크립트를 생성하고 싶으신가요? 상세하게 설명해주세요..."
                helperText={`${episodeDescription.length}/2000자 ${episodeDescription.length < 10 ? '(최소 10자 필요)' : ''}`}
                error={episodeDescription.length > 2000}
                inputProps={{
                  'aria-describedby': 'description-helper-text',
                  maxLength: 2000,
                  'aria-required': 'true',
                }}
                onKeyDown={e => {
                  if (e.key === 'Tab' && !e.shiftKey) {
                    // Allow natural tab navigation to next field
                  }
                }}
              />

              <TextField
                label="추가 요청사항 (선택)"
                value={customPrompt}
                onChange={e => setCustomPrompt(e.target.value)}
                fullWidth
                multiline
                rows={2}
                margin="normal"
                disabled={generation.state.status === 'streaming'}
                placeholder="특별한 요구사항이나 스타일 지시사항을 입력하세요..."
                inputProps={{
                  'aria-describedby': 'custom-prompt-helper-text',
                  maxLength: 1000,
                }}
                helperText={`${customPrompt.length}/1000자`}
              />

              {/* Generation Settings */}
              <Stack
                direction={{ xs: 'column', sm: 'row' }}
                spacing={2}
                sx={{ mt: 2 }}
              >
                <TextField
                  select
                  label="스크립트 타입"
                  value={scriptType}
                  onChange={e => setScriptType(e.target.value as any)}
                  disabled={generation.state.status === 'streaming'}
                  SelectProps={{ native: true }}
                >
                  <option value="drama">드라마</option>
                  <option value="comedy">코미디</option>
                  <option value="documentary">다큐멘터리</option>
                </TextField>

                <TextField
                  type="number"
                  label="목표 길이 (단어)"
                  value={lengthTarget}
                  onChange={e => setLengthTarget(Number(e.target.value))}
                  disabled={generation.state.status === 'streaming'}
                  InputProps={{ inputProps: { min: 100, max: 50000 } }}
                />
              </Stack>
            </CardContent>
          </Card>

          {/* Progress Display */}
          {generation.state.status === 'streaming' && (
            <Fade in timeout={300}>
              <Card sx={{ mb: 3 }}>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    생성 진행상황
                  </Typography>

                  <Box sx={{ mb: 2 }}>
                    <Stack
                      direction="row"
                      justifyContent="space-between"
                      alignItems="center"
                      sx={{ mb: 1 }}
                    >
                      <Typography variant="body2" color="text.secondary">
                        진행률: {generation.state.progress}%
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {generation.getEstimatedTimeString()}
                      </Typography>
                    </Stack>
                    <LinearProgress
                      variant="determinate"
                      value={generation.state.progress}
                      sx={{ height: 8, borderRadius: 4 }}
                    />
                  </Box>

                  <Typography variant="body2" color="text.primary">
                    {generation.getProgressMessage()}
                  </Typography>
                </CardContent>
              </Card>
            </Fade>
          )}

          {/* Enhanced Error Display with actionable suggestions */}
          {generation.state.error && (
            <Fade in timeout={300}>
              <Alert
                severity="error"
                sx={{ mb: 3 }}
                icon={<ErrorIcon />}
                action={
                  <Stack direction="row" spacing={1}>
                    {generation.state.error.retryable && !isOnline && (
                      <Tooltip
                        title="네트워크 연결을 확인한 후 시도하세요"
                        arrow
                      >
                        <span>
                          <Button
                            color="inherit"
                            size="small"
                            startIcon={<RefreshIcon />}
                            onClick={handleRetry}
                            disabled={generation.state.isStarting || !isOnline}
                          >
                            재시도
                          </Button>
                        </span>
                      </Tooltip>
                    )}
                    {generation.state.error.retryable && isOnline && (
                      <Button
                        color="inherit"
                        size="small"
                        startIcon={<RefreshIcon />}
                        onClick={handleRetry}
                        disabled={generation.state.isStarting}
                      >
                        재시도
                      </Button>
                    )}
                  </Stack>
                }
              >
                <AlertTitle sx={{ fontWeight: 'bold' }}>
                  {generation.state.error.code === 'CONNECTION_ERROR'
                    ? '연결 오류'
                    : generation.state.error.code === 'VALIDATION_ERROR'
                      ? '입력 오류'
                      : generation.state.error.code ===
                          'GENERATION_START_FAILED'
                        ? '생성 시작 실패'
                        : '오류 발생'}
                </AlertTitle>

                <Typography variant="body2" gutterBottom>
                  {generation.state.error.message}
                </Typography>

                {/* Show actionable suggestions */}
                {(() => {
                  const errorInfo = getErrorMessage()
                  if (errorInfo?.suggestions.length) {
                    return (
                      <Box sx={{ mt: 2 }}>
                        <Typography variant="subtitle2" gutterBottom>
                          💡 해결 방법:
                        </Typography>
                        <Box component="ul" sx={{ pl: 3, mt: 1, mb: 0 }}>
                          {errorInfo.suggestions.map((suggestion, index) => (
                            <Box component="li" key={index} sx={{ mb: 0.5 }}>
                              <Typography variant="body2">
                                {suggestion}
                              </Typography>
                            </Box>
                          ))}
                        </Box>
                      </Box>
                    )
                  }
                  return null
                })()}
              </Alert>
            </Fade>
          )}

          {/* Offline Warning */}
          {!isOnline && (
            <Fade in timeout={300}>
              <Alert severity="warning" sx={{ mb: 3 }} icon={<OfflineIcon />}>
                <AlertTitle>오프라인 상태</AlertTitle>
                네트워크 연결을 확인한 후 스크립트 생성을 시도해주세요.
              </Alert>
            </Fade>
          )}

          {/* Enhanced Preview Content with loading skeleton */}
          {(generation.state.previewContent ||
            generation.state.status === 'streaming') && (
            <Fade in timeout={300}>
              <Card sx={{ mb: 3 }}>
                <CardContent>
                  <Stack
                    direction="row"
                    justifyContent="space-between"
                    alignItems="center"
                    sx={{ mb: 2 }}
                  >
                    <Typography variant="h6">
                      {generation.state.status === 'completed'
                        ? '완성된 스크립트 ✨'
                        : generation.state.status === 'streaming'
                          ? '실시간 미리보기 🔄'
                          : '스크립트 미리보기'}
                    </Typography>
                    <Stack direction="row" spacing={2}>
                      <Chip
                        label={`${generation.state.wordCount} 단어`}
                        size="small"
                        variant="outlined"
                        color={
                          generation.state.status === 'completed'
                            ? 'success'
                            : 'default'
                        }
                      />
                      <Chip
                        label={`${generation.state.tokens} 토큰`}
                        size="small"
                        variant="outlined"
                        color={
                          generation.state.status === 'completed'
                            ? 'success'
                            : 'default'
                        }
                      />
                    </Stack>
                  </Stack>

                  <Box
                    sx={{
                      maxHeight: 400,
                      overflow: 'auto',
                      bgcolor:
                        generation.state.status === 'completed'
                          ? 'success.50'
                          : 'grey.50',
                      p: 3,
                      borderRadius: 2,
                      border: '1px solid',
                      borderColor:
                        generation.state.status === 'completed'
                          ? 'success.200'
                          : 'grey.200',
                      fontFamily: 'Georgia, serif',
                      fontSize: '0.875rem',
                      lineHeight: 1.6,
                      whiteSpace: 'pre-wrap',
                      position: 'relative',
                    }}
                    role="document"
                    aria-label="생성된 스크립트 미리보기"
                    tabIndex={0}
                  >
                    {generation.state.previewContent || (
                      <Stack spacing={1}>
                        <Skeleton variant="text" width="100%" height={20} />
                        <Skeleton variant="text" width="85%" height={20} />
                        <Skeleton variant="text" width="95%" height={20} />
                        <Skeleton variant="text" width="70%" height={20} />
                        <Typography
                          variant="body2"
                          color="textSecondary"
                          align="center"
                          sx={{ mt: 2 }}
                        >
                          스크립트를 생성하고 있습니다...
                        </Typography>
                      </Stack>
                    )}

                    {/* Streaming indicator */}
                    {generation.state.status === 'streaming' &&
                      generation.state.previewContent && (
                        <Box
                          sx={{
                            position: 'absolute',
                            bottom: 8,
                            right: 8,
                            bgcolor: 'primary.main',
                            color: 'white',
                            p: 1,
                            borderRadius: 1,
                            display: 'flex',
                            alignItems: 'center',
                            gap: 1,
                            fontSize: '0.75rem',
                          }}
                        >
                          <CircularProgress size={12} color="inherit" />
                          생성 중
                        </Box>
                      )}
                  </Box>

                  {generation.state.episodeId &&
                    generation.state.savedToEpisode && (
                      <Alert
                        severity="success"
                        sx={{ mt: 2 }}
                        icon={<SuccessIcon />}
                      >
                        <AlertTitle>자동 저장 완료</AlertTitle>
                        스크립트가 에피소드 {generation.state.episodeId}로 자동
                        저장되었습니다.
                      </Alert>
                    )}
                </CardContent>
              </Card>
            </Fade>
          )}
        </Box>

        {/* Footer Actions */}
        <Box
          sx={{
            p: 3,
            borderTop: 1,
            borderColor: 'divider',
            bgcolor: 'background.paper',
          }}
        >
          {/* Unsaved changes warning */}
          {hasUnsavedChanges && generation.state.status === 'queued' && (
            <Alert severity="info" sx={{ mb: 2 }} icon={<WarningIcon />}>
              <Typography variant="body2">
                작성하신 내용이 저장되지 않았습니다. 생성을 시작하기 전에 내용을
                확인해주세요.
              </Typography>
            </Alert>
          )}

          {renderActionButtons()}
        </Box>

        {/* Success Snackbar */}
        <Snackbar
          open={saveSuccessSnackbar}
          autoHideDuration={3000}
          onClose={() => setSaveSuccessSnackbar(false)}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
        >
          <Alert
            onClose={() => setSaveSuccessSnackbar(false)}
            severity="success"
            variant="filled"
            icon={<SuccessIcon />}
          >
            에피소드가 성공적으로 저장되었습니다! 🎉
          </Alert>
        </Snackbar>
      </Box>
    </Drawer>
  )
}
