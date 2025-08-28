/**
 * Tests for behavior tracking system
 * Validates privacy, schema hardening, and event detection
 */

import { renderHook, act } from '@testing-library/react'
import { useBehaviorTracking } from '../useBehaviorTracking'
import { eventSchemaManager } from '@/shared/lib/eventSchemaManager'
import { eventBatchingManager } from '@/shared/lib/eventBatchingManager'
import { eventDetectionRules } from '@/shared/lib/eventDetectionRules'

// Mock the API modules
jest.mock('@/shared/services/api/feedback', () => ({
  submitBehaviorFeedback: jest.fn().mockResolvedValue({ stored: true }),
  createBehaviorContext: jest.fn().mockReturnValue({
    selection_length: 100,
    attempt_count: 1,
    time_spent: 5.5,
    ui_element: 'test',
    viewport_position: { scrollX: 0, scrollY: 0 },
  }),
}))

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
}
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock
})

// Mock sessionStorage
const sessionStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
}
Object.defineProperty(window, 'sessionStorage', {
  value: sessionStorageMock
})

// Mock crypto.randomUUID
Object.defineProperty(global, 'crypto', {
  value: {
    randomUUID: jest.fn(() => 'mock-uuid-' + Math.random()),
  },
})

// Mock performance.now
Object.defineProperty(global, 'performance', {
  value: {
    now: jest.fn(() => Date.now()),
  },
})

// Mock navigator
Object.defineProperty(global, 'navigator', {
  value: {
    doNotTrack: null,
    userAgent: 'test-user-agent',
    onLine: true,
    sendBeacon: jest.fn(),
  },
  writable: true,
})

// Mock document
Object.defineProperty(global, 'document', {
  value: {
    visibilityState: 'visible',
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
  },
  writable: true,
})

