/**
 * Projects API client with delete functionality
 * Handles project CRUD operations including production-grade deletion
 */

import { projectHttp } from './clients'
import type { Project } from '@/shared/api/types'

export interface DeleteProjectOptions {
  /** Idempotency key for the deletion */
  deleteId: string
  /** Whether to force deletion (for admin operations) */
  force?: boolean
}

export interface ProjectDeleteError extends Error {
  code: string
  status: number
  details?: Record<string, any>
}

/**
 * Delete a project with idempotency and business logic guards
 * @param projectId - Project UUID to delete
 * @param options - Delete options including idempotency key
 * @returns Promise that resolves on successful deletion
 * @throws {ProjectDeleteError} When deletion fails with specific error details
 */
export const deleteProject = async (
  projectId: string,
  options: DeleteProjectOptions
): Promise<void> => {
  try {
    await projectHttp.delete(`/projects/${projectId}`, {
      headers: {
        'X-Delete-Id': options.deleteId,
        ...(options.force && { 'X-Force-Delete': 'true' }),
      },
    })
  } catch (error: any) {
    // Enhanced error handling for different deletion scenarios
    const apiError = error as any
    const deleteError = new Error(apiError.message || 'Project deletion failed') as ProjectDeleteError
    
    deleteError.code = apiError.code || 'DELETION_FAILED'
    deleteError.status = apiError.status || 500
    deleteError.details = apiError.details || {}
    
    // Add specific handling for business logic errors
    if (apiError.status === 409) {
      deleteError.code = 'ACTIVE_GENERATION_JOBS'
      deleteError.message = apiError.details?.message || '프로젝트에 활성 생성 작업이 있습니다. 먼저 작업을 중단하세요.'
    } else if (apiError.status === 404) {
      // 404 should be treated as success in most cases, but we'll let the caller decide
      deleteError.code = 'PROJECT_NOT_FOUND'
      deleteError.message = '프로젝트가 이미 삭제되었습니다.'
    }
    
    throw deleteError
  }
}

/**
 * Get project details
 * @param projectId - Project UUID
 * @returns Project data
 */
export const getProject = async (projectId: string): Promise<Project> => {
  const response = await projectHttp.get<{ data: Project }>(`/projects/${projectId}`)
  return response.data
}

/**
 * Get projects list
 * @param params - Query parameters for filtering and pagination
 */
export const getProjects = async (params?: {
  skip?: number
  limit?: number
  search?: string
  project_type?: string
  status?: string
}) => {
  const response = await projectHttp.get<{ data: Project[] }>('/projects/', {
    params,
  })
  return response.data
}

/**
 * Create a new project
 * @param projectData - Project creation data
 */
export const createProject = async (projectData: {
  name: string
  description?: string
  type: string
  status?: string
}) => {
  const response = await projectHttp.post<{ data: Project }>('/projects/', projectData)
  return response.data
}

/**
 * Update an existing project
 * @param projectId - Project UUID
 * @param projectData - Project update data
 */
export const updateProject = async (
  projectId: string,
  projectData: Partial<{
    name: string
    description: string
    type: string
    status: string
  }>
) => {
  const response = await projectHttp.put<{ data: Project }>(`/projects/${projectId}`, projectData)
  return response.data
}

/**
 * Update project progress
 * @param projectId - Project UUID
 * @param progress - Progress percentage (0-100)
 */
export const updateProjectProgress = async (
  projectId: string,
  progress: number
) => {
  const response = await projectHttp.patch<{ data: Project }>(
    `/projects/${projectId}/progress?progress=${progress}`
  )
  return response.data
}