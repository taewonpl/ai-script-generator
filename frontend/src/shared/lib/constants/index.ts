// API endpoints
export const API_ENDPOINTS = {
  PROJECTS: '/projects',
  EPISODES: '/episodes',
  GENERATION: '/generate',
  HEALTH: '/health',
} as const

// Project types
export const PROJECT_TYPES = [
  { value: 'drama', label: 'Drama' },
  { value: 'comedy', label: 'Comedy' },
  { value: 'documentary', label: 'Documentary' },
  { value: 'other', label: 'Other' },
] as const

// Project statuses
export const PROJECT_STATUSES = [
  { value: 'draft', label: 'Draft', color: 'default' },
  { value: 'active', label: 'Active', color: 'success' },
  { value: 'paused', label: 'Paused', color: 'warning' },
  { value: 'completed', label: 'Completed', color: 'primary' },
] as const

// Episode statuses
export const EPISODE_STATUSES = [
  { value: 'draft', label: 'Draft', color: 'default' },
  { value: 'completed', label: 'Completed', color: 'success' },
  { value: 'published', label: 'Published', color: 'primary' },
] as const

// AI Models
export const AI_MODELS = [
  { value: 'gpt-4', label: 'GPT-4', description: 'OpenAI GPT-4' },
  { value: 'claude-3', label: 'Claude 3', description: 'Anthropic Claude 3' },
] as const

// Query keys for React Query
export const QUERY_KEYS = {
  PROJECTS: ['projects'],
  PROJECT: (id: string) => ['projects', id],
  EPISODES: (projectId: string) => ['projects', projectId, 'episodes'],
  EPISODE: (projectId: string, episodeId: string) => [
    'projects',
    projectId,
    'episodes',
    episodeId,
  ],
  GENERATIONS: ['generations'],
  GENERATION: (id: string) => ['generations', id],
} as const

// Local storage keys
export const STORAGE_KEYS = {
  AUTH_TOKEN: 'auth_token',
  USER_PREFERENCES: 'user_preferences',
  THEME_MODE: 'theme_mode',
  RECENT_PROJECTS: 'recent_projects',
} as const

// App configuration
export const APP_CONFIG = {
  NAME: 'AI Script Generator',
  VERSION: '1.0.0',
  DEFAULT_PAGE_SIZE: 20,
  MAX_FILE_SIZE: 10 * 1024 * 1024, // 10MB
  DEBOUNCE_DELAY: 300,
} as const
