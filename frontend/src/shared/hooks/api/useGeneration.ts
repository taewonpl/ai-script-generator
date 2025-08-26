import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { UseQueryOptions } from '@tanstack/react-query'
import { generationService } from '@/shared/api/services/generation'
import type {
  Generation,
  GenerationRequest,
  GenerationStatus,
  ListResponse,
} from '@/shared/types/api'
import { projectKeys } from './useProjects'

// Query Keys
export const generationKeys = {
  all: ['generations'] as const,
  lists: () => [...generationKeys.all, 'list'] as const,
  list: (filters?: any) => [...generationKeys.lists(), { filters }] as const,
  details: () => [...generationKeys.all, 'detail'] as const,
  detail: (id: string) => [...generationKeys.details(), id] as const,
  history: (projectId?: string) =>
    [...generationKeys.all, 'history', { projectId }] as const,
  active: () => [...generationKeys.all, 'active'] as const,
  completed: () => [...generationKeys.all, 'completed'] as const,
  user: () => [...generationKeys.all, 'user'] as const,
  queue: () => [...generationKeys.all, 'queue'] as const,
  queuePosition: (id: string) => [...generationKeys.queue(), id] as const,
  models: () => [...generationKeys.all, 'models'] as const,
  model: (id: string) => [...generationKeys.models(), id] as const,
  templates: () => [...generationKeys.all, 'templates'] as const,
  presets: () => [...generationKeys.all, 'presets'] as const,
  stats: (period?: string) =>
    [...generationKeys.all, 'stats', { period }] as const,
  modelUsage: (period?: string) =>
    [...generationKeys.all, 'modelUsage', { period }] as const,
  costs: (period?: string) =>
    [...generationKeys.all, 'costs', { period }] as const,
  limits: () => [...generationKeys.all, 'limits'] as const,
}

// Generations List Hook
export function useGenerations(
  filters: {
    project_id?: string
    episode_id?: string
    status?: GenerationStatus
    page?: number
    limit?: number
  } = {},
  options?: Omit<
    UseQueryOptions<ListResponse<Generation>>,
    'queryKey' | 'queryFn'
  >,
) {
  return useQuery({
    queryKey: generationKeys.list(filters),
    queryFn: () => generationService.getGenerations(filters),
    staleTime: 1000 * 30, // 30 seconds (fast-changing data)
    gcTime: 1000 * 60 * 10, // 10 minutes
    ...options,
  })
}

// Single Generation Hook
export function useGeneration(
  generationId: string,
  options?: Omit<UseQueryOptions<Generation>, 'queryKey' | 'queryFn'>,
) {
  return useQuery({
    queryKey: generationKeys.detail(generationId),
    queryFn: () => generationService.getGeneration(generationId),
    enabled: !!generationId,
    staleTime: 1000 * 30, // 30 seconds
    gcTime: 1000 * 60 * 10, // 10 minutes
    refetchInterval: data => {
      // Auto-refresh if generation is in progress
      if (!data) return false
      const status = (data as any)?.status
      if (status === 'pending' || status === 'in_progress') {
        return 2000 // 2 seconds
      }
      return false
    },
    ...options,
  })
}

// Generation History Hook
export function useGenerationHistory(
  projectId?: string,
  limit = 50,
  options?: Omit<
    UseQueryOptions<ListResponse<Generation>>,
    'queryKey' | 'queryFn'
  >,
) {
  return useQuery({
    queryKey: generationKeys.history(projectId),
    queryFn: () => generationService.getGenerationHistory(projectId, limit),
    staleTime: 1000 * 60 * 2, // 2 minutes
    gcTime: 1000 * 60 * 30, // 30 minutes
    ...options,
  })
}

// Active Generations Hook
export function useActiveGenerations(
  options?: Omit<UseQueryOptions<Generation[]>, 'queryKey' | 'queryFn'>,
) {
  return useQuery({
    queryKey: generationKeys.active(),
    queryFn: () => generationService.getActiveGenerations(),
    staleTime: 1000 * 10, // 10 seconds
    gcTime: 1000 * 60 * 5, // 5 minutes
    refetchInterval: 5000, // Refresh every 5 seconds
    ...options,
  })
}

// User Generations Hook
export function useUserGenerations(
  page = 1,
  limit = 20,
  options?: Omit<
    UseQueryOptions<ListResponse<Generation>>,
    'queryKey' | 'queryFn'
  >,
) {
  return useQuery({
    queryKey: [...generationKeys.user(), { page, limit }],
    queryFn: () => generationService.getUserGenerations(page, limit),
    staleTime: 1000 * 60 * 2, // 2 minutes
    gcTime: 1000 * 60 * 30, // 30 minutes
    ...options,
  })
}

// Completed Generations Hook
export function useCompletedGenerations(
  page = 1,
  limit = 20,
  options?: Omit<
    UseQueryOptions<ListResponse<Generation>>,
    'queryKey' | 'queryFn'
  >,
) {
  return useQuery({
    queryKey: [...generationKeys.completed(), { page, limit }],
    queryFn: () => generationService.getCompletedGenerations(page, limit),
    staleTime: 1000 * 60 * 5, // 5 minutes
    gcTime: 1000 * 60 * 30, // 30 minutes
    ...options,
  })
}

