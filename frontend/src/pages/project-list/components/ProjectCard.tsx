import { memo, useCallback, useMemo, useState } from 'react'
import type { MouseEvent } from 'react'
import {
  Card,
  CardContent,
  CardActions,
  Typography,
  Chip,
  Box,
  Button,
  IconButton,
  Checkbox,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Stack,
  Avatar,
  Tooltip,
} from '@mui/material'
import {
  MoreVert as MoreIcon,
  Movie as MovieIcon,
  Tv as TvIcon,
  TheaterComedy as ComedyIcon,
  LocalMovies as ActionIcon,
  Favorite as RomanceIcon,
  Psychology as ThrillerIcon,
  VideoLibrary as DocumentaryIcon,
  Animation as AnimationIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Archive as ArchiveIcon,
  PlayArrow as GenerateIcon,
  Visibility as ViewIcon,
} from '@mui/icons-material'
import { useNavigate } from 'react-router-dom'
import type { Project } from '@/shared/types/project'

interface ProjectCardProps {
  project: Project
  selected: boolean
  onSelect: (id: string) => void
  onEdit: (project: Project) => void
  onDelete: (project: Project) => void
  onArchive: (project: Project) => void
  viewMode: 'grid' | 'list'
  showSelection: boolean
}

const TYPE_ICONS = {
  drama: MovieIcon,
  comedy: ComedyIcon,
  action: ActionIcon,
  romance: RomanceIcon,
  thriller: ThrillerIcon,
  documentary: DocumentaryIcon,
  animation: AnimationIcon,
  default: TvIcon,
} as const

const STATUS_COLORS = {
  active: 'success',
  completed: 'primary',
  paused: 'warning',
  archived: 'default',
} as const

// Memoized date formatter
const formatDate = (dateString: string): string => {
  return new Date(dateString).toLocaleDateString('ko-KR')
}

