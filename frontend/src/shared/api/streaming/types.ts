/**
 * SSE (Server-Sent Events) Types and Interfaces
 * Updated to match Python backend sse_models.py
 */

export type SSEConnectionState =
  | 'idle'
  | 'connecting'
  | 'open'
  | 'retrying'
  | 'closed'

export type SSEEventType =
  | 'progress'
  | 'preview'
  | 'completed'
  | 'failed'
  | 'heartbeat'

export type GenerationJobStatus =
  | 'queued'
  | 'streaming'
  | 'completed'
  | 'failed'
  | 'canceled'

/**
 * Progress event data matching Python ProgressEventData
 */
export interface ProgressEventData {
  type: 'progress'
  jobId: string
  value: number // 0-100 progress percentage
  percentage?: number // Alias for value for compatibility
  currentStep: string // Korean step description
  estimatedTime?: number // seconds remaining
  metadata?: Record<string, unknown>
}

/**
 * Preview event data matching Python PreviewEventData
 */
export interface PreviewEventData {
  type: 'preview'
  jobId: string
  markdown: string // partial script content
  content?: string // Alias for markdown for compatibility
  isPartial: boolean
  wordCount?: number
  estimatedTokens?: number
}

/**
 * Completed event data matching Python CompletedEventData
 */
export interface CompletedEventData {
  type: 'completed'
  jobId: string
  duration?: number // seconds taken for generation
  result: {
    markdown: string
    tokens: number
    wordCount?: number
    modelUsed?: string
    episodeId?: string
    savedToEpisode?: boolean
  }
}

/**
 * Failed event data matching Python FailedEventData
 */
export interface FailedEventData {
  type: 'failed'
  jobId: string
  error: {
    code: string
    message: string
    retryable: boolean
  }
}

/**
 * Heartbeat event data matching Python HeartbeatEventData
 */
export interface HeartbeatEventData {
  type: 'heartbeat'
  timestamp: string // ISO format
  jobId?: string
}

/**
 * SSE event wrapper matching Python SSEEvent structure
 */
export interface SSEEvent {
  type?: SSEEventType // Compatible with existing usage
  event: SSEEventType
  data:
    | ProgressEventData
    | PreviewEventData
    | CompletedEventData
    | FailedEventData
    | HeartbeatEventData
}

export type TypedSSEEventData =
  | ProgressEventData
  | PreviewEventData
  | CompletedEventData
  | FailedEventData
  | HeartbeatEventData

// 🔁 Backward-compat alias to fix TS2724 ("SSEEventData" not exported)
export type SSEEventData = TypedSSEEventData

export interface SSEOptions {
  url: string
  maxRetries?: number
  retryDelays?: number[] // [1000, 2000, 5000, 15000]
  heartbeatTimeout?: number // milliseconds
  withCredentials?: boolean
}

export interface SSEHookReturn {
  connectionState: SSEConnectionState
  events: TypedSSEEventData[]
  latestEvent: TypedSSEEventData | null
  error: Error | null
  connect: () => void
  disconnect: () => void
  clearEvents: () => void
  retryCount: number
  lastConnectedAt: Date | null
}

/**
 * Generation result data structure
 */
export interface GenerationResult {
  jobId: string
  projectId: string
  episodeId: string
  content: string
  script?: string | { markdown: string } // Support both string and object formats
  status: GenerationJobStatus
  duration?: number
  error?: string
}
