/**
 * Production-grade RAG Document Dropzone
 * Handles file upload with validation, progress tracking, and accessibility
 */

import { useState, useCallback, useRef } from 'react'
import {
  Box,
  Typography,
  Button,
  LinearProgress,
  Alert,
  Chip,
  Stack,
  Paper,
  IconButton,
  Tooltip,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
} from '@mui/material'
import {
  CloudUpload as UploadIcon,
  Description as FileIcon,
  Delete as DeleteIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Refresh as RetryIcon,
} from '@mui/icons-material'
import { useDropzone } from 'react-dropzone'

import { useRAGIngest } from '../hooks/useRAGIngest'
import type { RAGJobStatus } from '../types'

export interface FileUploadState {
  file: File
  jobId?: string
  status: RAGJobStatus
  progress: number
  error?: string
  uploadedAt: Date
}

export interface RAGDropzoneProps {
  /** Project ID for RAG ingestion */
  projectId: string
  /** Language for UI text */
  language?: 'kr' | 'en'
  /** Maximum file size in MB */
  maxFileSizeMB?: number
  /** Maximum number of files */
  maxFiles?: number
  /** Callback when files are successfully processed */
  onSuccess?: (documentIds: string[]) => void
  /** Callback when upload fails */
  onError?: (error: string) => void
}

/**
 * Production-grade RAG document dropzone with comprehensive file handling
 */
