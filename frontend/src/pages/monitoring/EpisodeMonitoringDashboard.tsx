/**
 * Episode numbering system monitoring dashboard
 */

import React, { useState, useEffect } from 'react'
import type { Alert } from '@mui/material'
import {
  Box,
  Card,
  CardContent,
  CardHeader,
  Typography,
  Button,
  LinearProgress,
  Switch,
  FormControlLabel,
  TextField,
  Tabs,
  Tab,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemSecondaryAction,
} from '@mui/material'
import {
  Refresh,
  Warning,
  Error,
  CheckCircle,
  BugReport,
  Speed,
  Notifications,
  PlayArrow,
  Build,
  Analytics,
} from '@mui/icons-material'

interface IntegritySummary {
  total_projects: number
  healthy_projects: number
  unhealthy_projects: number
  health_percentage: number
  total_episodes: number
  total_gaps: number
  total_duplicates: number
  check_timestamp: string
  projects_with_issues: Array<{
    project_id: string
    gaps: number
    duplicates: number
  }>
}

interface PerformanceStats {
  active_operations: number
  average_duration_seconds: number
  p95_duration_seconds: number
  p99_duration_seconds: number
  success_rate_percentage: number
  conflict_rate_percentage: number
  total_operations_today: number
  failed_operations_today: number
}

interface Alert {
  alert_id: string
  title: string
  description: string
  severity: 'info' | 'warning' | 'critical'
  timestamp: string
  project_id?: string
  resolved: boolean
}

