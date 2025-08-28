import { useState, useEffect, useCallback } from 'react'
import type { ReactNode } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Stack,
  Button,
  IconButton,
  Chip,
  Rating,
  TextField,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Tabs,
  Tab,
  Divider,
  Tooltip,
  CircularProgress,
} from '@mui/material'
import {
  Save as SaveIcon,
  Download as DownloadIcon,
  Refresh as RegenerateIcon,
  ContentCopy as CopyIcon,
  Visibility as PreviewIcon,
  Analytics as AnalyticsIcon,
  Psychology as AIIcon,
  Schedule as TimeIcon,
  TextFields as WordIcon,
  TextFields as TextFieldsIcon,
  MovieFilter as SceneIcon,
} from '@mui/icons-material'

import { useToastHelpers } from '@/shared/ui/components/toast'
import { useBehaviorTracking } from '@/shared/hooks/useBehaviorTracking'
import type { GenerationResult, GenerationJob } from '../types'
import { SaveProgressIndicator, useSaveProgress } from './SaveProgressIndicator'
import { SaveAndRetryProgress } from './RetryProgressDisplay'

interface GenerationResultsProps {
  result: GenerationResult
  job: GenerationJob
  onSave: (editedContent: string, title: string) => Promise<void>
  onRegenerate: () => void
  onEdit: () => void
  editable?: boolean
  showMetrics?: boolean
  projectId: string
  episodeId: string
}

interface TabPanelProps {
  children?: ReactNode
  index: number
  value: number
}

