/**
 * DTO → UI domain mappers for Project entities.
 * Normalize server payloads into the canonical UI shapes defined in
 * '@/shared/types/project'. Provide safe defaults here.
 */

import type { Project } from '@/shared/types/project'

// Server-side (raw) DTO. Keep this loose and align to your real API.
export interface ProjectDTO {
  id: string
  name: string
  title?: string
  description?: string
  type?: string
  status?: string
  tone?: string
  system_prompt?: string // snake_case example
  summary?: string
  progress_percentage?: number
  created_at?: string
  updated_at?: string
  user_id?: string
  episodes_count?: number
  scripts_count?: number
  metadata?: Record<string, unknown>
}

/**
 * Normalize a single ProjectDTO into the UI domain Project.
 * Supply safe defaults for optional fields so that UI components
 * can rely on consistent values.
 */
export function toProject(dto: ProjectDTO): Project {
  const createdAt = dto.created_at ?? ''
  const updatedAt = dto.updated_at ?? ''
  const progressPercentage =
    typeof dto.progress_percentage === 'number'
      ? Math.max(0, Math.min(100, dto.progress_percentage))
      : 0

  return {
    id: dto.id,
    name: dto.name,
    title: (dto.title ?? dto.name) || '',
    tone: dto.tone ?? 'neutral',
    systemPrompt: dto.system_prompt ?? '',
    summary: dto.summary,
    description: dto.description ?? '',
    type: dto.type ?? '',
    status: dto.status ?? '',
    createdAt,
    updatedAt,
    user_id: dto.user_id,
    progressPercentage,
    // 🔁 Transitional aliases for legacy code (to be removed later)
    created_at: createdAt,
    updated_at: updatedAt,
    progress_percentage: progressPercentage,
    episodes_count: dto.episodes_count ?? 0,
    scripts_count: dto.scripts_count ?? 0,
    metadata: dto.metadata ?? {},
  }
}

/**
 * Map a list of DTOs into the UI domain.
 */
export function toProjects(dtos: ProjectDTO[]): Project[] {
  return dtos.map(toProject)
}
