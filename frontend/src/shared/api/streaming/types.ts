/**
 * SSE (Server-Sent Events) Types and Interfaces
 * Enhanced with discriminated unions for compile-time type safety
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
  | 'patch_preview'
  | 'patch_apply'
  | 'completed'
  | 'failed'
  | 'heartbeat'

/**
 * Base SSE event structure
 */
type SSEBase = {
  jobId: string
  ts?: string // timestamp
}

/**
 * Discriminated Union for SSE Events
 * Provides compile-time type safety and exhaustive pattern matching
 */
export type SSEEventData =
  | ({ type: 'progress'; pct?: number; value?: number; percentage?: number; currentStep: string; estimatedTime?: number; metadata?: Record<string, unknown> } & SSEBase)
  | ({ type: 'preview'; text?: string; markdown: string; content?: string; isPartial: boolean; wordCount?: number; estimatedTokens?: number } & SSEBase)
  | ({ type: 'patch_preview'; range: { start: number; end: number }; text: string } & SSEBase)
  | ({ type: 'patch_apply'; range: { start: number; end: number } } & SSEBase)
  | ({ type: 'completed'; duration?: number; result: { markdown: string; tokens: number; wordCount?: number; modelUsed?: string; episodeId?: string; savedToEpisode?: boolean } } & SSEBase)
  | ({ type: 'failed'; error: { code: string; message: string; retryable: boolean } } & SSEBase)
  | ({ type: 'heartbeat'; timestamp: string } & Partial<SSEBase>)

export type GenerationJobStatus =
  | 'queued'
  | 'streaming'
  | 'completed'
  | 'failed'
  | 'canceled'

/**
 * Type-safe extractors for discriminated union
 * Extract specific event types from SSEEventData
 */
export type ProgressEventData = Extract<SSEEventData, { type: 'progress' }>
export type PreviewEventData = Extract<SSEEventData, { type: 'preview' }>
export type PatchPreviewEventData = Extract<SSEEventData, { type: 'patch_preview' }>
export type PatchApplyEventData = Extract<SSEEventData, { type: 'patch_apply' }>
export type CompletedEventData = Extract<SSEEventData, { type: 'completed' }>
export type FailedEventData = Extract<SSEEventData, { type: 'failed' }>
export type HeartbeatEventData = Extract<SSEEventData, { type: 'heartbeat' }>

/**
 * Type guard functions for runtime validation
 */
export const isProgressEvent = (event: SSEEventData): event is ProgressEventData =>
  event.type === 'progress'

export const isPreviewEvent = (event: SSEEventData): event is PreviewEventData =>
  event.type === 'preview'

export const isPatchPreviewEvent = (event: SSEEventData): event is PatchPreviewEventData =>
  event.type === 'patch_preview'

export const isPatchApplyEvent = (event: SSEEventData): event is PatchApplyEventData =>
  event.type === 'patch_apply'

export const isCompletedEvent = (event: SSEEventData): event is CompletedEventData =>
  event.type === 'completed'

export const isFailedEvent = (event: SSEEventData): event is FailedEventData =>
  event.type === 'failed'

export const isHeartbeatEvent = (event: SSEEventData): event is HeartbeatEventData =>
  event.type === 'heartbeat'

/**
 * Runtime validation function for SSE events
 */
export const isValidSSEEvent = (data: unknown): data is SSEEventData => {
  if (typeof data !== 'object' || data === null) return false
  
  const event = data as Record<string, unknown>
  
  if (typeof event.type !== 'string') return false
  
  const validTypes: SSEEventType[] = ['progress', 'preview', 'patch_preview', 'patch_apply', 'completed', 'failed', 'heartbeat']
  if (!validTypes.includes(event.type as SSEEventType)) return false
  
  // Basic jobId validation (except heartbeat which has optional jobId)
  if (event.type !== 'heartbeat' && typeof event.jobId !== 'string') return false
  
  return true
}

/**
 * SSE event wrapper matching Python SSEEvent structure
 * Enhanced with discriminated union support
 */
export interface SSEEvent {
  type?: SSEEventType // Compatible with existing usage
  event: SSEEventType
  data: SSEEventData
}

/**
 * Backward compatibility aliases
 */
export type TypedSSEEventData = SSEEventData

export interface SSEOptions {
  url: string
  maxRetries?: number
  retryDelays?: number[] // [1000, 2000, 5000, 15000]
  heartbeatTimeout?: number // milliseconds
  withCredentials?: boolean
}

export interface SSEHookReturn {
  connectionState: SSEConnectionState
  events: SSEEventData[]
  latestEvent: SSEEventData | null
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
