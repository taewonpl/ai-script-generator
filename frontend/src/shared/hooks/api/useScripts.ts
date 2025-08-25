import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { UseQueryOptions } from '@tanstack/react-query'
import { projectService } from '@/shared/api/services/project'
import type {
  Script,
  ScriptCreateRequest,
  ScriptUpdateRequest,
  ListResponse,
} from '@/shared/types/api'
import { projectKeys } from './useProjects'
import { episodeKeys } from './useEpisodes'

// Query Keys
export const scriptKeys = {
  all: ['scripts'] as const,
  lists: () => [...scriptKeys.all, 'list'] as const,
  list: (projectId: string, episodeId?: string) =>
    [...scriptKeys.lists(), projectId, { episodeId }] as const,
  details: () => [...scriptKeys.all, 'detail'] as const,
  detail: (id: string) => [...scriptKeys.details(), id] as const,
  versions: (id: string) => [...scriptKeys.detail(id), 'versions'] as const,
  search: (query: string, projectId?: string) =>
    [...scriptKeys.all, 'search', { query, projectId }] as const,
}

// Scripts List Hook
export function useScripts(
  projectId: string,
  episodeId?: string,
  page = 1,
  limit = 50,
  options?: Omit<UseQueryOptions<ListResponse<Script>>, 'queryKey' | 'queryFn'>,
) {
  return useQuery({
    queryKey: scriptKeys.list(projectId, episodeId),
    queryFn: () => projectService.getScripts(projectId, episodeId, page, limit),
    enabled: !!projectId,
    staleTime: 1000 * 60 * 5, // 5 minutes
    gcTime: 1000 * 60 * 30, // 30 minutes
    ...options,
  })
}

// Single Script Hook
export function useScript(
  scriptId: string,
  options?: Omit<UseQueryOptions<Script>, 'queryKey' | 'queryFn'>,
) {
  return useQuery({
    queryKey: scriptKeys.detail(scriptId),
    queryFn: () => projectService.getScript(scriptId),
    enabled: !!scriptId,
    staleTime: 1000 * 60 * 5, // 5 minutes
    gcTime: 1000 * 60 * 30, // 30 minutes
    ...options,
  })
}

// Script Versions Hook
export function useScriptVersions(
  scriptId: string,
  options?: Omit<UseQueryOptions<any[]>, 'queryKey' | 'queryFn'>,
) {
  return useQuery({
    queryKey: scriptKeys.versions(scriptId),
    queryFn: () => projectService.getScriptVersions(scriptId),
    enabled: !!scriptId,
    staleTime: 1000 * 60 * 10, // 10 minutes
    gcTime: 1000 * 60 * 60, // 1 hour
    ...options,
  })
}

// Script Search Hook
export function useScriptSearch(
  query: string,
  projectId?: string,
  page = 1,
  limit = 20,
  options?: Omit<UseQueryOptions<ListResponse<Script>>, 'queryKey' | 'queryFn'>,
) {
  return useQuery({
    queryKey: [...scriptKeys.search(query, projectId), { page, limit }],
    queryFn: () => projectService.searchScripts(query, projectId, page, limit),
    enabled: !!query.trim(),
    staleTime: 1000 * 60 * 2, // 2 minutes
    gcTime: 1000 * 60 * 10, // 10 minutes
    ...options,
  })
}

// Create Script Mutation
export function useCreateScript() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: ScriptCreateRequest) =>
      projectService.createScript(data),
    onSuccess: (newScript, { project_id, episode_id }) => {
      // Add new script to cache
      queryClient.setQueryData(scriptKeys.detail(newScript.data.id), newScript)

      // Invalidate scripts lists
      queryClient.invalidateQueries({
        queryKey: scriptKeys.list(project_id, episode_id),
      })
      queryClient.invalidateQueries({
        queryKey: scriptKeys.list(project_id),
      })

      // Update project and episode stats
      queryClient.invalidateQueries({
        queryKey: projectKeys.detail(project_id),
      })
      queryClient.invalidateQueries({ queryKey: projectKeys.stats(project_id) })
      queryClient.invalidateQueries({
        queryKey: episodeKeys.detail(project_id, episode_id),
      })
    },
  })
}

