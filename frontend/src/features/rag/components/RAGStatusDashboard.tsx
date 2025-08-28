/**
 * RAG Status Dashboard
 * Displays comprehensive status of RAG document processing for a project
 */

import { useState, useCallback } from 'react'
import {
  Box,
  Typography,
  Card,
  CardContent,
  CardActions,
  Grid,
  Chip,
  Button,
  LinearProgress,
  Stack,
  IconButton,
  Tooltip,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
  ListItemSecondaryAction,
  Avatar,
  Divider,
} from '@mui/material'
import {
  Description as DocumentIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Refresh as RetryIcon,
  Delete as DeleteIcon,
  Visibility as ViewIcon,
  GetApp as DownloadIcon,
  TrendingUp as TrendingUpIcon,
} from '@mui/icons-material'

import { useRAGDocuments } from '../hooks/useRAGDocuments'
import { useRAGJobStatus } from '../hooks/useRAGIngest'
import type { RAGDocument, RAGJobStatus } from '../types'

export interface RAGStatusDashboardProps {
  /** Project ID to show RAG status for */
  projectId: string
  /** Language for UI text */
  language?: 'kr' | 'en'
  /** Whether to auto-refresh data */
  autoRefresh?: boolean
  /** Callback when document is deleted */
  onDocumentDeleted?: (documentId: string) => void
}

/**
 * Comprehensive RAG status dashboard
 */