// Available Models Hook
export function useAvailableModels(
  options?: Omit<UseQueryOptions<any[]>, 'queryKey' | 'queryFn'>,
) {
  return useQuery({
    queryKey: generationKeys.models(),
    queryFn: () => generationService.getAvailableModels(),
    staleTime: 1000 * 60 * 30, // 30 minutes
    gcTime: 1000 * 60 * 60, // 1 hour
    ...options,
  })
}

// Model Info Hook
export function useModelInfo(
  modelId: string,
  options?: Omit<UseQueryOptions<any>, 'queryKey' | 'queryFn'>,
) {
  return useQuery({
    queryKey: generationKeys.model(modelId),
    queryFn: () => generationService.getModelInfo(modelId),
    enabled: !!modelId,
    staleTime: 1000 * 60 * 30, // 30 minutes
    gcTime: 1000 * 60 * 60, // 1 hour
    ...options,
  })
}

// Queue Status Hook
export function useQueueStatus(
  options?: Omit<UseQueryOptions<any>, 'queryKey' | 'queryFn'>,
) {
  return useQuery({
    queryKey: generationKeys.queue(),
    queryFn: () => generationService.getQueueStatus(),
    staleTime: 1000 * 5, // 5 seconds
    gcTime: 1000 * 60 * 5, // 5 minutes
    refetchInterval: 5000, // Refresh every 5 seconds
    ...options,
  })
}

// Queue Position Hook
export function useQueuePosition(
  generationId: string,
  options?: Omit<UseQueryOptions<any>, 'queryKey' | 'queryFn'>,
) {
  return useQuery({
    queryKey: generationKeys.queuePosition(generationId),
    queryFn: () => generationService.getQueuePosition(generationId),
    enabled: !!generationId,
    staleTime: 1000 * 5, // 5 seconds
    gcTime: 1000 * 60 * 5, // 5 minutes
    refetchInterval: 3000, // Refresh every 3 seconds
    ...options,
  })
}

// Generation Stats Hook
export function useGenerationStats(
  period: 'day' | 'week' | 'month' = 'week',
  options?: Omit<UseQueryOptions<any>, 'queryKey' | 'queryFn'>,
) {
  return useQuery({
    queryKey: generationKeys.stats(period),
    queryFn: () => generationService.getGenerationStats(period),
    staleTime: 1000 * 60 * 5, // 5 minutes
    gcTime: 1000 * 60 * 30, // 30 minutes
    ...options,
  })
}

// Usage Costs Hook
export function useUsageCosts(
  period: 'day' | 'week' | 'month' | 'year' = 'month',
  options?: Omit<UseQueryOptions<any>, 'queryKey' | 'queryFn'>,
) {
  return useQuery({
    queryKey: generationKeys.costs(period),
    queryFn: () => generationService.getUsageCosts(period),
    staleTime: 1000 * 60 * 5, // 5 minutes
    gcTime: 1000 * 60 * 30, // 30 minutes
    ...options,
  })
}

// Usage Limits Hook
export function useUsageLimits(
  options?: Omit<UseQueryOptions<any>, 'queryKey' | 'queryFn'>,
) {
  return useQuery({
    queryKey: generationKeys.limits(),
    queryFn: () => generationService.getUsageLimits(),
    staleTime: 1000 * 60 * 2, // 2 minutes
    gcTime: 1000 * 60 * 10, // 10 minutes
    refetchInterval: 1000 * 60 * 5, // Refresh every 5 minutes
    ...options,
  })
}

// Create Generation Mutation
export function useCreateGeneration() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: GenerationRequest) =>
      generationService.createGeneration(data),
    onSuccess: (newGeneration, { project_id }) => {
      // Add new generation to cache
      queryClient.setQueryData(
        generationKeys.detail(newGeneration.id),
        newGeneration,
      )

      // Invalidate relevant lists
      queryClient.invalidateQueries({ queryKey: generationKeys.lists() })
      queryClient.invalidateQueries({ queryKey: generationKeys.active() })
      queryClient.invalidateQueries({ queryKey: generationKeys.user() })
      queryClient.invalidateQueries({
        queryKey: generationKeys.history(project_id),
      })
      queryClient.invalidateQueries({ queryKey: generationKeys.queue() })

      // Update project and episode stats if needed
      queryClient.invalidateQueries({ queryKey: projectKeys.stats(project_id) })
    },
  })
}

// Update Generation Mutation
export function useUpdateGeneration() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      generationId,
      data,
    }: {
      generationId: string
      data: Partial<GenerationRequest>
    }) => generationService.updateGeneration(generationId, data),
    onSuccess: (updatedGeneration, { generationId }) => {
      // Update generation in cache
      queryClient.setQueryData(
        generationKeys.detail(generationId),
        updatedGeneration,
      )

      // Invalidate related queries
      queryClient.invalidateQueries({ queryKey: generationKeys.lists() })
    },
  })
}