export const EpisodeMonitoringDashboard: React.FC = () => {
  const [currentTab, setCurrentTab] = useState(0)
  const [integritySummary, setIntegritySummary] =
    useState<IntegritySummary | null>(null)
  const [performanceStats, setPerformanceStats] =
    useState<PerformanceStats | null>(null)
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [loading, setLoading] = useState(true)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [refreshInterval, setRefreshInterval] = useState(30)

  // Fetch monitoring data
  const fetchMonitoringData = async () => {
    try {
      setLoading(true)

      // Fetch integrity summary
      const integrityResponse = await fetch(
        '/api/monitoring/episodes/integrity/summary',
      )
      const integrityData = await integrityResponse.json()
      setIntegritySummary(integrityData.data)

      // Fetch performance stats
      const performanceResponse = await fetch(
        '/api/monitoring/episodes/performance/stats',
      )
      const performanceData = await performanceResponse.json()
      setPerformanceStats(performanceData.data)

      // Fetch active alerts
      const alertsResponse = await fetch(
        '/api/monitoring/episodes/alerts/active',
      )
      const alertsData = await alertsResponse.json()
      setAlerts(alertsData.data.active_alerts || [])
    } catch (error) {
      console.error('Failed to fetch monitoring data:', error)
    } finally {
      setLoading(false)
    }
  }

  // Auto refresh effect
  useEffect(() => {
    fetchMonitoringData()

    if (autoRefresh) {
      const interval = setInterval(fetchMonitoringData, refreshInterval * 1000)
      return () => clearInterval(interval)
    }
    
    return () => {} // cleanup function for when autoRefresh is false
  }, [autoRefresh, refreshInterval])

  const handleRefresh = () => {
    fetchMonitoringData()
  }

  const runIntegrityCheck = async (deepCheck = false) => {
    try {
      await fetch(
        `/api/monitoring/episodes/jobs/integrity/run-check?deep_check=${deepCheck}`,
        {
          method: 'POST',
        },
      )
      // Refresh data after check
      setTimeout(fetchMonitoringData, 2000)
    } catch (error) {
      console.error('Failed to run integrity check:', error)
    }
  }

  const resolveAlert = async (alertKey: string) => {
    try {
      await fetch(`/api/monitoring/episodes/alerts/${alertKey}/resolve`, {
        method: 'POST',
      })
      fetchMonitoringData()
    } catch (error) {
      console.error('Failed to resolve alert:', error)
    }
  }

  const getHealthColor = (percentage: number) => {
    if (percentage >= 98) return 'success'
    if (percentage >= 95) return 'warning'
    return 'error'
  }


  // Overview Tab
  const renderOverview = () => (
    <Box>
      {/* Header Controls */}
      <Box
        display="flex"
        justifyContent="space-between"
        alignItems="center"
        mb={3}
      >
        <Typography variant="h4">Episode Monitoring Dashboard</Typography>
        <Box display="flex" gap={2}>
          <FormControlLabel
            control={
              <Switch
                checked={autoRefresh}
                onChange={e => setAutoRefresh(e.target.checked)}
              />
            }
            label="Auto Refresh"
          />
          <TextField
            label="Interval (s)"
            type="number"
            size="small"
            value={refreshInterval}
            onChange={e => setRefreshInterval(Number(e.target.value))}
            sx={{ width: 100 }}
          />
          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={handleRefresh}
            disabled={loading}
          >
            Refresh
          </Button>
        </Box>
      </Box>

      {loading && <LinearProgress sx={{ mb: 2 }} />}

      {/* Key Metrics */}
      <Box display="flex" flexWrap="wrap" gap={3} sx={{ mb: 4 }}>
        {/* Integrity Health */}
        <Box flex="1 1 300px" minWidth="300px">
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" gap={1}>
                <CheckCircle
                  color={getHealthColor(
                    integritySummary?.health_percentage || 0,
                  )}
                />
                <Typography variant="h6">Integrity Health</Typography>
              </Box>
              <Typography
                variant="h4"
                color={getHealthColor(integritySummary?.health_percentage || 0)}
              >
                {integritySummary?.health_percentage?.toFixed(1) || 0}%
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {integritySummary?.healthy_projects || 0}/
                {integritySummary?.total_projects || 0} projects healthy
              </Typography>
            </CardContent>
          </Card>
        </Box>

        {/* Performance */}
        <Box flex="1 1 300px" minWidth="300px">
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" gap={1}>
                <Speed
                  color={getHealthColor(
                    performanceStats?.success_rate_percentage || 0,
                  )}
                />
                <Typography variant="h6">Success Rate</Typography>
              </Box>
              <Typography
                variant="h4"
                color={getHealthColor(
                  performanceStats?.success_rate_percentage || 0,
                )}
              >
                {performanceStats?.success_rate_percentage?.toFixed(1) || 0}%
              </Typography>
              <Typography variant="body2" color="text.secondary">
                P95: {performanceStats?.p95_duration_seconds?.toFixed(2) || 0}s
              </Typography>
            </CardContent>
          </Card>
        </Box>

        {/* Issues Found */}
        <Box flex="1 1 300px" minWidth="300px">
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" gap={1}>
                <BugReport
                  color={
                    integritySummary?.total_gaps ||
                    integritySummary?.total_duplicates
                      ? 'error'
                      : 'success'
                  }
                />
                <Typography variant="h6">Issues Found</Typography>
              </Box>
              <Typography
                variant="h4"
                color={
                  integritySummary?.total_gaps ||
                  integritySummary?.total_duplicates
                    ? 'error'
                    : 'success'
                }
              >
                {(integritySummary?.total_gaps || 0) +
                  (integritySummary?.total_duplicates || 0)}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {integritySummary?.total_gaps || 0} gaps,{' '}
                {integritySummary?.total_duplicates || 0} duplicates
              </Typography>
            </CardContent>
          </Card>
        </Box>

        {/* Active Alerts */}
        <Box flex="1 1 300px" minWidth="300px">
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" gap={1}>
                <Notifications
                  color={alerts.length > 0 ? 'error' : 'success'}
                />
                <Typography variant="h6">Active Alerts</Typography>
              </Box>
              <Typography
                variant="h4"
                color={alerts.length > 0 ? 'error' : 'success'}
              >
                {alerts.length}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {alerts.filter(a => a.severity === 'critical').length} critical
              </Typography>
            </CardContent>
          </Card>
        </Box>
      </Box>

      {/* Recent Alerts */}
      {alerts.length > 0 && (
        <Card sx={{ mb: 3 }}>
          <CardHeader title="Recent Alerts" />
          <CardContent>
            <List>
              {alerts.slice(0, 5).map(alert => (
                <ListItem key={alert.alert_id}>
                  <ListItemIcon>
                    {alert.severity === 'critical' ? (
                      <Error color="error" />
                    ) : alert.severity === 'warning' ? (
                      <Warning color="warning" />
                    ) : (
                      <Notifications color="info" />
                    )}
                  </ListItemIcon>
                  <ListItemText
                    primary={alert.title}
                    secondary={
                      <Box>
                        <Typography variant="body2">
                          {alert.description}
                        </Typography>
                        <Typography variant="caption">
                          {new Date(alert.timestamp).toLocaleString()}
                          {alert.project_id &&
                            ` • Project: ${alert.project_id}`}
                        </Typography>
                      </Box>
                    }
                  />
                  <ListItemSecondaryAction>
                    <Button
                      size="small"
                      onClick={() => resolveAlert(alert.alert_id)}
                    >
                      Resolve
                    </Button>
                  </ListItemSecondaryAction>
                </ListItem>
              ))}
            </List>
          </CardContent>
        </Card>
      )}

      {/* Quick Actions */}
      <Card>
        <CardHeader title="Quick Actions" />
        <CardContent>
          <Box display="flex" gap={2} flexWrap="wrap">
            <Button
              variant="outlined"
              startIcon={<PlayArrow />}
              onClick={() => runIntegrityCheck(false)}
            >
              Run Basic Check
            </Button>
            <Button
              variant="outlined"
              startIcon={<Analytics />}
              onClick={() => runIntegrityCheck(true)}
            >
              Run Deep Check
            </Button>
            <Button
              variant="outlined"
              startIcon={<Build />}
              onClick={() => {
                /* Open repair dialog */
              }}
            >
              Repair Tools
            </Button>
          </Box>
        </CardContent>
      </Card>
    </Box>
  )

  // Performance Tab
  const renderPerformance = () => (
    <Box>
      <Typography variant="h5" gutterBottom>
        Performance Metrics
      </Typography>

      <Box display="flex" flexWrap="wrap" gap={3}>
        <Box flex="1 1 400px" minWidth="400px">
          <Card>
            <CardHeader title="Response Times" />
            <CardContent>
              <Box mb={2}>
                <Typography variant="body2">Average Duration</Typography>
                <Typography variant="h6">
                  {performanceStats?.average_duration_seconds?.toFixed(3)}s
                </Typography>
              </Box>
              <Box mb={2}>
                <Typography variant="body2">95th Percentile</Typography>
                <Typography variant="h6">
                  {performanceStats?.p95_duration_seconds?.toFixed(3)}s
                </Typography>
              </Box>
              <Box>
                <Typography variant="body2">99th Percentile</Typography>
                <Typography variant="h6">
                  {performanceStats?.p99_duration_seconds?.toFixed(3)}s
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Box>

        <Box flex="1 1 400px" minWidth="400px">
          <Card>
            <CardHeader title="Operation Statistics" />
            <CardContent>
              <Box mb={2}>
                <Typography variant="body2">Total Operations Today</Typography>
                <Typography variant="h6">
                  {performanceStats?.total_operations_today?.toLocaleString()}
                </Typography>
              </Box>
              <Box mb={2}>
                <Typography variant="body2">Failed Operations</Typography>
                <Typography variant="h6" color="error">
                  {performanceStats?.failed_operations_today}
                </Typography>
              </Box>
              <Box>
                <Typography variant="body2">Conflict Rate</Typography>
                <Typography
                  variant="h6"
                  color={
                    performanceStats?.conflict_rate_percentage &&
                    performanceStats.conflict_rate_percentage > 5
                      ? 'error'
                      : 'success'
                  }
                >
                  {performanceStats?.conflict_rate_percentage?.toFixed(2)}%
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Box>
      </Box>
    </Box>
  )

  return (
    <Box p={3}>
      <Tabs
        value={currentTab}
        onChange={(_, newValue) => setCurrentTab(newValue)}
        sx={{ mb: 3 }}
      >
        <Tab label="Overview" />
        <Tab label="Performance" />
        <Tab label="Integrity" />
        <Tab label="Alerts" />
      </Tabs>

      {currentTab === 0 && renderOverview()}
      {currentTab === 1 && renderPerformance()}
      {currentTab === 2 && (
        <Typography>Integrity details coming soon...</Typography>
      )}
      {currentTab === 3 && (
        <Typography>Alert management coming soon...</Typography>
      )}
    </Box>
  )
}