export function RAGStatusDashboard({
  projectId,
  language = 'kr',
  autoRefresh = true,
  onDocumentDeleted,
}: RAGStatusDashboardProps) {
  const [selectedDocument, setSelectedDocument] = useState<RAGDocument | null>(null)
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)
  const [documentToDelete, setDocumentToDelete] = useState<RAGDocument | null>(null)

  const {
    documents,
    summary,
    isLoading,
    error,
    refetch,
    retryDocument,
    deleteDocument,
  } = useRAGDocuments({
    projectId,
    autoRefresh,
    language,
  })

  // Handle document actions
  const handleViewDocument = useCallback((document: RAGDocument) => {
    setSelectedDocument(document)
  }, [])

  const handleRetryDocument = useCallback(async (document: RAGDocument) => {
    try {
      await retryDocument(document.id)
    } catch (err) {
      console.error('Failed to retry document:', err)
    }
  }, [retryDocument])

  const handleDeleteDocument = useCallback((document: RAGDocument) => {
    setDocumentToDelete(document)
    setDeleteConfirmOpen(true)
  }, [])

  const confirmDelete = useCallback(async () => {
    if (!documentToDelete) return

    try {
      await deleteDocument(documentToDelete.id)
      onDocumentDeleted?.(documentToDelete.id)
      setDeleteConfirmOpen(false)
      setDocumentToDelete(null)
    } catch (err) {
      console.error('Failed to delete document:', err)
    }
  }, [documentToDelete, deleteDocument, onDocumentDeleted])

  // Get status info
  const getStatusInfo = (status: RAGJobStatus) => {
    switch (status) {
      case 'indexed':
        return {
          color: 'success' as const,
          label: language === 'kr' ? '완료' : 'Completed',
          icon: <SuccessIcon fontSize="small" />,
        }
      case 'queued':
      case 'uploading':
      case 'extracting':
      case 'ocr':
      case 'chunking':
      case 'embedding':
        return {
          color: 'primary' as const,
          label: language === 'kr' ? '처리중' : 'Processing',
          icon: <TrendingUpIcon fontSize="small" />,
        }
      default:
        if (status.startsWith('failed_')) {
          return {
            color: 'error' as const,
            label: language === 'kr' ? '실패' : 'Failed',
            icon: <ErrorIcon fontSize="small" />,
          }
        }
        return {
          color: 'default' as const,
          label: status,
          icon: <DocumentIcon fontSize="small" />,
        }
    }
  }

  // Format file size
  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  // Format date
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString(language === 'kr' ? 'ko-KR' : 'en-US')
  }

  const text = {
    title: language === 'kr' ? 'RAG 문서 상태' : 'RAG Document Status',
    summary: language === 'kr' ? '요약' : 'Summary',
    totalDocuments: language === 'kr' ? '전체 문서' : 'Total Documents',
    indexed: language === 'kr' ? '인덱싱 완료' : 'Indexed',
    processing: language === 'kr' ? '처리중' : 'Processing',
    failed: language === 'kr' ? '실패' : 'Failed',
    documents: language === 'kr' ? '문서 목록' : 'Documents',
    noDocuments: language === 'kr' ? '문서가 없습니다' : 'No documents found',
    refresh: language === 'kr' ? '새로고침' : 'Refresh',
    retry: language === 'kr' ? '재시도' : 'Retry',
    delete: language === 'kr' ? '삭제' : 'Delete',
    view: language === 'kr' ? '보기' : 'View',
    download: language === 'kr' ? '다운로드' : 'Download',
    confirmDeleteTitle: language === 'kr' ? '문서 삭제 확인' : 'Confirm Document Deletion',
    confirmDeleteMessage: language === 'kr' 
      ? '이 문서를 삭제하시겠습니까? 모든 청크와 임베딩이 제거됩니다.'
      : 'Are you sure you want to delete this document? All chunks and embeddings will be removed.',
    cancel: language === 'kr' ? '취소' : 'Cancel',
    confirm: language === 'kr' ? '삭제' : 'Delete',
    documentDetails: language === 'kr' ? '문서 상세정보' : 'Document Details',
    close: language === 'kr' ? '닫기' : 'Close',
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mt: 2 }}>
        <Typography>
          {language === 'kr' ? 'RAG 상태를 불러오는데 실패했습니다' : 'Failed to load RAG status'}
        </Typography>
      </Alert>
    )
  }

  return (
    <Box>
      {/* Header */}
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
        <Typography variant="h5" component="h2">
          {text.title}
        </Typography>
        <Button
          variant="outlined"
          startIcon={<RetryIcon />}
          onClick={() => refetch()}
          disabled={isLoading}
        >
          {text.refresh}
        </Button>
      </Stack>

      {/* Summary Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card>
            <CardContent>
              <Stack direction="row" alignItems="center" spacing={2}>
                <Avatar sx={{ bgcolor: 'primary.main' }}>
                  <DocumentIcon />
                </Avatar>
                <Box>
                  <Typography variant="h4" component="div">
                    {summary?.total || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {text.totalDocuments}
                  </Typography>
                </Box>
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card>
            <CardContent>
              <Stack direction="row" alignItems="center" spacing={2}>
                <Avatar sx={{ bgcolor: 'success.main' }}>
                  <SuccessIcon />
                </Avatar>
                <Box>
                  <Typography variant="h4" component="div">
                    {summary?.indexed_count || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {text.indexed}
                  </Typography>
                </Box>
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card>
            <CardContent>
              <Stack direction="row" alignItems="center" spacing={2}>
                <Avatar sx={{ bgcolor: 'info.main' }}>
                  <TrendingUpIcon />
                </Avatar>
                <Box>
                  <Typography variant="h4" component="div">
                    {summary?.processing_count || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {text.processing}
                  </Typography>
                </Box>
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card>
            <CardContent>
              <Stack direction="row" alignItems="center" spacing={2}>
                <Avatar sx={{ bgcolor: 'error.main' }}>
                  <ErrorIcon />
                </Avatar>
                <Box>
                  <Typography variant="h4" component="div">
                    {summary?.failed_count || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {text.failed}
                  </Typography>
                </Box>
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Documents List */}
      <Card>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 2 }}>
            {text.documents}
          </Typography>

          {isLoading ? (
            <LinearProgress />
          ) : documents.length === 0 ? (
            <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 4 }}>
              {text.noDocuments}
            </Typography>
          ) : (
            <List>
              {documents.map((document, index) => {
                const statusInfo = getStatusInfo(document.status as RAGJobStatus)
                const isProcessing = !document.status.startsWith('failed_') && document.status !== 'indexed'

                return (
                  <Box key={document.id}>
                    <ListItem alignItems="flex-start">
                      <ListItemAvatar>
                        <Avatar>
                          <DocumentIcon />
                        </Avatar>
                      </ListItemAvatar>

                      <ListItemText
                        primary={
                          <Stack direction="row" spacing={1} alignItems="center">
                            <Typography variant="subtitle1" component="div">
                              {document.name}
                            </Typography>
                            <Chip
                              icon={statusInfo.icon}
                              label={statusInfo.label}
                              color={statusInfo.color}
                              size="small"
                            />
                          </Stack>
                        }
                        secondary={
                          <Stack spacing={1} sx={{ mt: 1 }}>
                            <Typography variant="body2" color="text.secondary">
                              {formatFileSize(document.file_size)} • {document.chunks_count} chunks • {formatDate(document.uploaded_at)}
                            </Typography>
                            
                            {isProcessing && (
                              <LinearProgress 
                                variant="indeterminate" 
                                sx={{ height: 3, borderRadius: 1.5 }}
                              />
                            )}
                          </Stack>
                        }
                      />

                      <ListItemSecondaryAction>
                        <Stack direction="row" spacing={1}>
                          <Tooltip title={text.view}>
                            <IconButton size="small" onClick={() => handleViewDocument(document)}>
                              <ViewIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>

                          {document.status.startsWith('failed_') && (
                            <Tooltip title={text.retry}>
                              <IconButton 
                                size="small" 
                                onClick={() => handleRetryDocument(document)}
                                color="primary"
                              >
                                <RetryIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          )}

                          <Tooltip title={text.delete}>
                            <IconButton 
                              size="small" 
                              onClick={() => handleDeleteDocument(document)}
                              color="error"
                            >
                              <DeleteIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        </Stack>
                      </ListItemSecondaryAction>
                    </ListItem>
                    
                    {index < documents.length - 1 && <Divider />}
                  </Box>
                )
              })}
            </List>
          )}
        </CardContent>
      </Card>

      {/* Document Details Dialog */}
      <Dialog 
        open={!!selectedDocument} 
        onClose={() => setSelectedDocument(null)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>{text.documentDetails}</DialogTitle>
        <DialogContent>
          {selectedDocument && (
            <Stack spacing={2}>
              <Box>
                <Typography variant="subtitle2" color="text.secondary">Name</Typography>
                <Typography variant="body1">{selectedDocument.name}</Typography>
              </Box>

              <Box>
                <Typography variant="subtitle2" color="text.secondary">Status</Typography>
                <Chip
                  icon={getStatusInfo(selectedDocument.status as RAGJobStatus).icon}
                  label={getStatusInfo(selectedDocument.status as RAGJobStatus).label}
                  color={getStatusInfo(selectedDocument.status as RAGJobStatus).color}
                />
              </Box>

              <Box>
                <Typography variant="subtitle2" color="text.secondary">File Details</Typography>
                <Typography variant="body2">
                  Size: {formatFileSize(selectedDocument.file_size)}
                  <br />
                  Type: {selectedDocument.file_type}
                  <br />
                  Chunks: {selectedDocument.chunks_count}
                </Typography>
              </Box>

              <Box>
                <Typography variant="subtitle2" color="text.secondary">Timestamps</Typography>
                <Typography variant="body2">
                  Uploaded: {formatDate(selectedDocument.uploaded_at)}
                  {selectedDocument.indexed_at && (
                    <>
                      <br />
                      Indexed: {formatDate(selectedDocument.indexed_at)}
                    </>
                  )}
                </Typography>
              </Box>

              {selectedDocument.metadata && Object.keys(selectedDocument.metadata).length > 0 && (
                <Box>
                  <Typography variant="subtitle2" color="text.secondary">Metadata</Typography>
                  <pre style={{ fontSize: '0.8em', background: '#f5f5f5', padding: '8px', borderRadius: '4px' }}>
                    {JSON.stringify(selectedDocument.metadata, null, 2)}
                  </pre>
                </Box>
              )}
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSelectedDocument(null)}>
            {text.close}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteConfirmOpen} onClose={() => setDeleteConfirmOpen(false)}>
        <DialogTitle>{text.confirmDeleteTitle}</DialogTitle>
        <DialogContent>
          <Typography>
            {text.confirmDeleteMessage}
          </Typography>
          {documentToDelete && (
            <Typography variant="body2" sx={{ mt: 2, fontWeight: 'bold' }}>
              "{documentToDelete.name}"
            </Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteConfirmOpen(false)}>
            {text.cancel}
          </Button>
          <Button onClick={confirmDelete} color="error" variant="contained">
            {text.confirm}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default RAGStatusDashboard