// Cancel Generation Mutation
export function useCancelGeneration() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (generationId: string) =>
      generationService.cancelGeneration(generationId),
    onSuccess: (cancelledGeneration, generationId) => {
      // Update generation in cache
      queryClient.setQueryData(
        generationKeys.detail(generationId),
        cancelledGeneration,
      )

      // Invalidate relevant lists
      queryClient.invalidateQueries({ queryKey: generationKeys.lists() })
      queryClient.invalidateQueries({ queryKey: generationKeys.active() })
      queryClient.invalidateQueries({ queryKey: generationKeys.queue() })
    },
  })
}

// Retry Generation Mutation
export function useRetryGeneration() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (generationId: string) =>
      generationService.retryGeneration(generationId),
    onSuccess: (retriedGeneration, generationId) => {
      // Update generation in cache
      queryClient.setQueryData(
        generationKeys.detail(generationId),
        retriedGeneration,
      )

      // Invalidate relevant lists
      queryClient.invalidateQueries({ queryKey: generationKeys.lists() })
      queryClient.invalidateQueries({ queryKey: generationKeys.active() })
      queryClient.invalidateQueries({ queryKey: generationKeys.queue() })
    },
  })
}

// Delete Generation Mutation
export function useDeleteGeneration() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (generationId: string) =>
      generationService.deleteGeneration(generationId),
    onSuccess: (_, generationId) => {
      // Remove from cache
      queryClient.removeQueries({
        queryKey: generationKeys.detail(generationId),
      })

      // Invalidate lists
      queryClient.invalidateQueries({ queryKey: generationKeys.lists() })
      queryClient.invalidateQueries({ queryKey: generationKeys.user() })
      queryClient.invalidateQueries({ queryKey: generationKeys.completed() })
      queryClient.invalidateQueries({ queryKey: generationKeys.history() })
    },
  })
}

// Batch Operations
export function useBatchCreateGenerations() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (requests: GenerationRequest[]) =>
      generationService.batchCreateGenerations(requests),
    onSuccess: result => {
      // Add successful generations to cache
      result.generations.forEach((generation: any) => {
        queryClient.setQueryData(
          generationKeys.detail(generation.id),
          generation,
        )
      })

      // Invalidate relevant lists
      queryClient.invalidateQueries({ queryKey: generationKeys.lists() })
      queryClient.invalidateQueries({ queryKey: generationKeys.active() })
      queryClient.invalidateQueries({ queryKey: generationKeys.user() })
      queryClient.invalidateQueries({ queryKey: generationKeys.queue() })
    },
  })
}

export function useBatchCancelGenerations() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (generationIds: string[]) =>
      generationService.batchCancelGenerations(generationIds),
    onSuccess: (_, generationIds) => {
      // Invalidate affected generations
      generationIds.forEach(id => {
        queryClient.invalidateQueries({ queryKey: generationKeys.detail(id) })
      })

      // Invalidate lists
      queryClient.invalidateQueries({ queryKey: generationKeys.lists() })
      queryClient.invalidateQueries({ queryKey: generationKeys.active() })
      queryClient.invalidateQueries({ queryKey: generationKeys.queue() })
    },
  })
}

export function useBatchDeleteGenerations() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (generationIds: string[]) =>
      generationService.batchDeleteGenerations(generationIds),
    onSuccess: (_, generationIds) => {
      // Remove from cache
      generationIds.forEach(id => {
        queryClient.removeQueries({ queryKey: generationKeys.detail(id) })
      })

      // Invalidate lists
      queryClient.invalidateQueries({ queryKey: generationKeys.lists() })
      queryClient.invalidateQueries({ queryKey: generationKeys.user() })
      queryClient.invalidateQueries({ queryKey: generationKeys.completed() })
      queryClient.invalidateQueries({ queryKey: generationKeys.history() })
    },
  })
}

// Cache Utilities
export function useGenerationCacheUtils() {
  const queryClient = useQueryClient()

  const updateGenerationStatus = (
    generationId: string,
    status: GenerationStatus,
    progress?: number,
  ) => {
    queryClient.setQueryData(
      generationKeys.detail(generationId),
      (old: any) => {
        if (!old) return old
        return {
          ...old,
          data: {
            ...old.data,
            status,
            progress: progress !== undefined ? progress : old.data.progress,
            updated_at: new Date().toISOString(),
          },
        }
      },
    )
  }

  const prefetchGeneration = (generationId: string) => {
    queryClient.prefetchQuery({
      queryKey: generationKeys.detail(generationId),
      queryFn: () => generationService.getGeneration(generationId),
      staleTime: 1000 * 30,
    })
  }

  const invalidateGenerationData = (generationId?: string) => {
    if (generationId) {
      queryClient.invalidateQueries({
        queryKey: generationKeys.detail(generationId),
      })
    } else {
      queryClient.invalidateQueries({ queryKey: generationKeys.lists() })
    }
  }

  return {
    updateGenerationStatus,
    prefetchGeneration,
    invalidateGenerationData,
  }
}
