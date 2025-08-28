/**
 * RAG Worker System Dashboard Component
 * Provides monitoring and management for durable RAG workers
 */

import { useState } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Chip,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  LinearProgress,
  Alert,
  IconButton,
  Tooltip,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
} from '@mui/material'
import {
  Refresh as RefreshIcon,
  Cancel as CancelIcon,
  RestartAlt as RetryIcon,
  Info as InfoIcon,
  Error as ErrorIcon,
  CheckCircle as SuccessIcon,
  Queue as QueueIcon,
  Memory as MemoryIcon,
  Speed as SpeedIcon,
} from '@mui/icons-material'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useToastHelpers } from '@/shared/ui/components/toast'

interface QueueStats {
  queue_length: number
  dlq_length: number
  processing_jobs: number
  active_workers: number
  total_workers: number
  worker_utilization: number
  avg_processing_time_minutes: number
  jobs_completed_24h: number
  jobs_failed_24h: number
  success_rate_24h: number
  embedding_rate_current: number
  embedding_rate_limit: number
  embedding_quota_remaining: number
  embed_version: string
  outdated_documents: number
  queue_health: 'healthy' | 'degraded' | 'unhealthy'
  worker_health: 'healthy' | 'degraded' | 'unhealthy'
  storage_health: 'healthy' | 'degraded' | 'unhealthy'
}

interface JobStatus {
  job_id: string
  ingest_id: string
  status: string
  progress_pct: number
  current_step: string
  created_at?: string
  started_at?: string
  ended_at?: string
  estimated_remaining_seconds?: number
  document_id?: string
  chunks_indexed?: number
  error_code?: string
  error_message?: string
  retry_count: number
  queue_position?: number
}

interface DLQEntry {
  id: string
  original_job_id: string
  ingest_id: string
  project_id: string
  error_type: string
  error_code: string
  error_message: string
  last_step: string
  attempts: number
  failed_at: string
  resolved_at?: string
  trace_id: string
}

interface RAGWorkerDashboardProps {
  projectId?: string
  onJobSelect?: (jobId: string) => void
}

