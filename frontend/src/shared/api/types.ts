// Common API response types
export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  message?: string
  error?: string
}

// Project types
export interface Project {
  id: string
  name: string
  type: 'drama' | 'comedy' | 'documentary' | 'other'
  status: 'active' | 'completed' | 'paused' | 'draft'
  description?: string
  created_at: string
  updated_at: string
  progress_percentage?: number
}

export interface ProjectCreateRequest {
  name: string
  type: Project['type']
  description?: string
}

export interface ProjectUpdateRequest {
  name?: string
  type?: Project['type']
  description?: string
  status?: Project['status']
}

// Episode types
export interface Episode {
  id: string
  project_id: string
  title: string
  description?: string
  number: number
  order: number
  status: 'draft' | 'completed' | 'published'
  script_content?: string
  created_at: string
  updated_at: string
}

export interface EpisodeCreateRequest {
  title: string
  description?: string
  number?: number
  order?: number
}

export interface EpisodeUpdateRequest {
  title?: string
  description?: string
  number?: number
  order?: number
  status?: Episode['status']
  script_content?: string
}

// Generation types
export interface GenerationRequest {
  project_id: string
  episode_id?: string
  prompt: string
  model?: 'gpt-4' | 'claude-3'
  max_tokens?: number
  temperature?: number
}

export interface Generation {
  id: string
  project_id: string
  episode_id?: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  content?: string
  metadata?: Record<string, any>
  created_at: string
  updated_at: string
}

// Pagination types
export interface PaginationParams {
  page?: number
  limit?: number
  search?: string
}

export interface PaginatedResponse<T> {
  data: T[]
  pagination: {
    page: number
    limit: number
    total: number
    pages: number
  }
}

// Error types
export interface ApiError {
  code: string
  message: string
  details?: Record<string, any>
}
