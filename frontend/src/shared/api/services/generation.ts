import { APIClient, SERVICE_URLS } from '../base'
import type {
  Generation,
  GenerationRequest,
  GenerationParameters,
  GenerationStatus,
  ListResponse,
} from '@/shared/types/api'

class GenerationService extends APIClient {
  constructor() {
    super(SERVICE_URLS.GENERATION, 'generation')
  }

  // Generation Management
  async createGeneration(data: GenerationRequest) {
    return this.post<Generation>('/api/v1/generations', data)
  }

  async getGeneration(generationId: string) {
    return this.get<Generation>(`/api/v1/generations/${generationId}`)
  }

  async getGenerations(
    filters: {
      project_id?: string
      episode_id?: string
      status?: GenerationStatus
      page?: number
      limit?: number
    } = {},
  ) {
    const params = new URLSearchParams()

    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        params.append(key, String(value))
      }
    })

    return this.get<ListResponse<Generation>>(
      `/api/v1/generations?${params.toString()}`,
    )
  }

  async updateGeneration(
    generationId: string,
    data: Partial<GenerationRequest>,
  ) {
    return this.put<Generation>(`/api/v1/generations/${generationId}`, data)
  }

  async cancelGeneration(generationId: string) {
    return this.post<Generation>(`/api/v1/generations/${generationId}/cancel`)
  }

  async retryGeneration(generationId: string) {
    return this.post<Generation>(`/api/v1/generations/${generationId}/retry`)
  }

  async deleteGeneration(generationId: string) {
    return this.delete<void>(`/api/v1/generations/${generationId}`)
  }

  // Generation History
  async getGenerationHistory(projectId?: string, limit = 50) {
    const params = new URLSearchParams({ limit: String(limit) })
    if (projectId) {
      params.append('project_id', projectId)
    }

    return this.get<ListResponse<Generation>>(
      `/api/v1/generations/history?${params.toString()}`,
    )
  }

  async getUserGenerations(page = 1, limit = 20) {
    return this.get<ListResponse<Generation>>(
      `/api/v1/generations/user?page=${page}&limit=${limit}`,
    )
  }

  async getActiveGenerations() {
    return this.get<Generation[]>('/api/v1/generations/active')
  }

  async getCompletedGenerations(page = 1, limit = 20) {
    return this.get<ListResponse<Generation>>(
      `/api/v1/generations/completed?page=${page}&limit=${limit}`,
    )
  }

  // Model Management
  async getAvailableModels() {
    return this.get<
      Array<{
        id: string
        name: string
        description: string
        provider: string
        capabilities: string[]
        pricing: {
          input_tokens: number
          output_tokens: number
        }
        limits: {
          max_tokens: number
          context_window: number
        }
        status: 'available' | 'premium' | 'experimental' | 'maintenance'
      }>
    >('/api/v1/models')
  }

  async getModelInfo(modelId: string) {
    return this.get<{
      id: string
      name: string
      description: string
      provider: string
      version: string
      capabilities: string[]
      parameters: {
        temperature: { min: number; max: number; default: number }
        max_tokens: { min: number; max: number; default: number }
        top_p: { min: number; max: number; default: number }
        frequency_penalty: { min: number; max: number; default: number }
        presence_penalty: { min: number; max: number; default: number }
      }
      pricing: {
        input_tokens: number
        output_tokens: number
      }
      performance_metrics: {
        avg_response_time: number
        success_rate: number
        quality_score: number
      }
    }>(`/api/v1/models/${modelId}`)
  }

  // Templates and Presets
  async getPromptTemplates() {
    return this.get<
      Array<{
        id: string
        name: string
        description: string
        category: string
        prompt: string
        parameters: GenerationParameters
        tags: string[]
      }>
    >('/api/v1/templates/prompts')
  }

  async createPromptTemplate(data: {
    name: string
    description: string
    category: string
    prompt: string
    parameters: GenerationParameters
    tags?: string[]
  }) {
    return this.post<{
      id: string
      name: string
      description: string
      category: string
      prompt: string
      parameters: GenerationParameters
      tags: string[]
    }>('/api/v1/templates/prompts', data)
  }

  async getParameterPresets() {
    return this.get<
      Array<{
        id: string
        name: string
        description: string
        parameters: GenerationParameters
        use_cases: string[]
      }>
    >('/api/v1/presets/parameters')
  }

  async createParameterPreset(data: {
    name: string
    description: string
    parameters: GenerationParameters
    use_cases?: string[]
  }) {
    return this.post<{
      id: string
      name: string
      description: string
      parameters: GenerationParameters
      use_cases: string[]
    }>('/api/v1/presets/parameters', data)
  }

  // Analytics
  async getGenerationStats(period: 'day' | 'week' | 'month' = 'week') {
    return this.get<{
      total_generations: number
      successful_generations: number
      failed_generations: number
      avg_generation_time: number
      total_tokens_used: number
      total_cost: number
      success_rate: number
      most_used_models: Array<{
        model: string
        count: number
        success_rate: number
      }>
      daily_usage: Array<{
        date: string
        generations: number
        tokens: number
        cost: number
      }>
    }>(`/api/v1/analytics/generations?period=${period}`)
  }

  async getModelUsage(period: 'day' | 'week' | 'month' = 'week') {
    return this.get<
      Array<{
        model: string
        usage_count: number
        success_rate: number
        avg_response_time: number
        total_tokens: number
        total_cost: number
      }>
    >(`/api/v1/analytics/models?period=${period}`)
  }

  // Queue Management
  async getQueueStatus() {
    return this.get<{
      queue_size: number
      estimated_wait_time: number
      active_generations: number
      max_concurrent: number
      queue_items: Array<{
        generation_id: string
        position: number
        estimated_start_time: string
        priority: number
      }>
    }>('/api/v1/queue/status')
  }

  async getQueuePosition(generationId: string) {
    return this.get<{
      position: number
      estimated_start_time: string
      estimated_completion_time: string
    }>(`/api/v1/queue/${generationId}/position`)
  }

  // Batch Operations
  async batchCreateGenerations(requests: GenerationRequest[]) {
    return this.post<{
      generations: Generation[]
      failed_requests: Array<{
        index: number
        error: string
      }>
    }>('/api/v1/generations/batch', { requests })
  }

  async batchCancelGenerations(generationIds: string[]) {
    return this.post<{ cancelled_count: number }>(
      '/api/v1/generations/batch/cancel',
      {
        generation_ids: generationIds,
      },
    )
  }

  async batchDeleteGenerations(generationIds: string[]) {
    return this.post<{ deleted_count: number }>(
      '/api/v1/generations/batch/delete',
      {
        generation_ids: generationIds,
      },
    )
  }

  // Cost Management
  async getUsageCosts(period: 'day' | 'week' | 'month' | 'year' = 'month') {
    return this.get<{
      total_cost: number
      token_cost: number
      generations_count: number
      daily_costs: Array<{
        date: string
        cost: number
        tokens: number
        generations: number
      }>
      model_costs: Array<{
        model: string
        cost: number
        usage_count: number
      }>
    }>(`/api/v1/usage/costs?period=${period}`)
  }

  async getUsageLimits() {
    return this.get<{
      daily_limit: number
      monthly_limit: number
      current_daily_usage: number
      current_monthly_usage: number
      remaining_daily: number
      remaining_monthly: number
      reset_times: {
        daily_reset: string
        monthly_reset: string
      }
    }>('/api/v1/usage/limits')
  }

  // WebSocket connections
  createGenerationSocket(generationId: string) {
    return this.createWebSocket(`/ws/generations/${generationId}`)
  }

  createQueueSocket() {
    return this.createWebSocket('/ws/queue')
  }

  createGenerationUpdatesSocket() {
    return this.createWebSocket('/ws/generations/updates')
  }
}

export const generationService = new GenerationService()
