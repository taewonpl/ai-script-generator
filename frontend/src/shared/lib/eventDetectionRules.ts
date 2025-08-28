/**
 * Event Detection Rules
 * Provides precise classification rules for behavior events
 */

interface RegenerationContext {
  lastGenerateTime: number
  lastStrategy: string
  lastAgentModes: string[]
  lastSelectionLength?: number
  lastSelectionRange?: { start: number; end: number }
  scopeId: string
}

interface EditContext {
  lastAiOutputTime: number
  lastContentLength: number
  scopeId: string
}

interface PartialInteractionContext {
  previewStartTime: number
  selectionRange: { start: number; end: number }
  selectionLength: number
  scopeId: string
}

class EventDetectionRules {
  private static instance: EventDetectionRules
  private regenerationContexts = new Map<string, RegenerationContext>()
  private editContexts = new Map<string, EditContext>()
  private partialContexts = new Map<string, PartialInteractionContext>()
  
  private readonly REGEN_AGAIN_THRESHOLD_MS = 30000 // 30 seconds
  private readonly SELECTION_DIFF_THRESHOLD = 0.3 // 30% difference
  private readonly EDIT_DETECTION_DELAY_MS = 500 // 500ms after AI output

  private constructor() {
    this.setupCleanupTimer()
  }

  public static getInstance(): EventDetectionRules {
    if (!EventDetectionRules.instance) {
      EventDetectionRules.instance = new EventDetectionRules()
    }
    return EventDetectionRules.instance
  }

  /**
   * Classify regeneration event type
   */
  public classifyRegenerationEvent(
    scopeId: string,
    currentStrategy: string,
    currentAgentModes: string[],
    selectionLength?: number,
    selectionRange?: { start: number; end: number }
  ): 'regen_again' | 'regen_different' {
    const context = this.regenerationContexts.get(scopeId)
    const now = Date.now()

    if (!context) {
      // First generation for this scope
      this.updateRegenerationContext(scopeId, currentStrategy, currentAgentModes, selectionLength, selectionRange)
      return 'regen_different'
    }

    const timeSinceLastGenerate = now - context.lastGenerateTime
    const strategyUnchanged = context.lastStrategy === currentStrategy
    const agentModesUnchanged = this.arraysEqual(context.lastAgentModes, currentAgentModes)
    const selectionSimilar = this.isSelectionSimilar(
      context.lastSelectionLength,
      context.lastSelectionRange,
      selectionLength,
      selectionRange
    )

    // Update context for next comparison
    this.updateRegenerationContext(scopeId, currentStrategy, currentAgentModes, selectionLength, selectionRange)

    // Classification logic
    if (
      timeSinceLastGenerate <= this.REGEN_AGAIN_THRESHOLD_MS &&
      strategyUnchanged &&
      agentModesUnchanged &&
      selectionSimilar
    ) {
      return 'regen_again'
    }

    return 'regen_different'
  }

  /**
   * Detect manual edit event
   */
  public detectManualEdit(
    scopeId: string,
    newContentLength: number
  ): { isManualEdit: boolean; deltaChars: number } {
    const context = this.editContexts.get(scopeId)
    const now = Date.now()

    if (!context) {
      return { isManualEdit: false, deltaChars: 0 }
    }

    const timeSinceAiOutput = now - context.lastAiOutputTime
    const deltaChars = newContentLength - context.lastContentLength

    // Update context
    this.editContexts.set(scopeId, {
      ...context,
      lastContentLength: newContentLength,
    })

    // Detect if this is a manual edit (first keystroke after AI output)
    const isManualEdit = timeSinceAiOutput > this.EDIT_DETECTION_DELAY_MS && Math.abs(deltaChars) > 0

    return { isManualEdit, deltaChars }
  }

  /**
   * Record AI output completion
   */
  public recordAiOutputCompletion(scopeId: string, contentLength: number): void {
    this.editContexts.set(scopeId, {
      lastAiOutputTime: Date.now(),
      lastContentLength: contentLength,
      scopeId,
    })
  }

  /**
   * Record partial interaction start (preview shown)
   */
  public recordPartialInteractionStart(
    scopeId: string,
    selectionRange: { start: number; end: number },
    selectionLength: number
  ): void {
    this.partialContexts.set(scopeId, {
      previewStartTime: Date.now(),
      selectionRange,
      selectionLength,
      scopeId,
    })
  }

  /**
   * Get partial interaction context for accept/reject events
   */
  public getPartialInteractionContext(scopeId: string): {
    latencySincePreview: number
    rangeStart: number
    rangeEnd: number
    selectionLength: number
  } | null {
    const context = this.partialContexts.get(scopeId)
    if (!context) return null

    const latencySincePreview = Date.now() - context.previewStartTime

    return {
      latencySincePreview,
      rangeStart: context.selectionRange.start,
      rangeEnd: context.selectionRange.end,
      selectionLength: context.selectionLength,
    }
  }

