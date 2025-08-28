/**
 * Hook for tracking user behavior events in script generation
 * Provides non-intrusive data collection for AI improvement with privacy by construction
 */

import { useCallback, useRef, useState } from 'react'
import { createBehaviorContext } from '@/shared/services/api/feedback'
import type { SubmitFeedbackRequest } from '@/shared/services/api/feedback'
import { eventSchemaManager } from '@/shared/lib/eventSchemaManager'
import { eventBatchingManager } from '@/shared/lib/eventBatchingManager'
import { eventDetectionRules } from '@/shared/lib/eventDetectionRules'

interface BehaviorTrackingState {
  sessionStartTime: number
  lastAction: string | null
  attemptCounts: Record<string, number>
  timeSpentMap: Record<string, number>
}

interface UseBehaviorTrackingProps {
  projectId: string
  episodeId: string
  generationId?: string
}

interface TrackEventParams {
  uiElement?: string
  selectionLength?: number
  contentData?: Record<string, unknown>
}

export function useBehaviorTracking({
  projectId,
  episodeId,
}: UseBehaviorTrackingProps) {
  const sessionState = useRef<BehaviorTrackingState>({
    sessionStartTime: Date.now(),
    lastAction: null,
    attemptCounts: {},
    timeSpentMap: {},
  })

  const [isTracking, setIsTracking] = useState(true)
  const lastActionTimeRef = useRef<number>(Date.now())

  // Track time spent on actions
  const updateTimeSpent = useCallback((action: string) => {
    const now = Date.now()
    const timeSpent = now - lastActionTimeRef.current
    sessionState.current.timeSpentMap[action] = 
      (sessionState.current.timeSpentMap[action] || 0) + timeSpent
    lastActionTimeRef.current = now
  }, [])

  // Track attempt counts
  const incrementAttemptCount = useCallback((action: string) => {
    sessionState.current.attemptCounts[action] = 
      (sessionState.current.attemptCounts[action] || 0) + 1
  }, [])

  // Check if tracking is enabled (privacy controls)
  const isTrackingEnabled = useCallback((): boolean => {
    return isTracking && eventSchemaManager.isAnalyticsEnabled()
  }, [isTracking])

  // Submit behavior event with privacy and batching
  const trackEvent = useCallback(async (
    event: SubmitFeedbackRequest['event'],
    params: TrackEventParams = {}
  ) => {
    if (!isTrackingEnabled()) return

    try {
      // Update internal tracking
      incrementAttemptCount(event)
      updateTimeSpent(event)

      // Get visibility-aware time spent
      const visibilityAwareTime = eventBatchingManager.getVisibilityAwareTime()

      // Create behavior context (text-free)
      const behaviorContext = createBehaviorContext({
        selectionLength: params.selectionLength,
        attemptCount: sessionState.current.attemptCounts[event],
        timeSpent: visibilityAwareTime,
        previousAction: sessionState.current.lastAction || undefined,
        uiElement: params.uiElement,
      })

      // Create event metadata with schema hardening
      const metadata = eventSchemaManager.createEventMetadata(projectId, episodeId)

      // Create full event payload
      const eventPayload: SubmitFeedbackRequest = {
        ...metadata,
        event,
        project_id: projectId,
        episode_id: episodeId,
        commit_id: crypto.randomUUID(),
        behavior_context: behaviorContext,
        content_data: params.contentData,
      }

      // Validate event (privacy check)
      if (!eventSchemaManager.validateEvent(eventPayload)) {
        console.warn('Event failed privacy validation')
        return
      }

      // Add to batch queue instead of immediate submission
      await eventBatchingManager.enqueueEvent(eventPayload)

      // Update last action
      sessionState.current.lastAction = event

    } catch (error) {
      // Silently fail - don't disrupt user experience
      console.warn('Behavior tracking error:', error)
    }
  }, [isTrackingEnabled, projectId, episodeId, incrementAttemptCount, updateTimeSpent])

  // Intelligent tracking functions with event detection rules
  const trackAcceptPartial = useCallback((params: TrackEventParams = {}) => {
    const scopeId = eventSchemaManager.createEventMetadata(projectId, episodeId).editor_scope_id
    const partialContext = eventDetectionRules.getPartialInteractionContext(scopeId)
    
    if (partialContext) {
      const contentData = eventDetectionRules.createBehaviorContentData('accept_partial', {
        latencySincePreview: partialContext.latencySincePreview,
        rangeStart: partialContext.rangeStart,
        rangeEnd: partialContext.rangeEnd,
        selectionLength: partialContext.selectionLength,
      })
      
      return trackEvent('accept_partial', { ...params, contentData })
    }
    
    return trackEvent('accept_partial', params)
  }, [trackEvent, projectId, episodeId])

  const trackRejectPartial = useCallback((params: TrackEventParams = {}) => {
    const scopeId = eventSchemaManager.createEventMetadata(projectId, episodeId).editor_scope_id
    const partialContext = eventDetectionRules.getPartialInteractionContext(scopeId)
    
    if (partialContext) {
      const contentData = eventDetectionRules.createBehaviorContentData('reject_partial', {
        latencySincePreview: partialContext.latencySincePreview,
        rangeStart: partialContext.rangeStart,
        rangeEnd: partialContext.rangeEnd,
        selectionLength: partialContext.selectionLength,
      })
      
      return trackEvent('reject_partial', { ...params, contentData })
    }
    
    return trackEvent('reject_partial', params)
  }, [trackEvent, projectId, episodeId])

  const trackRegeneration = useCallback((
    strategy: string,
    agentModes: string[],
    selectionLength?: number,
    selectionRange?: { start: number; end: number }
  ) => {
    const scopeId = eventSchemaManager.createEventMetadata(projectId, episodeId).editor_scope_id
    const eventType = eventDetectionRules.classifyRegenerationEvent(
      scopeId,
      strategy,
      agentModes,
      selectionLength,
      selectionRange
    )
    
    const contentData = eventDetectionRules.createBehaviorContentData(eventType, {
      strategyChanged: eventType === 'regen_different',
      agentModesChanged: eventType === 'regen_different',
      selectionLength,
    })
    
    return trackEvent(eventType, { contentData })
  }, [trackEvent, projectId, episodeId])

  const trackEditManual = useCallback((contentLength: number, params: TrackEventParams = {}) => {
    const scopeId = eventSchemaManager.createEventMetadata(projectId, episodeId).editor_scope_id
    const { isManualEdit, deltaChars } = eventDetectionRules.detectManualEdit(scopeId, contentLength)
    
    if (isManualEdit) {
      const contentData = eventDetectionRules.createBehaviorContentData('edit_manual', {
        deltaChars,
      })
      
      return trackEvent('edit_manual', { ...params, contentData })
    }
    
    return Promise.resolve()
  }, [trackEvent, projectId, episodeId])

  // Helper functions for context management
  const recordAiOutputCompletion = useCallback((contentLength: number) => {
    const scopeId = eventSchemaManager.createEventMetadata(projectId, episodeId).editor_scope_id
    eventDetectionRules.recordAiOutputCompletion(scopeId, contentLength)
  }, [projectId, episodeId])

  const recordPartialInteractionStart = useCallback((
    selectionRange: { start: number; end: number },
    selectionLength: number
  ) => {
    const scopeId = eventSchemaManager.createEventMetadata(projectId, episodeId).editor_scope_id
    eventDetectionRules.recordPartialInteractionStart(scopeId, selectionRange, selectionLength)
  }, [projectId, episodeId])

  // Utility functions
  const getSessionDuration = useCallback(() => {
    return (Date.now() - sessionState.current.sessionStartTime) / 1000
  }, [])

  const getAttemptCount = useCallback((action: string) => {
    return sessionState.current.attemptCounts[action] || 0
  }, [])

  const getTotalTimeSpent = useCallback((action: string) => {
    return (sessionState.current.timeSpentMap[action] || 0) / 1000
  }, [])

  // Enable/disable tracking
  const setTracking = useCallback((enabled: boolean) => {
    setIsTracking(enabled)
  }, [])

  return {
    // Event tracking functions (intelligent)
    trackAcceptPartial,
    trackRejectPartial,
    trackRegeneration,
    trackEditManual,
    
    // Context management
    recordAiOutputCompletion,
    recordPartialInteractionStart,
    
    // Utility functions
    getSessionDuration,
    getAttemptCount,
    getTotalTimeSpent,
    
    // Control and privacy
    isTracking,
    setTracking,
    isAnalyticsEnabled: eventSchemaManager.isAnalyticsEnabled,
    setAnalyticsEnabled: eventSchemaManager.setAnalyticsEnabled,
    
    // Statistics
    getBatchingStats: eventBatchingManager.getStatistics,
    getDetectionStats: eventDetectionRules.getStatistics,
  }
}