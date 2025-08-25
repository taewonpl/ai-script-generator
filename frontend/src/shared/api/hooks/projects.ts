import { useQuery } from '@tanstack/react-query';
import type { UseQueryOptions } from '@tanstack/react-query';
import type { Project, ProjectFilters } from '@/shared/types/project';
import type { ProjectDTO } from '@/shared/api/mappers/projectMapper';
import { toProject, toProjects } from '@/shared/api/mappers/projectMapper';
import { projectApi } from '@/shared/api/client';

// Low-level fetchers (DTO 기반)
async function fetchProjectDTO(projectId: string): Promise<ProjectDTO> {
  const response = await projectApi.get<ProjectDTO>(`/projects/${projectId}`);
  return response.data;
}

async function fetchProjectsDTO(filters: ProjectFilters): Promise<ProjectDTO[]> {
  const params = new URLSearchParams();
  if (filters.search) params.set('q', filters.search);
  if (filters.sortBy) params.set('sortBy', filters.sortBy);
  const order = filters.sortOrder || 'desc';
  params.set('order', order);
  if (filters.status && filters.status !== 'all') params.set('status', String(filters.status));
  if (filters.type && filters.type !== 'all') params.set('type', String(filters.type));
  if (filters.page) params.set('page', String(filters.page));
  if (filters.limit) params.set('limit', String(filters.limit));
  const response = await projectApi.get<ProjectDTO[]>(`/projects?${params.toString()}`);
  return response.data;
}

// UI-facing typed hooks
export function useProject(
  projectId: string,
  options?: Omit<UseQueryOptions<Project>, 'queryKey' | 'queryFn' | 'select' | 'enabled'>
) {
  return useQuery<Project>({
    queryKey: ['project', projectId],
    queryFn: () => fetchProjectDTO(projectId),
    select: toProject,             // ✅ DTO → UI 도메인으로 정규화
    enabled: !!projectId,
    ...options,
  });
}

export function useProjects(
  filters: ProjectFilters = {},
  options?: Omit<UseQueryOptions<Project[]>, 'queryKey' | 'queryFn' | 'select'>
) {
  return useQuery<Project[]>({
    queryKey: ['projects', filters],
    queryFn: () => fetchProjectsDTO(filters),
    select: toProjects,           // ✅ DTO[] → UI Project[] 정규화
    staleTime: 1000 * 60 * 5,    // 5분간 캐시 유지
    ...options,
  });
}

// Query keys for invalidation
export const projectQueryKeys = {
  all: ['projects'] as const,
  lists: () => [...projectQueryKeys.all, 'list'] as const,
  list: (filters: ProjectFilters) => [...projectQueryKeys.lists(), filters] as const,
  details: () => [...projectQueryKeys.all, 'detail'] as const,
  detail: (id: string) => [...projectQueryKeys.details(), id] as const,
};