/**
 * Canonical UI domain types for Project-related features.
 * - Keep these types as the single source of truth on the FE side.
 * - Server responses (DTOs) should be normalized/mapped to these shapes
 *   in '@/shared/api/mappers/projectMapper'.
 */

export type SortKey = 'createdAt' | 'updatedAt' | 'name' | 'title' | 'progress_percentage';

export interface ProjectFilters {
  /** free text search */
  search?: string;
  /** filter by type */
  type?: string | 'all';
  /** filter by status */  
  status?: string | 'all';
  /** sort key */
  sortBy?: SortKey;
  /** sort order */
  sortOrder?: 'asc' | 'desc';
  /** pagination page (1-based) */
  page?: number;
  /** page size */
  limit?: number;
}

/**
 * UI-facing Project model (Canonical).
 * Single source of truth for Project types on the frontend.
 * NOTE:
 *  - Fields are optional where possible to allow backward compatibility
 *  - Provide defaults in the mapper (toProject) instead of making
 *    everything mandatory in the UI domain.
 */
export interface Project {
  id: string;
  name: string;
  title?: string;
  tone?: string;
  systemPrompt?: string;
  summary?: string;
  description?: string;
  type?: string;
  genre?: string;
  status?: string;
  isPublic?: boolean;
  tags?: string[];
  
  // Timestamps (camelCase preferred)  
  createdAt?: string;
  updatedAt?: string;
  user_id?: string;
  
  // Backend compatibility - transitional aliases for legacy references
  /** @deprecated transitional alias for legacy references */
  created_at?: string;
  /** @deprecated transitional alias for legacy references */
  updated_at?: string;
  /** optional progress 0..100 */
  progressPercentage?: number;
  /** @deprecated transitional alias */
  progress_percentage?: number;
  
  // Counts
  episodesCount?: number;
  scriptsCount?: number;
  episodes_count?: number;
  scripts_count?: number;
  
  /** arbitrary metadata */
  metadata?: Record<string, unknown>;
}

export interface Episode {
  id: string
  number: number // 필드명을 number로 통일
  title: string
  description?: string
  status: 'draft' | 'ready' | 'generating' | 'failed'
  script?: {
    markdown: string
    tokens?: number
  }
  createdAt: string
  updatedAt?: string
}

export interface GenerationRequest {
  projectId: string
  number: number
  customPrompt?: string
}

export interface GenerationResponse {
  episodeId: string
  status: 'success' | 'error'
  script?: {
    markdown: string
    tokens: number
  }
  error?: string
}

// 프로젝트 생성/수정을 위한 타입
export interface CreateProjectRequest {
  name: string
  title?: string
  description?: string
  type?: string
  tone?: string
  systemPrompt?: string
}

export interface UpdateProjectRequest extends Partial<CreateProjectRequest> {
  id: string
}

// 에피소드 생성/수정을 위한 타입
export interface CreateEpisodeRequest {
  projectId: string
  number: number
  title: string
  description?: string
}

export interface UpdateEpisodeRequest
  extends Partial<Omit<CreateEpisodeRequest, 'projectId'>> {
  id: string
}