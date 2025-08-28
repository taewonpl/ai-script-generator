/**
 * Simplified Dashboard - Projects List Only
 * Follows CLAUDE.md guidelines for simple, focused UI
 * Enhanced with StandardErrorPanel, accessibility, and performance optimizations
 */

import { useCallback, useEffect, useState } from 'react'
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
  Skeleton,
  Alert,
} from '@mui/material'
import { Add as AddIcon, Schedule as ScheduleIcon } from '@mui/icons-material'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'

import { projectApi } from '@/shared/api/client'
import type { Project } from '@/shared/api/types'
import { toProjects } from '@/shared/api/mappers/projectMapper'
import { StandardErrorPanel } from '@/features/error-panel/components/StandardErrorPanel'
import { adaptError } from '@/features/error-panel/adapters/errorAdapter'

const DashboardPage = () => {
  const navigate = useNavigate()
  const [showSlowLoadingBanner, setShowSlowLoadingBanner] = useState(false)
  const queryClient = useQueryClient()

  // Single API call - enhanced with performance optimizations
  const {
    data: projects,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['projects'],
    queryFn: async () => {
      const response = await projectApi.get<Project[]>('/projects')
      return response.data || []
    },
    select: toProjects,
    // Performance optimizations
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000,   // 10 minutes
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  })

  // Show "taking longer than usual" banner after 8 seconds
  useEffect(() => {
    if (!isLoading) {
      setShowSlowLoadingBanner(false)
      return
    }

    const timer = setTimeout(() => {
      setShowSlowLoadingBanner(true)
    }, 8000)

    return () => clearTimeout(timer)
  }, [isLoading])


  const formatDate = useCallback((dateString: string | undefined) => {
    if (!dateString) return '-'
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }, [])

  const getFormatLabel = useCallback((type: string | undefined) => {
    switch (type) {
      case 'drama':
        return 'Drama'
      case 'comedy':
        return 'Comedy'
      case 'thriller':
        return 'Thriller'
      case 'action':
        return 'Action'
      default:
        return type || 'Unknown'
    }
  }, [])

  // Loading state - enhanced with slow loading banner
  if (isLoading) {
    return (
      <Box sx={{ p: 3 }}>
        {/* Header */}
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
          <Typography variant="h4" component="h1">
            Projects
          </Typography>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => navigate('/projects/new')}
          >
            New Project
          </Button>
        </Box>

        {/* Slow Loading Banner */}
        {showSlowLoadingBanner && (
          <Alert 
            severity="info" 
            sx={{ mb: 3 }}
            icon={<ScheduleIcon />}
          >
            프로젝트 데이터를 불러오는 중입니다. 평소보다 시간이 오래 걸리고 있어요.
          </Alert>
        )}

        {/* Loading Table Skeleton (6-8 rows as specified) */}
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Format</TableCell>
                <TableCell>Updated</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {[...Array(7)].map((_, index) => (
                <TableRow key={index}>
                  <TableCell>
                    <Skeleton variant="text" width="60%" />
                  </TableCell>
                  <TableCell>
                    <Skeleton variant="text" width="40%" />
                  </TableCell>
                  <TableCell>
                    <Skeleton variant="text" width="50%" />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Box>
    )
  }

  // Error state - show StandardErrorPanel with retry
  if (error) {
    const standardError = adaptError(error, {
      endpoint: '/projects',
      method: 'GET',
    })

    return (
      <Box sx={{ p: 3 }}>
        <Typography variant="h4" component="h1" mb={3}>
          Projects
        </Typography>
        <StandardErrorPanel
          error={standardError}
          onRetry={async () => {
            await refetch()
          }}
          language="ko"
        />
      </Box>
    )
  }

  // Empty state - simple "Welcome!" message only
  if (!projects || projects.length === 0) {
    return (
      <Box sx={{ p: 3 }}>
        {/* Header */}
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
          <Typography variant="h4" component="h1">
            Projects
          </Typography>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => navigate('/projects/new')}
          >
            New Project
          </Button>
        </Box>

        {/* Simple Welcome Message - centered, blue text only */}
        <Box 
          display="flex" 
          justifyContent="center" 
          alignItems="center" 
          sx={{ py: 8 }}
        >
          <Typography 
            variant="h5" 
            color="primary" 
            sx={{ textAlign: 'center' }}
          >
            Welcome!
          </Typography>
        </Box>
      </Box>
    )
  }

  // Main UI - Projects table with Name | Format | Updated columns
  return (
    <Box sx={{ p: 3 }}>
      {/* Header - same as /projects page */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          Projects
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => navigate('/projects/new')}
        >
          New Project
        </Button>
      </Box>

      {/* Projects Table - sorted by updated_at DESC */}
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Format</TableCell>
              <TableCell>Updated</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {projects
              .sort((a, b) => {
                // Sort by updated_at DESC (most recent first)
                const dateA = a.updated_at ? new Date(a.updated_at).getTime() : 0
                const dateB = b.updated_at ? new Date(b.updated_at).getTime() : 0
                return dateB - dateA
              })
              .map((project) => (
                <TableRow
                  key={project.id}
                  hover
                  sx={{ 
                    cursor: 'pointer',
                    '&:hover': {
                      backgroundColor: 'action.hover',
                    },
                  }}
                  onClick={() => navigate(`/projects/${project.id}`)}
                  onMouseEnter={() => {
                    // Prefetch project details on hover
                    queryClient.prefetchQuery({
                      queryKey: ['project', project.id],
                      queryFn: async () => {
                        const response = await projectApi.get(`/projects/${project.id}`)
                        return response.data
                      },
                      staleTime: 5 * 60 * 1000,
                    })
                  }}
                  tabIndex={0}
                  role="button"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault()
                      navigate(`/projects/${project.id}`)
                    }
                  }}
                  aria-label={`프로젝트 ${project.name} 상세 보기`}
                >
                  <TableCell component="th" scope="row">
                    <Typography variant="body1" fontWeight="medium">
                      {project.name}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" color="text.secondary">
                      {getFormatLabel(project.type)}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" color="text.secondary">
                      {formatDate(project.updated_at)}
                    </Typography>
                  </TableCell>
                </TableRow>
              ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  )
}

export default DashboardPage