import { useState, useEffect } from 'react'
import {
  Box,
  Card,
  CardContent,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  Stack,
  Chip,
  Typography,
  InputAdornment,
  IconButton,
  Collapse,
} from '@mui/material'
import {
  Search as SearchIcon,
  Clear as ClearIcon,
  ArrowUpward as AscIcon,
  ArrowDownward as DescIcon,
} from '@mui/icons-material'

import type { ProjectFilters } from '@/shared/types/api'

interface ProjectListFiltersProps {
  filters: ProjectFilters
  onFiltersChange: {
    setSearch: (search: string) => void
    setStatus: (status: string) => void
    setType: (type: string) => void
    setSortBy: (sortBy: ProjectFilters['sortBy']) => void
    setSortOrder: (sortOrder: ProjectFilters['sortOrder']) => void
    resetFilters: () => void
    toggleSortOrder: () => void
  }
  expanded: boolean
  resultCount: number
}

const STATUS_OPTIONS = [
  { value: 'all', label: '전체' },
  { value: 'active', label: '진행중' },
  { value: 'completed', label: '완료' },
  { value: 'paused', label: '일시정지' },
  { value: 'archived', label: '아카이브' },
]

const TYPE_OPTIONS = [
  { value: 'all', label: '전체' },
  { value: 'drama', label: '드라마' },
  { value: 'comedy', label: '코미디' },
  { value: 'action', label: '액션' },
  { value: 'romance', label: '로맨스' },
  { value: 'thriller', label: '스릴러' },
  { value: 'documentary', label: '다큐멘터리' },
  { value: 'animation', label: '애니메이션' },
]

const SORT_OPTIONS = [
  { value: 'name', label: '이름' },
  { value: 'created_at', label: '생성일' },
  { value: 'updated_at', label: '수정일' },
]

export function ProjectListFilters({
  filters,
  onFiltersChange,
  expanded,
  resultCount,
}: ProjectListFiltersProps) {
  const [searchDebounce, setSearchDebounce] = useState(filters.search)

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      onFiltersChange.setSearch(searchDebounce || '')
    }, 300)

    return () => clearTimeout(timer)
  }, [searchDebounce, onFiltersChange])

  useEffect(() => {
    setSearchDebounce(filters.search)
  }, [filters.search])

  const activeFilterCount = [
    filters.search && 'search',
    filters.status !== 'all' && 'status',
    filters.type !== 'all' && 'type',
  ].filter(Boolean).length

  const clearSearch = () => {
    setSearchDebounce('')
    onFiltersChange.setSearch('')
  }

  return (
    <Box mb={3}>
      {/* Search Bar - Always Visible */}
      <Box mb={2}>
        <TextField
          fullWidth
          placeholder="프로젝트 검색..."
          value={searchDebounce}
          onChange={e => setSearchDebounce(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
            endAdornment: searchDebounce && (
              <InputAdornment position="end">
                <IconButton size="small" onClick={clearSearch} edge="end">
                  <ClearIcon />
                </IconButton>
              </InputAdornment>
            ),
          }}
        />
      </Box>

      {/* Advanced Filters - Collapsible */}
      <Collapse in={expanded}>
        <Card variant="outlined">
          <CardContent>
            <Stack spacing={3}>
              {/* Filter Controls */}
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
                {/* Status Filter */}
                <FormControl size="small" sx={{ minWidth: 120 }}>
                  <InputLabel>상태</InputLabel>
                  <Select
                    value={filters.status}
                    label="상태"
                    onChange={e => onFiltersChange.setStatus(e.target.value)}
                  >
                    {STATUS_OPTIONS.map(option => (
                      <MenuItem key={option.value} value={option.value}>
                        {option.label}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>

                {/* Type Filter */}
                <FormControl size="small" sx={{ minWidth: 120 }}>
                  <InputLabel>유형</InputLabel>
                  <Select
                    value={filters.type}
                    label="유형"
                    onChange={e => onFiltersChange.setType(e.target.value)}
                  >
                    {TYPE_OPTIONS.map(option => (
                      <MenuItem key={option.value} value={option.value}>
                        {option.label}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>

                {/* Sort Controls */}
                <FormControl size="small" sx={{ minWidth: 120 }}>
                  <InputLabel>정렬</InputLabel>
                  <Select
                    value={filters.sortBy}
                    label="정렬"
                    onChange={e =>
                      onFiltersChange.setSortBy(
                        e.target.value as ProjectFilters['sortBy'],
                      )
                    }
                  >
                    {SORT_OPTIONS.map(option => (
                      <MenuItem key={option.value} value={option.value}>
                        {option.label}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>

                {/* Sort Direction */}
                <Button
                  variant="outlined"
                  size="small"
                  startIcon={
                    filters.sortOrder === 'asc' ? <AscIcon /> : <DescIcon />
                  }
                  onClick={onFiltersChange.toggleSortOrder}
                  sx={{ minWidth: 100 }}
                >
                  {filters.sortOrder === 'asc' ? '오름차순' : '내림차순'}
                </Button>

                <Box flex={1} />

                {/* Reset Filters */}
                <Button
                  variant="outlined"
                  size="small"
                  onClick={onFiltersChange.resetFilters}
                  disabled={activeFilterCount === 0}
                >
                  초기화
                </Button>
              </Stack>

              {/* Active Filters Display */}
              <Box>
                <Stack
                  direction="row"
                  spacing={1}
                  alignItems="center"
                  flexWrap="wrap"
                >
                  <Typography variant="body2" color="textSecondary">
                    활성 필터:
                  </Typography>

                  {filters.search && (
                    <Chip
                      label={`검색: "${filters.search}"`}
                      size="small"
                      onDelete={clearSearch}
                    />
                  )}

                  {filters.status !== 'all' && (
                    <Chip
                      label={`상태: ${STATUS_OPTIONS.find(opt => opt.value === filters.status)?.label}`}
                      size="small"
                      onDelete={() => onFiltersChange.setStatus('all')}
                    />
                  )}

                  {filters.type !== 'all' && (
                    <Chip
                      label={`유형: ${TYPE_OPTIONS.find(opt => opt.value === filters.type)?.label}`}
                      size="small"
                      onDelete={() => onFiltersChange.setType('all')}
                    />
                  )}

                  {activeFilterCount === 0 && (
                    <Typography
                      variant="body2"
                      color="textSecondary"
                      fontStyle="italic"
                    >
                      없음
                    </Typography>
                  )}
                </Stack>

                {/* Result Count */}
                <Typography variant="body2" color="textSecondary" mt={2}>
                  {resultCount.toLocaleString()}개의 결과
                  {activeFilterCount > 0 && ' (필터 적용됨)'}
                </Typography>
              </Box>
            </Stack>
          </CardContent>
        </Card>
      </Collapse>
    </Box>
  )
}
