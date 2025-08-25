/**
 * Frontend tracing utilities for distributed tracing
 */

import type { TraceContext } from '../types/observability'
import { TraceHeaders } from '../types/observability'

// Generate unique trace ID
export function generateTraceId(): string {
  const timestamp = Date.now().toString(36)
  const random = Math.random().toString(36).substr(2, 9)
  return `trace_${timestamp}_${random}`
}

// Generate unique job ID for generation tasks
export function generateJobId(): string {
  const timestamp = Date.now().toString(36)
  const random = Math.random().toString(36).substr(2, 6)
  return `job_${timestamp}_${random}`
}

// Generate unique request ID
export function generateRequestId(): string {
  const timestamp = Date.now().toString(36)
  const random = Math.random().toString(36).substr(2, 6)
  return `req_${timestamp}_${random}`
}

// Generate UUID v4 compatible ID
export function generateUUID(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
    const r = (Math.random() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

// Extract trace context from browser environment
export function extractTraceContextFromURL(): Partial<TraceContext> {
  const urlParams = new URLSearchParams(window.location.search)

  return {
    traceId: urlParams.get('traceId') || undefined,
    jobId: urlParams.get('jobId') || undefined,
    projectId: urlParams.get('projectId') || undefined,
  }
}

// Create trace context for frontend operations
export function createTraceContext(
  options: {
    traceId?: string
    jobId?: string
    projectId?: string
    userId?: string
    service?: string
  } = {},
): TraceContext {
  return {
    traceId: options.traceId || generateTraceId(),
    jobId: options.jobId,
    projectId: options.projectId,
    userId: options.userId,
    service: options.service || 'frontend',
    requestTimestamp: new Date().toISOString(),
    requestPath: window.location.pathname,
    requestMethod: 'CLIENT',
    metadata: {
      userAgent: navigator.userAgent,
      url: window.location.href,
      referrer: document.referrer,
      timestamp: Date.now(),
    },
  }
}

// Create child trace context for related operations
export function createChildTraceContext(
  parentContext: TraceContext,
  options: {
    jobId?: string
    service?: string
    operation?: string
  } = {},
): TraceContext {
  return {
    ...parentContext,
    jobId: options.jobId || parentContext.jobId,
    service: options.service || parentContext.service,
    requestTimestamp: new Date().toISOString(),
    metadata: {
      ...parentContext.metadata,
      parentService: parentContext.service,
      operation: options.operation,
      childContext: true,
    },
  }
}

// Convert trace context to HTTP headers
export function traceContextToHeaders(
  context: TraceContext,
): Record<string, string> {
  const headers: Record<string, string> = {
    [TraceHeaders.TRACE_ID]: context.traceId,
  }

  if (context.jobId) {
    headers[TraceHeaders.JOB_ID] = context.jobId
  }

  if (context.projectId) {
    headers[TraceHeaders.PROJECT_ID] = context.projectId
  }

  if (context.userId) {
    headers[TraceHeaders.USER_ID] = context.userId
  }

  return headers
}

// Parse trace context from headers
export function headersToTraceContext(
  headers: Record<string, string>,
): Partial<TraceContext> {
  return {
    traceId:
      headers[TraceHeaders.TRACE_ID] ||
      headers[TraceHeaders.TRACE_ID.toLowerCase()],
    jobId:
      headers[TraceHeaders.JOB_ID] ||
      headers[TraceHeaders.JOB_ID.toLowerCase()],
    projectId:
      headers[TraceHeaders.PROJECT_ID] ||
      headers[TraceHeaders.PROJECT_ID.toLowerCase()],
    userId:
      headers[TraceHeaders.USER_ID] ||
      headers[TraceHeaders.USER_ID.toLowerCase()],
  }
}

// Trace context manager for maintaining context across async operations
export class TraceContextManager {
  private currentContext?: TraceContext
  private contextStack: TraceContext[] = []

  constructor(initialContext?: TraceContext) {
    this.currentContext = initialContext
  }

  getCurrentContext(): TraceContext | undefined {
    return this.currentContext
  }

  setCurrentContext(context: TraceContext): void {
    this.currentContext = context
  }

  pushContext(context: TraceContext): void {
    if (this.currentContext) {
      this.contextStack.push(this.currentContext)
    }
    this.currentContext = context
  }

  popContext(): TraceContext | undefined {
    const previous = this.contextStack.pop()
    this.currentContext = previous
    return previous
  }

  withContext<T>(
    context: TraceContext,
    fn: () => T | Promise<T>,
  ): T | Promise<T> {
    this.pushContext(context)

    try {
      const result = fn()

      // Handle async functions
      if (result instanceof Promise) {
        return result.finally(() => {
          this.popContext()
        })
      }

      // Handle synchronous functions
      this.popContext()
      return result
    } catch (error) {
      this.popContext()
      throw error
    }
  }

  createChildContext(
    options: { jobId?: string; service?: string; operation?: string } = {},
  ): TraceContext | undefined {
    if (!this.currentContext) {
      return undefined
    }

    return createChildTraceContext(this.currentContext, options)
  }
}

// Global trace context manager
export const globalTraceManager = new TraceContextManager()

// Initialize trace context from URL parameters on page load
if (typeof window !== 'undefined') {
  const urlContext = extractTraceContextFromURL()
  if (urlContext.traceId || urlContext.jobId || urlContext.projectId) {
    const fullContext = createTraceContext(urlContext)
    globalTraceManager.setCurrentContext(fullContext)
  }
}

// Utility to add trace context to URL
export function addTraceContextToURL(
  url: string,
  context: TraceContext,
): string {
  const urlObj = new URL(url, window.location.origin)

  if (context.traceId) {
    urlObj.searchParams.set('traceId', context.traceId)
  }

  if (context.jobId) {
    urlObj.searchParams.set('jobId', context.jobId)
  }

  if (context.projectId) {
    urlObj.searchParams.set('projectId', context.projectId)
  }

  return urlObj.toString()
}

// Performance timing with trace context
export class TracedPerformanceTimer {
  private startTime: number
  private startMark: string
  private endMark: string
  private measureName: string

  constructor(
    private readonly _operation: string,
    private readonly context?: TraceContext,
  ) {
    this.startTime = Date.now()
    this.startMark = `${this._operation}-start-${this.context?.traceId || 'unknown'}`
    this.endMark = `${this._operation}-end-${this.context?.traceId || 'unknown'}`
    this.measureName = `${this._operation}-${this.context?.traceId || 'unknown'}`

    // Use Performance API if available
    if (typeof performance !== 'undefined' && performance.mark) {
      performance.mark(this.startMark)
    }
  }

  end(): number {
    const duration = Date.now() - this.startTime

    if (
      typeof performance !== 'undefined' &&
      performance.mark &&
      performance.measure
    ) {
      performance.mark(this.endMark)
      performance.measure(this.measureName, this.startMark, this.endMark)
    }

    return duration
  }

  getPerformanceEntry(): PerformanceEntry | undefined {
    if (typeof performance !== 'undefined' && performance.getEntriesByName) {
      const entries = performance.getEntriesByName(this.measureName)
      return entries[entries.length - 1] // Get the latest entry
    }

    return undefined
  }
}

// Decorator for tracing function calls
export function traced(operation: string) {
  return function <T extends (...args: unknown[]) => unknown>(
    _target: unknown,
    _propertyName: string | symbol,
    descriptor: TypedPropertyDescriptor<T>,
  ): TypedPropertyDescriptor<T> | void {
    if (!descriptor.value) return

    const originalMethod = descriptor.value

    descriptor.value = function (this: unknown, ...args: unknown[]) {
      const context = globalTraceManager.getCurrentContext()
      const timer = new TracedPerformanceTimer(operation, context)

      try {
        const result = originalMethod.apply(this, args)

        // Handle async methods
        if (result instanceof Promise) {
          return result.finally(() => {
            timer.end()
          })
        }

        // Handle sync methods
        timer.end()
        return result
      } catch (error) {
        timer.end()
        throw error
      }
    } as T

    return descriptor
  }
}

// Utility for browser-specific trace context persistence
export class BrowserTraceStorage {
  private static readonly STORAGE_KEY = 'ai-script-trace-context'
  private static readonly EXPIRY_MS = 24 * 60 * 60 * 1000 // 24 hours

  static saveContext(context: TraceContext): void {
    if (typeof localStorage === 'undefined') return

    const data = {
      context,
      timestamp: Date.now(),
    }

    try {
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(data))
    } catch (error) {
      console.debug('Failed to save trace context to localStorage:', error)
    }
  }

  static loadContext(): TraceContext | null {
    if (typeof localStorage === 'undefined') return null

    try {
      const data = localStorage.getItem(this.STORAGE_KEY)
      if (!data) return null

      const parsed = JSON.parse(data)
      const age = Date.now() - parsed.timestamp

      // Check if context has expired
      if (age > this.EXPIRY_MS) {
        this.clearContext()
        return null
      }

      return parsed.context
    } catch (error) {
      console.debug('Failed to load trace context from localStorage:', error)
      return null
    }
  }

  static clearContext(): void {
    if (typeof localStorage === 'undefined') return

    try {
      localStorage.removeItem(this.STORAGE_KEY)
    } catch (error) {
      console.debug('Failed to clear trace context from localStorage:', error)
    }
  }
}

// Auto-restore trace context on page load
if (typeof window !== 'undefined') {
  const savedContext = BrowserTraceStorage.loadContext()
  if (savedContext && !globalTraceManager.getCurrentContext()) {
    globalTraceManager.setCurrentContext(savedContext)
  }
}
