/**
 * Hook for handling project deletion with optimistic updates and error recovery
 * Provides complete deletion workflow with telemetry and state management
 */

import { useState, useCallback } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'

import { deleteProject, type DeleteProjectOptions, type ProjectDeleteError } from '@/shared/services/api/projects'
import { useToastHelpers } from '@/shared/ui/components/toast'
import type { Project } from '@/shared/api/types'

export interface UseProjectDeleteOptions {
  /** Language for UI messages */
  language?: 'kr' | 'en'
  /** Whether to redirect after successful deletion */
  redirectAfterDelete?: boolean
  /** Custom redirect path (defaults to /projects) */
  redirectPath?: string
  /** Callback after successful deletion */
  onSuccess?: (projectId: string) => void
  /** Callback after failed deletion */
  onError?: (error: ProjectDeleteError) => void
}

export interface ProjectDeleteState {
  /** Whether deletion is in progress */
  isDeleting: boolean
  /** Error that occurred during deletion */
  error: ProjectDeleteError | null
  /** Delete the project */
  deleteProject: (projectId: string, projectName: string, options?: Partial<DeleteProjectOptions>) => Promise<void>
  /** Clear error state */
  clearError: () => void
  /** Retry the last failed deletion */
  retryDelete: () => Promise<void>
}

/**
 * Hook for managing project deletion workflow
 */
export function useProjectDelete(options: UseProjectDeleteOptions = {}): ProjectDeleteState {
  const {
    language = 'kr',
    redirectAfterDelete = true,
    redirectPath = '/projects',
    onSuccess,
    onError,
  } = options

  const [lastDeleteParams, setLastDeleteParams] = useState<{
    projectId: string
    projectName: string
    options: DeleteProjectOptions
  } | null>(null)

  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { showSuccess, showError } = useToastHelpers()

  // Mutation for project deletion
  const deleteMutation = useMutation({
    mutationFn: async ({
      projectId,
      projectName,
      options,
    }: {
      projectId: string
      projectName: string
      options: DeleteProjectOptions
    }) => {
      // Record deletion attempt
      recordDeletionMetrics('deletion_started', { projectId, deleteId: options.deleteId })

      await deleteProject(projectId, options)

      return { projectId, projectName }
    },
    
    onMutate: async ({ projectId, projectName: _projectName }) => {
      // Optimistic update: remove project from lists
      await queryClient.cancelQueries({ queryKey: ['projects'] })

      // Snapshot previous data for rollback
      const previousProjects = queryClient.getQueryData<{ data: Project[] }>(['projects'])
      
      // Optimistically remove the project
      if (previousProjects?.data) {
        queryClient.setQueryData(['projects'], {
          ...previousProjects,
          data: previousProjects.data.filter(project => project.id !== projectId),
        })
      }

      // Also remove from individual project cache
      queryClient.removeQueries({ queryKey: ['project', projectId] })

      recordDeletionMetrics('optimistic_update', { projectId })

      return { previousProjects, projectId, projectName: _projectName }
    },

    onSuccess: (data, _variables, _context) => {
      const { projectId, projectName } = data

      // Show success message
      const successMessage = language === 'kr'
        ? `프로젝트 "${projectName}"이(가) 삭제되었습니다`
        : `Project "${projectName}" has been deleted`
      
      showSuccess(successMessage)

      // Invalidate and refetch projects list to ensure consistency
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      
      // Record successful deletion
      recordDeletionMetrics('deletion_success', { 
        projectId, 
        deleteId: lastDeleteParams?.options.deleteId 
      })

      // Callback
      onSuccess?.(projectId)

      // Clear last delete params
      setLastDeleteParams(null)

      // Navigate away from project if needed
      if (redirectAfterDelete) {
        navigate(redirectPath)
      }
    },

    onError: (error: ProjectDeleteError, _variables, context) => {
      const deleteError = error as ProjectDeleteError

      // Rollback optimistic update
      if (context?.previousProjects) {
        queryClient.setQueryData(['projects'], context.previousProjects)
      }

      // Handle specific error types
      let errorMessage: string
      let shouldShowToast = true

      if (deleteError.code === 'ACTIVE_GENERATION_JOBS') {
        errorMessage = language === 'kr'
          ? '생성 작업을 먼저 중단하세요'
          : 'Please stop generation jobs first'
      } else if (deleteError.code === 'PROJECT_NOT_FOUND') {
        // 404 - already deleted, treat as success
        errorMessage = language === 'kr'
          ? '프로젝트가 이미 삭제되었습니다'
          : 'Project was already deleted'
        
        // Show as success toast and clean up optimistic state
        showSuccess(errorMessage)
        queryClient.invalidateQueries({ queryKey: ['projects'] })
        
        if (redirectAfterDelete) {
          navigate(redirectPath)
        }
        
        shouldShowToast = false
        recordDeletionMetrics('deletion_already_deleted', { 
          projectId: context?.projectId,
          deleteId: lastDeleteParams?.options.deleteId 
        })
        return
      } else {
        errorMessage = deleteError.message || (language === 'kr' 
          ? '프로젝트 삭제에 실패했습니다'
          : 'Failed to delete project')
      }

      if (shouldShowToast) {
        showError(errorMessage)
      }

      // Record failure
      recordDeletionMetrics('deletion_failed', {
        projectId: context?.projectId,
        deleteId: lastDeleteParams?.options.deleteId,
        errorCode: deleteError.code,
        errorStatus: deleteError.status,
      })

      // Callback
      onError?.(deleteError)
    },
  })

  // Main delete function
  const handleDelete = useCallback(async (
    projectId: string,
    projectName: string,
    options: Partial<DeleteProjectOptions> = {}
  ) => {
    const deleteOptions: DeleteProjectOptions = {
      deleteId: crypto.randomUUID?.() || `del-${Date.now()}-${Math.random()}`,
      ...options,
    }

    // Store for retry purposes
    setLastDeleteParams({
      projectId,
      projectName,
      options: deleteOptions,
    })

    await deleteMutation.mutateAsync({
      projectId,
      projectName,
      options: deleteOptions,
    })
  }, [deleteMutation])

  // Retry function
  const retryDelete = useCallback(async () => {
    if (!lastDeleteParams) {
      throw new Error('No previous deletion to retry')
    }

    const { projectId, projectName, options } = lastDeleteParams
    
    // Generate new delete ID for retry to avoid idempotency conflicts
    const retryOptions = {
      ...options,
      deleteId: crypto.randomUUID?.() || `del-retry-${Date.now()}-${Math.random()}`,
    }

    setLastDeleteParams({
      projectId,
      projectName,
      options: retryOptions,
    })

    await deleteMutation.mutateAsync({
      projectId,
      projectName,
      options: retryOptions,
    })
  }, [lastDeleteParams, deleteMutation])

  // Clear error
  const clearError = useCallback(() => {
    deleteMutation.reset()
  }, [deleteMutation])

  return {
    isDeleting: deleteMutation.isPending,
    error: deleteMutation.error as ProjectDeleteError | null,
    deleteProject: handleDelete,
    clearError,
    retryDelete,
  }
}

/**
 * Record deletion metrics for monitoring
 */
function recordDeletionMetrics(event: string, data: Record<string, any>) {
  const timestamp = new Date().toISOString()
  const logData = {
    event,
    timestamp,
    ...data,
  }

  if (import.meta.env.DEV) {
    console.log('📊 Project Deletion Metrics:', logData)
  }

  // In production, send to analytics/monitoring service
  // Example: analytics.track(event, logData)
}