export const ProjectCard = memo(function ProjectCard({
  project,
  selected,
  onSelect,
  onEdit,
  onDelete,
  onArchive,
  viewMode,
  showSelection,
}: ProjectCardProps) {
  const navigate = useNavigate()
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)

  // Memoized computed values
  const IconComponent = useMemo(
    () =>
      TYPE_ICONS[project.type as keyof typeof TYPE_ICONS] || TYPE_ICONS.default,
    [project.type],
  )

  const statusColor = useMemo(
    () =>
      STATUS_COLORS[project.status as keyof typeof STATUS_COLORS] || 'default',
    [project.status],
  )

  const formattedCreatedAt = useMemo(
    () => formatDate(project.created_at || project.createdAt || ''),
    [project.created_at, project.createdAt],
  )
  const formattedUpdatedAt = useMemo(
    () => formatDate(project.updated_at || project.updatedAt || ''),
    [project.updated_at, project.updatedAt],
  )

  // Memoized callbacks
  const handleMenuClick = useCallback((event: MouseEvent<HTMLElement>) => {
    event.stopPropagation()
    setAnchorEl(event.currentTarget)
  }, [])

  const handleMenuClose = useCallback(() => {
    setAnchorEl(null)
  }, [])

  const handleMenuAction = useCallback(
    (action: () => void) => {
      action()
      handleMenuClose()
    },
    [handleMenuClose],
  )

  const handleCardClick = useCallback(() => {
    if (showSelection) {
      onSelect(project.id)
    } else {
      navigate(`/projects/${project.id}`)
    }
  }, [showSelection, onSelect, project.id, navigate])

  const handleSelectionClick = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      event.stopPropagation()
      onSelect(project.id)
    },
    [onSelect, project.id],
  )

  const handleViewClick = useCallback(
    (e: MouseEvent) => {
      e.stopPropagation()
      navigate(`/projects/${project.id}`)
    },
    [navigate, project.id],
  )

  const handleGenerateClick = useCallback(
    (e: MouseEvent) => {
      e.stopPropagation()
      navigate(`/projects/${project.id}/generate`)
    },
    [navigate, project.id],
  )

  const handleEditClick = useCallback(() => onEdit(project), [onEdit, project])
  const handleArchiveClick = useCallback(
    () => onArchive(project),
    [onArchive, project],
  )
  const handleDeleteClick = useCallback(
    () => onDelete(project),
    [onDelete, project],
  )

  // Memoized card styles
  const cardStyles = useMemo(
    () => ({
      cursor: 'pointer',
      '&:hover':
        viewMode === 'grid'
          ? {
              transform: 'translateY(-2px)',
              boxShadow: 2,
              transition: 'all 0.2s ease-in-out',
            }
          : {
              bgcolor: 'action.hover',
              borderColor: 'primary.main',
            },
      bgcolor: selected ? 'action.selected' : 'background.paper',
      ...(viewMode === 'grid'
        ? {
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            position: 'relative',
          }
        : {
            variant: 'outlined',
          }),
    }),
    [viewMode, selected],
  )

  if (viewMode === 'list') {
    return (
      <Card sx={cardStyles} onClick={handleCardClick}>
        <CardContent sx={{ py: 2 }}>
          <Box display="flex" alignItems="center" gap={2}>
            {/* Selection Checkbox */}
            {showSelection && (
              <Checkbox checked={selected} onChange={handleSelectionClick} />
            )}

            {/* Project Icon */}
            <Avatar sx={{ bgcolor: 'primary.main' }}>
              <IconComponent />
            </Avatar>

            {/* Project Info */}
            <Box flex={1}>
              <Typography variant="h6" component="h3" noWrap>
                {project.name}
              </Typography>
              <Stack direction="row" spacing={1} alignItems="center" mt={0.5}>
                <Chip label={project.status} size="small" color={statusColor} />
                <Chip label={project.type} size="small" variant="outlined" />
                {project.episodes_count !== undefined && (
                  <Chip
                    label={`${project.episodes_count}개 에피소드`}
                    size="small"
                    variant="outlined"
                  />
                )}
                {project.scripts_count !== undefined && (
                  <Chip
                    label={`${project.scripts_count}개 스크립트`}
                    size="small"
                    variant="outlined"
                  />
                )}
              </Stack>
            </Box>

            {/* Dates */}
            <Box textAlign="right" minWidth={100}>
              <Typography variant="body2" color="textSecondary">
                생성: {formattedCreatedAt}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                수정: {formattedUpdatedAt}
              </Typography>
            </Box>

            {/* Actions */}
            <Stack direction="row" spacing={1}>
              <Tooltip title="상세 보기">
                <IconButton size="small" onClick={handleViewClick}>
                  <ViewIcon />
                </IconButton>
              </Tooltip>

              <Tooltip title="스크립트 생성">
                <IconButton
                  size="small"
                  color="primary"
                  onClick={handleGenerateClick}
                >
                  <GenerateIcon />
                </IconButton>
              </Tooltip>

              <IconButton size="small" onClick={handleMenuClick}>
                <MoreIcon />
              </IconButton>
            </Stack>
          </Box>
        </CardContent>
      </Card>
    )
  }

  // Grid view
  return (
    <Card sx={cardStyles} onClick={handleCardClick}>
      {/* Selection Checkbox */}
      {showSelection && (
        <Box position="absolute" top={8} left={8} zIndex={1}>
          <Checkbox
            checked={selected}
            onChange={handleSelectionClick}
            size="small"
            sx={{
              bgcolor: 'background.paper',
              borderRadius: '50%',
              '&.Mui-checked': {
                bgcolor: 'primary.main',
              },
            }}
          />
        </Box>
      )}

      {/* Menu Button */}
      <Box position="absolute" top={8} right={8} zIndex={1}>
        <IconButton
          size="small"
          onClick={handleMenuClick}
          sx={{
            bgcolor: 'background.paper',
            '&:hover': { bgcolor: 'grey.100' },
          }}
        >
          <MoreIcon />
        </IconButton>
      </Box>

      <CardContent sx={{ flexGrow: 1, pt: showSelection ? 5 : 5 }}>
        {/* Project Icon and Title */}
        <Box display="flex" alignItems="center" mb={2}>
          <IconComponent color="primary" sx={{ mr: 1 }} />
          <Typography variant="h6" component="h3" noWrap>
            {project.name}
          </Typography>
        </Box>

        {/* Description */}
        <Typography
          variant="body2"
          color="textSecondary"
          sx={{
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            display: '-webkit-box',
            WebkitLineClamp: 3,
            WebkitBoxOrient: 'vertical',
            mb: 2,
            minHeight: '3.6em',
          }}
        >
          {project.description || '설명이 없습니다.'}
        </Typography>

        {/* Status and Type Chips */}
        <Stack direction="row" spacing={1} mb={2}>
          <Chip label={project.status} size="small" color={statusColor} />
          <Chip label={project.type} size="small" variant="outlined" />
        </Stack>

        {/* Statistics */}
        {(project.episodes_count !== undefined ||
          project.scripts_count !== undefined) && (
          <Stack direction="row" spacing={1} mb={2}>
            {project.episodes_count !== undefined && (
              <Chip
                label={`${project.episodes_count}개 에피소드`}
                size="small"
                variant="outlined"
                color="info"
              />
            )}
            {project.scripts_count !== undefined && (
              <Chip
                label={`${project.scripts_count}개 스크립트`}
                size="small"
                variant="outlined"
                color="secondary"
              />
            )}
          </Stack>
        )}

        {/* Dates */}
        <Box mt="auto">
          <Typography variant="caption" color="textSecondary" display="block">
            생성: {formattedCreatedAt}
          </Typography>
          <Typography variant="caption" color="textSecondary" display="block">
            수정: {formattedUpdatedAt}
          </Typography>
        </Box>
      </CardContent>

      <CardActions sx={{ pt: 0 }}>
        <Button size="small" startIcon={<ViewIcon />} onClick={handleViewClick}>
          상세 보기
        </Button>
        <Button
          size="small"
          color="primary"
          startIcon={<GenerateIcon />}
          onClick={handleGenerateClick}
        >
          스크립트 생성
        </Button>
      </CardActions>

      {/* Context Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
        onClick={e => e.stopPropagation()}
      >
        <MenuItem onClick={() => handleMenuAction(handleEditClick)}>
          <ListItemIcon>
            <EditIcon />
          </ListItemIcon>
          <ListItemText>편집</ListItemText>
        </MenuItem>

        <MenuItem onClick={() => handleMenuAction(handleArchiveClick)}>
          <ListItemIcon>
            <ArchiveIcon />
          </ListItemIcon>
          <ListItemText>아카이브</ListItemText>
        </MenuItem>

        <MenuItem
          onClick={() => handleMenuAction(handleDeleteClick)}
          sx={{ color: 'error.main' }}
        >
          <ListItemIcon>
            <DeleteIcon color="error" />
          </ListItemIcon>
          <ListItemText>삭제</ListItemText>
        </MenuItem>
      </Menu>
    </Card>
  )
})

// Display name for debugging
ProjectCard.displayName = 'ProjectCard'
