import { useState } from 'react'
import type { ReactNode, SyntheticEvent } from 'react'
import {
  Box,
  Container,
  Typography,
  Breadcrumbs,
  Link,
  Tabs,
  Tab,
  Paper,
  CircularProgress,
  Alert,
  Chip,
  Stack,
  Avatar,
  Button,
  IconButton,
  Divider,
} from '@mui/material'
import {
  ArrowBack as BackIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Archive as ArchiveIcon,
  PlayArrow as GenerateIcon,
  MoreVert as MoreIcon,
} from '@mui/icons-material'
import { useParams, useNavigate } from 'react-router-dom'
import { ProjectOverview } from './components/ProjectOverview'
import { ProjectEpisodes } from './components/ProjectEpisodes'
import { ProjectScripts } from './components/ProjectScripts'
import { ProjectSettings } from './components/ProjectSettings'
import { useToastHelpers } from '@/shared/ui/components/toast'
import { useProject } from '@/shared/api/hooks/projects'

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
      id={`project-tabpanel-${index}`}
      aria-labelledby={`project-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  )
}

const STATUS_COLORS = {
  active: 'success',
  completed: 'primary',
  paused: 'warning',
  archived: 'default',
} as const

export default function ProjectDetailPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const { showSuccess: _showSuccess, showError: _showError } = useToastHelpers()
  const [currentTab, setCurrentTab] = useState(0)

  // Load project data using unified hook
  const {
    data: project,
    isLoading,
    error,
    refetch,
  } = useProject(projectId!)

  const handleTabChange = (_: SyntheticEvent, newValue: number) => {
    setCurrentTab(newValue)
  }

  const handleEdit = () => {
    navigate(`/projects/${projectId}/edit`)
  }

  const handleDelete = () => {
    // TODO: Implement delete confirmation dialog
    console.log('Delete project:', projectId)
  }

  const handleArchive = () => {
    // TODO: Implement archive functionality
    console.log('Archive project:', projectId)
  }

  const handleGenerate = () => {
    navigate(`/projects/${projectId}/generate`)
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ko-KR')
  }

  if (isLoading) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        minHeight="50vh"
      >
        <CircularProgress />
      </Box>
    )
  }

  if (error) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Alert severity="error">프로젝트를 불러오는데 실패했습니다.</Alert>
      </Container>
    )
  }

  if (!project) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Alert severity="warning">프로젝트를 찾을 수 없습니다.</Alert>
      </Container>
    )
  }

  const statusColor =
    STATUS_COLORS[project.status as keyof typeof STATUS_COLORS] || 'default'

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      {/* Breadcrumbs */}
      <Breadcrumbs sx={{ mb: 3 }}>
        <Link
          component="button"
          variant="body1"
          onClick={() => navigate('/projects')}
          sx={{ textDecoration: 'none' }}
        >
          프로젝트
        </Link>
        <Typography color="textPrimary">{project.name}</Typography>
      </Breadcrumbs>

      {/* Project Header */}
      <Paper elevation={1} sx={{ p: 3, mb: 3 }}>
        <Box
          display="flex"
          alignItems="flex-start"
          justifyContent="space-between"
          mb={2}
        >
          <Box display="flex" alignItems="center" gap={2} flex={1}>
            <IconButton onClick={() => navigate('/projects')}>
              <BackIcon />
            </IconButton>

            <Avatar sx={{ bgcolor: 'primary.main', width: 56, height: 56 }}>
              {project.name.charAt(0).toUpperCase()}
            </Avatar>

            <Box flex={1}>
              <Typography variant="h4" component="h1" gutterBottom>
                {project.name}
              </Typography>

              <Stack direction="row" spacing={1} alignItems="center" mb={2}>
                <Chip label={project.status} color={statusColor} size="small" />
                <Chip label={project.type} variant="outlined" size="small" />
                {project.progress_percentage !== undefined && (
                  <Chip
                    label={`${project.progress_percentage}% 완료`}
                    variant="outlined"
                    size="small"
                    color="info"
                  />
                )}
              </Stack>

              <Stack direction="row" spacing={3} color="textSecondary">
                <Typography variant="body2">
                  생성일: {formatDate(project.created_at || project.createdAt || '')}
                </Typography>
                <Typography variant="body2">
                  수정일: {formatDate(project.updated_at || project.updatedAt || '')}
                </Typography>
                {project.episodes_count !== undefined && (
                  <Typography variant="body2">
                    에피소드: {project.episodes_count}개
                  </Typography>
                )}
                {project.scripts_count !== undefined && (
                  <Typography variant="body2">
                    스크립트: {project.scripts_count}개
                  </Typography>
                )}
              </Stack>
            </Box>
          </Box>

          {/* Action Buttons */}
          <Stack direction="row" spacing={1}>
            <Button
              variant="contained"
              startIcon={<GenerateIcon />}
              onClick={handleGenerate}
              color="primary"
            >
              스크립트 생성
            </Button>

            <Button
              variant="outlined"
              startIcon={<EditIcon />}
              onClick={handleEdit}
            >
              편집
            </Button>

            <IconButton onClick={handleArchive}>
              <ArchiveIcon />
            </IconButton>

            <IconButton onClick={handleDelete} color="error">
              <DeleteIcon />
            </IconButton>

            <IconButton>
              <MoreIcon />
            </IconButton>
          </Stack>
        </Box>

        {/* Project Description */}
        {project.description && (
          <>
            <Divider sx={{ mb: 2 }} />
            <Typography variant="body1" color="textSecondary">
              {project.description}
            </Typography>
          </>
        )}
      </Paper>

      {/* Tab Navigation */}
      <Paper elevation={1}>
        <Tabs
          value={currentTab}
          onChange={handleTabChange}
          indicatorColor="primary"
          textColor="primary"
          variant="scrollable"
          scrollButtons="auto"
        >
          <Tab label="개요" />
          <Tab label="에피소드" />
          <Tab label="스크립트" />
          <Tab label="설정" />
        </Tabs>

        {/* Tab Content */}
        <TabPanel value={currentTab} index={0}>
          <ProjectOverview project={project} onRefresh={refetch} />
        </TabPanel>

        <TabPanel value={currentTab} index={1}>
          <ProjectEpisodes project={project} />
        </TabPanel>

        <TabPanel value={currentTab} index={2}>
          <ProjectScripts projectId={project.id} />
        </TabPanel>

        <TabPanel value={currentTab} index={3}>
          <ProjectSettings project={project} onUpdate={refetch} />
        </TabPanel>
      </Paper>
    </Container>
  )
}