// Update Script Mutation
export function useUpdateScript() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      scriptId,
      data,
    }: {
      scriptId: string
      data: ScriptUpdateRequest
    }) => projectService.updateScript(scriptId, data),
    onSuccess: (updatedScript, { scriptId }) => {
      // Update script in cache
      queryClient.setQueryData(scriptKeys.detail(scriptId), updatedScript)

      // Invalidate versions if version changed
      queryClient.invalidateQueries({ queryKey: scriptKeys.versions(scriptId) })

      // Invalidate script lists
      queryClient.invalidateQueries({ queryKey: scriptKeys.lists() })
    },
  })
}

// Delete Script Mutation
export function useDeleteScript() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (scriptId: string) => projectService.deleteScript(scriptId),
    onMutate: async scriptId => {
      // Get script data before deletion for rollback
      const script = queryClient.getQueryData(
        scriptKeys.detail(scriptId),
      ) as any
      return { script }
    },
    onSuccess: (_, scriptId, context) => {
      // Remove from cache
      queryClient.removeQueries({ queryKey: scriptKeys.detail(scriptId) })
      queryClient.removeQueries({ queryKey: scriptKeys.versions(scriptId) })

      // Invalidate lists
      queryClient.invalidateQueries({ queryKey: scriptKeys.lists() })

      // Update related data if we have the script context
      if (context?.script?.data) {
        const { project_id, episode_id } = context.script.data
        queryClient.invalidateQueries({
          queryKey: projectKeys.detail(project_id),
        })
        queryClient.invalidateQueries({
          queryKey: projectKeys.stats(project_id),
        })
        queryClient.invalidateQueries({
          queryKey: episodeKeys.detail(project_id, episode_id),
        })
      }
    },
    onError: (_, __, context) => {
      // Restore script data on error
      if (context?.script) {
        queryClient.setQueryData(
          scriptKeys.detail(context.script.data.id),
          context.script,
        )
      }
    },
  })
}

// Rate Script Mutation
export function useRateScript() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ scriptId, rating }: { scriptId: string; rating: number }) =>
      projectService.rateScript(scriptId, rating),
    onMutate: async ({ scriptId, rating }) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: scriptKeys.detail(scriptId) })

      // Snapshot previous value
      const previousScript = queryClient.getQueryData(
        scriptKeys.detail(scriptId),
      )

      // Optimistically update
      queryClient.setQueryData(scriptKeys.detail(scriptId), (old: any) => {
        if (!old) return old
        return {
          ...old,
          data: { ...old.data, rating },
        }
      })

      return { previousScript }
    },
    onError: (_, { scriptId }, context) => {
      // Rollback on error
      if (context?.previousScript) {
        queryClient.setQueryData(
          scriptKeys.detail(scriptId),
          context.previousScript,
        )
      }
    },
    onSettled: (_, __, { scriptId }) => {
      // Always refetch after mutation
      queryClient.invalidateQueries({ queryKey: scriptKeys.detail(scriptId) })
    },
  })
}

// Add Script Tags Mutation
export function useAddScriptTags() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ scriptId, tags }: { scriptId: string; tags: string[] }) =>
      projectService.addScriptTags(scriptId, tags),
    onSuccess: (updatedScript, { scriptId }) => {
      // Update script in cache
      queryClient.setQueryData(scriptKeys.detail(scriptId), updatedScript)

      // Invalidate lists to show updated tags
      queryClient.invalidateQueries({ queryKey: scriptKeys.lists() })
    },
  })
}

// Remove Script Tag Mutation
export function useRemoveScriptTag() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ scriptId, tag }: { scriptId: string; tag: string }) =>
      projectService.removeScriptTag(scriptId, tag),
    onSuccess: (updatedScript, { scriptId }) => {
      // Update script in cache
      queryClient.setQueryData(scriptKeys.detail(scriptId), updatedScript)

      // Invalidate lists
      queryClient.invalidateQueries({ queryKey: scriptKeys.lists() })
    },
  })
}

