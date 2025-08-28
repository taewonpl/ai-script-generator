import { useMutation, useQueryClient } from '@tanstack/react-query'
import { generationHttp } from '@/shared/services/api/clients'
import { AxiosError } from 'axios'

/**
 * Job control types
 */
export interface CancelJobRequest {
  jobId: string
  reason?: string
}

export interface CancelJobResponse {
  success: boolean
  jobId: string
  message: string
  canceledAt: string
}

export interface JobControlError {
  message: string
  code?: string
  jobId: string
}

/**
 * Hook for job control operations (cancel, pause, resume)
 *
 * Features:
 * - Idempotent job cancellation
 * - TanStack Query mutation
 * - Optimistic updates
 * - Error handling
 * - Cache invalidation
 */
export function useJobControl() {
  const queryClient = useQueryClient()

  // Cancel job mutation
  const cancelJobMutation = useMutation<
    CancelJobResponse,
    AxiosError,
    CancelJobRequest
  >({
    mutationFn: async ({ jobId, reason }: CancelJobRequest) => {
      console.log(`🛑 Canceling job: ${jobId}`, { reason })

      // Using generationHttp helper - automatically returns .data (no more regression risk!)
      return await generationHttp.delete<CancelJobResponse>(
        `/jobs/${jobId}`,
        {
          data: { reason },
          headers: {
            'Content-Type': 'application/json',
          },
        },
      )
    },

    // Optimistic update - immediately mark job as canceling
    onMutate: async ({
      jobId,
    }): Promise<{
      previousJob: unknown
      previousJobs: unknown
      jobId: string
    }> => {
      // Cancel any outgoing refetches for jobs
      await queryClient.cancelQueries({ queryKey: ['jobs'] })
      await queryClient.cancelQueries({ queryKey: ['job', jobId] })

      // Snapshot previous values
      const previousJob = queryClient.getQueryData(['job', jobId])
      const previousJobs = queryClient.getQueryData(['jobs'])

      // Optimistically update job status
      queryClient.setQueryData(['job', jobId], (old: any) => ({
        ...old,
        status: 'canceling',
        updatedAt: new Date().toISOString(),
      }))

      // Update jobs list
      queryClient.setQueryData(['jobs'], (old: any) => {
        if (!old?.data) return old

        return {
          ...old,
          data: old.data.map((job: any) =>
            job.id === jobId
              ? {
                  ...job,
                  status: 'canceling',
                  updatedAt: new Date().toISOString(),
                }
              : job,
          ),
        }
      })

      return { previousJob, previousJobs, jobId }
    },

    // Success - update with server response
    onSuccess: (data, { jobId }) => {
      console.log('✅ Job canceled successfully:', data)

      // Update individual job query
      queryClient.setQueryData(['job', jobId], (old: any) => ({
        ...old,
        status: 'canceled',
        canceledAt: data.canceledAt,
        updatedAt: new Date().toISOString(),
      }))

      // Update jobs list
      queryClient.setQueryData(['jobs'], (old: any) => {
        if (!old?.data) return old

        return {
          ...old,
          data: old.data.map((job: any) =>
            job.id === jobId
              ? {
                  ...job,
                  status: 'canceled',
                  canceledAt: data.canceledAt,
                  updatedAt: new Date().toISOString(),
                }
              : job,
          ),
        }
      })

      // Invalidate related queries to ensure consistency
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      queryClient.invalidateQueries({ queryKey: ['job-statistics'] })
    },

    // Error - rollback optimistic updates
    onError: (error, { jobId }, context) => {
      console.error('❌ Failed to cancel job:', error)

      // Rollback optimistic updates
      if (
        context &&
        typeof context === 'object' &&
        'previousJob' in context &&
        context.previousJob !== undefined
      ) {
        queryClient.setQueryData(['job', jobId], context.previousJob)
      }
      if (
        context &&
        typeof context === 'object' &&
        'previousJobs' in context &&
        context.previousJobs !== undefined
      ) {
        queryClient.setQueryData(['jobs'], context.previousJobs)
      }

      // Handle specific error cases
      if (error.response?.status === 404) {
        console.warn('⚠️ Job not found, may already be completed or canceled')
      } else if (error.response?.status === 409) {
        console.warn('⚠️ Job is already canceled or completed')
        // Still update local state to reflect server state
        queryClient.invalidateQueries({ queryKey: ['jobs'] })
        queryClient.invalidateQueries({ queryKey: ['job', jobId] })
      }
    },

    // Always refresh after mutation
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
    },
  })

  // Helper function for idempotent job cancellation
  const cancelJob = async (
    jobId: string,
    reason?: string,
  ): Promise<boolean> => {
    try {
      await cancelJobMutation.mutateAsync({ jobId, reason })
      return true
    } catch (error) {
      // Handle idempotent cases as success
      if (error instanceof AxiosError) {
        if (error.response?.status === 409) {
          console.log('✅ Job was already canceled or completed')
          return true
        }
        if (error.response?.status === 404) {
          console.log('✅ Job not found (may have been cleaned up)')
          return true
        }
      }
      throw error
    }
  }

  // Check if job can be canceled
  const canCancelJob = (jobStatus: string): boolean => {
    const cancelableStatuses = ['pending', 'running', 'queued', 'paused']
    return cancelableStatuses.includes(jobStatus.toLowerCase())
  }

  // Get cancellation error details
  const getCancelError = (): JobControlError | null => {
    const error = cancelJobMutation.error
    if (!error) return null

    const jobId = cancelJobMutation.variables?.jobId || 'unknown'

    if (error.response?.status === 404) {
      return {
        message: 'Job not found or already completed',
        code: 'JOB_NOT_FOUND',
        jobId,
      }
    }

    if (error.response?.status === 409) {
      return {
        message: 'Job is already canceled or completed',
        code: 'JOB_ALREADY_FINISHED',
        jobId,
      }
    }

    if (error.response?.status === 403) {
      return {
        message: 'Not authorized to cancel this job',
        code: 'INSUFFICIENT_PERMISSIONS',
        jobId,
      }
    }

    return {
      message:
        (error.response?.data as any)?.message ||
        error.message ||
        'Failed to cancel job',
      code: (error.response?.data as any)?.code || 'CANCEL_ERROR',
      jobId,
    }
  }

  return {
    // Mutation state
    cancelJob,
    isCanceling: cancelJobMutation.isPending,
    cancelError: getCancelError(),
    canCancelJob,

    // Mutation object (for advanced usage)
    cancelJobMutation,

    // Helper functions
    reset: () => cancelJobMutation.reset(),
  }
}