  /**
   * Create content data for behavior events (text-free)
   */
  public createBehaviorContentData(
    eventType: 'accept_partial' | 'reject_partial' | 'regen_again' | 'regen_different' | 'edit_manual',
    params: {
      deltaChars?: number
      latencySincePreview?: number
      rangeStart?: number
      rangeEnd?: number
      selectionLength?: number
      strategyChanged?: boolean
      agentModesChanged?: boolean
      timeSinceLastAction?: number
    }
  ): Record<string, unknown> {
    const baseData = {
      event_type: eventType,
      timestamp: Date.now(),
    }

    switch (eventType) {
      case 'accept_partial':
      case 'reject_partial':
        return {
          ...baseData,
          latency_since_preview_ms: params.latencySincePreview,
          range_start: params.rangeStart,
          range_end: params.rangeEnd,
          selection_length: params.selectionLength,
        }

      case 'regen_again':
        return {
          ...baseData,
          time_since_last_action_ms: params.timeSinceLastAction,
          identical_context: true,
        }

      case 'regen_different':
        return {
          ...baseData,
          strategy_changed: params.strategyChanged,
          agent_modes_changed: params.agentModesChanged,
          selection_length_changed: params.selectionLength !== undefined,
        }

      case 'edit_manual':
        return {
          ...baseData,
          delta_chars: params.deltaChars, // +/- only, no actual text content
        }

      default:
        return baseData
    }
  }

  /**
   * Private helper methods
   */
  private updateRegenerationContext(
    scopeId: string,
    strategy: string,
    agentModes: string[],
    selectionLength?: number,
    selectionRange?: { start: number; end: number }
  ): void {
    this.regenerationContexts.set(scopeId, {
      lastGenerateTime: Date.now(),
      lastStrategy: strategy,
      lastAgentModes: [...agentModes],
      lastSelectionLength: selectionLength,
      lastSelectionRange: selectionRange ? { ...selectionRange } : undefined,
      scopeId,
    })
  }

  private arraysEqual(a: string[], b: string[]): boolean {
    if (a.length !== b.length) return false
    return a.every((val, index) => val === b[index])
  }

  private isSelectionSimilar(
    lastLength?: number,
    lastRange?: { start: number; end: number },
    currentLength?: number,
    currentRange?: { start: number; end: number }
  ): boolean {
    // If we don't have selection data, consider them similar
    if (!lastLength || !currentLength) return true

    // Check if selection length is within threshold
    const lengthDiff = Math.abs(lastLength - currentLength) / Math.max(lastLength, currentLength)
    const lengthSimilar = lengthDiff <= this.SELECTION_DIFF_THRESHOLD

    // If we have range data, check range similarity too
    if (lastRange && currentRange) {
      const rangeOverlap = this.calculateRangeOverlap(lastRange, currentRange)
      const totalRange = Math.max(currentRange.end, lastRange.end) - Math.min(currentRange.start, lastRange.start)
      const overlapRatio = rangeOverlap / totalRange
      
      return lengthSimilar && overlapRatio > (1 - this.SELECTION_DIFF_THRESHOLD)
    }

    return lengthSimilar
  }

  private calculateRangeOverlap(
    range1: { start: number; end: number },
    range2: { start: number; end: number }
  ): number {
    const overlapStart = Math.max(range1.start, range2.start)
    const overlapEnd = Math.min(range1.end, range2.end)
    return Math.max(0, overlapEnd - overlapStart)
  }

  private setupCleanupTimer(): void {
    // Clean up old contexts every 5 minutes
    setInterval(() => {
      const now = Date.now()
      const maxAge = 5 * 60 * 1000 // 5 minutes

      // Clean up old regeneration contexts
      for (const [scopeId, context] of this.regenerationContexts.entries()) {
        if (now - context.lastGenerateTime > maxAge) {
          this.regenerationContexts.delete(scopeId)
        }
      }

      // Clean up old edit contexts
      for (const [scopeId, context] of this.editContexts.entries()) {
        if (now - context.lastAiOutputTime > maxAge) {
          this.editContexts.delete(scopeId)
        }
      }

      // Clean up old partial contexts
      for (const [scopeId, context] of this.partialContexts.entries()) {
        if (now - context.previewStartTime > maxAge) {
          this.partialContexts.delete(scopeId)
        }
      }
    }, 5 * 60 * 1000)
  }

  /**
   * Get detection statistics
   */
  public getStatistics() {
    return {
      regenerationContexts: this.regenerationContexts.size,
      editContexts: this.editContexts.size,
      partialContexts: this.partialContexts.size,
      thresholds: {
        regenAgainMs: this.REGEN_AGAIN_THRESHOLD_MS,
        selectionDiffRatio: this.SELECTION_DIFF_THRESHOLD,
        editDetectionDelayMs: this.EDIT_DETECTION_DELAY_MS,
      },
    }
  }
}

export const eventDetectionRules = EventDetectionRules.getInstance()