export function RAGDropzone({
  projectId,
  language = 'kr',
  maxFileSizeMB = 50,
  maxFiles = 10,
  onSuccess,
  onError,
}: RAGDropzoneProps) {
  const [uploadedFiles, setUploadedFiles] = useState<Map<string, FileUploadState>>(new Map())
  const fileInputRef = useRef<HTMLInputElement>(null)
  
  const { ingestDocument, isLoading: isIngesting } = useRAGIngest({
    language,
    onSuccess: (jobId, file) => {
      setUploadedFiles(prev => {
        const newMap = new Map(prev)
        const fileKey = `${file.name}-${file.size}-${file.lastModified}`
        newMap.set(fileKey, {
          file,
          jobId,
          status: 'queued',
          progress: 0,
          uploadedAt: new Date(),
        })
        return newMap
      })
    },
    onError: (error, file) => {
      if (file) {
        const fileKey = `${file.name}-${file.size}-${file.lastModified}`
        setUploadedFiles(prev => {
          const newMap = new Map(prev)
          newMap.set(fileKey, {
            file,
            status: 'failed_extract',
            progress: 0,
            error: error.message || 'Upload failed',
            uploadedAt: new Date(),
          })
          return newMap
        })
      }
      onError?.(error.message || 'Upload failed')
    },
  })

  // File validation
  const validateFile = useCallback((file: File): string | null => {
    const maxSizeBytes = maxFileSizeMB * 1024 * 1024
    
    if (file.size > maxSizeBytes) {
      return language === 'kr' 
        ? `파일 크기가 ${maxFileSizeMB}MB를 초과합니다`
        : `File size exceeds ${maxFileSizeMB}MB limit`
    }
    
    const allowedTypes = [
      'application/pdf',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/msword',
      'text/plain',
      'text/markdown',
    ]
    
    if (!allowedTypes.includes(file.type)) {
      return language === 'kr'
        ? '지원하지 않는 파일 형식입니다 (PDF, DOCX, TXT, MD만 지원)'
        : 'Unsupported file type (PDF, DOCX, TXT, MD only)'
    }
    
    return null
  }, [maxFileSizeMB, language])

  // Handle file drop/selection
  const onDrop = useCallback((acceptedFiles: File[], rejectedFiles: any[]) => {
    // Handle rejected files
    if (rejectedFiles.length > 0) {
      const rejectedReasons = rejectedFiles.map(({file, errors}) => 
        `${file.name}: ${errors.map((e: any) => e.message).join(', ')}`
      ).join('; ')
      
      onError?.(language === 'kr' 
        ? `파일 거부됨: ${rejectedReasons}`
        : `Files rejected: ${rejectedReasons}`
      )
    }

    // Validate and process accepted files
    for (const file of acceptedFiles) {
      const validationError = validateFile(file)
      if (validationError) {
        onError?.(validationError)
        continue
      }
      
      // Check if file already exists
      const fileKey = `${file.name}-${file.size}-${file.lastModified}`
      if (uploadedFiles.has(fileKey)) {
        onError?.(language === 'kr' 
          ? '이미 업로드된 파일입니다'
          : 'File already uploaded'
        )
        continue
      }
      
      // Check max files limit
      if (uploadedFiles.size >= maxFiles) {
        onError?.(language === 'kr'
          ? `최대 ${maxFiles}개의 파일만 업로드할 수 있습니다`
          : `Maximum ${maxFiles} files allowed`
        )
        break
      }
      
      // Start upload
      ingestDocument(projectId, file)
    }
  }, [
    uploadedFiles, 
    validateFile, 
    ingestDocument, 
    projectId, 
    maxFiles, 
    language, 
    onError
  ])

  const {
    getRootProps,
    getInputProps,
    isDragActive,
    isDragReject,
  } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/msword': ['.doc'],
      'text/plain': ['.txt'],
      'text/markdown': ['.md'],
    },
    maxSize: maxFileSizeMB * 1024 * 1024,
    maxFiles: maxFiles - uploadedFiles.size,
    disabled: isIngesting,
  })

  // Handle file removal
  const handleRemoveFile = useCallback((fileKey: string) => {
    setUploadedFiles(prev => {
      const newMap = new Map(prev)
      newMap.delete(fileKey)
      return newMap
    })
  }, [])

  // Handle file retry
  const handleRetryFile = useCallback((fileKey: string) => {
    const fileState = uploadedFiles.get(fileKey)
    if (fileState) {
      ingestDocument(projectId, fileState.file)
    }
  }, [uploadedFiles, ingestDocument, projectId])

  // Get status info
  const getStatusInfo = (status: RAGJobStatus) => {
    switch (status) {
      case 'queued':
        return { 
          color: 'info' as const, 
          label: language === 'kr' ? '대기중' : 'Queued',
          icon: <UploadIcon fontSize="small" />
        }
      case 'uploading':
        return { 
          color: 'primary' as const, 
          label: language === 'kr' ? '업로드중' : 'Uploading',
          icon: <UploadIcon fontSize="small" />
        }
      case 'extracting':
        return { 
          color: 'primary' as const, 
          label: language === 'kr' ? '텍스트 추출중' : 'Extracting',
          icon: <FileIcon fontSize="small" />
        }
      case 'ocr':
        return { 
          color: 'primary' as const, 
          label: language === 'kr' ? 'OCR 처리중' : 'OCR Processing',
          icon: <FileIcon fontSize="small" />
        }
      case 'chunking':
        return { 
          color: 'primary' as const, 
          label: language === 'kr' ? '청킹중' : 'Chunking',
          icon: <FileIcon fontSize="small" />
        }
      case 'embedding':
        return { 
          color: 'primary' as const, 
          label: language === 'kr' ? '임베딩중' : 'Embedding',
          icon: <FileIcon fontSize="small" />
        }
      case 'indexed':
        return { 
          color: 'success' as const, 
          label: language === 'kr' ? '완료' : 'Completed',
          icon: <SuccessIcon fontSize="small" />
        }
      default:
        if (status.startsWith('failed_')) {
          return { 
            color: 'error' as const, 
            label: language === 'kr' ? '실패' : 'Failed',
            icon: <ErrorIcon fontSize="small" />
          }
        }
        return { 
          color: 'default' as const, 
          label: status,
          icon: <FileIcon fontSize="small" />
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

  const text = {
    title: language === 'kr' ? 'RAG 문서 업로드' : 'Upload RAG Documents',
    dropzoneText: language === 'kr' 
      ? '파일을 여기에 드래그하거나 클릭하여 선택하세요'
      : 'Drag files here or click to select',
    browseButton: language === 'kr' ? '파일 선택' : 'Browse Files',
    supportedFormats: language === 'kr' 
      ? 'PDF, DOCX, TXT, MD 파일 지원'
      : 'Supports PDF, DOCX, TXT, MD files',
    maxSizeNote: language === 'kr' 
      ? `최대 ${maxFileSizeMB}MB, ${maxFiles}개 파일까지`
      : `Max ${maxFileSizeMB}MB, up to ${maxFiles} files`,
    uploadedFiles: language === 'kr' ? '업로드된 파일' : 'Uploaded Files',
    noFiles: language === 'kr' ? '업로드된 파일이 없습니다' : 'No files uploaded',
  }

  const filesArray = Array.from(uploadedFiles.entries())
  const completedCount = filesArray.filter(([, file]) => file.status === 'indexed').length
  const processingCount = filesArray.filter(([, file]) => 
    file.status !== 'indexed' && !file.status.startsWith('failed_')
  ).length

  return (
    <Box>
      {/* Upload Area */}
      <Paper
        {...getRootProps()}
        sx={{
          p: 4,
          border: '2px dashed',
          borderColor: isDragActive ? 'primary.main' : 
                      isDragReject ? 'error.main' : 'grey.300',
          bgcolor: isDragActive ? 'primary.50' : 
                   isDragReject ? 'error.50' : 'background.paper',
          cursor: isIngesting ? 'not-allowed' : 'pointer',
          transition: 'all 0.2s ease',
          textAlign: 'center',
          opacity: isIngesting ? 0.6 : 1,
          '&:hover': {
            borderColor: isIngesting ? 'grey.300' : 'primary.main',
            bgcolor: isIngesting ? 'background.paper' : 'primary.50',
          },
        }}
      >
        <input {...getInputProps()} ref={fileInputRef} />
        
        <Stack spacing={2} alignItems="center">
          <UploadIcon 
            sx={{ 
              fontSize: 48, 
              color: isDragActive ? 'primary.main' : 
                     isDragReject ? 'error.main' : 'grey.400' 
            }} 
          />
          
          <Typography variant="h6" color="text.primary">
            {text.title}
          </Typography>
          
          <Typography variant="body1" color="text.secondary">
            {isDragActive 
              ? (language === 'kr' ? '파일을 놓으세요' : 'Drop files here')
              : text.dropzoneText
            }
          </Typography>
          
          <Button
            variant="outlined"
            disabled={isIngesting}
            onClick={() => fileInputRef.current?.click()}
          >
            {text.browseButton}
          </Button>
          
          <Stack spacing={1} alignItems="center">
            <Typography variant="body2" color="text.secondary">
              {text.supportedFormats}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {text.maxSizeNote}
            </Typography>
          </Stack>
        </Stack>
      </Paper>

      {/* Progress Summary */}
      {filesArray.length > 0 && (
        <Box sx={{ mt: 2 }}>
          <Stack direction="row" spacing={2} alignItems="center">
            <Typography variant="subtitle1">{text.uploadedFiles}</Typography>
            <Chip 
              label={`${completedCount}/${filesArray.length}`}
              color={completedCount === filesArray.length ? 'success' : 'default'}
              size="small"
            />
            {processingCount > 0 && (
              <Chip 
                label={language === 'kr' ? `${processingCount}개 처리중` : `${processingCount} processing`}
                color="primary"
                size="small"
              />
            )}
          </Stack>
        </Box>
      )}

      {/* File List */}
      {filesArray.length > 0 ? (
        <List sx={{ mt: 1 }}>
          {filesArray.map(([fileKey, fileState]) => {
            const statusInfo = getStatusInfo(fileState.status)
            const isProcessing = !fileState.status.startsWith('failed_') && fileState.status !== 'indexed'
            const canRetry = fileState.status.startsWith('failed_')
            
            return (
              <ListItem
                key={fileKey}
                sx={{
                  border: 1,
                  borderColor: 'grey.200',
                  borderRadius: 1,
                  mb: 1,
                }}
              >
                <ListItemText
                  primary={
                    <Stack direction="row" spacing={1} alignItems="center">
                      <Typography variant="subtitle2" noWrap>
                        {fileState.file.name}
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
                    <Stack spacing={1}>
                      <Typography variant="caption" color="text.secondary">
                        {formatFileSize(fileState.file.size)} • {fileState.uploadedAt.toLocaleTimeString()}
                      </Typography>
                      
                      {isProcessing && (
                        <LinearProgress 
                          variant="determinate" 
                          value={fileState.progress} 
                          sx={{ height: 4, borderRadius: 2 }}
                        />
                      )}
                      
                      {fileState.error && (
                        <Alert severity="error" sx={{ py: 0.5 }}>
                          <Typography variant="caption">
                            {fileState.error}
                          </Typography>
                        </Alert>
                      )}
                    </Stack>
                  }
                />
                
                <ListItemSecondaryAction>
                  <Stack direction="row" spacing={1}>
                    {canRetry && (
                      <Tooltip title={language === 'kr' ? '다시 시도' : 'Retry'}>
                        <IconButton
                          size="small"
                          onClick={() => handleRetryFile(fileKey)}
                          disabled={isIngesting}
                        >
                          <RetryIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    )}
                    
                    <Tooltip title={language === 'kr' ? '삭제' : 'Remove'}>
                      <IconButton
                        size="small"
                        onClick={() => handleRemoveFile(fileKey)}
                        disabled={isProcessing}
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </Stack>
                </ListItemSecondaryAction>
              </ListItem>
            )
          })}
        </List>
      ) : (
        <Box sx={{ mt: 3, textAlign: 'center' }}>
          <Typography variant="body2" color="text.secondary">
            {text.noFiles}
          </Typography>
        </Box>
      )}
    </Box>
  )
}

export default RAGDropzone