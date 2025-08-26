/**
 * TypeScript types for SSE Generation system
 * Extends shared schema types for complete type safety
 */

// =============================================================================
// SSE Event Types (Backend Compatible)
// =============================================================================

export type SSEEventType =
  | 'progress'
  | 'preview'
  | 'completed'
  | 'failed'
  | 'heartbeat'

export interface BaseSSEEvent {
  type: SSEEventType
  jobId: string
}

export interface ProgressEventData extends BaseSSEEvent {
  type: 'progress'
  value: number // 0-100
  currentStep: string // Korean description of current step
  estimatedTime?: number // Estimated remaining time in seconds
  metadata?: Record<string, unknown>
}

export interface PreviewEventData extends BaseSSEEvent {
  type: 'preview'
  markdown: string // Partial script content
  isPartial: boolean // Whether this is partial content
  wordCount?: number
  estimatedTokens?: number
}

export interface CompletedEventData extends BaseSSEEvent {
  type: 'completed'
  result: {
    markdown: string // Final complete script
    tokens: number
    wordCount?: number
    modelUsed?: string
    episodeId?: string // ChromaDB episode ID
    savedToEpisode?: boolean
  }
}

export interface FailedEventData extends BaseSSEEvent {
  type: 'failed'
  error: {
    code: string
    message: string
    retryable: boolean
    details?: Record<string, unknown>
  }
}

export interface HeartbeatEventData extends BaseSSEEvent {
  type: 'heartbeat'
  timestamp: string // ISO timestamp
}

export type SSEEventData =
  | ProgressEventData
  | PreviewEventData
  | CompletedEventData
  | FailedEventData
  | HeartbeatEventData

// =============================================================================
// Generation Job Types
// =============================================================================

export type GenerationJobStatus =
  | 'queued'
  | 'streaming'
  | 'completed'
  | 'failed'
  | 'canceled'

export interface GenerationJobRequest {
  projectId: string
  episodeNumber?: number // Auto-assigned if not provided
  title?: string // Auto-generated if not provided
  description: string // Script description/prompt
  scriptType?: 'drama' | 'comedy' | 'documentary' | 'commercial' | 'educational'
  model?: string
  temperature?: number
  lengthTarget?: number // Target length in words
}

export interface GenerationJobResponse {
  jobId: string
  status: GenerationJobStatus
  sseUrl: string // SSE endpoint URL
  cancelUrl: string // Cancellation endpoint URL
  projectId: string
  episodeNumber?: number
  title: string
  estimatedDuration?: number // Estimated duration in seconds
}

export interface GenerationJobDetails {
  jobId: string
  status: GenerationJobStatus
  progress: number // 0-100
  currentStep: string
  projectId: string
  episodeNumber?: number
  title: string
  wordCount: number
  tokens: number
  createdAt: string // ISO timestamp
  startedAt?: string // ISO timestamp
  completedAt?: string // ISO timestamp
  estimatedRemainingTime?: number // Seconds
  errorCode?: string
  errorMessage?: string
  episodeId?: string // Created episode ID
  savedToEpisode: boolean
}

// =============================================================================
// Connection State Types
// =============================================================================

export type SSEConnectionState = 'connecting' | 'connected' | 'error' | 'closed'

export interface SSEConnectionStatus {
  state: SSEConnectionState
  lastHeartbeat?: string // ISO timestamp
  retryCount: number
  maxRetries: number
  nextRetryIn?: number // Seconds until next retry attempt
  error?: string
}

// =============================================================================
// Generation State Management Types
// =============================================================================

export interface GenerationState {
  // Job information
  jobId?: string
  status: GenerationJobStatus

  // Progress tracking
  progress: number // 0-100
  currentStep: string
  estimatedRemainingTime?: number

  // Content
  previewContent: string
  finalContent?: string
  wordCount: number
  tokens: number

  // Connection status
  connectionStatus: SSEConnectionStatus

  // Error handling
  error?: {
    code: string
    message: string
    retryable: boolean
  }

  // Episode integration
  episodeId?: string
  savedToEpisode: boolean

  // UI state
  isStarting: boolean
  isCancelling: boolean
  canRetry: boolean
  canSave: boolean
}

// =============================================================================
// UI Component Types
// =============================================================================

export interface GenerationDrawerProps {
  isOpen: boolean
  onClose: () => void
  projectId: string
  projectName: string
  initialRequest?: Partial<GenerationJobRequest>
  onEpisodeCreated?: (episodeId: string, episodeNumber: number) => void
}

