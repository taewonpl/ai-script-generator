// Auto-generated types from backend services
export interface APIResponse<T = unknown> {
  success: boolean
  data: T
  message?: string
  errors?: Record<string, string[]>
  meta?: {
    total?: number
    page?: number
    limit?: number
    totalPages?: number
  }
}

export interface APIError {
  message: string
  code?: string
  status?: number
  details?: Record<string, unknown>
}

// Core Service Types (Port 8000)
export interface User {
  id: string
  email: string
  name: string
  avatar?: string
  created_at: string
  updated_at: string
}

export interface UserProfile extends User {
  bio?: string
  language: string
  timezone: string
  preferences: UserPreferences
}

export interface UserPreferences {
  emailNotifications: boolean
  profileVisibility: boolean
  theme: 'light' | 'dark' | 'system'
}

// Project Service Types (Port 8001)
export const ProjectType = {
  DRAMA: 'drama',
  COMEDY: 'comedy',
  ACTION: 'action',
  ROMANCE: 'romance',
  THRILLER: 'thriller',
  HORROR: 'horror',
  FANTASY: 'fantasy',
  SCIFI: 'scifi',
} as const

export type ProjectType = (typeof ProjectType)[keyof typeof ProjectType]

export const ProjectStatus = {
  PLANNING: 'planning',
  ACTIVE: 'active',
  PAUSED: 'paused',
  COMPLETED: 'completed',
  ARCHIVED: 'archived',
} as const

export type ProjectStatus = (typeof ProjectStatus)[keyof typeof ProjectStatus]

export interface Project {
  id: string
  name: string
  description?: string
  type: ProjectType
  status: ProjectStatus
  progress_percentage: number
  created_at: string
  updated_at: string
  user_id: string
  episodes_count: number
  scripts_count: number
  metadata?: Record<string, unknown>
}

export interface ProjectCreateRequest {
  name: string
  description?: string
  type: ProjectType
  status?: ProjectStatus
  metadata?: Record<string, unknown>
}

export interface ProjectUpdateRequest extends Partial<ProjectCreateRequest> {
  progress_percentage?: number
}

export interface ProjectFilters {
  search?: string
  type?: ProjectType
  status?: ProjectStatus
  sortBy?: 'name' | 'created_at' | 'updated_at' | 'progress_percentage'
  sortOrder?: 'asc' | 'desc'
  page?: number
  limit?: number
}

export const EpisodeStatus = {
  DRAFT: 'draft',
  OUTLINE: 'outline',
  FIRST_DRAFT: 'first_draft',
  REVISION: 'revision',
  FINAL: 'final',
  APPROVED: 'approved',
} as const

export type EpisodeStatus = (typeof EpisodeStatus)[keyof typeof EpisodeStatus]

export interface Episode {
  id: string
  project_id: string
  title: string
  description?: string
  number: number
  season_number?: number
  status: EpisodeStatus
  duration?: number
  order: number
  created_at: string
  updated_at: string
  script_count: number
  metadata?: Record<string, unknown>
}

export interface EpisodeCreateRequest {
  project_id: string
  title: string
  description?: string
  number: number
  season_number?: number
  status?: EpisodeStatus
  duration?: number
  metadata?: Record<string, unknown>
}

export interface EpisodeUpdateRequest
  extends Partial<Omit<EpisodeCreateRequest, 'project_id'>> {
  order?: number
}

// Generation Service Types (Port 8002)
export const GenerationStatus = {
  PENDING: 'pending',
  IN_PROGRESS: 'in_progress',
  COMPLETED: 'completed',
  FAILED: 'failed',
  CANCELLED: 'cancelled',
} as const

export type GenerationStatus = (typeof GenerationStatus)[keyof typeof GenerationStatus]

export interface GenerationRequest {
  project_id: string
  episode_id: string
  prompt?: string
  model?: string
  parameters?: GenerationParameters
}

export interface GenerationParameters {
  temperature?: number
  max_tokens?: number
  top_p?: number
  frequency_penalty?: number
  presence_penalty?: number
  style?: string
  tone?: string
  length?: 'short' | 'medium' | 'long'
}

export interface Generation {
  id: string
  project_id: string
  episode_id: string
  status: GenerationStatus
  progress: number
  prompt?: string
  model: string
  parameters: GenerationParameters
  result?: string
  error_message?: string
  started_at: string
  completed_at?: string
  created_at: string
  updated_at: string
  user_id: string
  metadata?: Record<string, unknown>
}

export interface Script {
  id: string
  project_id: string
  episode_id: string
  generation_id?: string
  title: string
  content: string
  status: 'draft' | 'review' | 'approved' | 'published'
  version: number
  word_count: number
  ai_generated: boolean
  rating?: number
  tags: string[]
  created_at: string
  updated_at: string
  created_by: string
  metadata?: Record<string, unknown>
}

export interface ScriptCreateRequest {
  project_id: string
  episode_id: string
  title: string
  content: string
  status?: Script['status']
  tags?: string[]
  metadata?: Record<string, unknown>
}

export interface ScriptUpdateRequest
  extends Partial<Omit<ScriptCreateRequest, 'project_id' | 'episode_id'>> {
  version?: number
  rating?: number
}

// System Status Types
export interface ServiceHealth {
  service: string
  status: 'healthy' | 'warning' | 'error'
  response_time: number
  uptime: number
  last_check: string
  message?: string
}

export interface SystemMetrics {
  cpu_usage: number
  memory_usage: number
  disk_usage: number
  network_usage: number
  active_connections: number
  queue_size: number
}

export interface SystemStatus {
  services: ServiceHealth[]
  metrics: SystemMetrics
  alerts: SystemAlert[]
  overall_health: 'healthy' | 'warning' | 'error'
}

export interface SystemAlert {
  id: string
  severity: 'info' | 'warning' | 'error'
  title: string
  message: string
  timestamp: string
  acknowledged: boolean
}

// Analytics Types
export interface UsageStats {
  total_projects: number
  total_scripts: number
  total_generations: number
  active_users: number
  usage_hours: number
  success_rate: number
  avg_generation_time: number
}

export interface ProjectStats {
  project_id: string
  episodes_count: number
  scripts_count: number
  generations_count: number
  avg_rating?: number
  completion_rate: number
  last_activity: string
}

// Pagination and Filtering
export interface PaginationParams {
  page?: number
  limit?: number
  offset?: number
}

export interface SortParams {
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
}

export interface SearchParams {
  search?: string
  filters?: Record<string, unknown>
}

export interface ListResponse<T> {
  items: T[]
  total: number
  page: number
  limit: number
  totalPages: number
  hasNext: boolean
  hasPrev: boolean
}

// WebSocket Types
export interface WebSocketMessage<T = unknown> {
  type: string
  data: T
  timestamp: string
}

export interface GenerationUpdate {
  generation_id: string
  status: GenerationStatus
  progress: number
  message?: string
  error?: string
}

export interface SystemUpdate {
  type: 'service_status' | 'metrics' | 'alert'
  data: ServiceHealth | SystemMetrics | SystemAlert
}
