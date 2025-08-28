/**
 * Hook for managing RAG documents
 * Handles fetching, retrying, and deleting RAG documents
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useCallback } from 'react'

import { useToastHelpers } from '@/shared/ui/components/toast'
import type { RAGDocumentsResponse, RAGDocument, RAGError } from '../types'

export interface UseRAGDocumentsOptions {
  /** Project ID to fetch documents for */
  projectId: string
  /** Language for UI messages */
  language?: 'kr' | 'en'
  /** Whether to auto-refresh data */
  autoRefresh?: boolean
  /** Status filter */
  statusFilter?: string
  /** Pagination limit */
  limit?: number
  /** Pagination offset */
  offset?: number
}

export interface UseRAGDocumentsResult {
  /** List of RAG documents */
  documents: RAGDocument[]
  /** Summary statistics */
  summary: {
    total: number
    indexed_count: number
    processing_count: number
    failed_count: number
  } | null
  /** Whether data is loading */
  isLoading: boolean
  /** Current error */
  error: Error | null
  /** Refetch documents */
  refetch: () => void
  /** Retry document processing */
  retryDocument: (documentId: string) => Promise<void>
  /** Delete document */
  deleteDocument: (documentId: string) => Promise<void>
}

/**
 * API service for fetching RAG documents
 */
async function fetchRAGDocuments(
  projectId: string,
  options: {
    statusFilter?: string
    limit?: number
    offset?: number
  } = {}
): Promise<RAGDocumentsResponse> {
  const params = new URLSearchParams({
    project_id: projectId,
    limit: String(options.limit || 50),
    offset: String(options.offset || 0),
  })

  if (options.statusFilter) {
    params.append('status_filter', options.statusFilter)
  }

  const response = await fetch(`/api/rag/documents?${params}`)

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData.message || 'Failed to fetch RAG documents')
  }

  return response.json()
}

/**
 * API service for retrying document processing
 */
async function retryRAGDocument(documentId: string): Promise<{ job_id: string; status: string }> {
  const response = await fetch(`/api/rag/retry/${documentId}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw {
      code: errorData.code || 'RETRY_FAILED',
      message: errorData.message || 'Failed to retry document processing',
      status: response.status,
      details: errorData.details || {},
    } as RAGError
  }

  return response.json()
}

/**
 * API service for deleting RAG document
 */
async function deleteRAGDocument(documentId: string): Promise<{ status: string; document_id: string }> {
  const response = await fetch(`/api/rag/documents/${documentId}`, {
    method: 'DELETE',
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw {
      code: errorData.code || 'DELETE_FAILED',
      message: errorData.message || 'Failed to delete document',
      status: response.status,
      details: errorData.details || {},
    } as RAGError
  }

  return response.json()
}

/**
 * Hook for managing RAG documents
 */
export function useRAGDocuments(options: UseRAGDocumentsOptions): UseRAGDocumentsResult {
  const {
    projectId,
    language = 'kr',
    autoRefresh = false,
    statusFilter,
    limit = 50,
    offset = 0,
  } = options

  const queryClient = useQueryClient()
  const { showSuccess, showError } = useToastHelpers()

  // Query for fetching RAG documents
  const {
    data,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['rag-documents', projectId, statusFilter, limit, offset],
    queryFn: () => fetchRAGDocuments(projectId, {
      statusFilter,
      limit,
      offset,
    }),
    refetchInterval: autoRefresh ? 5000 : undefined, // Auto-refresh every 5 seconds
    staleTime: 2000, // Consider data stale after 2 seconds
  })

  // Mutation for retrying document processing
  const retryMutation = useMutation({
    mutationFn: retryRAGDocument,
    onSuccess: (data) => {
      const successMessage = language === 'kr'
        ? '문서 처리 재시도가 시작되었습니다'
        : 'Document processing retry started'
      
      showSuccess(successMessage)
      
      // Invalidate queries to refresh data
      queryClient.invalidateQueries({ queryKey: ['rag-documents'] })
      queryClient.invalidateQueries({ queryKey: ['rag-jobs'] })
    },
    onError: (error: RAGError) => {
      const errorMessage = error.message || (language === 'kr'
        ? '문서 처리 재시도에 실패했습니다'
        : 'Failed to retry document processing')
      
      if (error.code === 'DOCUMENT_NOT_FOUND') {
        showError(language === 'kr' ? '문서를 찾을 수 없습니다' : 'Document not found')
      } else if (error.code === 'NOT_RETRYABLE') {
        showError(language === 'kr' ? '재시도할 수 없는 상태입니다' : 'Document cannot be retried')
      } else {
        showError(errorMessage)
      }
    },
  })

  // Mutation for deleting document
  const deleteMutation = useMutation({
    mutationFn: deleteRAGDocument,
    onSuccess: (data, documentId) => {
      const successMessage = language === 'kr'
        ? '문서가 삭제되었습니다'
        : 'Document has been deleted'
      
      showSuccess(successMessage)
      
      // Update cache optimistically
      queryClient.setQueryData(
        ['rag-documents', projectId, statusFilter, limit, offset],
        (oldData: RAGDocumentsResponse | undefined) => {
          if (!oldData) return oldData
          
          return {
            ...oldData,
            documents: oldData.documents.filter(doc => doc.id !== documentId),
            total: oldData.total - 1,
          }
        }
      )
      
      // Invalidate queries to refresh data
      queryClient.invalidateQueries({ queryKey: ['rag-documents'] })
    },
    onError: (error: RAGError) => {
      const errorMessage = error.message || (language === 'kr'
        ? '문서 삭제에 실패했습니다'
        : 'Failed to delete document')
      
      if (error.code === 'DOCUMENT_NOT_FOUND') {
        showError(language === 'kr' ? '문서를 찾을 수 없습니다' : 'Document not found')
      } else {
        showError(errorMessage)
      }
    },
  })

  // Retry document function
  const retryDocument = useCallback(async (documentId: string) => {
    await retryMutation.mutateAsync(documentId)
  }, [retryMutation])

  // Delete document function
  const deleteDocument = useCallback(async (documentId: string) => {
    await deleteMutation.mutateAsync(documentId)
  }, [deleteMutation])

  return {
    documents: data?.documents || [],
    summary: data ? {
      total: data.total,
      indexed_count: data.indexed_count,
      processing_count: data.processing_count,
      failed_count: data.failed_count,
    } : null,
    isLoading,
    error,
    refetch,
    retryDocument,
    deleteDocument,
  }
}

/**
 * Hook for getting a single RAG document
 */
export function useRAGDocument(documentId: string | null) {
  const { data: documentsData } = useQuery({
    queryKey: ['rag-documents'],
    enabled: false, // Don't auto-fetch
  })

  if (!documentId || !documentsData) return null
  
  return documentsData.documents?.find((doc: RAGDocument) => doc.id === documentId) || null
}