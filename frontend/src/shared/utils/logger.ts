/**
 * Frontend structured logging system matching Python backend format
 */

import type {
  StructuredLogEntry,
  LogLevelType,
  EventType,
} from '../types/observability'
import { LogLevel } from '../types/observability'

interface BrowserLoggerConfig {
  serviceName: string
  version?: string
  environment?: string
  enableConsoleOutput?: boolean
  enableRemoteLogging?: boolean
  remoteLogEndpoint?: string
}

class BrowserLogger {
  private config: Required<BrowserLoggerConfig>
  private traceContext?: {
    traceId?: string
    jobId?: string
    projectId?: string
  }

  constructor(config: BrowserLoggerConfig) {
    this.config = {
      version: '1.0.0',
      environment: import.meta.env.MODE || 'development',
      enableConsoleOutput: true,
      enableRemoteLogging: false,
      remoteLogEndpoint: '/api/v1/logs',
      ...config,
    }
  }

  setTraceContext(context: {
    traceId?: string
    jobId?: string
    projectId?: string
  }): void {
    this.traceContext = context
  }

  private createLogEntry(
    level: LogLevelType,
    message: string,
    metadata?: Record<string, unknown>,
    durationMs?: number,
    errorCode?: string,
    errorType?: string,
    stackTrace?: string,
  ): StructuredLogEntry {
    return {
      timestamp: new Date().toISOString(),
      level,
      service: this.config.serviceName,
      traceId: this.traceContext?.traceId,
      jobId: this.traceContext?.jobId,
      projectId: this.traceContext?.projectId,
      message,
      metadata: {
        ...metadata,
        serviceVersion: this.config.version,
        environment: this.config.environment,
        userAgent: navigator.userAgent,
        url: window.location.href,
        timestamp: Date.now(),
      },
      durationMs,
      errorCode,
      errorType,
      stackTrace,
    }
  }

  private outputLog(entry: StructuredLogEntry): void {
    const logData = JSON.stringify(entry, null, 2)

    // Console output with appropriate level
    if (this.config.enableConsoleOutput) {
      switch (entry.level) {
        case LogLevel.TRACE:
        case LogLevel.DEBUG:
          console.debug(logData)
          break
        case LogLevel.INFO:
          console.info(logData)
          break
        case LogLevel.WARNING:
          console.warn(logData)
          break
        case LogLevel.ERROR:
        case LogLevel.CRITICAL:
          console.error(logData)
          break
        default:
          console.log(logData)
      }
    }

    // Remote logging (if enabled)
    if (this.config.enableRemoteLogging && this.config.remoteLogEndpoint) {
      this.sendToRemoteLogger(entry).catch(error => {
        console.error('Failed to send log to remote endpoint:', error)
      })
    }
  }