export interface GenerationProgressProps {
  progress: number
  currentStep: string
  estimatedTime?: number
  connectionState: SSEConnectionState
  retryCount?: number
  maxRetries?: number
}

export interface GenerationPreviewProps {
  content: string
  wordCount: number
  tokens: number
  isPartial: boolean
}

export interface GenerationControlsProps {
  status: GenerationJobStatus
  connectionState: SSEConnectionState
  canRetry: boolean
  canCancel: boolean
  canSave: boolean
  isStarting: boolean
  isCancelling: boolean
  onStart: () => void
  onCancel: () => void
  onRetry: () => void
  onSave: () => void
}

// =============================================================================
// Hook Return Types
// =============================================================================

export interface UseGenerationResult {
  // State
  state: GenerationState

  // Actions
  startGeneration: (request: GenerationJobRequest) => Promise<boolean>
  cancelGeneration: () => Promise<boolean>
  retryGeneration: () => Promise<boolean>

  // Helpers
  reset: () => void
  getProgressMessage: () => string
  getEstimatedTimeString: () => string
}

// =============================================================================
// Error Types
// =============================================================================

export class GenerationError extends Error {
  public code: string
  public retryable: boolean
  public details?: Record<string, unknown>

  constructor(
    message: string,
    code: string,
    retryable: boolean,
    details?: Record<string, unknown>,
  ) {
    super(message)
    this.name = 'GenerationError'
    this.code = code
    this.retryable = retryable
    this.details = details
  }
}

export interface UseSSEConnectionResult {
  // Connection management
  connect: (sseUrl: string, jobId: string) => void
  disconnect: () => void

  // State
  connectionStatus: SSEConnectionStatus
  lastEvent?: SSEEventData

  // Event handlers
  onProgress?: (data: ProgressEventData) => void
  onPreview?: (data: PreviewEventData) => void
  onCompleted?: (data: CompletedEventData) => void
  onFailed?: (data: FailedEventData) => void
  onHeartbeat?: (data: HeartbeatEventData) => void
}

// =============================================================================
// Episode Integration Types
// =============================================================================

export interface EpisodeFromGeneration {
  id: string
  projectId: string
  number: number // Auto-assigned
  title: string
  script: {
    markdown: string
    tokens: number
  }
  createdAt: string
}

export interface EpisodeListUpdate {
  type: 'episode_created'
  episode: EpisodeFromGeneration
}

// =============================================================================
// Error Types
// =============================================================================

export interface SSEConnectionError extends Error {
  connectionState: SSEConnectionState
  retryCount: number
  canRetry: boolean
}

// =============================================================================
// Service Configuration Types
// =============================================================================

export interface GenerationServiceConfig {
  baseUrl: string
  timeout: number
  retryDelays: number[] // [1000, 2000, 5000] for exponential backoff
  maxRetries: number
  heartbeatTimeout: number // Max time between heartbeats before considering connection dead
}

export interface SSEEventHandlers {
  onProgress?: (data: ProgressEventData) => void
  onPreview?: (data: PreviewEventData) => void
  onCompleted?: (data: CompletedEventData) => void
  onFailed?: (data: FailedEventData) => void
  onHeartbeat?: (data: HeartbeatEventData) => void
  onConnectionChange?: (status: SSEConnectionStatus) => void
  onError?: (error: Error) => void
}

// =============================================================================
// API Response Types
// =============================================================================

export interface ApiResponse<T = unknown> {
  success: boolean
  message: string
  data?: T
  error?: {
    code: string
    message: string
    details?: Record<string, unknown>
  }
}

export type GenerationStartResponse = ApiResponse<GenerationJobResponse>
export type GenerationStatusResponse = ApiResponse<GenerationJobDetails>
export type GenerationListResponse = ApiResponse<{
  active_jobs: GenerationJobDetails[]
  total_active: number
}>
export type GenerationStatsResponse = ApiResponse<{
  job_statistics: Record<string, number>
  service_status: string
  timestamp: number
}>

// =============================================================================
// Route and URL Types
// =============================================================================

export interface GenerationRouteParams {
  projectId: string
  gen?: 'new' | string // 'new' for new generation, jobId for existing
}

export interface GenerationURLState {
  drawerOpen: boolean
  jobId?: string
  status?: GenerationJobStatus
}
