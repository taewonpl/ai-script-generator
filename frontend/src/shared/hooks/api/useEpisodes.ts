import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { UseQueryOptions } from '@tanstack/react-query'
import { projectService } from '@/shared/api/services/project'
import type {
  Episode,
  EpisodeCreateRequest,
  EpisodeUpdateRequest,
  ListResponse,
} from '@/shared/types/api'
import { projectKeys } from './useProjects'

// Query Keys
export const episodeKeys = {
  all: ['episodes'] as const,
  lists: () => [...episodeKeys.all, 'list'] as const,
  list: (projectId: string) => [...episodeKeys.lists(), projectId] as const,
  details: () => [...episodeKeys.all, 'detail'] as const,
  detail: (projectId: string, episodeId: string) =>
    [...episodeKeys.details(), projectId, episodeId] as const,
  nextNumber: (projectId: string) =>
    [...episodeKeys.all, 'nextNumber', projectId] as const,
}

// Episodes List Hook
export function useEpisodes(
  projectId: string,
  page = 1,
  limit = 50,
  options?: Omit<
    UseQueryOptions<ListResponse<Episode>>,
    'queryKey' | 'queryFn'
  >,
) {
  return useQuery({
    queryKey: episodeKeys.list(projectId),
    queryFn: () => projectService.getEpisodes(projectId, page, limit),
    enabled: !!projectId,
    staleTime: 1000 * 60 * 5, // 5 minutes
    gcTime: 1000 * 60 * 30, // 30 minutes
    ...options,
  })
}

// All Episodes Hook (without pagination)
export function useAllEpisodes(
  projectId: string,
  options?: Omit<UseQueryOptions<Episode[]>, 'queryKey' | 'queryFn'>,
) {
  return useQuery({
    queryKey: [...episodeKeys.list(projectId), 'all'],
    queryFn: () => projectService.getAllEpisodes(projectId),
    enabled: !!projectId,
    staleTime: 1000 * 60 * 5, // 5 minutes
    gcTime: 1000 * 60 * 30, // 30 minutes
    ...options,
  })
}

// Single Episode Hook
export function useEpisode(
  projectId: string,
  episodeId: string,
  options?: Omit<UseQueryOptions<Episode>, 'queryKey' | 'queryFn'>,
) {
  return useQuery({
    queryKey: episodeKeys.detail(projectId, episodeId),
    queryFn: () => projectService.getEpisode(projectId, episodeId),
    enabled: !!projectId && !!episodeId,
    staleTime: 1000 * 60 * 5, // 5 minutes
    gcTime: 1000 * 60 * 30, // 30 minutes
    ...options,
  })
}

// Next Episode Number Hook
export function useNextEpisodeNumber(
  projectId: string,
  options?: Omit<
    UseQueryOptions<{ next_episode_number: number }>,
    'queryKey' | 'queryFn'
  >,
) {
  return useQuery({
    queryKey: episodeKeys.nextNumber(projectId),
    queryFn: () => projectService.getNextEpisodeNumber(projectId),
    enabled: !!projectId,
    staleTime: 1000 * 60 * 2, // 2 minutes
    gcTime: 1000 * 60 * 10, // 10 minutes
    ...options,
  })
}

// Create Episode Mutation
export function useCreateEpisode() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: EpisodeCreateRequest) =>
      projectService.createEpisode(data),
    onSuccess: (newEpisode, { project_id }) => {
      // Add new episode to cache
      queryClient.setQueryData(
        episodeKeys.detail(project_id, newEpisode.data.id),
        newEpisode,
      )

      // Invalidate episodes lists
      queryClient.invalidateQueries({ queryKey: episodeKeys.list(project_id) })
      queryClient.invalidateQueries({
        queryKey: [...episodeKeys.list(project_id), 'all'],
      })
      queryClient.invalidateQueries({
        queryKey: episodeKeys.nextNumber(project_id),
      })

      // Invalidate project data to update episode count
      queryClient.invalidateQueries({
        queryKey: projectKeys.detail(project_id),
      })
      queryClient.invalidateQueries({ queryKey: projectKeys.stats(project_id) })
    },
  })
}

// Update Episode Mutation
export function useUpdateEpisode() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      projectId,
      episodeId,
      data,
    }: {
      projectId: string
      episodeId: string
      data: EpisodeUpdateRequest
    }) => projectService.updateEpisode(projectId, episodeId, data),
    onSuccess: (updatedEpisode, { projectId, episodeId }) => {
      // Update episode in cache
      queryClient.setQueryData(
        episodeKeys.detail(projectId, episodeId),
        updatedEpisode,
      )

      // Invalidate related queries
      queryClient.invalidateQueries({ queryKey: episodeKeys.list(projectId) })
      queryClient.invalidateQueries({
        queryKey: [...episodeKeys.list(projectId), 'all'],
      })
      queryClient.invalidateQueries({ queryKey: projectKeys.detail(projectId) })
      queryClient.invalidateQueries({ queryKey: projectKeys.stats(projectId) })
    },
  })
}

// Delete Episode Mutation
export function useDeleteEpisode() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      projectId,
      episodeId,
    }: {
      projectId: string
      episodeId: string
    }) => projectService.deleteEpisode(projectId, episodeId),
    onSuccess: (_, { projectId, episodeId }) => {
      // Remove from cache
      queryClient.removeQueries({
        queryKey: episodeKeys.detail(projectId, episodeId),
      })

      // Invalidate lists and related data
      queryClient.invalidateQueries({ queryKey: episodeKeys.list(projectId) })
      queryClient.invalidateQueries({
        queryKey: [...episodeKeys.list(projectId), 'all'],
      })
      queryClient.invalidateQueries({
        queryKey: episodeKeys.nextNumber(projectId),
      })
      queryClient.invalidateQueries({ queryKey: projectKeys.detail(projectId) })
      queryClient.invalidateQueries({ queryKey: projectKeys.stats(projectId) })
    },
  })
}