  private async sendToRemoteLogger(entry: StructuredLogEntry): Promise<void> {
    try {
      await fetch(this.config.remoteLogEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(entry),
      })
    } catch (error) {
      // Silent failure for remote logging to prevent infinite loops
      console.debug('Remote logging failed:', error)
    }
  }

  // Standard logging methods
  trace(message: string, metadata?: Record<string, unknown>): void {
    const entry = this.createLogEntry(LogLevel.TRACE, message, metadata)
    this.outputLog(entry)
  }

  debug(message: string, metadata?: Record<string, unknown>): void {
    const entry = this.createLogEntry(LogLevel.DEBUG, message, metadata)
    this.outputLog(entry)
  }

  info(message: string, metadata?: Record<string, unknown>): void {
    const entry = this.createLogEntry(LogLevel.INFO, message, metadata)
    this.outputLog(entry)
  }

  warning(message: string, metadata?: Record<string, unknown>): void {
    const entry = this.createLogEntry(LogLevel.WARNING, message, metadata)
    this.outputLog(entry)
  }

  error(
    message: string,
    error?: Error,
    metadata?: Record<string, unknown>,
  ): void {
    const entry = this.createLogEntry(
      LogLevel.ERROR,
      message,
      metadata,
      undefined,
      undefined,
      error?.name,
      error?.stack,
    )
    this.outputLog(entry)
  }

  critical(
    message: string,
    error?: Error,
    metadata?: Record<string, unknown>,
  ): void {
    const entry = this.createLogEntry(
      LogLevel.CRITICAL,
      message,
      metadata,
      undefined,
      undefined,
      error?.name,
      error?.stack,
    )
    this.outputLog(entry)
  }

  // Event logging
  logEvent(eventType: EventType, metadata?: Record<string, unknown>): void {
    const message = `Event: ${eventType}`
    const entry = this.createLogEntry(LogLevel.INFO, message, {
      ...metadata,
      eventType,
      isEvent: true,
    })
    this.outputLog(entry)
  }

  // Performance logging
  logPerformance(
    operation: string,
    durationMs: number,
    success: boolean = true,
    metadata?: Record<string, unknown>,
  ): void {
    const level = success ? LogLevel.INFO : LogLevel.WARNING
    const message = `${operation} ${success ? 'completed' : 'failed'} in ${durationMs}ms`

    const entry = this.createLogEntry(
      level,
      message,
      {
        ...metadata,
        operation,
        success,
        isPerformanceLog: true,
      },
      durationMs,
    )

    this.outputLog(entry)
  }

  // Error logging with structured details
  logError(
    context: string,
    error: Error,
    metadata?: Record<string, unknown>,
  ): void {
    const message = `${context}: ${error.message}`

    const entry = this.createLogEntry(
      LogLevel.ERROR,
      message,
      {
        ...metadata,
        errorContext: context,
        isErrorLog: true,
      },
      undefined,
      undefined,
      error.name,
      error.stack,
    )

    this.outputLog(entry)
  }

  // API request/response logging
  logApiRequest(
    method: string,
    url: string,
    statusCode?: number,
    durationMs?: number,
    metadata?: Record<string, unknown>,
  ): void {
    const success = statusCode ? statusCode < 400 : false
    const level = success ? LogLevel.INFO : LogLevel.ERROR
    const message = `API ${method} ${url} ${statusCode ? `- ${statusCode}` : ''}`

    const entry = this.createLogEntry(
      level,
      message,
      {
        ...metadata,
        method,
        url,
        statusCode,
        isApiLog: true,
      },
      durationMs,
    )

    this.outputLog(entry)
  }

  // User action logging
  logUserAction(
    action: string,
    element?: string,
    metadata?: Record<string, unknown>,
  ): void {
    const message = `User action: ${action}${element ? ` on ${element}` : ''}`

    const entry = this.createLogEntry(LogLevel.INFO, message, {
      ...metadata,
      action,
      element,
      isUserAction: true,
    })

    this.outputLog(entry)
  }

  // Create child logger with additional context
  withContext(additionalContext: Record<string, unknown>): BrowserLogger {
    const childLogger = new BrowserLogger(this.config)
    childLogger.traceContext = this.traceContext

    // Override createLogEntry to include additional context
    const originalCreateLogEntry = childLogger.createLogEntry.bind(childLogger)
    childLogger.createLogEntry = (level, message, metadata, ...args) => {
      return originalCreateLogEntry(
        level,
        message,
        {
          ...additionalContext,
          ...metadata,
        },
        ...args,
      )
    }

    return childLogger
  }
}

// Global logger registry
const loggers = new Map<string, BrowserLogger>()

// Create or get logger instance
export function createLogger(
  serviceName: string,
  config?: Partial<BrowserLoggerConfig>,
): BrowserLogger {
  const key = serviceName

  if (!loggers.has(key)) {
    loggers.set(
      key,
      new BrowserLogger({
        serviceName,
        ...config,
      }),
    )
  }

  return loggers.get(key)!
}

// Convenience functions matching Python backend patterns
export function logEvent(
  logger: BrowserLogger,
  eventType: EventType,
  eventName: string,
  metadata?: Record<string, unknown>,
): void {
  logger.logEvent(eventType, {
    eventName,
    ...metadata,
  })
}

export function logError(
  logger: BrowserLogger,
  error: Error,
  context: string,
  metadata?: Record<string, unknown>,
): void {
  logger.logError(context, error, metadata)
}

export function logPerformance(
  logger: BrowserLogger,
  operation: string,
  startTime: Date,
  success: boolean = true,
  metadata?: Record<string, unknown>,
): void {
  const duration = Date.now() - startTime.getTime()
  logger.logPerformance(operation, duration, success, metadata)
}

// Timer utility for performance logging
export class PerformanceTimer {
  private startTime: Date
  private operation: string
  private logger: BrowserLogger

  constructor(logger: BrowserLogger, operation: string) {
    this.logger = logger
    this.operation = operation
    this.startTime = new Date()
  }

  end(success: boolean = true, metadata?: Record<string, unknown>): void {
    const duration = Date.now() - this.startTime.getTime()
    this.logger.logPerformance(this.operation, duration, success, metadata)
  }
}

// Global error handler integration
export function setupGlobalErrorLogging(logger: BrowserLogger): void {
  // Handle uncaught errors
  window.addEventListener('error', event => {
    logger.error('Uncaught error', event.error, {
      filename: event.filename,
      lineno: event.lineno,
      colno: event.colno,
      isGlobalError: true,
    })
  })

  // Handle unhandled promise rejections
  window.addEventListener('unhandledrejection', event => {
    logger.error('Unhandled promise rejection', event.reason, {
      isUnhandledRejection: true,
    })
  })
}

// Export types for external use
export type { BrowserLogger, BrowserLoggerConfig }

// Create default application logger
export const appLogger = createLogger('ai-script-generator-frontend', {
  environment: import.meta.env.MODE || 'development',
  enableRemoteLogging: import.meta.env.PROD === true,
})

// Setup global error logging
if (typeof window !== 'undefined') {
  setupGlobalErrorLogging(appLogger)
}