// Revert to Version Mutation
export function useRevertToVersion() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      scriptId,
      version,
    }: {
      scriptId: string
      version: number
    }) => projectService.revertToVersion(scriptId, version),
    onSuccess: (revertedScript, { scriptId }) => {
      // Update script in cache
      queryClient.setQueryData(scriptKeys.detail(scriptId), revertedScript)

      // Invalidate versions to show new version
      queryClient.invalidateQueries({ queryKey: scriptKeys.versions(scriptId) })

      // Invalidate lists
      queryClient.invalidateQueries({ queryKey: scriptKeys.lists() })
    },
  })
}

// Export Script Mutation
export function useExportScript() {
  return useMutation({
    mutationFn: ({
      scriptId,
      format,
    }: {
      scriptId: string
      format?: 'txt' | 'pdf' | 'docx'
    }) => projectService.exportScript(scriptId, format),
  })
}

// Batch Delete Scripts Mutation
export function useBatchDeleteScripts() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (scriptIds: string[]) =>
      projectService.batchDeleteScripts(scriptIds),
    onSuccess: (_, scriptIds) => {
      // Remove scripts from cache
      scriptIds.forEach(id => {
        queryClient.removeQueries({ queryKey: scriptKeys.detail(id) })
        queryClient.removeQueries({ queryKey: scriptKeys.versions(id) })
      })

      // Invalidate lists
      queryClient.invalidateQueries({ queryKey: scriptKeys.lists() })

      // Invalidate project stats (scripts count changed)
      queryClient.invalidateQueries({ queryKey: projectKeys.all })
    },
  })
}

// Optimistic Updates Helper
export function useOptimisticScriptUpdate() {
  const queryClient = useQueryClient()

  const updateScriptOptimistically = (
    scriptId: string,
    updates: Partial<Script>,
  ) => {
    queryClient.setQueryData(scriptKeys.detail(scriptId), (old: any) => {
      if (!old) return old
      return {
        ...old,
        data: { ...old.data, ...updates },
      }
    })

    // Also update in lists
    queryClient.setQueriesData({ queryKey: scriptKeys.lists() }, (old: any) => {
      if (!old) return old
      return {
        ...old,
        data: {
          ...old.data,
          items: old.data.items.map((script: Script) =>
            script.id === scriptId ? { ...script, ...updates } : script,
          ),
        },
      }
    })
  }

  return { updateScriptOptimistically }
}

// Cache Utilities
export function useScriptCacheUtils() {
  const queryClient = useQueryClient()

  const prefetchScript = (scriptId: string) => {
    queryClient.prefetchQuery({
      queryKey: scriptKeys.detail(scriptId),
      queryFn: () => projectService.getScript(scriptId),
      staleTime: 1000 * 60 * 5,
    })
  }

  const prefetchScriptVersions = (scriptId: string) => {
    queryClient.prefetchQuery({
      queryKey: scriptKeys.versions(scriptId),
      queryFn: () => projectService.getScriptVersions(scriptId),
      staleTime: 1000 * 60 * 10,
    })
  }

  const invalidateScriptData = (scriptId?: string) => {
    if (scriptId) {
      queryClient.invalidateQueries({ queryKey: scriptKeys.detail(scriptId) })
      queryClient.invalidateQueries({ queryKey: scriptKeys.versions(scriptId) })
    } else {
      queryClient.invalidateQueries({ queryKey: scriptKeys.lists() })
    }
  }

  const getScriptFromCache = (scriptId: string): Script | undefined => {
    const cachedData = queryClient.getQueryData(
      scriptKeys.detail(scriptId),
    ) as any
    return cachedData?.data
  }

  const updateScriptRating = (scriptId: string, rating: number) => {
    queryClient.setQueryData(scriptKeys.detail(scriptId), (old: any) => {
      if (!old) return old
      return {
        ...old,
        data: { ...old.data, rating },
      }
    })
  }

  return {
    prefetchScript,
    prefetchScriptVersions,
    invalidateScriptData,
    getScriptFromCache,
    updateScriptRating,
  }
}
