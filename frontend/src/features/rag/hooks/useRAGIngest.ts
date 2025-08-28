/**
 * Hook for RAG document ingestion
 * Handles file upload, job tracking, and status monitoring
 */

import { useState, useCallback, useRef, useEffect } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'

import { useToastHelpers } from '@/shared/ui/components/toast'
import type { RAGIngestResponse, RAGJobStatus, RAGError } from '../types'

export interface UseRAGIngestOptions {
  /** Language for UI messages */
  language?: 'kr' | 'en'
  /** Callback after successful ingest start */
  onSuccess?: (jobId: string, file: File) => void
  /** Callback after failed ingest */
  onError?: (error: RAGError, file?: File) => void
}

export interface RAGIngestState {
  /** Whether ingestion is in progress */
  isLoading: boolean
  /** Current ingestion error */
  error: RAGError | null
  /** Ingest a document */
  ingestDocument: (projectId: string, file: File, options?: { force_ocr?: boolean }) => Promise<void>
  /** Clear error state */
  clearError: () => void
}

/**
 * Mock file upload service for RAG ingestion
 * In production, this would upload to actual file storage
 */
async function uploadFile(file: File): Promise<string> {
  // Simulate file upload with progress
  await new Promise(resolve => setTimeout(resolve, 1000))
  
  // Generate mock file ID
  return `file_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

/**
 * RAG ingestion API service
 */
async function ingestRAGDocument(
  projectId: string,
  fileId: string,
  options?: { chunk_size?: number; chunk_overlap?: number; force_ocr?: boolean }
): Promise<RAGIngestResponse> {
  const response = await fetch('/api/rag/ingest', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Ingest-Id': crypto.randomUUID?.() || `ingest-${Date.now()}`,
    },
    body: JSON.stringify({
      project_id: projectId,
      file_id: fileId,
      ...options,
    }),
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw {
      code: errorData.code || 'INGEST_FAILED',
      message: errorData.message || 'Failed to start document ingestion',
      status: response.status,
      details: errorData.details || {},
    } as RAGError
  }

  return response.json()
}

/**
 * Hook for managing RAG document ingestion
 */
export function useRAGIngest(options: UseRAGIngestOptions = {}): RAGIngestState {
  const {
    language = 'kr',
    onSuccess,
    onError,
  } = options

  const queryClient = useQueryClient()
  const { showSuccess, showError } = useToastHelpers()
  const [currentFile, setCurrentFile] = useState<File | null>(null)

  // Mutation for document ingestion
  const ingestMutation = useMutation({
    mutationFn: async ({
      projectId,
      file,
      ingestOptions = {},
    }: {
      projectId: string
      file: File
      ingestOptions?: { force_ocr?: boolean }
    }) => {
      // Step 1: Upload file
      const fileId = await uploadFile(file)
      
      // Step 2: Start RAG ingestion
      const response = await ingestRAGDocument(projectId, fileId, {
        force_ocr: ingestOptions.force_ocr,
        // Default chunking parameters
        chunk_size: 1024,
        chunk_overlap: 128,
      })

      return { response, file, fileId }
    },

    onSuccess: ({ response, file }) => {
      // Show success message
      const successMessage = language === 'kr'
        ? `문서 "${file.name}" 처리가 시작되었습니다`
        : `Document "${file.name}" processing started`
      
      if (response.is_duplicate) {
        const duplicateMessage = language === 'kr'
          ? `문서 "${file.name}"는 이미 처리된 중복 파일입니다`
          : `Document "${file.name}" is a duplicate and already processed`
        showSuccess(duplicateMessage)
      } else {
        showSuccess(successMessage)
      }

      // Invalidate RAG-related queries
      queryClient.invalidateQueries({ queryKey: ['rag-documents'] })
      queryClient.invalidateQueries({ queryKey: ['rag-jobs'] })
      
      // Callback
      onSuccess?.(response.job_id, file)
      setCurrentFile(null)
    },

    onError: (error: RAGError) => {
      const errorMessage = error.message || (language === 'kr' 
        ? '문서 처리 시작에 실패했습니다'
        : 'Failed to start document processing')
      
      // Handle specific error types
      if (error.code === 'RATE_LIMITED') {
        const rateLimitMessage = language === 'kr'
          ? '요청이 너무 빈번합니다. 잠시 후 다시 시도해주세요'
          : 'Too many requests. Please try again later'
        showError(rateLimitMessage)
      } else if (error.code === 'FILE_TOO_LARGE') {
        const sizeLimitMessage = language === 'kr'
          ? '파일 크기가 너무 큽니다'
          : 'File size is too large'
        showError(sizeLimitMessage)
      } else if (error.code === 'UNSUPPORTED_FORMAT') {
        const formatMessage = language === 'kr'
          ? '지원하지 않는 파일 형식입니다'
          : 'Unsupported file format'
        showError(formatMessage)
      } else {
        showError(errorMessage)
      }

      // Callback
      onError?.(error, currentFile || undefined)
      setCurrentFile(null)
    },
  })

  // Main ingest function
  const ingestDocument = useCallback(async (
    projectId: string,
    file: File,
    options: { force_ocr?: boolean } = {}
  ) => {
    setCurrentFile(file)
    
    await ingestMutation.mutateAsync({
      projectId,
      file,
      ingestOptions: options,
    })
  }, [ingestMutation])

  // Clear error
  const clearError = useCallback(() => {
    ingestMutation.reset()
    setCurrentFile(null)
  }, [ingestMutation])

  return {
    isLoading: ingestMutation.isPending,
    error: ingestMutation.error as RAGError | null,
    ingestDocument,
    clearError,
  }
}

/**
 * Hook for polling RAG job status
 */
export function useRAGJobStatus(jobId: string | null, enabled: boolean = true) {
  const [status, setStatus] = useState<RAGJobStatus>('queued')
  const [progress, setProgress] = useState(0)
  const [currentStep, setCurrentStep] = useState('queued')
  const [error, setError] = useState<string | null>(null)
  
  const intervalRef = useRef<NodeJS.Timeout>()

  const pollStatus = useCallback(async () => {
    if (!jobId) return

    try {
      const response = await fetch(`/api/rag/jobs/${jobId}`)
      if (response.ok) {
        const data = await response.json()
        setStatus(data.status)
        setProgress(data.progress_pct)
        setCurrentStep(data.current_step)
        setError(data.error_message || null)

        // Stop polling if job is finished
        if (data.status === 'indexed' || data.status.startsWith('failed_')) {
          if (intervalRef.current) {
            clearInterval(intervalRef.current)
            intervalRef.current = undefined
          }
        }
      }
    } catch (err) {
      console.error('Failed to poll job status:', err)
    }
  }, [jobId])

  useEffect(() => {
    if (jobId && enabled) {
      pollStatus() // Initial poll
      intervalRef.current = setInterval(pollStatus, 2000) // Poll every 2 seconds
      
      return () => {
        if (intervalRef.current) {
          clearInterval(intervalRef.current)
        }
      }
    }
  }, [jobId, enabled, pollStatus])

  return {
    status,
    progress,
    currentStep,
    error,
    isPolling: !!intervalRef.current,
  }
}