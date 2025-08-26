import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { UseQueryOptions } from '@tanstack/react-query'
import { projectService } from '@/shared/api/services/project'
import type {
  Project,
  ProjectCreateRequest,
  ProjectUpdateRequest,
  ProjectFilters,
  ListResponse,
  ProjectStats,
} from '@/shared/types/api'

// Query Keys
export const projectKeys = {
  all: ['projects'] as const,
  lists: () => [...projectKeys.all, 'list'] as const,
  list: (filters: ProjectFilters) =>
    [...projectKeys.lists(), { filters }] as const,
  details: () => [...projectKeys.all, 'detail'] as const,
  detail: (id: string) => [...projectKeys.details(), id] as const,
  stats: (id: string) => [...projectKeys.detail(id), 'stats'] as const,
  search: (query: string, filters?: Partial<ProjectFilters>) =>
    [...projectKeys.all, 'search', { query, filters }] as const,
  templates: () => [...projectKeys.all, 'templates'] as const,
}

// Projects List Hook
export function useProjects(
  filters: ProjectFilters = {},
  options?: Omit<
    UseQueryOptions<ListResponse<Project>>,
    'queryKey' | 'queryFn'
  >,
) {
  return useQuery({
    queryKey: projectKeys.list(filters),
    queryFn: () => projectService.getProjects(filters),
    staleTime: 1000 * 60 * 5, // 5 minutes
    gcTime: 1000 * 60 * 30, // 30 minutes
    ...options,
  })
}

// Single Project Hook
export function useProject(
  projectId: string,
  options?: Omit<UseQueryOptions<Project>, 'queryKey' | 'queryFn'>,
) {
  return useQuery({
    queryKey: projectKeys.detail(projectId),
    queryFn: () => projectService.getProject(projectId),
    enabled: !!projectId,
    staleTime: 1000 * 60 * 5, // 5 minutes
    gcTime: 1000 * 60 * 30, // 30 minutes
    ...options,
  })
}

// Project Stats Hook
export function useProjectStats(
  projectId: string,
  options?: Omit<UseQueryOptions<ProjectStats>, 'queryKey' | 'queryFn'>,
) {
  return useQuery({
    queryKey: projectKeys.stats(projectId),
    queryFn: () => projectService.getProjectStats(projectId),
    enabled: !!projectId,
    staleTime: 1000 * 60 * 2, // 2 minutes
    gcTime: 1000 * 60 * 10, // 10 minutes
    ...options,
  })
}

// Project Search Hook
export function useProjectSearch(
  query: string,
  filters: Partial<ProjectFilters> = {},
  options?: Omit<
    UseQueryOptions<ListResponse<Project>>,
    'queryKey' | 'queryFn'
  >,
) {
  return useQuery({
    queryKey: projectKeys.search(query, filters),
    queryFn: () => projectService.searchProjects(query, filters),
    enabled: !!query.trim(),
    staleTime: 1000 * 60 * 2, // 2 minutes
    gcTime: 1000 * 60 * 10, // 10 minutes
    ...options,
  })
}

// Project Templates Hook
export function useProjectTemplates(
  options?: Omit<UseQueryOptions<any[]>, 'queryKey' | 'queryFn'>,
) {
  return useQuery({
    queryKey: projectKeys.templates(),
    queryFn: () => projectService.getProjectTemplates(),
    staleTime: 1000 * 60 * 30, // 30 minutes
    gcTime: 1000 * 60 * 60, // 1 hour
    ...options,
  })
}

// Create Project Mutation
export function useCreateProject() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: ProjectCreateRequest) =>
      projectService.createProject(data),
    onSuccess: newProject => {
      // Invalidate projects list queries
      queryClient.invalidateQueries({ queryKey: projectKeys.lists() })

      // Add new project to cache
      queryClient.setQueryData(projectKeys.detail(newProject.id), newProject)
    },
  })
}

// Update Project Mutation
export function useUpdateProject() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      projectId,
      data,
    }: {
      projectId: string
      data: ProjectUpdateRequest
    }) => projectService.updateProject(projectId, data),
    onSuccess: (updatedProject, { projectId }) => {
      // Update project in cache
      queryClient.setQueryData(projectKeys.detail(projectId), updatedProject)

      // Invalidate related queries
      queryClient.invalidateQueries({ queryKey: projectKeys.lists() })
      queryClient.invalidateQueries({ queryKey: projectKeys.stats(projectId) })
    },
  })
}

