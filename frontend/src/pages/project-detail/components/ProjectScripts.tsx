import { useState, type MouseEvent } from 'react'
import {
  Box,
  Typography,
  Button,
  Card,
  CardContent,
  Chip,
  IconButton,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  Stack,
  LinearProgress,
  Tooltip,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import EditIcon from '@mui/icons-material/Edit'
import DeleteIcon from '@mui/icons-material/Delete'
import DownloadIcon from '@mui/icons-material/Download'
import MoreIcon from '@mui/icons-material/MoreVert'
import ViewIcon from '@mui/icons-material/Visibility'
import StarIcon from '@mui/icons-material/Star'
import StarBorderIcon from '@mui/icons-material/StarBorder'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'

import { projectApi } from '@/shared/api/client'
import { validateApiResponse } from '@/shared/api/base'
import { useToastHelpers } from '@/shared/ui/components/toast'

interface Script {
  id: string
  title: string
  episode_id: string
  episode_title: string
  episode_number: number
  content: string
  status: 'draft' | 'review' | 'approved' | 'published'
  version: number
  word_count: number
  created_at: string
  updated_at: string
  created_by: string
  ai_generated: boolean
  rating?: number
  tags: string[]
}

interface ProjectScriptsProps {
  projectId: string
}

const STATUS_COLORS = {
  draft: 'default',
  review: 'warning',
  approved: 'success',
  published: 'primary',
} as const

const STATUS_LABELS = {
  draft: '초안',
  review: '검토중',
  approved: '승인됨',
  published: '발행됨',
}

export function ProjectScripts({ projectId }: ProjectScriptsProps) {
  const navigate = useNavigate()
  const { showSuccess, showError } = useToastHelpers()

  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)
  const [selectedScript, setSelectedScript] = useState<Script | null>(null)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [_viewMode, _setViewMode] = useState<'grid' | 'list'>('grid')

  // Load scripts
  const {
    data: scripts = [],
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['project-scripts', projectId],
    queryFn: async () => {
      const response = await projectApi.get(`/projects/${projectId}/scripts`)
      return validateApiResponse<Script[]>(response.data)
    },
  })

  const handleMenuOpen = (event: MouseEvent<HTMLElement>, script: Script) => {
    event.stopPropagation()
    setSelectedScript(script)
    setAnchorEl(event.currentTarget)
  }

  const handleMenuClose = () => {
    setAnchorEl(null)
    setSelectedScript(null)
  }

  const handleView = (script: Script) => {
    navigate(`/scripts/${script.id}`)
    handleMenuClose()
  }

  const handleEdit = (script: Script) => {
    navigate(`/scripts/${script.id}/edit`)
    handleMenuClose()
  }

  const handleDownload = async (script: Script) => {
    try {
      const element = document.createElement('a')
      const file = new Blob([script.content], { type: 'text/plain' })
      element.href = URL.createObjectURL(file)
      element.download = `${script.title}.txt`
      document.body.appendChild(element)
      element.click()
      document.body.removeChild(element)
      showSuccess('스크립트가 다운로드되었습니다.')
    } catch {
      showError('다운로드에 실패했습니다.')
    }
    handleMenuClose()
  }

  const handleDelete = (script: Script) => {
    setSelectedScript(script)
    setShowDeleteDialog(true)
    handleMenuClose()
  }

  const confirmDelete = async () => {
    if (!selectedScript) return

    try {
      await projectApi.delete(`/scripts/${selectedScript.id}`)
      showSuccess('스크립트가 삭제되었습니다.')
      refetch()
    } catch {
      showError('스크립트 삭제에 실패했습니다.')
    } finally {
      setShowDeleteDialog(false)
      setSelectedScript(null)
    }
  }

  const handleGenerate = () => {
    navigate(`/projects/${projectId}/generate`)
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ko-KR')
  }

  const formatWordCount = (count: number) => {
    if (count >= 1000) {
      return `${(count / 1000).toFixed(1)}k`
    }
    return count.toString()
  }

  const estimateReadingTime = (wordCount: number) => {
    // 한국어 기준 약 250자/분
    const minutes = Math.ceil(wordCount / 250)
    if (minutes < 60) return `${minutes}분`
    const hours = Math.floor(minutes / 60)
    const remainingMinutes = minutes % 60
    return `${hours}시간 ${remainingMinutes}분`
  }

  if (isLoading) {
    return <LinearProgress />
  }

  if (error) {
    return <Alert severity="error">스크립트를 불러오는데 실패했습니다.</Alert>
  }

  return (
    <Box>
      {/* Header */}
      <Box
        display="flex"
        justifyContent="space-between"
        alignItems="center"
        mb={3}
      >
        <Box>
          <Typography variant="h6" gutterBottom>
            스크립트 관리
          </Typography>
          <Typography variant="body2" color="textSecondary">
            총 {scripts.length}개의 스크립트
          </Typography>
        </Box>

        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleGenerate}
        >
          새 스크립트 생성
        </Button>
      </Box>

      {/* Scripts Grid */}
      {scripts.length > 0 ? (
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
          {scripts
            .sort(
              (a, b) =>
                new Date(b.updated_at).getTime() -
                new Date(a.updated_at).getTime(),
            )
            .map(script => (
              <Box
                key={script.id}
                sx={{
                  flex: {
                    xs: '1 1 100%',
                    sm: '1 1 calc(50% - 12px)',
                    md: '1 1 calc(33.333% - 16px)',
                  },
                }}
              >
                <Card
                  sx={{
                    height: '100%',
                    display: 'flex',
                    flexDirection: 'column',
                    cursor: 'pointer',
                    position: 'relative',
                    '&:hover': {
                      transform: 'translateY(-2px)',
                      boxShadow: 2,
                      transition: 'all 0.2s ease-in-out',
                    },
                  }}
                  onClick={() => handleView(script)}
                >
                  {/* AI Generated Badge */}
                  {script.ai_generated && (
                    <Chip
                      label="AI 생성"
                      size="small"
                      color="primary"
                      sx={{
                        position: 'absolute',
                        top: 8,
                        left: 8,
                        zIndex: 1,
                      }}
                    />
                  )}

                  {/* Menu Button */}
                  <Box position="absolute" top={8} right={8} zIndex={1}>
                    <IconButton
                      size="small"
                      onClick={e => handleMenuOpen(e, script)}
                      sx={{
                        bgcolor: 'background.paper',
                        '&:hover': { bgcolor: 'grey.100' },
                      }}
                    >
                      <MoreIcon />
                    </IconButton>
                  </Box>

                  <CardContent
                    sx={{ flexGrow: 1, pt: script.ai_generated ? 5 : 2 }}
                  >
                    {/* Script Title */}
                    <Typography variant="h6" component="h3" gutterBottom noWrap>
                      {script.title}
                    </Typography>

                    {/* Episode Info */}
                    <Typography variant="body2" color="primary" gutterBottom>
                      {script.episode_number}화: {script.episode_title}
                    </Typography>

                    {/* Status and Version */}
                    <Stack direction="row" spacing={1} mb={2}>
                      <Chip
                        label={STATUS_LABELS[script.status]}
                        size="small"
                        color={STATUS_COLORS[script.status]}
                      />
                      <Chip
                        label={`v${script.version}`}
                        size="small"
                        variant="outlined"
                      />
                    </Stack>

                    {/* Tags */}
                    {script.tags.length > 0 && (
                      <Stack
                        direction="row"
                        spacing={0.5}
                        mb={2}
                        flexWrap="wrap"
                      >
                        {script.tags.slice(0, 3).map(tag => (
                          <Chip
                            key={tag}
                            label={tag}
                            size="small"
                            variant="outlined"
                            sx={{ fontSize: '0.75rem', height: 20 }}
                          />
                        ))}
                        {script.tags.length > 3 && (
                          <Chip
                            label={`+${script.tags.length - 3}`}
                            size="small"
                            variant="outlined"
                            sx={{ fontSize: '0.75rem', height: 20 }}
                          />
                        )}
                      </Stack>
                    )}

                    {/* Statistics */}
                    <Box mb={2}>
                      <Stack direction="row" spacing={2} alignItems="center">
                        <Tooltip title="단어 수">
                          <Typography variant="caption" color="textSecondary">
                            📝 {formatWordCount(script.word_count)}자
                          </Typography>
                        </Tooltip>
                        <Tooltip title="예상 읽기 시간">
                          <Typography variant="caption" color="textSecondary">
                            ⏱️ {estimateReadingTime(script.word_count)}
                          </Typography>
                        </Tooltip>
                      </Stack>

                      {/* Rating */}
                      {script.rating && (
                        <Box display="flex" alignItems="center" mt={1}>
                          <Stack direction="row" spacing={0.5}>
                            {[1, 2, 3, 4, 5].map(star => (
                              <Box
                                key={star}
                                color={
                                  star <= script.rating!
                                    ? 'warning.main'
                                    : 'grey.300'
                                }
                              >
                                {star <= script.rating! ? (
                                  <StarIcon sx={{ fontSize: 16 }} />
                                ) : (
                                  <StarBorderIcon sx={{ fontSize: 16 }} />
                                )}
                              </Box>
                            ))}
                          </Stack>
                          <Typography
                            variant="caption"
                            color="textSecondary"
                            ml={1}
                          >
                            {script.rating}/5
                          </Typography>
                        </Box>
                      )}
                    </Box>

                    {/* Author and Date */}
                    <Box mt="auto">
                      <Typography
                        variant="caption"
                        color="textSecondary"
                        display="block"
                      >
                        작성자: {script.created_by}
                      </Typography>
                      <Typography
                        variant="caption"
                        color="textSecondary"
                        display="block"
                      >
                        수정: {formatDate(script.updated_at)}
                      </Typography>
                    </Box>
                  </CardContent>
                </Card>
              </Box>
            ))}
        </Box>
      ) : (
        <Card variant="outlined" sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="h6" color="textSecondary" gutterBottom>
            아직 스크립트가 없습니다
          </Typography>
          <Typography variant="body2" color="textSecondary" mb={3}>
            AI를 사용하여 첫 번째 스크립트를 생성해보세요
          </Typography>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={handleGenerate}
          >
            스크립트 생성
          </Button>
        </Card>
      )}

      {/* Context Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={() => selectedScript && handleView(selectedScript)}>
          <ListItemIcon>
            <ViewIcon />
          </ListItemIcon>
          <ListItemText>상세 보기</ListItemText>
        </MenuItem>

        <MenuItem onClick={() => selectedScript && handleEdit(selectedScript)}>
          <ListItemIcon>
            <EditIcon />
          </ListItemIcon>
          <ListItemText>편집</ListItemText>
        </MenuItem>

        <MenuItem
          onClick={() => selectedScript && handleDownload(selectedScript)}
        >
          <ListItemIcon>
            <DownloadIcon />
          </ListItemIcon>
          <ListItemText>다운로드</ListItemText>
        </MenuItem>

        <MenuItem
          onClick={() => selectedScript && handleDelete(selectedScript)}
        >
          <ListItemIcon>
            <DeleteIcon color="error" />
          </ListItemIcon>
          <ListItemText sx={{ color: 'error.main' }}>삭제</ListItemText>
        </MenuItem>
      </Menu>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={showDeleteDialog}
        onClose={() => setShowDeleteDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>스크립트 삭제</DialogTitle>
        <DialogContent>
          <Typography>
            '{selectedScript?.title}' 스크립트를 삭제하시겠습니까?
          </Typography>
          <Typography variant="body2" color="error" mt={2}>
            이 작업은 되돌릴 수 없습니다.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowDeleteDialog(false)}>취소</Button>
          <Button onClick={confirmDelete} color="error" variant="contained">
            삭제
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