// Reorder Episodes Mutation
export function useReorderEpisodes() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      projectId,
      episodeIds,
    }: {
      projectId: string
      episodeIds: string[]
    }) => projectService.reorderEpisodes(projectId, episodeIds),
    onSuccess: (reorderedEpisodes, { projectId }) => {
      // Update episodes in cache
      reorderedEpisodes.data.forEach(episode => {
        queryClient.setQueryData(episodeKeys.detail(projectId, episode.id), {
          data: episode,
          success: true,
        })
      })

      // Invalidate lists to refresh order
      queryClient.invalidateQueries({ queryKey: episodeKeys.list(projectId) })
      queryClient.invalidateQueries({
        queryKey: [...episodeKeys.list(projectId), 'all'],
      })
    },
  })
}

// Duplicate Episode Mutation
export function useDuplicateEpisode() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      projectId,
      episodeId,
    }: {
      projectId: string
      episodeId: string
    }) => projectService.duplicateEpisode(projectId, episodeId),
    onSuccess: (newEpisode, { projectId }) => {
      // Add duplicated episode to cache
      queryClient.setQueryData(
        episodeKeys.detail(projectId, newEpisode.data.id),
        newEpisode,
      )

      // Invalidate lists and related data
      queryClient.invalidateQueries({ queryKey: episodeKeys.list(projectId) })
      queryClient.invalidateQueries({
        queryKey: [...episodeKeys.list(projectId), 'all'],
      })
      queryClient.invalidateQueries({
        queryKey: episodeKeys.nextNumber(projectId),
      })
      queryClient.invalidateQueries({ queryKey: projectKeys.detail(projectId) })
      queryClient.invalidateQueries({ queryKey: projectKeys.stats(projectId) })
    },
  })
}

// Batch Delete Episodes Mutation
export function useBatchDeleteEpisodes() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      projectId,
      episodeIds,
    }: {
      projectId: string
      episodeIds: string[]
    }) => projectService.batchDeleteEpisodes(projectId, episodeIds),
    onSuccess: (_, { projectId, episodeIds }) => {
      // Remove deleted episodes from cache
      episodeIds.forEach(episodeId => {
        queryClient.removeQueries({
          queryKey: episodeKeys.detail(projectId, episodeId),
        })
      })

      // Invalidate lists and related data
      queryClient.invalidateQueries({ queryKey: episodeKeys.list(projectId) })
      queryClient.invalidateQueries({
        queryKey: [...episodeKeys.list(projectId), 'all'],
      })
      queryClient.invalidateQueries({
        queryKey: episodeKeys.nextNumber(projectId),
      })
      queryClient.invalidateQueries({ queryKey: projectKeys.detail(projectId) })
      queryClient.invalidateQueries({ queryKey: projectKeys.stats(projectId) })
    },
  })
}

// Optimistic Updates Helper
export function useOptimisticEpisodeUpdate() {
  const queryClient = useQueryClient()

  const updateEpisodeOptimistically = (
    projectId: string,
    episodeId: string,
    updates: Partial<Episode>,
  ) => {
    queryClient.setQueryData(
      episodeKeys.detail(projectId, episodeId),
      (old: any) => {
        if (!old) return old
        return {
          ...old,
          data: { ...old.data, ...updates },
        }
      },
    )

    // Also update in lists
    queryClient.setQueryData(episodeKeys.list(projectId), (old: any) => {
      if (!old) return old
      return {
        ...old,
        data: {
          ...old.data,
          items: old.data.items.map((episode: Episode) =>
            episode.id === episodeId ? { ...episode, ...updates } : episode,
          ),
        },
      }
    })

    queryClient.setQueryData(
      [...episodeKeys.list(projectId), 'all'],
      (old: any) => {
        if (!old) return old
        return {
          ...old,
          data: old.data.map((episode: Episode) =>
            episode.id === episodeId ? { ...episode, ...updates } : episode,
          ),
        }
      },
    )
  }

  return { updateEpisodeOptimistically }
}

// Cache Utilities
export function useEpisodeCacheUtils() {
  const queryClient = useQueryClient()

  const prefetchEpisode = (projectId: string, episodeId: string) => {
    queryClient.prefetchQuery({
      queryKey: episodeKeys.detail(projectId, episodeId),
      queryFn: () => projectService.getEpisode(projectId, episodeId),
      staleTime: 1000 * 60 * 5, // 5 minutes
    })
  }

  const invalidateEpisodeData = (projectId: string, episodeId?: string) => {
    if (episodeId) {
      queryClient.invalidateQueries({
        queryKey: episodeKeys.detail(projectId, episodeId),
      })
    } else {
      queryClient.invalidateQueries({ queryKey: episodeKeys.list(projectId) })
      queryClient.invalidateQueries({
        queryKey: [...episodeKeys.list(projectId), 'all'],
      })
    }
  }

  const getEpisodeFromCache = (
    projectId: string,
    episodeId: string,
  ): Episode | undefined => {
    const cachedData = queryClient.getQueryData(
      episodeKeys.detail(projectId, episodeId),
    ) as any
    return cachedData?.data
  }

  return {
    prefetchEpisode,
    invalidateEpisodeData,
    getEpisodeFromCache,
  }
}
