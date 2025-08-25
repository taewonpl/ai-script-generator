import { useState, useCallback, useEffect } from 'react'
import type { MouseEvent } from 'react'
import {
  Box,
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
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
  Fab,
  Fade,
} from '@mui/material'
import {
  Edit as EditIcon,
  Delete as DeleteIcon,
  PlayArrow as GenerateIcon,
  MoreVert as MoreIcon,
  Visibility as ViewIcon,
  AutoAwesome as ScriptGenerateIcon,
} from '@mui/icons-material'
import { useQueryClient } from '@tanstack/react-query'
import { useNavigate, useSearchParams } from 'react-router-dom'

// Import new components and hooks
import { GenerateDrawer } from '@/features/script-generation/components/GenerateDrawer'
import { useEpisodes } from '@/shared/hooks/api/useEpisodes'
import { useToastHelpers } from '@/shared/ui/components/toast'
import type { Project } from '@/shared/types/api'

// Updated Episode interface matching ChromaDB API
interface Episode {
  id: string
  projectId: string
  number: number // Auto-assigned episode number
  title: string
  description?: string
  script?: {
    markdown: string
    tokens: number
  }
  createdAt: string
  updatedAt?: string
}

interface ProjectEpisodesProps {
  project: Project
}

export function ProjectEpisodes({ project }: ProjectEpisodesProps) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { showSuccess, showError } = useToastHelpers()
  const [searchParams, setSearchParams] = useSearchParams()

  // State management
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)
  const [selectedEpisode, setSelectedEpisode] = useState<Episode | null>(null)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [showGenerateDrawer, setShowGenerateDrawer] = useState(false)

  // Episodes hook for API operations
  const {
    data: episodesResponse = { items: [], total: 0 },
    isLoading,
    error,
  } = useEpisodes(project.id)

  const episodes = Array.isArray(episodesResponse)
    ? episodesResponse
    : episodesResponse.items || []

  // Check URL for generation trigger
  const shouldOpenGenerate = searchParams.get('gen') === 'new'

  // Open generate drawer if requested via URL
  useEffect(() => {
    if (shouldOpenGenerate) {
      setShowGenerateDrawer(true)
    }
  }, [shouldOpenGenerate])

  // Close generate drawer handler
  const handleCloseGenerateDrawer = useCallback(() => {
    setShowGenerateDrawer(false)
    // Remove gen parameter from URL
    const newSearchParams = new URLSearchParams(searchParams)
    newSearchParams.delete('gen')
    setSearchParams(newSearchParams, { replace: true })
  }, [searchParams, setSearchParams])

  // Episode created handler - refresh episode list
  const handleEpisodeCreated = useCallback(
    (_episodeId: string, episodeNumber: number) => {
      showSuccess(
        `에피소드 ${episodeNumber}가 성공적으로 생성되어 저장되었습니다!`,
      )

      // Refresh episodes data
      queryClient.invalidateQueries({ queryKey: ['episodes', project.id] })

      // Close drawer
      handleCloseGenerateDrawer()
    },
    [project.id, queryClient, showSuccess, handleCloseGenerateDrawer],
  )

  // Menu handlers
  const handleMenuOpen = (event: MouseEvent<HTMLElement>, episode: Episode) => {
    event.stopPropagation()
    setSelectedEpisode(episode)
    setAnchorEl(event.currentTarget)
  }

  const handleMenuClose = () => {
    setAnchorEl(null)
    setSelectedEpisode(null)
  }

  const handleView = (episode: Episode) => {
    navigate(`/projects/${project.id}/episodes/${episode.id}`)
    handleMenuClose()
  }

  const handleEdit = (episode: Episode) => {
    navigate(`/projects/${project.id}/episodes/${episode.id}/edit`)
    handleMenuClose()
  }

  const handleGenerateForEpisode = (episode: Episode) => {
    // Open generation drawer with specific episode context
    setSelectedEpisode(episode)
    setShowGenerateDrawer(true)
    handleMenuClose()
  }

  const handleDelete = (episode: Episode) => {
    setSelectedEpisode(episode)
    setShowDeleteDialog(true)
    handleMenuClose()
  }

  const confirmDelete = async () => {
    if (!selectedEpisode) return

    try {
      // TODO: Implement delete episode functionality
      // await deleteEpisode(selectedEpisode.id)
      console.log('Delete episode:', selectedEpisode.id)
      showSuccess('에피소드가 삭제되었습니다.')
    } catch {
      showError('에피소드 삭제에 실패했습니다.')
    } finally {
      setShowDeleteDialog(false)
      setSelectedEpisode(null)
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }

  const getNextEpisodeNumber = () => {
    if (episodes.length === 0) return 1
    return Math.max(...episodes.map((ep: any) => ep.number)) + 1
  }

  if (isLoading) {
    return <LinearProgress />
  }

  if (error) {
    return <Alert severity="error">에피소드를 불러오는데 실패했습니다.</Alert>
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
            에피소드 관리
          </Typography>
          <Typography variant="body2" color="textSecondary">
            총 {episodes.length}개의 에피소드 • 다음 번호:{' '}
            {getNextEpisodeNumber()}
          </Typography>
        </Box>

        <Stack direction="row" spacing={2}>
          <Button
            variant="contained"
            startIcon={<ScriptGenerateIcon />}
            onClick={() => setShowGenerateDrawer(true)}
            color="primary"
          >
            스크립트 생성
          </Button>
        </Stack>
      </Box>

      {/* Episodes Table */}
      {episodes.length > 0 ? (
        <TableContainer component={Paper} variant="outlined">
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>에피소드</TableCell>
                <TableCell>제목</TableCell>
                <TableCell>스크립트 정보</TableCell>
                <TableCell>생성일</TableCell>
                <TableCell align="center">작업</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {episodes
                .sort((a: any, b: any) => a.number - b.number)
                .map((episode: any) => (
                  <TableRow
                    key={episode.id}
                    hover
                    sx={{ cursor: 'pointer' }}
                    onClick={() => handleView(episode)}
                  >
                    <TableCell>
                      <Typography variant="subtitle1" fontWeight="medium">
                        에피소드 {episode.number}
                      </Typography>
                    </TableCell>

                    <TableCell>
                      <Typography variant="subtitle2" gutterBottom>
                        {episode.title}
                      </Typography>
                      {episode.description && (
                        <Typography
                          variant="body2"
                          color="textSecondary"
                          sx={{
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            display: '-webkit-box',
                            WebkitLineClamp: 2,
                            WebkitBoxOrient: 'vertical',
                            maxWidth: 300,
                          }}
                        >
                          {episode.description}
                        </Typography>
                      )}
                    </TableCell>

                    <TableCell>
                      {episode.script ? (
                        <Stack spacing={1}>
                          <Chip
                            label={`${episode.script.tokens} 토큰`}
                            size="small"
                            color="success"
                            variant="outlined"
                          />
                          <Typography variant="caption" color="textSecondary">
                            {Math.round(episode.script.tokens / 4)}단어 추정
                          </Typography>
                        </Stack>
                      ) : (
                        <Chip
                          label="스크립트 없음"
                          size="small"
                          color="default"
                          variant="outlined"
                        />
                      )}
                    </TableCell>

                    <TableCell>
                      <Typography variant="body2">
                        {formatDate(episode.createdAt)}
                      </Typography>
                    </TableCell>

                    <TableCell align="center">
                      <IconButton
                        size="small"
                        onClick={e => handleMenuOpen(e, episode)}
                      >
                        <MoreIcon />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
            </TableBody>
          </Table>
        </TableContainer>
      ) : (
        <Paper variant="outlined" sx={{ p: 6, textAlign: 'center' }}>
          <ScriptGenerateIcon
            sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }}
          />
          <Typography variant="h6" color="textSecondary" gutterBottom>
            아직 에피소드가 없습니다
          </Typography>
          <Typography variant="body2" color="textSecondary" mb={4}>
            첫 번째 에피소드 스크립트를 AI로 생성해보세요
          </Typography>
          <Button
            variant="contained"
            size="large"
            startIcon={<ScriptGenerateIcon />}
            onClick={() => setShowGenerateDrawer(true)}
          >
            첫 에피소드 생성하기
          </Button>
        </Paper>
      )}

      {/* Floating Action Button for Quick Generation */}
      <Fade in timeout={300}>
        <Fab
          color="primary"
          aria-label="스크립트 생성"
          onClick={() => setShowGenerateDrawer(true)}
          sx={{
            position: 'fixed',
            bottom: 24,
            right: 24,
            zIndex: 1000,
          }}
        >
          <ScriptGenerateIcon />
        </Fab>
      </Fade>

      {/* Context Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'right',
        }}
        transformOrigin={{
          vertical: 'top',
          horizontal: 'right',
        }}
      >
        <MenuItem
          onClick={() => selectedEpisode && handleView(selectedEpisode)}
        >
          <ListItemIcon>
            <ViewIcon />
          </ListItemIcon>
          <ListItemText>상세 보기</ListItemText>
        </MenuItem>

        <MenuItem
          onClick={() => selectedEpisode && handleEdit(selectedEpisode)}
        >
          <ListItemIcon>
            <EditIcon />
          </ListItemIcon>
          <ListItemText>편집</ListItemText>
        </MenuItem>

        <MenuItem
          onClick={() =>
            selectedEpisode && handleGenerateForEpisode(selectedEpisode)
          }
        >
          <ListItemIcon>
            <GenerateIcon />
          </ListItemIcon>
          <ListItemText>스크립트 재생성</ListItemText>
        </MenuItem>

        <MenuItem
          onClick={() => selectedEpisode && handleDelete(selectedEpisode)}
        >
          <ListItemIcon>
            <DeleteIcon color="error" />
          </ListItemIcon>
          <ListItemText sx={{ color: 'error.main' }}>삭제</ListItemText>
        </MenuItem>
      </Menu>

      {/* Generation Drawer */}
      <GenerateDrawer
        isOpen={showGenerateDrawer}
        onClose={handleCloseGenerateDrawer}
        project={project}
        projectName={project.name || project.title}
        initialEpisodeNumber={selectedEpisode?.number || getNextEpisodeNumber()}
        onEpisodeCreated={handleEpisodeCreated}
      />

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={showDeleteDialog}
        onClose={() => setShowDeleteDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>에피소드 삭제</DialogTitle>
        <DialogContent>
          <Typography gutterBottom>
            '
            <strong>
              에피소드 {selectedEpisode?.number}: {selectedEpisode?.title}
            </strong>
            '을(를) 삭제하시겠습니까?
          </Typography>
          <Alert severity="warning" sx={{ mt: 2 }}>
            이 작업은 되돌릴 수 없으며, 에피소드와 관련된 모든 스크립트 데이터도
            함께 삭제됩니다.
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowDeleteDialog(false)}>취소</Button>
          <Button
            onClick={confirmDelete}
            color="error"
            variant="contained"
            disabled={false}
          >
            삭제
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
