import { useState } from 'react'
import {
  Box,
  Typography,
  Button,
  Card,
  CardContent,
  CardActions,
  Chip,
  TextField,
  InputAdornment,
  Fab,
} from '@mui/material'
import {
  Search as SearchIcon,
  Add as AddIcon,
  Movie as MovieIcon,
} from '@mui/icons-material'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'

import { projectApi } from '@/shared/api/client'
import type { Project } from '@/shared/api/types'
import { toProjects } from '@/shared/api/mappers/projectMapper'

const ProjectListPage = () => {
  const [searchTerm, setSearchTerm] = useState('')
  const navigate = useNavigate()

  const {
    data: projects,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['projects'],
    queryFn: async () => {
      const response = await projectApi.get<Project[]>('/projects')
      return response.data || []
    },
    select: toProjects, // DTO를 UI 도메인으로 정규화
  })

  const filteredProjects = projects?.filter(project =>
    project.name.toLowerCase().includes(searchTerm.toLowerCase()),
  )

  const getStatusColor = (status: Project['status']) => {
    switch (status) {
      case 'active':
        return 'success'
      case 'completed':
        return 'primary'
      case 'paused':
        return 'warning'
      default:
        return 'default'
    }
  }

  const getTypeIcon = (_type: Project['type']) => {
    return <MovieIcon color="action" />
  }

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" p={4}>
        <Typography>Loading projects...</Typography>
      </Box>
    )
  }

  if (error) {
    return (
      <Box display="flex" justifyContent="center" p={4}>
        <Typography color="error">Error loading projects</Typography>
      </Box>
    )
  }

  return (
    <Box>
      <Box
        display="flex"
        justifyContent="space-between"
        alignItems="center"
        mb={3}
      >
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

      <Box mb={3}>
        <TextField
          fullWidth
          placeholder="Search projects..."
          value={searchTerm}
          onChange={e => setSearchTerm(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
          }}
        />
      </Box>

      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
        {filteredProjects?.map(project => (
          <Box
            key={project.id}
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
                '&:hover': {
                  transform: 'translateY(-2px)',
                  transition: 'transform 0.2s ease-in-out',
                },
              }}
              onClick={() => navigate(`/projects/${project.id}`)}
            >
              <CardContent sx={{ flexGrow: 1 }}>
                <Box display="flex" alignItems="center" mb={2}>
                  {getTypeIcon(project.type)}
                  <Typography variant="h6" component="h2" ml={1}>
                    {project.name}
                  </Typography>
                </Box>

                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    display: '-webkit-box',
                    WebkitLineClamp: 3,
                    WebkitBoxOrient: 'vertical',
                  }}
                >
                  {project.description || 'No description'}
                </Typography>

                <Box mt={2}>
                  <Chip
                    label={project.status}
                    color={getStatusColor(project.status)}
                    size="small"
                  />
                  <Chip
                    label={project.type}
                    variant="outlined"
                    size="small"
                    sx={{ ml: 1 }}
                  />
                </Box>
              </CardContent>

              <CardActions>
                <Button
                  size="small"
                  onClick={e => {
                    e.stopPropagation()
                    navigate(`/projects/${project.id}/episodes`)
                  }}
                >
                  Episodes
                </Button>
                <Button
                  size="small"
                  onClick={e => {
                    e.stopPropagation()
                    navigate(`/projects/${project.id}`)
                  }}
                >
                  Details
                </Button>
              </CardActions>
            </Card>
          </Box>
        ))}
      </Box>

      {filteredProjects?.length === 0 && (
        <Box
          display="flex"
          flexDirection="column"
          alignItems="center"
          justifyContent="center"
          py={8}
        >
          <MovieIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" color="text.secondary" mb={1}>
            No projects found
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {searchTerm
              ? 'Try a different search term'
              : 'Create your first project to get started'}
          </Typography>
        </Box>
      )}

      <Fab
        color="primary"
        aria-label="add project"
        sx={{
          position: 'fixed',
          bottom: 16,
          right: 16,
          display: { xs: 'flex', sm: 'none' },
        }}
        onClick={() => navigate('/projects/new')}
      >
        <AddIcon />
      </Fab>
    </Box>
  )
}

export default ProjectListPage
