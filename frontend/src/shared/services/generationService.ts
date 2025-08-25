/**
 * Generation Service API
 * Handles HTTP API calls for generation management
 */

import { client } from '../api/client'
import type {
  GenerationJobRequest,
  GenerationJobResponse,
  GenerationJobDetails,
  GenerationStartResponse,
  GenerationStatusResponse,
  GenerationListResponse,
  GenerationStatsResponse,
} from '../types/generation'
import { GenerationError } from '../types/generation'

const GENERATION_API_BASE = '/generations'

export class GenerationService {
  /**
   * Start a new generation job
   */
  static async startGeneration(
    request: GenerationJobRequest,
  ): Promise<GenerationJobResponse> {
    try {
      const response = await client.post<GenerationStartResponse>(
        GENERATION_API_BASE,
        request,
      )

      if (!response?.success || !response.data) {
        throw new GenerationError(
          response?.error?.message || 'Failed to start generation',
          'GENERATION_START_FAILED',
          false,
        )
      }

      return response.data
    } catch (error) {
      console.error('Failed to start generation:', error)

      if (error instanceof GenerationError) {
        throw error
      }

      // Convert generic errors to GenerationError
      const message = error instanceof Error ? error.message : 'Unknown error'
      throw new GenerationError(message, 'NETWORK_ERROR', true)
    }
  }

  /**
   * Get generation job status
   */
  static async getGenerationStatus(
    jobId: string,
  ): Promise<GenerationJobDetails | null> {
    try {
      const response = await client.get<GenerationStatusResponse>(
        `${GENERATION_API_BASE}/${jobId}`,
      )

      if ((response as any).status === 404) {
        return null // Job not found
      }

      if (!response?.success) {
        throw new GenerationError(
          response?.error?.message || 'Failed to get generation status',
          'STATUS_FETCH_FAILED',
          true,
        )
      }

      return response.data || null
    } catch (error) {
      console.error('Failed to get generation status:', error)

      if (error instanceof GenerationError) {
        throw error
      }

      // Handle 404 specifically
      if (
        (error as { response?: { status?: number } })?.response?.status === 404
      ) {
        return null
      }

      const message = error instanceof Error ? error.message : 'Unknown error'
      throw new GenerationError(message, 'NETWORK_ERROR', true)
    }
  }

  /**
   * Cancel a generation job (idempotent)
   */
  static async cancelGeneration(jobId: string): Promise<boolean> {
    try {
      const response = await client.delete(`${GENERATION_API_BASE}/${jobId}`)

      // DELETE returns 204 for successful cancellation (idempotent)
      return (response as any).status === 204
    } catch (error) {
      console.error('Failed to cancel generation:', error)

      // Even if the request fails, treat it as successful for user experience
      // The actual cancellation might have succeeded server-side
      return true
    }
  }

  /**
   * List active generation jobs
   */
  static async listActiveGenerations(): Promise<GenerationJobDetails[]> {
    try {
      const response = await client.get<GenerationListResponse>(
        `${GENERATION_API_BASE}/active`,
      )

      if (!response?.success || !response.data) {
        return []
      }

      return response.data.active_jobs || []
    } catch (error) {
      console.error('Failed to list active generations:', error)
      return []
    }
  }

  /**
   * Get generation service statistics
   */
  static async getGenerationStats(): Promise<Record<string, number>> {
    try {
      const response = await client.get<GenerationStatsResponse>(
        `${GENERATION_API_BASE}/_stats`,
      )

      if (!response?.success || !response.data) {
        return {}
      }

      return response.data.job_statistics || {}
    } catch (error) {
      console.error('Failed to get generation stats:', error)
      return {}
    }
  }

  /**
   * Build SSE URL for a job ID
   */
  static buildSSEUrl(jobId: string): string {
    const baseUrl =
      process.env.NODE_ENV === 'production'
        ? '/api/v1'
        : 'http://localhost:8000/api/v1'

    return `${baseUrl}${GENERATION_API_BASE}/${jobId}/events`
  }

  /**
   * Validate generation request
   */
  static validateGenerationRequest(request: GenerationJobRequest): string[] {
    const errors: string[] = []

    if (!request.projectId?.trim()) {
      errors.push('프로젝트 ID는 필수입니다.')
    }

    if (!request.description?.trim()) {
      errors.push('스크립트 설명은 필수입니다.')
    }

    if (request.description && request.description.length < 10) {
      errors.push('스크립트 설명은 최소 10자 이상이어야 합니다.')
    }

    if (request.description && request.description.length > 2000) {
      errors.push('스크립트 설명은 최대 2000자까지 입력 가능합니다.')
    }

    if (request.title && request.title.length > 200) {
      errors.push('제목은 최대 200자까지 입력 가능합니다.')
    }

    if (request.temperature !== undefined) {
      if (request.temperature < 0 || request.temperature > 2) {
        errors.push('창의도는 0과 2 사이의 값이어야 합니다.')
      }
    }

    if (request.lengthTarget !== undefined) {
      if (request.lengthTarget < 100 || request.lengthTarget > 50000) {
        errors.push('목표 길이는 100자에서 50,000자 사이여야 합니다.')
      }
    }

    if (request.episodeNumber !== undefined && request.episodeNumber < 1) {
      errors.push('에피소드 번호는 1 이상이어야 합니다.')
    }

    return errors
  }

  /**
   * Estimate generation duration based on request
   */
  static estimateGenerationDuration(request: GenerationJobRequest): number {
    const baseTime = 60 // 1 minute base

    // Adjust based on content length
    const contentFactor = (request.description?.length || 0) / 100
    const lengthFactor = (request.lengthTarget || 1000) / 1000

    const estimated = baseTime + contentFactor * 10 + lengthFactor * 30
    return Math.max(30, Math.min(300, Math.round(estimated))) // Between 30s and 5 minutes
  }
}
