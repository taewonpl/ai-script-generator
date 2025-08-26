import React from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  LinearProgress,
  Stack,
  Chip,
  Button,
  Avatar,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  Divider,
  Alert,
} from '@mui/material'
import {
  TrendingUp as TrendingIcon,
  Schedule as ScheduleIcon,
  Movie as EpisodeIcon,
  Description as ScriptIcon,
  People as TeamIcon,
  CalendarToday as CalendarIcon,
  Assessment as StatsIcon,
} from '@mui/icons-material'
import { useQuery } from '@tanstack/react-query'
import type { Project } from '@/shared/types/project'

interface ProjectOverviewProps {
  project: Project
  onRefresh: () => void
}

interface ProjectStats {
  totalEpisodes: number
  completedEpisodes: number
  totalScripts: number
  recentActivity: ActivityItem[]
  upcomingMilestones: Milestone[]
  teamMembers: TeamMember[]
}

interface ActivityItem {
  id: string
  type: 'episode_created' | 'script_generated' | 'project_updated'
  description: string
  timestamp: string
  user: string
}

interface Milestone {
  id: string
  title: string
  dueDate: string
  progress: number
  status: 'pending' | 'in_progress' | 'completed'
}

interface TeamMember {
  id: string
  name: string
  role: string
  avatar?: string
  lastActive: string
}

