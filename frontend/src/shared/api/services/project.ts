import { APIClient, SERVICE_URLS } from '../base'
import type {
  Project,
  ProjectCreateRequest,
  ProjectUpdateRequest,
  ProjectFilters,
  Episode,
  EpisodeCreateRequest,
  EpisodeUpdateRequest,
  Script,
  ScriptCreateRequest,
  ScriptUpdateRequest,
  ProjectStats,
  ListResponse,
} from '@/shared/types/api'

class ProjectService extends APIClient {
  constructor() {
    super(SERVICE_URLS.PROJECT, 'project')
  }

  // Projects
  async getProjects(filters: ProjectFilters = {}) {
    const params = new URLSearchParams()

    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        params.append(key, String(value))
      }
    })

    return this.get<ListResponse<Project>>(
      `/api/v1/projects?${params.toString()}`,
    )
  }

  async getProject(projectId: string) {
    return this.get<Project>(`/api/v1/projects/${projectId}`)
  }

  async createProject(data: ProjectCreateRequest) {
    return this.post<Project>('/api/v1/projects', data)
  }

  async updateProject(projectId: string, data: ProjectUpdateRequest) {
    return this.put<Project>(`/api/v1/projects/${projectId}`, data)
  }

  async deleteProject(projectId: string) {
    return this.delete<void>(`/api/v1/projects/${projectId}`)
  }

  async duplicateProject(projectId: string, name?: string) {
    return this.post<Project>(`/api/v1/projects/${projectId}/duplicate`, {
      name: name || `Copy of ${projectId}`,
    })
  }

  async archiveProject(projectId: string) {
    return this.patch<Project>(`/api/v1/projects/${projectId}/archive`)
  }

  async unarchiveProject(projectId: string) {
    return this.patch<Project>(`/api/v1/projects/${projectId}/unarchive`)
  }

  async updateProjectProgress(projectId: string, progress: number) {
    return this.patch<Project>(`/api/v1/projects/${projectId}/progress`, {
      progress_percentage: progress,
    })
  }

  async getProjectStats(projectId: string) {
    return this.get<ProjectStats>(`/api/v1/projects/${projectId}/stats`)
  }

  async exportProject(
    projectId: string,
    format: 'json' | 'pdf' | 'docx' = 'json',
  ) {
    return this.get<{ download_url: string }>(
      `/api/v1/projects/${projectId}/export?format=${format}`,
    )
  }

  // Episodes
  async getEpisodes(projectId: string, page = 1, limit = 50) {
    return this.get<ListResponse<Episode>>(
      `/api/v1/projects/${projectId}/episodes?page=${page}&limit=${limit}`,
    )
  }

  async getAllEpisodes(projectId: string) {
    return this.get<Episode[]>(`/api/v1/projects/${projectId}/episodes/all`)
  }

  async getEpisode(projectId: string, episodeId: string) {
    return this.get<Episode>(
      `/api/v1/projects/${projectId}/episodes/${episodeId}`,
    )
  }

  async createEpisode(data: EpisodeCreateRequest) {
    return this.post<Episode>(
      `/api/v1/projects/${data.project_id}/episodes`,
      data,
    )
  }

  async updateEpisode(
    projectId: string,
    episodeId: string,
    data: EpisodeUpdateRequest,
  ) {
    return this.put<Episode>(
      `/api/v1/projects/${projectId}/episodes/${episodeId}`,
      data,
    )
  }

  async deleteEpisode(projectId: string, episodeId: string) {
    return this.delete<void>(
      `/api/v1/projects/${projectId}/episodes/${episodeId}`,
    )
  }

  async reorderEpisodes(projectId: string, episodeIds: string[]) {
    return this.post<Episode[]>(
      `/api/v1/projects/${projectId}/episodes/reorder`,
      {
        episode_ids: episodeIds,
      },
    )
  }

  async duplicateEpisode(projectId: string, episodeId: string) {
    return this.post<Episode>(
      `/api/v1/projects/${projectId}/episodes/${episodeId}/duplicate`,
    )
  }

  async getNextEpisodeNumber(projectId: string) {
    return this.get<{ next_episode_number: number }>(
      `/api/v1/projects/${projectId}/episodes/next-number`,
    )
  }

  // Scripts
  async getScripts(
    projectId: string,
    episodeId?: string,
    page = 1,
    limit = 50,
  ) {
    const params = new URLSearchParams({
      page: String(page),
      limit: String(limit),
    })
    if (episodeId) {
      params.append('episode_id', episodeId)
    }

    return this.get<ListResponse<Script>>(
      `/api/v1/projects/${projectId}/scripts?${params.toString()}`,
    )
  }

  async getScript(scriptId: string) {
    return this.get<Script>(`/api/v1/scripts/${scriptId}`)
  }

  async createScript(data: ScriptCreateRequest) {
    return this.post<Script>(
      `/api/v1/projects/${data.project_id}/scripts`,
      data,
    )
  }

  async updateScript(scriptId: string, data: ScriptUpdateRequest) {
    return this.put<Script>(`/api/v1/scripts/${scriptId}`, data)
  }

  async deleteScript(scriptId: string) {
    return this.delete<void>(`/api/v1/scripts/${scriptId}`)
  }

  async rateScript(scriptId: string, rating: number) {
    return this.post<Script>(`/api/v1/scripts/${scriptId}/rate`, { rating })
  }

  async addScriptTags(scriptId: string, tags: string[]) {
    return this.post<Script>(`/api/v1/scripts/${scriptId}/tags`, { tags })
  }

  async removeScriptTag(scriptId: string, tag: string) {
    return this.delete<Script>(
      `/api/v1/scripts/${scriptId}/tags/${encodeURIComponent(tag)}`,
    )
  }

  async getScriptVersions(scriptId: string) {
    return this.get<
      Array<{
        version: number
        content: string
        created_at: string
        word_count: number
      }>
    >(`/api/v1/scripts/${scriptId}/versions`)
  }

  async revertToVersion(scriptId: string, version: number) {
    return this.post<Script>(`/api/v1/scripts/${scriptId}/revert`, { version })
  }

  async exportScript(scriptId: string, format: 'txt' | 'pdf' | 'docx' = 'txt') {
    return this.get<{ download_url: string }>(
      `/api/v1/scripts/${scriptId}/export?format=${format}`,
    )
  }

  // Batch Operations
  async batchDeleteProjects(projectIds: string[]) {
    return this.post<{ deleted_count: number }>(
      '/api/v1/projects/batch/delete',
      {
        project_ids: projectIds,
      },
    )
  }

  async batchUpdateProjects(
    projectIds: string[],
    updates: Partial<ProjectUpdateRequest>,
  ) {
    return this.post<{ updated_count: number }>(
      '/api/v1/projects/batch/update',
      {
        project_ids: projectIds,
        updates,
      },
    )
  }

  async batchDeleteEpisodes(projectId: string, episodeIds: string[]) {
    return this.post<{ deleted_count: number }>(
      `/api/v1/projects/${projectId}/episodes/batch/delete`,
      {
        episode_ids: episodeIds,
      },
    )
  }

  async batchDeleteScripts(scriptIds: string[]) {
    return this.post<{ deleted_count: number }>(
      '/api/v1/scripts/batch/delete',
      {
        script_ids: scriptIds,
      },
    )
  }

  // Search
  async searchProjects(query: string, filters: Partial<ProjectFilters> = {}) {
    const params = new URLSearchParams({ q: query })

    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        params.append(key, String(value))
      }
    })

    return this.get<ListResponse<Project>>(
      `/api/v1/search/projects?${params.toString()}`,
    )
  }

  async searchScripts(query: string, projectId?: string, page = 1, limit = 20) {
    const params = new URLSearchParams({
      q: query,
      page: String(page),
      limit: String(limit),
    })

    if (projectId) {
      params.append('project_id', projectId)
    }

    return this.get<ListResponse<Script>>(
      `/api/v1/search/scripts?${params.toString()}`,
    )
  }

  // Templates
  async getProjectTemplates() {
    return this.get<
      Array<{
        id: string
        name: string
        description: string
        type: string
        episodes_template: Array<{
          title: string
          description: string
        }>
      }>
    >('/api/v1/templates/projects')
  }

  async createProjectFromTemplate(templateId: string, projectName: string) {
    return this.post<Project>('/api/v1/templates/projects/create', {
      template_id: templateId,
      name: projectName,
    })
  }

  // WebSocket connections
  createProjectSocket(projectId: string) {
    return this.createWebSocket(`/ws/projects/${projectId}`)
  }

  createEpisodeSocket(projectId: string, episodeId: string) {
    return this.createWebSocket(
      `/ws/projects/${projectId}/episodes/${episodeId}`,
    )
  }
}

export const projectService = new ProjectService()