function TabPanel({ children, value, index, ...other }: TabPanelProps) {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`result-tabpanel-${index}`}
      aria-labelledby={`result-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  )
}

/**
 * Quality metrics display
 */
function QualityMetrics({ quality }: { quality: GenerationResult['quality'] }) {
  const aspects = [
    { key: 'coherence', label: '일관성', description: '스토리의 논리적 흐름' },
    {
      key: 'creativity',
      label: '창의성',
      description: '독창적이고 흥미로운 아이디어',
    },
    { key: 'dialogue', label: '대화', description: '자연스럽고 생생한 대화' },
    { key: 'pacing', label: '흐름', description: '적절한 속도와 리듬' },
    {
      key: 'characterization',
      label: '인물묘사',
      description: '캐릭터의 개성과 깊이',
    },
  ]

  return (
    <Stack spacing={2}>
      <Box display="flex" alignItems="center" gap={2}>
        <Typography variant="h6" display="flex" alignItems="center" gap={1}>
          <AnalyticsIcon color="primary" />
          품질 분석
        </Typography>
        <Chip
          label={`전체 점수: ${Math.round(quality.score * 10)}/10`}
          color={
            quality.score >= 0.8
              ? 'success'
              : quality.score >= 0.6
                ? 'warning'
                : 'error'
          }
        />
      </Box>

      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
        {aspects.map(aspect => {
          const score =
            quality.aspects[aspect.key as keyof typeof quality.aspects]
          return (
            <Box
              key={aspect.key}
              sx={{
                flex: {
                  xs: '1 1 100%',
                  sm: '1 1 calc(50% - 8px)',
                  md: '1 1 calc(33.333% - 16px)',
                },
              }}
            >
              <Card variant="outlined">
                <CardContent sx={{ pb: '16px !important' }}>
                  <Box
                    display="flex"
                    alignItems="center"
                    justifyContent="between"
                    mb={1}
                  >
                    <Typography variant="subtitle2">{aspect.label}</Typography>
                    <Typography
                      variant="body2"
                      color="primary"
                      fontWeight="bold"
                    >
                      {Math.round(score * 10)}/10
                    </Typography>
                  </Box>
                  <Rating
                    value={score * 5}
                    readOnly
                    precision={0.1}
                    size="small"
                  />
                  <Typography
                    variant="caption"
                    color="textSecondary"
                    display="block"
                    mt={1}
                  >
                    {aspect.description}
                  </Typography>
                </CardContent>
              </Card>
            </Box>
          )
        })}
      </Box>
    </Stack>
  )
}

/**
 * Script content editor
 */
function ScriptEditor({
  content,
  title,
  onContentChange,
  onTitleChange,
  editable,
  onEditDetected,
}: {
  content: string
  title: string
  onContentChange: (content: string) => void
  onTitleChange: (title: string) => void
  editable: boolean
  onEditDetected?: (contentLength: number) => void
}) {
  const [isFullscreen, setIsFullscreen] = useState(false)

  const wordCount = content.split(/\s+/).filter(word => word.length > 0).length
  const characterCount = content.length
  const lineCount = content.split('\n').length
  
  // Handle content change with edit detection
  const handleContentChange = (newContent: string) => {
    onContentChange(newContent)
    if (onEditDetected) {
      onEditDetected(newContent.length)
    }
  }

  return (
    <Stack spacing={2}>
      {/* Title Editor */}
      <TextField
        fullWidth
        value={title}
        onChange={e => onTitleChange(e.target.value)}
        placeholder="스크립트 제목"
        variant="outlined"
        disabled={!editable}
        sx={{
          '& .MuiInputBase-input': {
            fontSize: '1.25rem',
            fontWeight: 'bold',
          },
        }}
      />

      {/* Content Stats */}
      <Stack direction="row" spacing={2} alignItems="center">
        <Chip
          icon={<WordIcon />}
          label={`${wordCount.toLocaleString()}단어`}
          size="small"
          variant="outlined"
        />
        <Chip
          icon={<TextFieldsIcon />}
          label={`${characterCount.toLocaleString()}자`}
          size="small"
          variant="outlined"
        />
        <Chip
          icon={<SceneIcon />}
          label={`${lineCount}줄`}
          size="small"
          variant="outlined"
        />

        <Box flex={1} />

        <Tooltip title="전체화면으로 보기">
          <IconButton onClick={() => setIsFullscreen(true)} size="small">
            <PreviewIcon />
          </IconButton>
        </Tooltip>
      </Stack>

      {/* Content Editor */}
      <TextField
        fullWidth
        multiline
        rows={20}
        value={content}
        onChange={e => handleContentChange(e.target.value)}
        placeholder="생성된 스크립트가 여기에 표시됩니다..."
        variant="outlined"
        disabled={!editable}
        sx={{
          '& .MuiInputBase-root': {
            fontFamily: 'monospace',
            fontSize: '0.875rem',
            lineHeight: 1.6,
          },
        }}
      />

      {/* Fullscreen Editor Dialog */}
      <Dialog
        open={isFullscreen}
        onClose={() => setIsFullscreen(false)}
        maxWidth={false}
        fullWidth
        fullScreen
      >
        <DialogTitle>
          <Box display="flex" alignItems="center" justifyContent="between">
            <Typography variant="h6">{title || '스크립트 편집기'}</Typography>
            <Stack direction="row" spacing={1}>
              <Chip label={`${wordCount}단어`} size="small" />
              <Chip label={`${characterCount}자`} size="small" />
            </Stack>
          </Box>
        </DialogTitle>
        <DialogContent sx={{ p: 0 }}>
          <TextField
            fullWidth
            multiline
            value={content}
            onChange={e => handleContentChange(e.target.value)}
            variant="filled"
            disabled={!editable}
            sx={{
              height: '100%',
              '& .MuiInputBase-root': {
                height: '100%',
                alignItems: 'flex-start',
                fontFamily: 'monospace',
                fontSize: '1rem',
                lineHeight: 1.6,
              },
              '& .MuiInputBase-input': {
                height: '100% !important',
                overflow: 'auto !important',
              },
            }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setIsFullscreen(false)}>닫기</Button>
        </DialogActions>
      </Dialog>
    </Stack>
  )
}

/**
 * Generation results display and editing component
 */
export function GenerationResults({
  result,
  job,
  onSave,
  onRegenerate,
  onEdit: _onEdit,
  editable = true,
  showMetrics = true,
  projectId,
  episodeId,
}: GenerationResultsProps) {
  const [currentTab, setCurrentTab] = useState(0)
  const [editedContent, setEditedContent] = useState(result.content)
  const [editedTitle, setEditedTitle] = useState(result.title)
  const [isSaving, setIsSaving] = useState(false)
  const [showSaveDialog, setShowSaveDialog] = useState(false)

  const { showSuccess, showError } = useToastHelpers()
  const { saveState, handleManualSave } = useSaveProgress(job.id)
  
  // Behavior tracking with privacy by construction
  const {
    trackEditManual,
    trackRegeneration,
    recordAiOutputCompletion,
  } = useBehaviorTracking({
    projectId,
    episodeId,
    generationId: job.id,
  })

  const hasChanges =
    editedContent !== result.content || editedTitle !== result.title

  // Record AI output completion on mount
  useEffect(() => {
    if (result.content) {
      recordAiOutputCompletion(result.content.length)
    }
  }, [result.content, recordAiOutputCompletion])

  // Handle regeneration with behavior tracking
  const handleRegenerate = useCallback(() => {
    // Track regeneration event with context
    trackRegeneration(
      'default', // Default strategy for now
      [], // Default agent modes
      editedContent.length,
      undefined // No selection range in this context
    )
    
    onRegenerate()
  }, [trackRegeneration, editedContent.length, onRegenerate])

  // Handle edit detection
  const handleEditDetected = useCallback((contentLength: number) => {
    trackEditManual(contentLength, { uiElement: 'script_editor' })
  }, [trackEditManual])

  // Handle save
  const handleSave = async () => {
    if (!hasChanges) return

    setIsSaving(true)
    try {
      await onSave(editedContent, editedTitle)
      showSuccess('스크립트가 저장되었습니다!')
      setShowSaveDialog(false)
    } catch {
      showError('저장 중 오류가 발생했습니다.')
    } finally {
      setIsSaving(false)
    }
  }

  // Handle copy to clipboard
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(editedContent)
      showSuccess('스크립트가 클립보드에 복사되었습니다!')
    } catch {
      showError('복사 중 오류가 발생했습니다.')
    }
  }

  // Handle download
  const handleDownload = () => {
    const element = document.createElement('a')
    const file = new Blob([editedContent], { type: 'text/plain' })
    element.href = URL.createObjectURL(file)
    element.download = `${editedTitle || 'script'}.txt`
    document.body.appendChild(element)
    element.click()
    document.body.removeChild(element)
    showSuccess('스크립트가 다운로드되었습니다!')
  }

  const formatDuration = (minutes: number) => {
    const hours = Math.floor(minutes / 60)
    const mins = minutes % 60
    if (hours > 0) {
      return `${hours}시간 ${mins}분`
    }
    return `${mins}분`
  }

  return (
    <Stack spacing={3}>
      {/* Header */}
      <Card>
        <CardContent>
          <Box
            display="flex"
            alignItems="center"
            justifyContent="between"
            mb={2}
          >
            <Typography variant="h5" display="flex" alignItems="center" gap={1}>
              ✨ 생성 완료
            </Typography>

            <Stack direction="row" spacing={1}>
              <Tooltip title="클립보드로 복사">
                <IconButton onClick={handleCopy}>
                  <CopyIcon />
                </IconButton>
              </Tooltip>
              <Tooltip title="파일로 다운로드">
                <IconButton onClick={handleDownload}>
                  <DownloadIcon />
                </IconButton>
              </Tooltip>
              <Button
                variant="outlined"
                startIcon={<RegenerateIcon />}
                onClick={handleRegenerate}
                size="small"
              >
                다시 생성
              </Button>
              {editable && hasChanges && (
                <Button
                  variant="contained"
                  startIcon={<SaveIcon />}
                  onClick={() => setShowSaveDialog(true)}
                  disabled={isSaving}
                >
                  {isSaving ? <CircularProgress size={16} /> : '저장'}
                </Button>
              )}
            </Stack>
          </Box>

          {/* Generation Info */}
          <Stack direction="row" spacing={2} flexWrap="wrap">
            <Chip
              icon={<AIIcon />}
              label={`AI: ${result.metadata.aiModel}`}
              size="small"
            />
            <Chip
              icon={<TimeIcon />}
              label={`생성 시간: ${formatDuration(Math.round((job.completedAt!.getTime() - job.createdAt.getTime()) / 60000))}`}
              size="small"
            />
            <Chip
              icon={<WordIcon />}
              label={`${result.metadata.wordCount.toLocaleString()}단어`}
              size="small"
            />
            <Chip
              icon={<SceneIcon />}
              label={`예상 런타임: ${formatDuration(result.metadata.estimatedDuration)}`}
              size="small"
            />
          </Stack>

          {/* Save Progress Indicator */}
          <Box mt={2}>
            <SaveProgressIndicator
              saveState={saveState}
              onManualSave={handleManualSave}
              generationId={job.id}
            />
          </Box>
        </CardContent>
      </Card>

      {/* Retry Progress Display */}
      <SaveAndRetryProgress generationId={job.id} />

      {/* Tabs */}
      <Box>
        <Tabs
          value={currentTab}
          onChange={(_, newValue) => setCurrentTab(newValue)}
        >
          <Tab label="스크립트" />
          {showMetrics && <Tab label="품질 분석" />}
          <Tab label="생성 설정" />
        </Tabs>

        {/* Script Tab */}
        <TabPanel value={currentTab} index={0}>
          <ScriptEditor
            content={editedContent}
            title={editedTitle}
            onContentChange={setEditedContent}
            onTitleChange={setEditedTitle}
            editable={editable}
            onEditDetected={handleEditDetected}
          />
        </TabPanel>

        {/* Quality Analysis Tab */}
        {showMetrics && (
          <TabPanel value={currentTab} index={1}>
            <QualityMetrics quality={result.quality} />

            {result.suggestions && result.suggestions.length > 0 && (
              <Box mt={4}>
                <Typography variant="h6" gutterBottom>
                  개선 제안사항
                </Typography>
                <Stack spacing={1}>
                  {result.suggestions.map((suggestion, index) => (
                    <Alert key={index} severity="info" variant="outlined">
                      {suggestion}
                    </Alert>
                  ))}
                </Stack>
              </Box>
            )}
          </TabPanel>
        )}

        {/* Generation Settings Tab */}
        <TabPanel value={currentTab} index={showMetrics ? 2 : 1}>
          <Stack spacing={2}>
            <Typography variant="h6">생성 설정 정보</Typography>

            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
              <Box sx={{ flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 8px)' } }}>
                <Typography variant="subtitle2" color="textSecondary">
                  AI 모델
                </Typography>
                <Typography>{job.config.aiModel}</Typography>
              </Box>

              <Box sx={{ flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 8px)' } }}>
                <Typography variant="subtitle2" color="textSecondary">
                  장르 / 톤
                </Typography>
                <Typography>
                  {job.config.genre} / {job.config.tone}
                </Typography>
              </Box>

              <Box sx={{ flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 8px)' } }}>
                <Typography variant="subtitle2" color="textSecondary">
                  언어 / 길이
                </Typography>
                <Typography>
                  {job.config.language} / {job.config.length}
                </Typography>
              </Box>

              <Box sx={{ flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 8px)' } }}>
                <Typography variant="subtitle2" color="textSecondary">
                  생성 일시
                </Typography>
                <Typography>
                  {result.metadata.generatedAt.toLocaleString()}
                </Typography>
              </Box>
            </Box>

            <Divider />

            <Box>
              <Typography
                variant="subtitle2"
                color="textSecondary"
                gutterBottom
              >
                원본 프롬프트
              </Typography>
              <Card variant="outlined">
                <CardContent>
                  <Typography
                    variant="body2"
                    style={{ whiteSpace: 'pre-wrap' }}
                  >
                    {job.config.prompt}
                  </Typography>
                </CardContent>
              </Card>
            </Box>

            {(job.config.characters?.length || 0) > 0 && (
              <Box>
                <Typography
                  variant="subtitle2"
                  color="textSecondary"
                  gutterBottom
                >
                  등장인물
                </Typography>
                <Stack direction="row" spacing={1} flexWrap="wrap">
                  {job.config.characters?.map(character => (
                    <Chip key={character} label={character} size="small" />
                  ))}
                </Stack>
              </Box>
            )}

            {(job.config.themes?.length || 0) > 0 && (
              <Box>
                <Typography
                  variant="subtitle2"
                  color="textSecondary"
                  gutterBottom
                >
                  주제
                </Typography>
                <Stack direction="row" spacing={1} flexWrap="wrap">
                  {job.config.themes?.map(theme => (
                    <Chip key={theme} label={theme} size="small" />
                  ))}
                </Stack>
              </Box>
            )}
          </Stack>
        </TabPanel>
      </Box>

      {/* Save Confirmation Dialog */}
      <Dialog
        open={showSaveDialog}
        onClose={() => setShowSaveDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>스크립트 저장</DialogTitle>
        <DialogContent>
          <Typography gutterBottom>
            편집된 스크립트를 저장하시겠습니까?
          </Typography>
          <Typography variant="body2" color="textSecondary">
            제목: {editedTitle}
          </Typography>
          <Typography variant="body2" color="textSecondary">
            단어 수:{' '}
            {editedContent
              .split(/\s+/)
              .filter(w => w.length > 0)
              .length.toLocaleString()}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowSaveDialog(false)}>취소</Button>
          <Button onClick={handleSave} variant="contained" disabled={isSaving}>
            {isSaving ? <CircularProgress size={16} /> : '저장'}
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  )
}