export function RAGWorkerDashboard({ projectId, onJobSelect }: RAGWorkerDashboardProps) {
  const { showSuccess, showError } = useToastHelpers()
  const queryClient = useQueryClient()
  
  const [_selectedJob, setSelectedJob] = useState<JobStatus | null>(null)
  const [dlqDialogOpen, setDlqDialogOpen] = useState(false)
  const [reindexDialogOpen, setReindexDialogOpen] = useState(false)

  // Query queue statistics
  const { data: queueStats, isLoading: statsLoading, error: statsError } = useQuery({
    queryKey: ['rag-queue-stats'],
    queryFn: async (): Promise<QueueStats> => {
      const response = await fetch('/api/generation/rag/queue/stats')
      if (!response.ok) throw new Error('Failed to fetch queue stats')
      return response.json()
    },
    refetchInterval: 10000, // Refresh every 10 seconds
  })

  // Query recent jobs for project
  const { data: projectJobs, isLoading: jobsLoading } = useQuery({
    queryKey: ['rag-project-jobs', projectId],
    queryFn: async (): Promise<{ documents: JobStatus[] }> => {
      if (!projectId) return { documents: [] }
      const response = await fetch(`/api/generation/rag/projects/${projectId}/documents?limit=20`)
      if (!response.ok) throw new Error('Failed to fetch project jobs')
      return response.json()
    },
    enabled: !!projectId,
    refetchInterval: 15000,
  })

  // Query DLQ entries
  const { data: dlqData, isLoading: dlqLoading } = useQuery({
    queryKey: ['rag-dlq'],
    queryFn: async (): Promise<{ entries: DLQEntry[], total: number, error_type_counts: Record<string, number> }> => {
      const response = await fetch('/api/generation/rag/dlq?limit=20&resolved_filter=false')
      if (!response.ok) throw new Error('Failed to fetch DLQ')
      return response.json()
    },
    refetchInterval: 30000,
  })

  // Cancel job mutation
  const cancelJobMutation = useMutation({
    mutationFn: async ({ jobId, reason }: { jobId: string, reason: string }) => {
      const response = await fetch(`/api/generation/rag/jobs/${jobId}/cancel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason }),
      })
      if (!response.ok) throw new Error('Failed to cancel job')
      return response.json()
    },
    onSuccess: () => {
      showSuccess('Job canceled successfully')
      queryClient.invalidateQueries({ queryKey: ['rag-project-jobs'] })
    },
    onError: (error) => {
      showError(`Failed to cancel job: ${error.message}`)
    },
  })

  // Retry job mutation
  const retryJobMutation = useMutation({
    mutationFn: async (jobId: string) => {
      const response = await fetch(`/api/generation/rag/jobs/${jobId}/retry`, {
        method: 'POST',
      })
      if (!response.ok) throw new Error('Failed to retry job')
      return response.json()
    },
    onSuccess: () => {
      showSuccess('Job retry scheduled')
      queryClient.invalidateQueries({ queryKey: ['rag-project-jobs'] })
    },
    onError: (error) => {
      showError(`Failed to retry job: ${error.message}`)
    },
  })

  // Reindex all mutation
  const reindexAllMutation = useMutation({
    mutationFn: async (data: { project_id: string, batch_size: number }) => {
      const response = await fetch('/api/generation/rag/reindex-all', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      })
      if (!response.ok) throw new Error('Failed to start reindex')
      return response.json()
    },
    onSuccess: (data) => {
      showSuccess(`Reindexing started: ${data.documents_to_reindex} documents`)
      setReindexDialogOpen(false)
      queryClient.invalidateQueries({ queryKey: ['rag-queue-stats'] })
    },
    onError: (error) => {
      showError(`Failed to start reindex: ${error.message}`)
    },
  })

  const getHealthColor = (health: string) => {
    switch (health) {
      case 'healthy': return 'success'
      case 'degraded': return 'warning' 
      case 'unhealthy': return 'error'
      default: return 'default'
    }
  }

  const getStatusIcon = (status: string) => {
    if (status.includes('failed')) return <ErrorIcon color="error" />
    if (status === 'indexed') return <SuccessIcon color="success" />
    if (status === 'canceled') return <CancelIcon color="disabled" />
    return <QueueIcon color="primary" />
  }


  if (statsError) {
    return (
      <Alert severity="error">
        Failed to load RAG worker dashboard. Make sure USE_DURABLE_WORKER=true is set.
      </Alert>
    )
  }

  return (
    <Box>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h5" component="h1">
          RAG Worker Dashboard
        </Typography>
        <Box display="flex" gap={1}>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={() => queryClient.invalidateQueries({ queryKey: ['rag-queue-stats'] })}
            disabled={statsLoading}
          >
            Refresh
          </Button>
          <Button
            variant="outlined"
            startIcon={<InfoIcon />}
            onClick={() => setDlqDialogOpen(true)}
          >
            DLQ ({dlqData?.total || 0})
          </Button>
          {projectId && queueStats && queueStats.outdated_documents > 0 && (
            <Button
              variant="contained"
              color="warning"
              onClick={() => setReindexDialogOpen(true)}
            >
              Reindex ({queueStats.outdated_documents})
            </Button>
          )}
        </Box>
      </Box>

      {/* System Health Overview */}
      <Grid container spacing={3} mb={3}>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" gap={2}>
                <QueueIcon fontSize="large" />
                <Box>
                  <Typography variant="h6">Queue Health</Typography>
                  <Chip
                    label={queueStats?.queue_health || 'loading'}
                    color={getHealthColor(queueStats?.queue_health || 'default')}
                    size="small"
                  />
                </Box>
              </Box>
              <Typography variant="body2" color="text.secondary" mt={1}>
                {queueStats?.queue_length || 0} jobs queued
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" gap={2}>
                <MemoryIcon fontSize="large" />
                <Box>
                  <Typography variant="h6">Workers</Typography>
                  <Typography variant="h5">
                    {queueStats?.active_workers || 0}/{queueStats?.total_workers || 0}
                  </Typography>
                </Box>
              </Box>
              <Typography variant="body2" color="text.secondary" mt={1}>
                {Math.round(queueStats?.worker_utilization || 0)}% utilization
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" gap={2}>
                <SpeedIcon fontSize="large" />
                <Box>
                  <Typography variant="h6">Success Rate</Typography>
                  <Typography variant="h5" color={(queueStats?.success_rate_24h || 0) >= 90 ? 'success.main' : 'warning.main'}>
                    {Math.round(queueStats?.success_rate_24h || 0)}%
                  </Typography>
                </Box>
              </Box>
              <Typography variant="body2" color="text.secondary" mt={1}>
                Last 24 hours
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Detailed Metrics */}
      <Grid container spacing={3} mb={3}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Processing Metrics</Typography>
              <List dense>
                <ListItem>
                  <ListItemText primary="Jobs Completed (24h)" />
                  <ListItemSecondaryAction>
                    <Typography variant="body2">{queueStats?.jobs_completed_24h || 0}</Typography>
                  </ListItemSecondaryAction>
                </ListItem>
                <ListItem>
                  <ListItemText primary="Jobs Failed (24h)" />
                  <ListItemSecondaryAction>
                    <Typography variant="body2" color={(queueStats?.jobs_failed_24h || 0) > 0 ? 'error' : 'text.secondary'}>
                      {queueStats?.jobs_failed_24h || 0}
                    </Typography>
                  </ListItemSecondaryAction>
                </ListItem>
                <ListItem>
                  <ListItemText primary="Avg Processing Time" />
                  <ListItemSecondaryAction>
                    <Typography variant="body2">
                      {Math.round(queueStats?.avg_processing_time_minutes || 0)}m
                    </Typography>
                  </ListItemSecondaryAction>
                </ListItem>
                <ListItem>
                  <ListItemText primary="Embedding Version" />
                  <ListItemSecondaryAction>
                    <Chip label={queueStats?.embed_version || 'N/A'} size="small" />
                  </ListItemSecondaryAction>
                </ListItem>
              </List>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Rate Limits</Typography>
              <Box mb={2}>
                <Typography variant="body2" gutterBottom>
                  Embedding Usage: {queueStats?.embedding_rate_current || 0}/{queueStats?.embedding_rate_limit || 1000} per minute
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={Math.min(100, (queueStats?.embedding_rate_current || 0) / (queueStats?.embedding_rate_limit || 1000) * 100)}
                  color={(queueStats?.embedding_rate_current || 0) > ((queueStats?.embedding_rate_limit || 1000) * 0.8) ? 'warning' : 'primary'}
                />
              </Box>
              <Typography variant="body2" color="text.secondary">
                Quota Remaining: {queueStats?.embedding_quota_remaining?.toLocaleString() || 'N/A'}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Recent Jobs Table */}
      {projectId && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Recent Jobs for Project
            </Typography>
            {jobsLoading ? (
              <LinearProgress />
            ) : (
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Status</TableCell>
                      <TableCell>Job ID</TableCell>
                      <TableCell>Progress</TableCell>
                      <TableCell>Step</TableCell>
                      <TableCell>Created</TableCell>
                      <TableCell>Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {(projectJobs?.documents || []).map((job) => (
                      <TableRow key={job.job_id}>
                        <TableCell>
                          <Box display="flex" alignItems="center" gap={1}>
                            {getStatusIcon(job.status)}
                            <Typography variant="body2">{job.status}</Typography>
                            {job.retry_count > 0 && (
                              <Chip label={`Retry ${job.retry_count}`} size="small" color="warning" />
                            )}
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" fontFamily="monospace">
                            {job.job_id.substring(0, 8)}...
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Box display="flex" alignItems="center" gap={1}>
                            <LinearProgress
                              variant="determinate"
                              value={job.progress_pct}
                              sx={{ width: 60 }}
                            />
                            <Typography variant="body2">{Math.round(job.progress_pct)}%</Typography>
                          </Box>
                        </TableCell>
                        <TableCell>{job.current_step}</TableCell>
                        <TableCell>
                          {job.created_at ? new Date(job.created_at).toLocaleString() : 'N/A'}
                        </TableCell>
                        <TableCell>
                          <Box display="flex" gap={1}>
                            <Tooltip title="View Details">
                              <IconButton
                                size="small"
                                onClick={() => {
                                  setSelectedJob(job)
                                  onJobSelect?.(job.job_id)
                                }}
                              >
                                <InfoIcon />
                              </IconButton>
                            </Tooltip>
                            {job.status.includes('failed') && (
                              <Tooltip title="Retry Job">
                                <IconButton
                                  size="small"
                                  onClick={() => retryJobMutation.mutate(job.job_id)}
                                  disabled={retryJobMutation.isPending}
                                >
                                  <RetryIcon />
                                </IconButton>
                              </Tooltip>
                            )}
                            {!job.status.includes('indexed') && !job.status.includes('failed') && !job.status.includes('canceled') && (
                              <Tooltip title="Cancel Job">
                                <IconButton
                                  size="small"
                                  onClick={() => cancelJobMutation.mutate({ jobId: job.job_id, reason: 'User canceled from dashboard' })}
                                  disabled={cancelJobMutation.isPending}
                                >
                                  <CancelIcon />
                                </IconButton>
                              </Tooltip>
                            )}
                          </Box>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </CardContent>
        </Card>
      )}

      {/* DLQ Dialog */}
      <Dialog open={dlqDialogOpen} onClose={() => setDlqDialogOpen(false)} maxWidth="lg" fullWidth>
        <DialogTitle>Dead Letter Queue</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            Failed jobs that exceeded retry limits
          </Typography>
          
          {dlqLoading ? (
            <LinearProgress />
          ) : (
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Error Type</TableCell>
                    <TableCell>Job ID</TableCell>
                    <TableCell>Project</TableCell>
                    <TableCell>Attempts</TableCell>
                    <TableCell>Failed At</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {(dlqData?.entries || []).map((entry) => (
                    <TableRow key={entry.id}>
                      <TableCell>
                        <Chip label={entry.error_type} color="error" size="small" />
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" fontFamily="monospace">
                          {entry.original_job_id.substring(0, 12)}...
                        </Typography>
                      </TableCell>
                      <TableCell>{entry.project_id}</TableCell>
                      <TableCell>{entry.attempts}</TableCell>
                      <TableCell>{new Date(entry.failed_at).toLocaleString()}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDlqDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Reindex Dialog */}
      <Dialog open={reindexDialogOpen} onClose={() => setReindexDialogOpen(false)}>
        <DialogTitle>Reindex All Documents</DialogTitle>
        <DialogContent>
          <Typography gutterBottom>
            This will reindex all documents in the project with the current embedding version.
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Current version: {queueStats?.embed_version}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Outdated documents: {queueStats?.outdated_documents}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setReindexDialogOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={() => projectId && reindexAllMutation.mutate({ project_id: projectId, batch_size: 10 })}
            disabled={!projectId || reindexAllMutation.isPending}
          >
            Start Reindex
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default RAGWorkerDashboard