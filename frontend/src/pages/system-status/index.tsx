import React from 'react'
import {
  Box,
  Container,
  Typography,
  Card,
  CardContent,
  Chip,
  LinearProgress,
  Stack,
  Avatar,
  IconButton,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider,
} from '@mui/material'
import {
  Warning as WarningIcon,
  Error as ErrorIcon,
  Refresh as RefreshIcon,
  Storage as DatabaseIcon,
  Cloud as APIIcon,
  Speed as PerformanceIcon,
  Memory as MemoryIcon,
  Computer as ServerIcon,
  NetworkCheck as NetworkIcon,
  CheckCircle,
  Warning,
} from '@mui/icons-material'
import { useQuery } from '@tanstack/react-query'

interface ServiceStatus {
  name: string
  status: 'healthy' | 'warning' | 'error'
  responseTime: number
  uptime: number
  lastCheck: string
  message?: string
}

interface SystemMetrics {
  cpu: number
  memory: number
  disk: number
  network: number
}

interface APIEndpoint {
  endpoint: string
  method: string
  status: 'healthy' | 'warning' | 'error'
  responseTime: number
  lastCheck: string
  errorCount: number
}

interface SystemStatusData {
  services: ServiceStatus[]
  metrics: SystemMetrics
  apiEndpoints: APIEndpoint[]
  alerts: SystemAlert[]
  overallHealth: 'healthy' | 'warning' | 'error'
}

interface SystemAlert {
  id: string
  severity: 'info' | 'warning' | 'error'
  title: string
  message: string
  timestamp: string
}

const STATUS_COLORS = {
  healthy: 'success',
  warning: 'warning',
  error: 'error',
} as const

const STATUS_ICONS = {
  healthy: CheckCircle,
  warning: Warning,
  error: Error,
}

