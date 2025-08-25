import React from 'react'
import {
  Box,
  Container,
  Typography,
  Card,
  CardContent,
  Button,
  Stack,
  Avatar,
  Chip,
  LinearProgress,
  IconButton,
  Paper,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  Divider,
  Alert,
} from '@mui/material'
import {
  Add as AddIcon,
  TrendingUp as StatsIcon,
  PlayArrow as GenerateIcon,
  Schedule as TimeIcon,
  Movie as ProjectIcon,
  Description as ScriptIcon,
  Assessment as AnalyticsIcon,
  Refresh as RefreshIcon,
  Launch as LaunchIcon,
  AutoAwesome as AIIcon,
} from '@mui/icons-material'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'

interface DashboardStats {
  totalProjects: number
  activeScripts: number
  totalScripts: number
  totalUsageHours: number
  recentProjects: RecentProject[]
  scriptGenerations: ScriptGeneration[]
  weeklyStats: WeeklyStats
}

interface RecentProject {
  id: string
  name: string
  type: string
  status: string
  progress: number
  lastActivity: string
  episodesCount: number
  scriptsCount: number
}

interface ScriptGeneration {
  id: string
  projectName: string
  episodeTitle: string
  status: 'pending' | 'in_progress' | 'completed' | 'failed'
  progress: number
  startedAt: string
  estimatedCompletion?: string
}

interface WeeklyStats {
  scriptsGenerated: number
  hoursUsed: number
  projectsCreated: number
  completionRate: number
}

const STATUS_COLORS = {
  active: 'success',
  completed: 'primary',
  paused: 'warning',
  archived: 'default',
  pending: 'default',
  in_progress: 'info',
  failed: 'error',
} as const

