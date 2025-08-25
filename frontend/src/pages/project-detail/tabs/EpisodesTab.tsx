import { useState, useEffect, useMemo } from 'react'
import {
  Box,
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
  TextField,
  InputAdornment,
  Stack,
  Typography,
  Pagination,
  Tooltip,
  Menu,
  MenuItem,
  LinearProgress,
  CircularProgress,
} from '@mui/material'
import GenerateIcon from '@mui/icons-material/AutoAwesome'
import SearchIcon from '@mui/icons-material/Search'
import MoreIcon from '@mui/icons-material/MoreVert'
import ViewIcon from '@mui/icons-material/Visibility'
import EditIcon from '@mui/icons-material/Edit'
import DeleteIcon from '@mui/icons-material/Delete'
import CompletedIcon from '@mui/icons-material/CheckCircle'
import PendingIcon from '@mui/icons-material/Schedule'
import CancelledIcon from '@mui/icons-material/Cancel'
import { useSearchParams } from 'react-router-dom'

interface EpisodesTabProps {
  projectId: string
  onGenerateClick: () => void
}

interface Episode {
  id: string
  number: number
  title: string
  description: string
  status: 'draft' | 'in_progress' | 'completed' | 'cancelled'
  scriptCount: number
  progress: number
  createdAt: string
  updatedAt: string
}

const STATUS_CONFIG = {
  draft: { label: '초안', color: 'default', icon: <PendingIcon /> },
  in_progress: { label: '진행중', color: 'info', icon: <PendingIcon /> },
  completed: { label: '완료', color: 'success', icon: <CompletedIcon /> },
  cancelled: { label: '취소', color: 'error', icon: <CancelledIcon /> },
} as const