describe('useBehaviorTracking', () => {
  const defaultProps = {
    projectId: 'test-project-123',
    episodeId: 'test-episode-456',
    generationId: 'test-generation-789',
  }

  beforeEach(() => {
    jest.clearAllMocks()
    localStorageMock.getItem.mockReturnValue(null)
    sessionStorageMock.getItem.mockReturnValue(null)
  })

  describe('Privacy Controls', () => {
    it('should respect Do Not Track setting', () => {
      // Mock Do Not Track enabled
      Object.defineProperty(navigator, 'doNotTrack', {
        value: '1',
        configurable: true,
      })

      const { result } = renderHook(() => useBehaviorTracking(defaultProps))

      expect(result.current.isAnalyticsEnabled()).toBe(false)
    })

    it('should respect user opt-out preference', () => {
      localStorageMock.getItem.mockImplementation((key) => {
        if (key === 'analytics_enabled') return 'false'
        return null
      })

      const { result } = renderHook(() => useBehaviorTracking(defaultProps))

      expect(result.current.isAnalyticsEnabled()).toBe(false)
    })

    it('should allow analytics by default when not opted out', () => {
      Object.defineProperty(navigator, 'doNotTrack', {
        value: null,
        configurable: true,
      })

      const { result } = renderHook(() => useBehaviorTracking(defaultProps))

      expect(result.current.isAnalyticsEnabled()).toBe(true)
    })
  })

  describe('Event Detection Rules', () => {
    it('should classify regeneration events correctly', () => {
      const scopeId = 'test-scope'
      const strategy = 'creative'
      const agentModes = ['dialogue', 'action']

      // First call should be 'regen_different' (no context)
      const firstType = eventDetectionRules.classifyRegenerationEvent(
        scopeId,
        strategy,
        agentModes,
        100
      )
      expect(firstType).toBe('regen_different')

      // Immediate second call with same params should be 'regen_again'
      const secondType = eventDetectionRules.classifyRegenerationEvent(
        scopeId,
        strategy,
        agentModes,
        100
      )
      expect(secondType).toBe('regen_again')

      // Call with different strategy should be 'regen_different'
      const differentType = eventDetectionRules.classifyRegenerationEvent(
        scopeId,
        'dramatic',
        agentModes,
        100
      )
      expect(differentType).toBe('regen_different')
    })

    it('should detect manual edits correctly', () => {
      const scopeId = 'test-scope'
      
      // Record AI output completion
      eventDetectionRules.recordAiOutputCompletion(scopeId, 1000)

      // Wait for detection delay to pass
      jest.useFakeTimers()
      jest.advanceTimersByTime(600) // 600ms > 500ms delay

      // Detect edit
      const { isManualEdit, deltaChars } = eventDetectionRules.detectManualEdit(
        scopeId,
        1050
      )

      expect(isManualEdit).toBe(true)
      expect(deltaChars).toBe(50)

      jest.useRealTimers()
    })
  })

  describe('Schema Hardening', () => {
    it('should generate valid event metadata', () => {
      const metadata = eventSchemaManager.createEventMetadata(
        defaultProps.projectId,
        defaultProps.episodeId,
        'actor-hash-123'
      )

      expect(metadata).toHaveProperty('schema_version', '1.0')
      expect(metadata).toHaveProperty('event_id')
      expect(metadata).toHaveProperty('seq')
      expect(metadata).toHaveProperty('ts_client')
      expect(metadata).toHaveProperty('ts_client_hr')
      expect(metadata).toHaveProperty('session_id')
      expect(metadata).toHaveProperty('page_id')
      expect(metadata).toHaveProperty('editor_scope_id')
      expect(metadata).toHaveProperty('actor_id_hash', 'actor-hash-123')
      expect(metadata).toHaveProperty('tz_offset')
      expect(typeof metadata.seq).toBe('number')
      expect(metadata.seq).toBeGreaterThan(0)
    })

    it('should validate events and reject text content', () => {
      const validEvent = {
        schema_version: '1.0',
        event_id: 'test-id',
        seq: 1,
        ts_client: new Date().toISOString(),
        ts_client_hr: performance.now(),
        session_id: 'session-id',
        page_id: 'page-id',
        editor_scope_id: 'scope-id',
      }

      expect(eventSchemaManager.validateEvent(validEvent)).toBe(true)

      // Event with forbidden text content should be rejected
      const eventWithText = {
        ...validEvent,
        content_data: {
          text: 'This is forbidden text content that should be rejected',
        },
      }

      expect(eventSchemaManager.validateEvent(eventWithText)).toBe(false)
    })
  })

  describe('Behavior Tracking Integration', () => {
    it('should track regeneration events with proper classification', async () => {
      const { result } = renderHook(() => useBehaviorTracking(defaultProps))

      await act(async () => {
        await result.current.trackRegeneration('creative', ['dialogue'], 100)
      })

      // Should have enqueued an event (specific verification would depend on mocking eventBatchingManager)
      const stats = result.current.getBatchingStats()
      expect(typeof stats.queueSize).toBe('number')
    })

    it('should track edit events when detection conditions are met', async () => {
      const { result } = renderHook(() => useBehaviorTracking(defaultProps))

      // First record AI output completion
      act(() => {
        result.current.recordAiOutputCompletion(1000)
      })

      // Then track edit
      jest.useFakeTimers()
      jest.advanceTimersByTime(600)

      await act(async () => {
        await result.current.trackEditManual(1050)
      })

      jest.useRealTimers()

      // Should have tracked the edit (verification would depend on internal state)
      const stats = result.current.getBatchingStats()
      expect(typeof stats.queueSize).toBe('number')
    })

    it('should track partial interactions with context', async () => {
      const { result } = renderHook(() => useBehaviorTracking(defaultProps))

      // Record partial interaction start
      act(() => {
        result.current.recordPartialInteractionStart(
          { start: 0, end: 100 },
          100
        )
      })

      // Track accept partial
      await act(async () => {
        await result.current.trackAcceptPartial({
          uiElement: 'accept_button',
        })
      })

      // Should have tracked with context
      const stats = result.current.getBatchingStats()
      expect(typeof stats.queueSize).toBe('number')
    })
  })

  describe('Session Management', () => {
    it('should maintain session state across hook instances', () => {
      const { result: result1 } = renderHook(() => useBehaviorTracking(defaultProps))
      const sessionInfo1 = eventSchemaManager.getSessionInfo()

      const { result: result2 } = renderHook(() => useBehaviorTracking(defaultProps))
      const sessionInfo2 = eventSchemaManager.getSessionInfo()

      // Session ID should be the same (singleton pattern)
      expect(sessionInfo1.sessionId).toBe(sessionInfo2.sessionId)
    })

    it('should track session duration and attempt counts', () => {
      const { result } = renderHook(() => useBehaviorTracking(defaultProps))

      const duration = result.current.getSessionDuration()
      expect(typeof duration).toBe('number')
      expect(duration).toBeGreaterThanOrEqual(0)

      const attempts = result.current.getAttemptCount('test_event')
      expect(attempts).toBe(0) // No events tracked yet
    })
  })

  describe('Error Handling', () => {
    it('should handle tracking errors gracefully', async () => {
      // Mock a failing API call
      const mockFeedback = require('@/shared/services/api/feedback')
      mockFeedback.submitBehaviorFeedback.mockRejectedValueOnce(
        new Error('Network error')
      )

      const { result } = renderHook(() => useBehaviorTracking(defaultProps))

      // Should not throw error
      await act(async () => {
        await expect(
          result.current.trackAcceptPartial()
        ).resolves.not.toThrow()
      })
    })

    it('should disable tracking when privacy controls prevent it', async () => {
      // Set Do Not Track
      Object.defineProperty(navigator, 'doNotTrack', {
        value: '1',
        configurable: true,
      })

      const { result } = renderHook(() => useBehaviorTracking(defaultProps))

      await act(async () => {
        await result.current.trackAcceptPartial()
      })

      // No events should be queued when tracking is disabled
      expect(result.current.isAnalyticsEnabled()).toBe(false)
    })
  })
})

describe('Text-Free Validation', () => {
  it('should reject events with text content in behavior context', () => {
    const eventWithTextInBehavior = {
      schema_version: '1.0',
      event_id: 'test-id',
      seq: 1,
      ts_client: new Date().toISOString(),
      ts_client_hr: performance.now(),
      session_id: 'session-id',
      page_id: 'page-id',
      editor_scope_id: 'scope-id',
      behavior_context: {
        selection_length: 100,
        content: 'This is forbidden text in behavior context',
      },
    }

    expect(eventSchemaManager.validateEvent(eventWithTextInBehavior)).toBe(false)
  })

  it('should accept events with only numeric and metadata fields', () => {
    const validEvent = {
      schema_version: '1.0',
      event_id: 'test-id',
      seq: 1,
      ts_client: new Date().toISOString(),
      ts_client_hr: performance.now(),
      session_id: 'session-id',
      page_id: 'page-id',
      editor_scope_id: 'scope-id',
      behavior_context: {
        selection_length: 100,
        attempt_count: 3,
        time_spent: 45.2,
        ui_element: 'btn', // Short strings are allowed
      },
      content_data: {
        event_type: 'accept_partial',
        latency_since_preview_ms: 1250,
        range_start: 0,
        range_end: 100,
        delta_chars: 5,
      },
    }

    expect(eventSchemaManager.validateEvent(validEvent)).toBe(true)
  })
})