export default function DashboardPage() {
  const navigate = useNavigate()

  // Load dashboard data
  const {
    data: dashboardData,
    error,
    refetch,
  } = useQuery({
    queryKey: ['dashboard'],
    queryFn: async (): Promise<DashboardStats> => {
      // Mock data - replace with actual API calls
      const mockData: DashboardStats = {
        totalProjects: 12,
        activeScripts: 3,
        totalScripts: 48,
        totalUsageHours: 127.5,
        recentProjects: [
          {
            id: '1',
            name: '로맨틱 코미디 시리즈',
            type: 'comedy',
            status: 'active',
            progress: 75,
            lastActivity: new Date(Date.now() - 3600000).toISOString(),
            episodesCount: 8,
            scriptsCount: 6,
          },
          {
            id: '2',
            name: '액션 드라마',
            type: 'action',
            status: 'active',
            progress: 45,
            lastActivity: new Date(Date.now() - 7200000).toISOString(),
            episodesCount: 12,
            scriptsCount: 5,
          },
          {
            id: '3',
            name: '미스터리 스릴러',
            type: 'drama',
            status: 'paused',
            progress: 30,
            lastActivity: new Date(Date.now() - 86400000).toISOString(),
            episodesCount: 6,
            scriptsCount: 2,
          },
        ],
        scriptGenerations: [
          {
            id: '1',
            projectName: '로맨틱 코미디 시리즈',
            episodeTitle: '첫 만남',
            status: 'in_progress',
            progress: 65,
            startedAt: new Date(Date.now() - 1800000).toISOString(),
            estimatedCompletion: new Date(Date.now() + 900000).toISOString(),
          },
          {
            id: '2',
            projectName: '액션 드라마',
            episodeTitle: '추격전',
            status: 'pending',
            progress: 0,
            startedAt: new Date().toISOString(),
          },
          {
            id: '3',
            projectName: '미스터리 스릴러',
            episodeTitle: '단서 발견',
            status: 'completed',
            progress: 100,
            startedAt: new Date(Date.now() - 3600000).toISOString(),
          },
        ],
        weeklyStats: {
          scriptsGenerated: 8,
          hoursUsed: 24.5,
          projectsCreated: 2,
          completionRate: 87.5,
        },
      }
      return mockData
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  const formatTimeAgo = (timestamp: string) => {
    const now = new Date()
    const time = new Date(timestamp)
    const diffMs = now.getTime() - time.getTime()
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
    const diffDays = Math.floor(diffHours / 24)

    if (diffHours < 1) return '방금 전'
    if (diffHours < 24) return `${diffHours}시간 전`
    return `${diffDays}일 전`
  }

  const getGenerationIcon = (status: ScriptGeneration['status']) => {
    switch (status) {
      case 'completed':
        return <ScriptIcon color="success" />
      case 'in_progress':
        return <AIIcon color="primary" />
      case 'failed':
        return <ScriptIcon color="error" />
      default:
        return <ScriptIcon color="action" />
    }
  }

  const getStatusLabel = (status: string) => {
    const labels = {
      pending: '대기중',
      in_progress: '생성중',
      completed: '완료',
      failed: '실패',
    }
    return labels[status as keyof typeof labels] || status
  }

  if (error) {
    return (
      <Container maxWidth="xl" sx={{ py: 4 }}>
        <Alert severity="error">대시보드를 불러오는데 실패했습니다.</Alert>
      </Container>
    )
  }

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      {/* Header */}
      <Box
        display="flex"
        justifyContent="space-between"
        alignItems="center"
        mb={4}
      >
        <Box>
          <Typography variant="h4" component="h1" gutterBottom>
            대시보드
          </Typography>
          <Typography variant="body1" color="textSecondary">
            프로젝트 현황과 AI 스크립트 생성 상태를 확인하세요
          </Typography>
        </Box>
        <Stack direction="row" spacing={2}>
          <IconButton onClick={() => refetch()}>
            <RefreshIcon />
          </IconButton>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => navigate('/projects/new')}
          >
            새 프로젝트
          </Button>
        </Stack>
      </Box>

      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
        {/* Quick Stats */}
        <Box sx={{ flex: { xs: '1 1 100%', md: '1 1 calc(25% - 18px)' } }}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <Avatar sx={{ bgcolor: 'primary.main', mr: 2 }}>
                  <ProjectIcon />
                </Avatar>
                <Box>
                  <Typography variant="h4" color="primary">
                    {dashboardData?.totalProjects || 0}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    총 프로젝트
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Box>

        <Box sx={{ flex: { xs: '1 1 100%', md: '1 1 calc(25% - 18px)' } }}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <Avatar sx={{ bgcolor: 'success.main', mr: 2 }}>
                  <ScriptIcon />
                </Avatar>
                <Box>
                  <Typography variant="h4" color="success.main">
                    {dashboardData?.totalScripts || 0}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    생성된 스크립트
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Box>

        <Box sx={{ flex: { xs: '1 1 100%', md: '1 1 calc(25% - 18px)' } }}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <Avatar sx={{ bgcolor: 'info.main', mr: 2 }}>
                  <AIIcon />
                </Avatar>
                <Box>
                  <Typography variant="h4" color="info.main">
                    {dashboardData?.activeScripts || 0}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    생성 진행중
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Box>

        <Box sx={{ flex: { xs: '1 1 100%', md: '1 1 calc(25% - 18px)' } }}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <Avatar sx={{ bgcolor: 'warning.main', mr: 2 }}>
                  <TimeIcon />
                </Avatar>
                <Box>
                  <Typography variant="h4" color="warning.main">
                    {dashboardData?.totalUsageHours.toFixed(1) || '0.0'}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    총 사용 시간
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Box>

        {/* Recent Projects */}
        <Box sx={{ flex: { xs: '1 1 100%', md: '1 1 calc(66.667% - 16px)' } }}>
          <Card>
            <CardContent>
              <Box
                display="flex"
                justifyContent="space-between"
                alignItems="center"
                mb={3}
              >
                <Typography variant="h6">최근 프로젝트</Typography>
                <Button
                  size="small"
                  endIcon={<LaunchIcon />}
                  onClick={() => navigate('/projects')}
                >
                  모두 보기
                </Button>
              </Box>

              {dashboardData?.recentProjects.length ? (
                <Stack spacing={2}>
                  {dashboardData.recentProjects.map(project => (
                    <Card
                      key={project.id}
                      variant="outlined"
                      sx={{
                        cursor: 'pointer',
                        '&:hover': { bgcolor: 'grey.50' },
                      }}
                      onClick={() => navigate(`/projects/${project.id}`)}
                    >
                      <CardContent sx={{ py: 2 }}>
                        <Box
                          display="flex"
                          alignItems="center"
                          justifyContent="space-between"
                          mb={2}
                        >
                          <Box display="flex" alignItems="center" gap={2}>
                            <Avatar sx={{ bgcolor: 'primary.main' }}>
                              {project.name.charAt(0)}
                            </Avatar>
                            <Box>
                              <Typography variant="subtitle1">
                                {project.name}
                              </Typography>
                              <Stack direction="row" spacing={1}>
                                <Chip
                                  label={project.status}
                                  size="small"
                                  color={
                                    STATUS_COLORS[
                                      project.status as keyof typeof STATUS_COLORS
                                    ]
                                  }
                                />
                                <Chip
                                  label={project.type}
                                  size="small"
                                  variant="outlined"
                                />
                              </Stack>
                            </Box>
                          </Box>
                          <Box textAlign="right">
                            <Typography variant="body2" color="textSecondary">
                              {formatTimeAgo(project.lastActivity)}
                            </Typography>
                            <Typography variant="body2" color="textSecondary">
                              {project.episodesCount}개 에피소드,{' '}
                              {project.scriptsCount}개 스크립트
                            </Typography>
                          </Box>
                        </Box>

                        <Box>
                          <Box
                            display="flex"
                            justifyContent="space-between"
                            alignItems="center"
                            mb={1}
                          >
                            <Typography variant="body2" color="textSecondary">
                              진행률
                            </Typography>
                            <Typography variant="body2" color="primary">
                              {project.progress}%
                            </Typography>
                          </Box>
                          <LinearProgress
                            variant="determinate"
                            value={project.progress}
                            sx={{ height: 6, borderRadius: 3 }}
                          />
                        </Box>
                      </CardContent>
                    </Card>
                  ))}
                </Stack>
              ) : (
                <Alert severity="info">
                  아직 프로젝트가 없습니다. 새 프로젝트를 시작해보세요.
                </Alert>
              )}
            </CardContent>
          </Card>
        </Box>

        {/* Quick Actions */}
        <Box sx={{ flex: { xs: '1 1 100%', md: '1 1 calc(33.333% - 16px)' } }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                빠른 작업
              </Typography>
              <Stack spacing={2}>
                <Button
                  variant="contained"
                  fullWidth
                  startIcon={<AddIcon />}
                  onClick={() => navigate('/projects/new')}
                >
                  새 프로젝트 생성
                </Button>
                <Button
                  variant="outlined"
                  fullWidth
                  startIcon={<GenerateIcon />}
                  onClick={() => navigate('/generate')}
                >
                  AI 스크립트 생성
                </Button>
                <Button
                  variant="outlined"
                  fullWidth
                  startIcon={<AnalyticsIcon />}
                  onClick={() => navigate('/analytics')}
                >
                  상세 분석 보기
                </Button>
                <Button
                  variant="outlined"
                  fullWidth
                  startIcon={<StatsIcon />}
                  onClick={() => navigate('/system-status')}
                >
                  시스템 상태 확인
                </Button>
              </Stack>
            </CardContent>
          </Card>
        </Box>

        {/* Script Generation Status */}
        <Box sx={{ flex: '1 1 100%' }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                스크립트 생성 현황
              </Typography>

              {dashboardData?.scriptGenerations.length ? (
                <List>
                  {dashboardData.scriptGenerations.map((generation, index) => (
                    <React.Fragment key={generation.id}>
                      <ListItem alignItems="flex-start" sx={{ px: 0 }}>
                        <ListItemAvatar>
                          <Avatar sx={{ width: 40, height: 40 }}>
                            {getGenerationIcon(generation.status)}
                          </Avatar>
                        </ListItemAvatar>
                        <ListItemText
                          primary={
                            <Box
                              display="flex"
                              alignItems="center"
                              justifyContent="space-between"
                            >
                              <Typography variant="subtitle1">
                                {generation.projectName} -{' '}
                                {generation.episodeTitle}
                              </Typography>
                              <Chip
                                label={getStatusLabel(generation.status)}
                                size="small"
                                color={STATUS_COLORS[generation.status]}
                              />
                            </Box>
                          }
                          secondary={
                            <Box mt={1}>
                              {generation.status === 'in_progress' && (
                                <Box mb={1}>
                                  <Box
                                    display="flex"
                                    justifyContent="space-between"
                                    alignItems="center"
                                    mb={0.5}
                                  >
                                    <Typography
                                      variant="body2"
                                      color="textSecondary"
                                    >
                                      진행률
                                    </Typography>
                                    <Typography variant="body2" color="primary">
                                      {generation.progress}%
                                    </Typography>
                                  </Box>
                                  <LinearProgress
                                    variant="determinate"
                                    value={generation.progress}
                                    sx={{ height: 4 }}
                                  />
                                </Box>
                              )}
                              <Stack
                                direction="row"
                                spacing={2}
                                alignItems="center"
                              >
                                <Typography
                                  variant="caption"
                                  color="textSecondary"
                                >
                                  시작: {formatTimeAgo(generation.startedAt)}
                                </Typography>
                                {generation.estimatedCompletion && (
                                  <Typography
                                    variant="caption"
                                    color="textSecondary"
                                  >
                                    예상 완료:{' '}
                                    {formatTimeAgo(
                                      generation.estimatedCompletion,
                                    )}
                                  </Typography>
                                )}
                              </Stack>
                            </Box>
                          }
                        />
                      </ListItem>
                      {index < dashboardData.scriptGenerations.length - 1 && (
                        <Divider />
                      )}
                    </React.Fragment>
                  ))}
                </List>
              ) : (
                <Alert severity="info">
                  현재 생성 중인 스크립트가 없습니다.
                </Alert>
              )}
            </CardContent>
          </Card>
        </Box>

        {/* Weekly Statistics */}
        <Box sx={{ flex: '1 1 100%' }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                이번 주 통계
              </Typography>

              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
                <Box
                  sx={{
                    flex: {
                      xs: '1 1 100%',
                      sm: '1 1 calc(50% - 12px)',
                      md: '1 1 calc(25% - 18px)',
                    },
                  }}
                >
                  <Paper variant="outlined" sx={{ p: 2, textAlign: 'center' }}>
                    <Typography variant="h3" color="primary" gutterBottom>
                      {dashboardData?.weeklyStats.scriptsGenerated || 0}
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      생성된 스크립트
                    </Typography>
                  </Paper>
                </Box>
                <Box
                  sx={{
                    flex: {
                      xs: '1 1 100%',
                      sm: '1 1 calc(50% - 12px)',
                      md: '1 1 calc(25% - 18px)',
                    },
                  }}
                >
                  <Paper variant="outlined" sx={{ p: 2, textAlign: 'center' }}>
                    <Typography variant="h3" color="success.main" gutterBottom>
                      {dashboardData?.weeklyStats.hoursUsed.toFixed(1) || '0.0'}
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      사용 시간
                    </Typography>
                  </Paper>
                </Box>
                <Box
                  sx={{
                    flex: {
                      xs: '1 1 100%',
                      sm: '1 1 calc(50% - 12px)',
                      md: '1 1 calc(25% - 18px)',
                    },
                  }}
                >
                  <Paper variant="outlined" sx={{ p: 2, textAlign: 'center' }}>
                    <Typography variant="h3" color="info.main" gutterBottom>
                      {dashboardData?.weeklyStats.projectsCreated || 0}
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      새 프로젝트
                    </Typography>
                  </Paper>
                </Box>
                <Box
                  sx={{
                    flex: {
                      xs: '1 1 100%',
                      sm: '1 1 calc(50% - 12px)',
                      md: '1 1 calc(25% - 18px)',
                    },
                  }}
                >
                  <Paper variant="outlined" sx={{ p: 2, textAlign: 'center' }}>
                    <Typography variant="h3" color="warning.main" gutterBottom>
                      {dashboardData?.weeklyStats.completionRate.toFixed(1) ||
                        '0.0'}
                      %
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      완료율
                    </Typography>
                  </Paper>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Box>
      </Box>
    </Container>
  )
}