// Delete Project Mutation
export function useDeleteProject() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (projectId: string) => projectService.deleteProject(projectId),
    onSuccess: (_, projectId) => {
      // Remove from cache
      queryClient.removeQueries({ queryKey: projectKeys.detail(projectId) })
      queryClient.removeQueries({ queryKey: projectKeys.stats(projectId) })

      // Invalidate lists to refresh
      queryClient.invalidateQueries({ queryKey: projectKeys.lists() })
    },
  })
}

// Duplicate Project Mutation
export function useDuplicateProject() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ projectId, name }: { projectId: string; name?: string }) =>
      projectService.duplicateProject(projectId, name),
    onSuccess: newProject => {
      // Add duplicated project to cache
      queryClient.setQueryData(projectKeys.detail(newProject.id), newProject)

      // Invalidate lists
      queryClient.invalidateQueries({ queryKey: projectKeys.lists() })
    },
  })
}

// Archive/Unarchive Project Mutations
export function useArchiveProject() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (projectId: string) => projectService.archiveProject(projectId),
    onSuccess: (updatedProject, projectId) => {
      queryClient.setQueryData(projectKeys.detail(projectId), updatedProject)
      queryClient.invalidateQueries({ queryKey: projectKeys.lists() })
    },
  })
}

export function useUnarchiveProject() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (projectId: string) =>
      projectService.unarchiveProject(projectId),
    onSuccess: (updatedProject, projectId) => {
      queryClient.setQueryData(projectKeys.detail(projectId), updatedProject)
      queryClient.invalidateQueries({ queryKey: projectKeys.lists() })
    },
  })
}

// Update Project Progress Mutation
export function useUpdateProjectProgress() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      projectId,
      progress,
    }: {
      projectId: string
      progress: number
    }) => projectService.updateProjectProgress(projectId, progress),
    onSuccess: (updatedProject, { projectId }) => {
      queryClient.setQueryData(projectKeys.detail(projectId), updatedProject)
      queryClient.invalidateQueries({ queryKey: projectKeys.lists() })
      queryClient.invalidateQueries({ queryKey: projectKeys.stats(projectId) })
    },
  })
}

// Export Project Mutation
export function useExportProject() {
  return useMutation({
    mutationFn: ({
      projectId,
      format,
    }: {
      projectId: string
      format?: 'json' | 'pdf' | 'docx'
    }) => projectService.exportProject(projectId, format),
  })
}

// Batch Operations
export function useBatchDeleteProjects() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (projectIds: string[]) =>
      projectService.batchDeleteProjects(projectIds),
    onSuccess: (_, projectIds) => {
      // Remove deleted projects from cache
      projectIds.forEach(id => {
        queryClient.removeQueries({ queryKey: projectKeys.detail(id) })
        queryClient.removeQueries({ queryKey: projectKeys.stats(id) })
      })

      // Invalidate lists
      queryClient.invalidateQueries({ queryKey: projectKeys.lists() })
    },
  })
}

export function useBatchUpdateProjects() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      projectIds,
      updates,
    }: {
      projectIds: string[]
      updates: Partial<ProjectUpdateRequest>
    }) => projectService.batchUpdateProjects(projectIds, updates),
    onSuccess: (_, { projectIds }) => {
      // Invalidate affected projects
      projectIds.forEach(id => {
        queryClient.invalidateQueries({ queryKey: projectKeys.detail(id) })
        queryClient.invalidateQueries({ queryKey: projectKeys.stats(id) })
      })

      // Invalidate lists
      queryClient.invalidateQueries({ queryKey: projectKeys.lists() })
    },
  })
}

// Create Project from Template Mutation
export function useCreateProjectFromTemplate() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ templateId, name }: { templateId: string; name: string }) =>
      projectService.createProjectFromTemplate(templateId, name),
    onSuccess: newProject => {
      queryClient.setQueryData(projectKeys.detail(newProject.id), newProject)
      queryClient.invalidateQueries({ queryKey: projectKeys.lists() })
    },
  })
}