export function ProjectOverview({ project }: ProjectOverviewProps) {
  // Load project statistics
  const { data: stats } = useQuery({
    queryKey: ['project-stats', project.id],
    queryFn: async () => {
      // Mock data - replace with actual API call
      const mockStats: ProjectStats = {
        totalEpisodes: project.episodes_count || 0,
        completedEpisodes: Math.floor((project.episodes_count || 0) * 0.6),
        totalScripts: project.scripts_count || 0,
        recentActivity: [
          {
            id: '1',
            type: 'script_generated',
            description: 'AI 스크립트가 생성되었습니다 - Episode 3',
            timestamp: new Date().toISOString(),
            user: 'AI 시스템',
          },
          {
            id: '2',
            type: 'episode_created',
            description: '새 에피소드가 생성되었습니다 - Episode 4',
            timestamp: new Date(Date.now() - 86400000).toISOString(),
            user: '김작가',
          },
          {
            id: '3',
            type: 'project_updated',
            description: '프로젝트 설정이 업데이트되었습니다',
            timestamp: new Date(Date.now() - 172800000).toISOString(),
            user: '이감독',
          },
        ],
        upcomingMilestones: [
          {
            id: '1',
            title: '1차 스크립트 검토',
            dueDate: new Date(Date.now() + 604800000).toISOString(),
            progress: 60,
            status: 'in_progress',
          },
          {
            id: '2',
            title: '전체 에피소드 완성',
            dueDate: new Date(Date.now() + 2592000000).toISOString(),
            progress: 30,
            status: 'pending',
          },
        ],
        teamMembers: [
          {
            id: '1',
            name: '김작가',
            role: '메인 작가',
            lastActive: new Date(Date.now() - 3600000).toISOString(),
          },
          {
            id: '2',
            name: '이감독',
            role: '연출',
            lastActive: new Date(Date.now() - 7200000).toISOString(),
          },
        ],
      }
      return mockStats
    },
  })

  const getActivityIcon = (type: ActivityItem['type']) => {
    switch (type) {
      case 'episode_created':
        return <EpisodeIcon color="primary" />
      case 'script_generated':
        return <ScriptIcon color="success" />
      case 'project_updated':
        return <StatsIcon color="info" />
      default:
        return <StatsIcon />
    }
  }

  const formatTimeAgo = (timestamp: string) => {
    const now = new Date()
    const time = new Date(timestamp)
    const diffMs = now.getTime() - time.getTime()
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
    const diffDays = Math.floor(diffHours / 24)

    if (diffHours < 1) return '방금 전'
    if (diffHours < 24) return `${diffHours}시간 전`
    if (diffDays < 7) return `${diffDays}일 전`
    return time.toLocaleDateString('ko-KR')
  }

  const formatDueDate = (dueDate: string) => {
    const date = new Date(dueDate)
    const now = new Date()
    const diffMs = date.getTime() - now.getTime()
    const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24))

    if (diffDays < 0) return '기한 초과'
    if (diffDays === 0) return '오늘'
    if (diffDays === 1) return '내일'
    if (diffDays < 7) return `${diffDays}일 후`
    return date.toLocaleDateString('ko-KR')
  }

  const getMilestoneColor = (status: Milestone['status']) => {
    switch (status) {
      case 'completed':
        return 'success'
      case 'in_progress':
        return 'primary'
      case 'pending':
        return 'default'
      default:
        return 'default'
    }
  }

  const progressPercentage = project.progress_percentage || 0

  return (
    <Box>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
        {/* Progress Overview */}
        <Box sx={{ flex: { xs: '1 1 100%', md: '1 1 calc(66.667% - 16px)' } }}>
          <Card>
            <CardContent>
              <Typography
                variant="h6"
                gutterBottom
                display="flex"
                alignItems="center"
                gap={1}
              >
                <TrendingIcon color="primary" />
                프로젝트 진행현황
              </Typography>

              <Box mb={2}>
                <Box
                  display="flex"
                  justifyContent="space-between"
                  alignItems="center"
                  mb={1}
                >
                  <Typography variant="body2" color="textSecondary">
                    전체 진행률
                  </Typography>
                  <Typography variant="h6" color="primary">
                    {progressPercentage}%
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={progressPercentage}
                  sx={{ height: 8, borderRadius: 4 }}
                />
              </Box>

              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
                <Box
                  sx={{
                    flex: {
                      xs: '1 1 calc(50% - 8px)',
                      sm: '1 1 calc(25% - 12px)',
                    },
                  }}
                >
                  <Box textAlign="center">
                    <Typography variant="h4" color="primary">
                      {stats?.totalEpisodes || 0}
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      총 에피소드
                    </Typography>
                  </Box>
                </Box>
                <Box
                  sx={{
                    flex: {
                      xs: '1 1 calc(50% - 8px)',
                      sm: '1 1 calc(25% - 12px)',
                    },
                  }}
                >
                  <Box textAlign="center">
                    <Typography variant="h4" color="success.main">
                      {stats?.completedEpisodes || 0}
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      완료된 에피소드
                    </Typography>
                  </Box>
                </Box>
                <Box
                  sx={{
                    flex: {
                      xs: '1 1 calc(50% - 8px)',
                      sm: '1 1 calc(25% - 12px)',
                    },
                  }}
                >
                  <Box textAlign="center">
                    <Typography variant="h4" color="info.main">
                      {stats?.totalScripts || 0}
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      생성된 스크립트
                    </Typography>
                  </Box>
                </Box>
                <Box
                  sx={{
                    flex: {
                      xs: '1 1 calc(50% - 8px)',
                      sm: '1 1 calc(25% - 12px)',
                    },
                  }}
                >
                  <Box textAlign="center">
                    <Typography variant="h4" color="warning.main">
                      {Math.max(
                        0,
                        (stats?.totalEpisodes || 0) -
                          (stats?.completedEpisodes || 0),
                      )}
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      남은 에피소드
                    </Typography>
                  </Box>
                </Box>
              </Box>
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
                  startIcon={<ScriptIcon />}
                  onClick={() => {
                    /* Navigate to script generation */
                  }}
                >
                  새 스크립트 생성
                </Button>
                <Button
                  variant="outlined"
                  fullWidth
                  startIcon={<EpisodeIcon />}
                  onClick={() => {
                    /* Navigate to episode creation */
                  }}
                >
                  새 에피소드 추가
                </Button>
                <Button
                  variant="outlined"
                  fullWidth
                  startIcon={<StatsIcon />}
                  onClick={() => {
                    /* Navigate to analytics */
                  }}
                >
                  상세 분석 보기
                </Button>
              </Stack>
            </CardContent>
          </Card>
        </Box>

        {/* Recent Activity */}
        <Box sx={{ flex: { xs: '1 1 100%', md: '1 1 calc(50% - 8px)' } }}>
          <Card>
            <CardContent>
              <Typography
                variant="h6"
                gutterBottom
                display="flex"
                alignItems="center"
                gap={1}
              >
                <ScheduleIcon color="primary" />
                최근 활동
              </Typography>

              {stats?.recentActivity.length ? (
                <List dense>
                  {stats.recentActivity.map((activity, index) => (
                    <React.Fragment key={activity.id}>
                      <ListItem alignItems="flex-start" sx={{ px: 0 }}>
                        <ListItemAvatar>
                          <Avatar sx={{ width: 32, height: 32 }}>
                            {getActivityIcon(activity.type)}
                          </Avatar>
                        </ListItemAvatar>
                        <ListItemText
                          primary={activity.description}
                          secondary={
                            <Stack
                              direction="row"
                              spacing={1}
                              alignItems="center"
                            >
                              <Typography
                                variant="caption"
                                color="textSecondary"
                              >
                                {activity.user}
                              </Typography>
                              <Typography
                                variant="caption"
                                color="textSecondary"
                              >
                                •
                              </Typography>
                              <Typography
                                variant="caption"
                                color="textSecondary"
                              >
                                {formatTimeAgo(activity.timestamp)}
                              </Typography>
                            </Stack>
                          }
                        />
                      </ListItem>
                      {index < stats.recentActivity.length - 1 && (
                        <Divider variant="inset" />
                      )}
                    </React.Fragment>
                  ))}
                </List>
              ) : (
                <Alert severity="info">아직 활동이 없습니다.</Alert>
              )}
            </CardContent>
          </Card>
        </Box>

        {/* Upcoming Milestones */}
        <Box sx={{ flex: { xs: '1 1 100%', md: '1 1 calc(50% - 8px)' } }}>
          <Card>
            <CardContent>
              <Typography
                variant="h6"
                gutterBottom
                display="flex"
                alignItems="center"
                gap={1}
              >
                <CalendarIcon color="primary" />
                예정된 마일스톤
              </Typography>

              {stats?.upcomingMilestones.length ? (
                <List dense>
                  {stats.upcomingMilestones.map((milestone, index) => (
                    <React.Fragment key={milestone.id}>
                      <ListItem alignItems="flex-start" sx={{ px: 0 }}>
                        <ListItemText
                          primary={
                            <Box
                              display="flex"
                              alignItems="center"
                              justifyContent="space-between"
                              mb={1}
                            >
                              <Typography variant="subtitle2">
                                {milestone.title}
                              </Typography>
                              <Chip
                                label={formatDueDate(milestone.dueDate)}
                                size="small"
                                color={
                                  getMilestoneColor(milestone.status) as
                                    | 'default'
                                    | 'primary'
                                    | 'secondary'
                                    | 'error'
                                    | 'info'
                                    | 'success'
                                    | 'warning'
                                }
                                variant="outlined"
                              />
                            </Box>
                          }
                          secondary={
                            <Box>
                              <LinearProgress
                                variant="determinate"
                                value={milestone.progress}
                                sx={{ mb: 1 }}
                              />
                              <Typography
                                variant="caption"
                                color="textSecondary"
                              >
                                {milestone.progress}% 완료
                              </Typography>
                            </Box>
                          }
                        />
                      </ListItem>
                      {index < stats.upcomingMilestones.length - 1 && (
                        <Divider />
                      )}
                    </React.Fragment>
                  ))}
                </List>
              ) : (
                <Alert severity="info">예정된 마일스톤이 없습니다.</Alert>
              )}
            </CardContent>
          </Card>
        </Box>

        {/* Team Members */}
        <Box sx={{ flex: '1 1 100%' }}>
          <Card>
            <CardContent>
              <Typography
                variant="h6"
                gutterBottom
                display="flex"
                alignItems="center"
                gap={1}
              >
                <TeamIcon color="primary" />팀 멤버
              </Typography>

              {stats?.teamMembers.length ? (
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
                  {stats.teamMembers.map(member => (
                    <Box
                      key={member.id}
                      sx={{
                        flex: {
                          xs: '1 1 100%',
                          sm: '1 1 calc(50% - 8px)',
                          md: '1 1 calc(33.333% - 16px)',
                        },
                      }}
                    >
                      <Card variant="outlined">
                        <CardContent sx={{ pb: '16px !important' }}>
                          <Box display="flex" alignItems="center" gap={2}>
                            <Avatar>{member.name.charAt(0)}</Avatar>
                            <Box flex={1}>
                              <Typography variant="subtitle2">
                                {member.name}
                              </Typography>
                              <Typography variant="body2" color="textSecondary">
                                {member.role}
                              </Typography>
                              <Typography
                                variant="caption"
                                color="textSecondary"
                              >
                                마지막 활동: {formatTimeAgo(member.lastActive)}
                              </Typography>
                            </Box>
                          </Box>
                        </CardContent>
                      </Card>
                    </Box>
                  ))}
                </Box>
              ) : (
                <Alert severity="info">팀 멤버 정보가 없습니다.</Alert>
              )}
            </CardContent>
          </Card>
        </Box>
      </Box>
    </Box>
  )
}
