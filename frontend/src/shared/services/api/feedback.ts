/**
 * Feedback API client for episode commit system
 * Handles positive feedback submission with idempotency
 */

import { projectHttp } from './clients'

export interface SubmitFeedbackRequest {
  // Event schema hardening
  schema_version: string
  event_id: string  // UUIDv4 for idempotency
  seq: number       // Monotonic sequence per session
  
  // Event details
  event: 'commit_positive' | 'accept_partial' | 'reject_partial' | 'regen_again' | 'regen_different' | 'edit_manual'
  project_id: string
  episode_id: string
  commit_id: string
  
  // Timestamps
  ts_client: string      // ISO8601 timestamp
  ts_client_hr: number   // performance.now() in milliseconds
  
  // Session and scope tracking
  session_id: string
  page_id: string
  editor_scope_id: string
  
  // Reserved tracking fields
  actor_id_hash?: string
  request_id?: string
  trace_id?: string
  ua_hash?: string
  ip_anonymized?: string
  tz_offset: number
  
  // Legacy compatibility (to be deprecated)
  client_ts: string
  
  // Extended behavior data
  behavior_context?: BehaviorContext
  content_data?: Record<string, unknown>
}

export interface BehaviorContext {
  selection_length?: number
  attempt_count?: number
  time_spent?: number
  previous_action?: string
  ui_element?: string
  viewport_position?: Record<string, unknown>
}

export interface SubmitFeedbackResponse {
  stored: boolean
  commit_id: string
  timestamp: string
  request_id: string
  trace_id: string
}

export interface EpisodeCommit {
  commit_id: string
  event_type: string
  client_timestamp: string
  server_timestamp: string
  request_id: string
  trace_id: string
  created_at: string | null
}

export interface EpisodeCommitsResponse {
  episode_id: string
  commits: EpisodeCommit[]
  total: number
}

/**
 * Submit positive feedback for an episode
 * @param request - Feedback request with commit details
 * @returns Response indicating if commit was stored or was duplicate
 */
export const submitFeedback = async (
  request: SubmitFeedbackRequest
): Promise<SubmitFeedbackResponse> => {
  const response = await projectHttp.post<SubmitFeedbackResponse>('/feedback', request)
  return response
}

/**
 * Get commit history for an episode
 * @param episodeId - Episode UUID
 * @returns List of commits for the episode
 */
export const getEpisodeCommits = async (
  episodeId: string
): Promise<EpisodeCommitsResponse> => {
  const response = await projectHttp.get<EpisodeCommitsResponse>(`/episodes/${episodeId}/commits`)
  return response
}

/**
 * Generate a unique commit ID for idempotency
 * @returns UUID string for commit identification
 */
export const generateCommitId = (): string => {
  // Use crypto.randomUUID if available, fallback to timestamp-based UUID
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  
  // Fallback UUID v4 implementation
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0
    const v = c === 'x' ? r : (r & 0x3 | 0x8)
    return v.toString(16)
  })
}

/**
 * Submit behavior feedback for user interactions with schema hardening
 * @param event - Behavior event type
 * @param projectId - Project UUID
 * @param episodeId - Episode UUID
 * @param behaviorContext - Context data for the behavior
 * @param contentData - Additional content data
 * @param actorIdHash - Optional anonymized user identifier
 * @returns Response indicating if feedback was stored
 */
export const submitBehaviorFeedback = async (
  event: SubmitFeedbackRequest['event'],
  projectId: string,
  episodeId: string,
  behaviorContext?: BehaviorContext,
  contentData?: Record<string, unknown>,
  actorIdHash?: string
): Promise<SubmitFeedbackResponse> => {
  const { eventSchemaManager } = await import('@/shared/lib/eventSchemaManager')
  
  // Create hardened event metadata
  const metadata = eventSchemaManager.createEventMetadata(projectId, episodeId, actorIdHash)
  
  const request: SubmitFeedbackRequest = {
    // Schema hardening fields
    ...metadata,
    
    // Event details
    event,
    project_id: projectId,
    episode_id: episodeId,
    commit_id: generateCommitId(),
    
    // Extended behavior data
    behavior_context: behaviorContext,
    content_data: contentData,
  }
  
  // Validate before sending
  if (!eventSchemaManager.validateEvent(request)) {
    console.warn('Invalid event schema:', request)
    throw new Error('Event validation failed')
  }
  
  return await submitFeedback(request)
}

/**
 * Create behavior context from current UI state
 */
export const createBehaviorContext = (params: {
  selectionLength?: number
  attemptCount?: number
  timeSpent?: number
  previousAction?: string
  uiElement?: string
}): BehaviorContext => {
  const viewport = {
    scrollX: window.scrollX,
    scrollY: window.scrollY,
    innerWidth: window.innerWidth,
    innerHeight: window.innerHeight,
  }

  return {
    selection_length: params.selectionLength,
    attempt_count: params.attemptCount,
    time_spent: params.timeSpent,
    previous_action: params.previousAction,
    ui_element: params.uiElement,
    viewport_position: viewport,
  }
}