export function EpisodesTab({ projectId, onGenerateClick }: EpisodesTabProps) {
  const [searchParams, setSearchParams] = useSearchParams()
  const [episodes, setEpisodes] = useState<Episode[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)
  const [_selectedEpisode, setSelectedEpisode] = useState<Episode | null>(null)

  // URL 쿼리 상태 동기화
  const searchQuery = useMemo(
    () => searchParams.get('search') || '',
    [searchParams],
  )
  const currentPage = useMemo(
    () => parseInt(searchParams.get('page') || '1'),
    [searchParams],
  )
  const filterStatus = useMemo(
    () => searchParams.get('status') || 'all',
    [searchParams],
  )

  // Mock 데이터
  useEffect(() => {
    const loadEpisodes = async () => {
      setIsLoading(true)
      try {
        // Mock 데이터 - 실제로는 API 호출
        const mockEpisodes: Episode[] = [
          {
            id: '1',
            number: 1,
            title: '첫 만남',
            description: '주인공들이 운명적으로 만나는 첫 번째 에피소드',
            status: 'completed',
            scriptCount: 3,
            progress: 100,
            createdAt: '2024-01-15T09:00:00Z',
            updatedAt: '2024-01-20T15:30:00Z',
          },
          {
            id: '2',
            number: 2,
            title: '오해와 갈등',
            description: '서로에 대한 오해로 인한 갈등이 시작되는 에피소드',
            status: 'in_progress',
            scriptCount: 1,
            progress: 45,
            createdAt: '2024-01-16T10:00:00Z',
            updatedAt: '2024-01-22T11:15:00Z',
          },
          {
            id: '3',
            number: 3,
            title: '진실 발견',
            description: '숨겨진 진실을 발견하게 되는 에피소드',
            status: 'draft',
            scriptCount: 0,
            progress: 0,
            createdAt: '2024-01-17T14:00:00Z',
            updatedAt: '2024-01-17T14:00:00Z',
          },
        ]

        setEpisodes(mockEpisodes)
      } catch {
        // 에러는 상위 컴포넌트에서 처리
      } finally {
        setIsLoading(false)
      }
    }

    loadEpisodes()
  }, [projectId])

  // 검색 핸들러
  const handleSearchChange = (value: string) => {
    const newParams = new URLSearchParams(searchParams)
    if (value) {
      newParams.set('search', value)
    } else {
      newParams.delete('search')
    }
    newParams.set('page', '1') // 검색시 첫 페이지로
    setSearchParams(newParams)
  }

  // 페이지 변경
  const handlePageChange = (
    _event: React.ChangeEvent<unknown>,
    page: number,
  ) => {
    const newParams = new URLSearchParams(searchParams)
    newParams.set('page', page.toString())
    setSearchParams(newParams)
  }

  // 상태 필터 변경
  const handleStatusFilter = (status: string) => {
    const newParams = new URLSearchParams(searchParams)
    if (status === 'all') {
      newParams.delete('status')
    } else {
      newParams.set('status', status)
    }
    newParams.set('page', '1')
    setSearchParams(newParams)
  }

  // 메뉴 핸들러
  const handleMenuClick = (
    event: React.MouseEvent<HTMLElement>,
    episode: Episode,
  ) => {
    setAnchorEl(event.currentTarget)
    setSelectedEpisode(episode)
  }

  const handleMenuClose = () => {
    setAnchorEl(null)
    setSelectedEpisode(null)
  }

  // 필터링된 에피소드
  const filteredEpisodes = useMemo(() => {
    let filtered = episodes

    // 검색 필터
    if (searchQuery) {
      filtered = filtered.filter(
        episode =>
          episode.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
          episode.description.toLowerCase().includes(searchQuery.toLowerCase()),
      )
    }

    // 상태 필터
    if (filterStatus !== 'all') {
      filtered = filtered.filter(episode => episode.status === filterStatus)
    }

    return filtered
  }, [episodes, searchQuery, filterStatus])

  const totalPages = Math.ceil(filteredEpisodes.length / 10)

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Box>
      {/* 상단 액션 바 */}
      <Stack direction="row" spacing={2} sx={{ mb: 3 }} alignItems="center">
        <TextField
          placeholder="에피소드 검색..."
          size="small"
          value={searchQuery}
          onChange={e => handleSearchChange(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon color="action" />
              </InputAdornment>
            ),
          }}
          sx={{ minWidth: 300 }}
          aria-label="에피소드 검색"
        />

        <Stack direction="row" spacing={1}>
          {['all', 'draft', 'in_progress', 'completed'].map(status => (
            <Chip
              key={status}
              label={
                status === 'all'
                  ? '전체'
                  : STATUS_CONFIG[status as keyof typeof STATUS_CONFIG]
                      ?.label || status
              }
              variant={filterStatus === status ? 'filled' : 'outlined'}
              color={filterStatus === status ? 'primary' : 'default'}
              onClick={() => handleStatusFilter(status)}
              clickable
              size="small"
            />
          ))}
        </Stack>

        <Box sx={{ flexGrow: 1 }} />

        <Button
          variant="contained"
          startIcon={<GenerateIcon />}
          onClick={onGenerateClick}
          color="primary"
        >
          스크립트 생성
        </Button>
      </Stack>

      {/* 에피소드 테이블 */}
      <TableContainer component={Paper}>
        <Table aria-label="에피소드 목록">
          <TableHead>
            <TableRow>
              <TableCell>순서</TableCell>
              <TableCell>제목</TableCell>
              <TableCell>설명</TableCell>
              <TableCell>상태</TableCell>
              <TableCell>스크립트</TableCell>
              <TableCell>진행률</TableCell>
              <TableCell>업데이트</TableCell>
              <TableCell width={60}>액션</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredEpisodes.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} align="center" sx={{ py: 4 }}>
                  <Typography color="text.secondary">
                    {searchQuery || filterStatus !== 'all'
                      ? '검색 조건에 맞는 에피소드가 없습니다.'
                      : '아직 에피소드가 없습니다.'}
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              filteredEpisodes
                .slice((currentPage - 1) * 10, currentPage * 10)
                .map(episode => {
                  const statusConfig = STATUS_CONFIG[episode.status]
                  return (
                    <TableRow key={episode.id} hover>
                      <TableCell>
                        <Typography fontWeight="bold">
                          {episode.number}
                        </Typography>
                      </TableCell>

                      <TableCell>
                        <Typography variant="subtitle2">
                          에피소드 {episode.number}: {episode.title}
                        </Typography>
                      </TableCell>

                      <TableCell>
                        <Typography
                          variant="body2"
                          color="text.secondary"
                          sx={{
                            maxWidth: 200,
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {episode.description}
                        </Typography>
                      </TableCell>

                      <TableCell>
                        <Chip
                          icon={statusConfig.icon}
                          label={statusConfig.label}
                          color={
                            statusConfig.color as
                              | 'default'
                              | 'info'
                              | 'success'
                              | 'error'
                          }
                          size="small"
                        />
                      </TableCell>

                      <TableCell>
                        <Typography variant="body2">
                          {episode.scriptCount}개
                        </Typography>
                      </TableCell>

                      <TableCell sx={{ minWidth: 120 }}>
                        <Box
                          sx={{ display: 'flex', alignItems: 'center', gap: 1 }}
                        >
                          <LinearProgress
                            variant="determinate"
                            value={episode.progress}
                            sx={{ flexGrow: 1, height: 6, borderRadius: 3 }}
                          />
                          <Typography variant="caption" color="text.secondary">
                            {episode.progress}%
                          </Typography>
                        </Box>
                      </TableCell>

                      <TableCell>
                        <Typography variant="caption" color="text.secondary">
                          {new Date(episode.updatedAt).toLocaleDateString(
                            'ko-KR',
                          )}
                        </Typography>
                      </TableCell>

                      <TableCell>
                        <Tooltip title="더 보기">
                          <IconButton
                            size="small"
                            onClick={e => handleMenuClick(e, episode)}
                            aria-label={`${episode.title} 액션 메뉴`}
                          >
                            <MoreIcon />
                          </IconButton>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  )
                })
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* 페이지네이션 */}
      {totalPages > 1 && (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
          <Pagination
            count={totalPages}
            page={currentPage}
            onChange={handlePageChange}
            color="primary"
            showFirstButton
            showLastButton
          />
        </Box>
      )}

      {/* 액션 메뉴 */}
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
        <MenuItem onClick={handleMenuClose}>
          <ViewIcon sx={{ mr: 1 }} fontSize="small" />
          상세 보기
        </MenuItem>
        <MenuItem onClick={handleMenuClose}>
          <EditIcon sx={{ mr: 1 }} fontSize="small" />
          편집
        </MenuItem>
        <MenuItem onClick={handleMenuClose}>
          <GenerateIcon sx={{ mr: 1 }} fontSize="small" />
          스크립트 생성
        </MenuItem>
        <MenuItem onClick={handleMenuClose} sx={{ color: 'error.main' }}>
          <DeleteIcon sx={{ mr: 1 }} fontSize="small" />
          삭제
        </MenuItem>
      </Menu>
    </Box>
  )
}