export default function SystemStatusPage() {
  // Load system status
  const {
    data: systemStatus,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['system-status'],
    queryFn: async (): Promise<SystemStatusData> => {
      try {
        // Mock data - replace with actual API calls
        const mockData: SystemStatusData = {
          services: [
            {
              name: 'Project Service',
              status: 'healthy',
              responseTime: 45,
              uptime: 99.9,
              lastCheck: new Date().toISOString(),
              message: '정상 작동 중',
            },
            {
              name: 'Script Generation API',
              status: 'warning',
              responseTime: 1250,
              uptime: 97.5,
              lastCheck: new Date().toISOString(),
              message: '응답 시간이 느림',
            },
            {
              name: 'Database',
              status: 'healthy',
              responseTime: 12,
              uptime: 100,
              lastCheck: new Date().toISOString(),
              message: '최적 상태',
            },
            {
              name: 'File Storage',
              status: 'healthy',
              responseTime: 89,
              uptime: 99.8,
              lastCheck: new Date().toISOString(),
              message: '정상 작동 중',
            },
            {
              name: 'Authentication',
              status: 'error',
              responseTime: 0,
              uptime: 85.2,
              lastCheck: new Date(Date.now() - 300000).toISOString(),
              message: '서비스 응답 없음',
            },
          ],
          metrics: {
            cpu: 45.2,
            memory: 67.8,
            disk: 34.1,
            network: 23.5,
          },
          apiEndpoints: [
            {
              endpoint: '/api/projects',
              method: 'GET',
              status: 'healthy',
              responseTime: 89,
              lastCheck: new Date().toISOString(),
              errorCount: 0,
            },
            {
              endpoint: '/api/scripts/generate',
              method: 'POST',
              status: 'warning',
              responseTime: 2340,
              lastCheck: new Date().toISOString(),
              errorCount: 3,
            },
            {
              endpoint: '/api/episodes',
              method: 'GET',
              status: 'healthy',
              responseTime: 156,
              lastCheck: new Date().toISOString(),
              errorCount: 0,
            },
            {
              endpoint: '/api/auth/login',
              method: 'POST',
              status: 'error',
              responseTime: 0,
              lastCheck: new Date(Date.now() - 180000).toISOString(),
              errorCount: 12,
            },
          ],
          alerts: [
            {
              id: '1',
              severity: 'error',
              title: '인증 서비스 장애',
              message:
                '인증 서비스가 응답하지 않습니다. 시스템 관리자에게 문의하세요.',
              timestamp: new Date(Date.now() - 300000).toISOString(),
            },
            {
              id: '2',
              severity: 'warning',
              title: 'AI 생성 응답 지연',
              message:
                'AI 스크립트 생성 서비스의 응답 시간이 평소보다 느립니다.',
              timestamp: new Date(Date.now() - 900000).toISOString(),
            },
            {
              id: '3',
              severity: 'info',
              title: '정기 백업 완료',
              message:
                '오늘 새벽 데이터베이스 백업이 성공적으로 완료되었습니다.',
              timestamp: new Date(Date.now() - 18000000).toISOString(),
            },
          ],
          overallHealth: 'warning',
        }
        return mockData
      } catch (err) {
        throw new Error('시스템 상태를 불러올 수 없습니다')
      }
    },
    refetchInterval: 10000, // Refresh every 10 seconds
  })

  const getStatusIcon = (status: 'healthy' | 'warning' | 'error') => {
    const IconComponent = STATUS_ICONS[status] as React.ElementType
    return <IconComponent color={STATUS_COLORS[status]} />
  }

  const getHealthColor = (status: string) => {
    return STATUS_COLORS[status as keyof typeof STATUS_COLORS] || 'default'
  }

  const formatUptime = (uptime: number) => {
    return `${uptime.toFixed(1)}%`
  }

  const formatResponseTime = (time: number) => {
    if (time === 0) return 'N/A'
    return `${time}ms`
  }

  const formatTimeAgo = (timestamp: string) => {
    const now = new Date()
    const time = new Date(timestamp)
    const diffMs = now.getTime() - time.getTime()
    const diffMinutes = Math.floor(diffMs / (1000 * 60))
    const diffHours = Math.floor(diffMinutes / 60)

    if (diffMinutes < 1) return '방금 전'
    if (diffMinutes < 60) return `${diffMinutes}분 전`
    if (diffHours < 24) return `${diffHours}시간 전`
    return time.toLocaleDateString('ko-KR')
  }

  const getMetricColor = (
    value: number,
    thresholds = { warning: 70, error: 90 },
  ) => {
    if (value >= thresholds.error) return 'error'
    if (value >= thresholds.warning) return 'warning'
    return 'success'
  }

  if (error) {
    return (
      <Container maxWidth="xl" sx={{ py: 4 }}>
        <Alert severity="error">시스템 상태를 불러오는데 실패했습니다.</Alert>
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
            시스템 상태
          </Typography>
          <Stack direction="row" spacing={2} alignItems="center">
            <Typography variant="body1" color="textSecondary">
              실시간 시스템 모니터링 및 서비스 상태
            </Typography>
            {systemStatus && (
              <Chip
                label={`전체 상태: ${systemStatus.overallHealth === 'healthy' ? '정상' : systemStatus.overallHealth === 'warning' ? '주의' : '장애'}`}
                color={getHealthColor(systemStatus.overallHealth)}
                icon={getStatusIcon(systemStatus.overallHealth)}
              />
            )}
          </Stack>
        </Box>
        <IconButton onClick={() => refetch()} disabled={isLoading}>
          <RefreshIcon />
        </IconButton>
      </Box>

      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
        {/* Service Status Overview */}
        <Box sx={{ flex: '1 1 100%' }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                서비스 상태
              </Typography>

              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
                {systemStatus?.services.map(service => (
                  <Box
                    key={service.name}
                    sx={{
                      flex: {
                        xs: '1 1 100%',
                        sm: '1 1 calc(50% - 8px)',
                        md: '1 1 calc(33.333% - 16px)',
                        lg: '1 1 calc(20% - 16px)',
                      },
                    }}
                  >
                    <Card variant="outlined">
                      <CardContent sx={{ textAlign: 'center', py: 2 }}>
                        <Avatar
                          sx={{
                            bgcolor: `${getHealthColor(service.status)}.light`,
                            mx: 'auto',
                            mb: 1,
                          }}
                        >
                          {getStatusIcon(service.status)}
                        </Avatar>
                        <Typography variant="subtitle2" gutterBottom>
                          {service.name}
                        </Typography>
                        <Chip
                          label={
                            service.status === 'healthy'
                              ? '정상'
                              : service.status === 'warning'
                                ? '주의'
                                : '장애'
                          }
                          size="small"
                          color={getHealthColor(service.status)}
                        />
                        <Typography
                          variant="caption"
                          display="block"
                          color="textSecondary"
                          mt={1}
                        >
                          응답시간: {formatResponseTime(service.responseTime)}
                        </Typography>
                        <Typography
                          variant="caption"
                          display="block"
                          color="textSecondary"
                        >
                          가동률: {formatUptime(service.uptime)}
                        </Typography>
                      </CardContent>
                    </Card>
                  </Box>
                ))}
              </Box>
            </CardContent>
          </Card>
        </Box>

        {/* System Metrics */}
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
                <PerformanceIcon color="primary" />
                시스템 메트릭스
              </Typography>

              {systemStatus?.metrics && (
                <Stack spacing={3}>
                  <Box>
                    <Box
                      display="flex"
                      justifyContent="space-between"
                      alignItems="center"
                      mb={1}
                    >
                      <Typography
                        variant="body2"
                        display="flex"
                        alignItems="center"
                        gap={1}
                      >
                        <ServerIcon fontSize="small" />
                        CPU 사용률
                      </Typography>
                      <Typography
                        variant="body2"
                        color={`${getMetricColor(systemStatus.metrics.cpu)}.main`}
                      >
                        {systemStatus.metrics.cpu.toFixed(1)}%
                      </Typography>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={systemStatus.metrics.cpu}
                      color={getMetricColor(systemStatus.metrics.cpu)}
                      sx={{ height: 8, borderRadius: 4 }}
                    />
                  </Box>

                  <Box>
                    <Box
                      display="flex"
                      justifyContent="space-between"
                      alignItems="center"
                      mb={1}
                    >
                      <Typography
                        variant="body2"
                        display="flex"
                        alignItems="center"
                        gap={1}
                      >
                        <MemoryIcon fontSize="small" />
                        메모리 사용률
                      </Typography>
                      <Typography
                        variant="body2"
                        color={`${getMetricColor(systemStatus.metrics.memory)}.main`}
                      >
                        {systemStatus.metrics.memory.toFixed(1)}%
                      </Typography>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={systemStatus.metrics.memory}
                      color={getMetricColor(systemStatus.metrics.memory)}
                      sx={{ height: 8, borderRadius: 4 }}
                    />
                  </Box>

                  <Box>
                    <Box
                      display="flex"
                      justifyContent="space-between"
                      alignItems="center"
                      mb={1}
                    >
                      <Typography
                        variant="body2"
                        display="flex"
                        alignItems="center"
                        gap={1}
                      >
                        <DatabaseIcon fontSize="small" />
                        디스크 사용률
                      </Typography>
                      <Typography
                        variant="body2"
                        color={`${getMetricColor(systemStatus.metrics.disk, { warning: 80, error: 95 })}.main`}
                      >
                        {systemStatus.metrics.disk.toFixed(1)}%
                      </Typography>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={systemStatus.metrics.disk}
                      color={getMetricColor(systemStatus.metrics.disk, {
                        warning: 80,
                        error: 95,
                      })}
                      sx={{ height: 8, borderRadius: 4 }}
                    />
                  </Box>

                  <Box>
                    <Box
                      display="flex"
                      justifyContent="space-between"
                      alignItems="center"
                      mb={1}
                    >
                      <Typography
                        variant="body2"
                        display="flex"
                        alignItems="center"
                        gap={1}
                      >
                        <NetworkIcon fontSize="small" />
                        네트워크 사용률
                      </Typography>
                      <Typography
                        variant="body2"
                        color={`${getMetricColor(systemStatus.metrics.network, { warning: 80, error: 95 })}.main`}
                      >
                        {systemStatus.metrics.network.toFixed(1)}%
                      </Typography>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={systemStatus.metrics.network}
                      color={getMetricColor(systemStatus.metrics.network, {
                        warning: 80,
                        error: 95,
                      })}
                      sx={{ height: 8, borderRadius: 4 }}
                    />
                  </Box>
                </Stack>
              )}
            </CardContent>
          </Card>
        </Box>

        {/* API Endpoints */}
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
                <APIIcon color="primary" />
                API 엔드포인트 상태
              </Typography>

              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>엔드포인트</TableCell>
                      <TableCell>상태</TableCell>
                      <TableCell>응답시간</TableCell>
                      <TableCell>오류수</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {systemStatus?.apiEndpoints.map(endpoint => (
                      <TableRow key={endpoint.endpoint}>
                        <TableCell>
                          <Typography variant="body2" component="code">
                            {endpoint.method} {endpoint.endpoint}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Chip
                            size="small"
                            label={
                              endpoint.status === 'healthy'
                                ? '정상'
                                : endpoint.status === 'warning'
                                  ? '주의'
                                  : '장애'
                            }
                            color={getHealthColor(endpoint.status)}
                            icon={getStatusIcon(endpoint.status)}
                          />
                        </TableCell>
                        <TableCell>
                          <Typography
                            variant="body2"
                            color={
                              endpoint.responseTime > 1000
                                ? 'error.main'
                                : endpoint.responseTime > 500
                                  ? 'warning.main'
                                  : 'success.main'
                            }
                          >
                            {formatResponseTime(endpoint.responseTime)}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography
                            variant="body2"
                            color={
                              endpoint.errorCount > 0
                                ? 'error.main'
                                : 'textSecondary'
                            }
                          >
                            {endpoint.errorCount}
                          </Typography>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Box>

        {/* System Alerts */}
        <Box sx={{ flex: '1 1 100%' }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                시스템 알림
              </Typography>

              {systemStatus?.alerts.length ? (
                <List>
                  {systemStatus.alerts.map((alert, index) => (
                    <React.Fragment key={alert.id}>
                      <ListItem alignItems="flex-start" sx={{ px: 0 }}>
                        <ListItemIcon>
                          {alert.severity === 'error' ? (
                            <ErrorIcon color="error" />
                          ) : alert.severity === 'warning' ? (
                            <WarningIcon color="warning" />
                          ) : (
                            <CheckCircle color="info" />
                          )}
                        </ListItemIcon>
                        <ListItemText
                          primary={
                            <Box
                              display="flex"
                              alignItems="center"
                              justifyContent="space-between"
                            >
                              <Typography variant="subtitle2">
                                {alert.title}
                              </Typography>
                              <Typography
                                variant="caption"
                                color="textSecondary"
                              >
                                {formatTimeAgo(alert.timestamp)}
                              </Typography>
                            </Box>
                          }
                          secondary={
                            <Typography variant="body2" color="textSecondary">
                              {alert.message}
                            </Typography>
                          }
                        />
                      </ListItem>
                      {index < systemStatus.alerts.length - 1 && <Divider />}
                    </React.Fragment>
                  ))}
                </List>
              ) : (
                <Alert severity="info">현재 알림이 없습니다.</Alert>
              )}
            </CardContent>
          </Card>
        </Box>
      </Box>
    </Container>
  )
}
