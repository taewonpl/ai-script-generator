import {
  Box,
  Typography,
  Button,
  IconButton,
  Tooltip,
  Chip,
  Stack,
  Badge,
} from '@mui/material'
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Archive as ArchiveIcon,
  Refresh as RefreshIcon,
  FilterList as FilterIcon,
  ViewList as ListViewIcon,
  ViewModule as GridViewIcon,
} from '@mui/icons-material'

interface ProjectListHeaderProps {
  totalCount: number
  selectedCount: number
  hasFilters: boolean
  viewMode: 'grid' | 'list'
  onCreateProject: () => void
  onDeleteSelected: () => void
  onArchiveSelected: () => void
  onRefresh: () => void
  onToggleFilters: () => void
  onViewModeChange: (mode: 'grid' | 'list') => void
  loading?: boolean
}

export function ProjectListHeader({
  totalCount,
  selectedCount,
  hasFilters,
  viewMode,
  onCreateProject,
  onDeleteSelected,
  onArchiveSelected,
  onRefresh,
  onToggleFilters,
  onViewModeChange,
  loading = false,
}: ProjectListHeaderProps) {
  const hasSelection = selectedCount > 0

  return (
    <Box>
      {/* Main Header */}
      <Box
        display="flex"
        justifyContent="space-between"
        alignItems="center"
        mb={2}
      >
        <Box>
          <Typography variant="h4" component="h1" gutterBottom>
            프로젝트 관리
          </Typography>
          <Stack direction="row" spacing={1} alignItems="center">
            <Typography variant="body2" color="textSecondary">
              총 {totalCount.toLocaleString()}개 프로젝트
            </Typography>
            {hasFilters && (
              <Chip
                label="필터 적용됨"
                size="small"
                color="primary"
                variant="outlined"
              />
            )}
            {hasSelection && (
              <Chip
                label={`${selectedCount}개 선택됨`}
                size="small"
                color="secondary"
              />
            )}
          </Stack>
        </Box>

        <Stack direction="row" spacing={1} alignItems="center">
          {/* View Mode Toggle */}
          <Box border={1} borderColor="divider" borderRadius={1} p={0.5}>
            <IconButton
              size="small"
              color={viewMode === 'grid' ? 'primary' : 'default'}
              onClick={() => onViewModeChange('grid')}
            >
              <GridViewIcon />
            </IconButton>
            <IconButton
              size="small"
              color={viewMode === 'list' ? 'primary' : 'default'}
              onClick={() => onViewModeChange('list')}
            >
              <ListViewIcon />
            </IconButton>
          </Box>

          {/* Filter Toggle */}
          <Tooltip title="필터 표시/숨기기">
            <IconButton onClick={onToggleFilters}>
              <Badge color="primary" variant="dot" invisible={!hasFilters}>
                <FilterIcon />
              </Badge>
            </IconButton>
          </Tooltip>

          {/* Refresh */}
          <Tooltip title="새로고침">
            <IconButton onClick={onRefresh} disabled={loading}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>

          {/* Create Project */}
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={onCreateProject}
          >
            새 프로젝트
          </Button>
        </Stack>
      </Box>

      {/* Batch Actions Bar */}
      {hasSelection && (
        <Box
          display="flex"
          alignItems="center"
          justifyContent="space-between"
          p={2}
          mb={2}
          bgcolor="action.hover"
          borderRadius={1}
          border={1}
          borderColor="divider"
        >
          <Typography variant="body2" fontWeight="medium">
            {selectedCount}개 프로젝트가 선택되었습니다
          </Typography>

          <Stack direction="row" spacing={1}>
            <Button
              size="small"
              startIcon={<ArchiveIcon />}
              onClick={onArchiveSelected}
            >
              아카이브
            </Button>
            <Button
              size="small"
              color="error"
              startIcon={<DeleteIcon />}
              onClick={onDeleteSelected}
            >
              삭제
            </Button>
          </Stack>
        </Box>
      )}
    </Box>
  )
}
