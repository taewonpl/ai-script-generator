/**
 * Projects List Page with Delete Functionality
 * Demonstrates integration of DeleteConfirmDialog with project management
 */

import { useState, useCallback } from 'react'
import {
  Box,
  Typography,
  Button,
  Card,
  CardContent,
  CardActions,
  Grid,
  IconButton,
  Chip,
  Stack,
  Alert,
} from '@mui/material'
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Visibility as ViewIcon,
} from '@mui/icons-material'
import { Link, useNavigate } from 'react-router-dom'

import { DeleteConfirmDialog } from '@/features/project/components/DeleteConfirmDialog'
import { useProjectDelete } from '@/features/project/hooks/useProjectDelete'
// import { useToastHelpers } from '@/shared/ui/components/toast' // Reserved for future use
import type { Project } from '@/shared/api/types'

// Mock project data for demonstration
const mockProjects: Project[] = [
  {
    id: 'proj-1',
    name: '로맨틱 코미디 시리즈',
    description: '현대적 로맨스와 코미디를 결합한 시리즈',
    type: 'romance',
    status: 'draft',
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-01-20T14:30:00Z',
  },
  {
    id: 'proj-2', 
    name: 'SF 스릴러 프로젝트',
    description: '미래 사회를 배경으로 한 스릴러 드라마',
    type: 'thriller',
    status: 'completed',
    created_at: '2024-01-10T09:15:00Z',
    updated_at: '2024-01-25T16:45:00Z',
  },
  {
    id: 'proj-3',
    name: '역사 드라마',
    description: '조선시대를 배경으로 한 대하 드라마',
    type: 'drama',
    status: 'published',
    created_at: '2024-01-05T11:30:00Z',
    updated_at: '2024-01-22T13:15:00Z',
  },
]

const ProjectsPage = () => {
  const [projects, setProjects] = useState<Project[]>(mockProjects)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [projectToDelete, setProjectToDelete] = useState<Project | null>(null)
  
  const navigate = useNavigate()
  // const { showSuccess } = useToastHelpers() // Reserved for future use
  
  // Project deletion hook
  const { isDeleting, error, deleteProject, clearError } = useProjectDelete({
    language: 'kr',
    redirectAfterDelete: false, // Stay on projects page
    onSuccess: (projectId) => {
      // Update local state optimistically
      setProjects(prev => prev.filter(p => p.id !== projectId))
      setDeleteDialogOpen(false)
      setProjectToDelete(null)
    },
  })

  // Handle delete button click
  const handleDeleteClick = useCallback((project: Project) => {
    setProjectToDelete(project)
    setDeleteDialogOpen(true)
  }, [])

  // Handle delete confirmation
  const handleDeleteConfirm = useCallback(async (deleteId: string) => {
    if (!projectToDelete) return
    
    try {
      await deleteProject(projectToDelete.id, projectToDelete.name, { deleteId })
    } catch (err) {
      // Error is handled by the hook and will be displayed via error prop
      console.error('Delete confirmation failed:', err)
    }
  }, [projectToDelete, deleteProject])

  // Handle dialog close
  const handleDialogClose = useCallback(() => {
    if (isDeleting) return // Prevent closing during deletion
    setDeleteDialogOpen(false)
    setProjectToDelete(null)
    clearError()
  }, [isDeleting, clearError])

  // Get status color and label
  const getStatusInfo = (status: string | undefined) => {
    switch (status) {
      case 'draft':
        return { color: 'default' as const, label: '초안' }
      case 'completed':
        return { color: 'success' as const, label: '완료' }
      case 'published':
        return { color: 'primary' as const, label: '발행됨' }
      default:
        return { color: 'default' as const, label: status || 'unknown' }
    }
  }

  // Format date
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }

  return (
    <Box>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          프로젝트 관리
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          component={Link}
          to="/projects/create"
        >
          새 프로젝트
        </Button>
      </Box>

      {/* Projects Grid */}
      {projects.length === 0 ? (
        <Alert severity="info" sx={{ mt: 3 }}>
          프로젝트가 없습니다. 새 프로젝트를 생성해보세요.
        </Alert>
      ) : (
        <Grid container spacing={3}>
          {projects.map((project) => {
            const statusInfo = getStatusInfo(project.status)
            
            return (
              <Grid key={project.id} size={{ xs: 12, md: 6, lg: 4 }}>
                <Card variant="outlined" sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                  <CardContent sx={{ flexGrow: 1 }}>
                    <Stack spacing={2}>
                      {/* Project Name */}
                      <Typography variant="h6" component="h2" noWrap>
                        {project.name}
                      </Typography>
                      
                      {/* Description */}
                      <Typography 
                        variant="body2" 
                        color="text.secondary"
                        sx={{
                          display: '-webkit-box',
                          WebkitLineClamp: 2,
                          WebkitBoxOrient: 'vertical',
                          overflow: 'hidden',
                        }}
                      >
                        {project.description || '설명이 없습니다.'}
                      </Typography>
                      
                      {/* Status and Type */}
                      <Box display="flex" gap={1} flexWrap="wrap">
                        <Chip 
                          label={statusInfo.label} 
                          color={statusInfo.color}
                          size="small" 
                        />
                        <Chip 
                          label={project.type} 
                          variant="outlined" 
                          size="small" 
                        />
                      </Box>
                      
                      {/* Dates */}
                      <Stack spacing={0.5}>
                        <Typography variant="caption" color="text.secondary">
                          생성: {formatDate(project.created_at || '')}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          수정: {formatDate(project.updated_at || '')}
                        </Typography>
                      </Stack>
                    </Stack>
                  </CardContent>

                  <CardActions sx={{ p: 2, pt: 0 }}>
                    <Box display="flex" justifyContent="space-between" width="100%">
                      {/* Action Buttons */}
                      <Box display="flex" gap={0.5}>
                        <IconButton 
                          size="small"
                          onClick={() => navigate(`/projects/${project.id}`)}
                          title="프로젝트 보기"
                        >
                          <ViewIcon />
                        </IconButton>
                        <IconButton 
                          size="small"
                          onClick={() => navigate(`/projects/${project.id}/edit`)}
                          title="프로젝트 수정"
                        >
                          <EditIcon />
                        </IconButton>
                      </Box>
                      
                      {/* Delete Button */}
                      <IconButton
                        size="small"
                        color="error"
                        onClick={() => handleDeleteClick(project)}
                        title="프로젝트 삭제"
                      >
                        <DeleteIcon />
                      </IconButton>
                    </Box>
                  </CardActions>
                </Card>
              </Grid>
            )
          })}
        </Grid>
      )}

      {/* Delete Confirmation Dialog */}
      <DeleteConfirmDialog
        open={deleteDialogOpen}
        onClose={handleDialogClose}
        onConfirm={handleDeleteConfirm}
        projectName={projectToDelete?.name || ''}
        projectId={projectToDelete?.id || ''}
        language="kr"
        isDeleting={isDeleting}
        error={error}
        onClearError={clearError}
      />
    </Box>
  )
}

export default ProjectsPage