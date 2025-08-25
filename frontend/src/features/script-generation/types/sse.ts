/**
 * Server-Sent Events types matching backend implementation
 * Based on generation-service/src/generation_service/models/sse_models.py
 */
export const SSEEventType = {
  PROGRESS: 'progress',
  PREVIEW: 'preview',
  COMPLETED: 'completed',
  FAILED: 'failed',
  HEARTBEAT: 'heartbeat',
} as const

export type SSEEventType = (typeof SSEEventType)[keyof typeof SSEEventType]

/**
 * Job status enum matching backend GenerationJobStatus
 */
export const GenerationJobStatus = {
  QUEUED: 'queued',
  STREAMING: 'streaming',
  COMPLETED: 'completed',
  FAILED: 'failed',
  CANCELED: 'canceled',
} as const

export type GenerationJobStatus =
  (typeof GenerationJobStatus)[keyof typeof GenerationJobStatus]

/**
 * Progress event data structure - matches backend ProgressEventData exactly
 */
export interface ProgressEventData {
  type: 'progress'
  jobId: string
  value: number // 0-100 progress percentage (ge=0, le=100 in backend)
  currentStep: string // Korean step description
  estimatedTime?: number // Remaining time in seconds
  metadata?: Record<string, unknown>
}

/**
 * Preview event data structure - matches backend PreviewEventData exactly
 */
export interface PreviewEventData {
  type: 'preview'
  jobId: string
  markdown: string // Partial script content in markdown
  isPartial: boolean // Default True in backend for preview events
  wordCount?: number
  estimatedTokens?: number
}

/**
 * Completed event data structure - matches backend CompletedEventData exactly
 */
export interface CompletedEventData {
  type: 'completed'
  jobId: string
  result: {
    markdown: string // Final complete script
    tokens: number
    wordCount?: number
    modelUsed?: string
    episodeId?: string
    savedToEpisode?: boolean
    [key: string]: unknown // For additional fields like in create_result()
  }
}

/**
 * Failed event data structure - matches backend FailedEventData exactly
 */
export interface FailedEventData {
  type: 'failed'
  jobId: string
  error: {
    code: string
    message: string
    retryable: boolean
    [key: string]: unknown // For additional fields like in create_error()
  }
}

/**
 * Heartbeat event data structure - matches backend HeartbeatEventData exactly
 */
export interface HeartbeatEventData {
  type: 'heartbeat'
  timestamp: string // ISO timestamp from create_now()
  jobId?: string
}

/**
 * Union type for all SSE event data types
 * Matches backend SSEEvent data field discriminated union
 */
export type AppEvent =
  | ProgressEventData
  | PreviewEventData
  | CompletedEventData
  | FailedEventData
  | HeartbeatEventData

/**
 * Raw SSE message structure from EventSource
 * Matches the format_sse() output from backend SSEEvent
 */
export interface SSEMessage {
  id?: string // Event ID for Last-Event-ID support (job.lastEventId)
  event: SSEEventType
  data: AppEvent
}

/**
 * Client-side generation state for UI management
 */
export type GenerationState =
  | 'idle'
  | 'starting'
  | 'generating'
  | 'completed'
  | 'failed'
  | 'cancelled'

/**
 * Generation job tracking model - matches backend GenerationJob exactly
 */
export interface GenerationJob {
  // Core identification
  jobId: string
  projectId: string
  episodeNumber?: number

  // Job configuration
  title: string
  description: string
  scriptType: string
  promptSnapshot: string // Default "" in backend

  // Status and progress
  status: GenerationJobStatus // Default QUEUED in backend
  progress: number // Default 0, ge=0, le=100 in backend
  currentStep: string // Default "대기 중" in backend

  // Content
  currentContent: string // Default "" in backend
  finalContent?: string

  // Metadata
  tokens: number // Default 0 in backend
  wordCount: number // Default 0 in backend
  modelUsed?: string

  // Timing
  createdAt: string // ISO timestamp
  startedAt?: string // ISO timestamp
  completedAt?: string // ISO timestamp
  estimatedDuration?: number // Seconds

  // Error handling
  errorCode?: string
  errorMessage?: string
  retryCount: number // Default 0 in backend

  // Episode integration
  episodeId?: string
  savedToEpisode: boolean // Default False in backend

  // Event tracking for Last-Event-ID support
  eventSequence: number // Default 0 in backend
  lastEventId?: string
}

/**
 * Request to create a new generation job - matches backend GenerationJobRequest exactly
 */
export interface GenerationJobRequest {
  projectId: string
  episodeNumber?: number // Auto-assigned if not provided
  title?: string // Auto-generated if not provided
  description: string // Required script description/prompt
  scriptType?: string // Default "drama" in backend
  model?: string // Preferred AI model
  temperature?: number // Default 0.7 in backend
  lengthTarget?: number // Target length in words
}

/**
 * Response when creating a generation job - matches backend GenerationJobResponse exactly
 */
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

/**
 * SSE connection configuration for client-side usage
 */
export interface SSEConnectionConfig {
  url: string
  maxRetries: number
  reconnectDelays: number[] // [1s, 2s, 5s] with jitter as per CLAUDE.md
  heartbeatTimeout: number // 30 seconds as per backend
  idempotencyKey: string
}

/**
 * SSE hook return value for React components
 */
export interface UseSSEResult {
  state: GenerationState
  progress: number
  preview: string
  error: string | null
  retryCount: number
  isConnected: boolean
  lastHeartbeat: string | null
}
