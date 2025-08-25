import * as Sentry from '@sentry/react'
import type { AppError } from './types'
import { env, isProduction, isDevelopment } from '@/shared/config/env'

/**
 * Sentry error reporting integration
 */
export class SentryReporter {
  private static initialized = false

  /**
   * Initialize Sentry with configuration
   */
  static initialize(): void {
    if (this.initialized || !env.VITE_SENTRY_DSN) {
      return
    }

    try {
      Sentry.init({
        dsn: env.VITE_SENTRY_DSN,
        environment: env.VITE_ENV,

        // Performance monitoring
        tracesSampleRate: isProduction() ? 0.1 : 1.0,

        // Session tracking
        autoSessionTracking: true,

        // Error filtering
        beforeSend: this.beforeSend,

        // Release information
        release: env.VITE_APP_VERSION,

        // Integration configuration
        integrations: [
          Sentry.browserTracingIntegration({
            // Capture interactions
            tracePropagationTargets: [
              env.VITE_CORE_SERVICE_URL,
              env.VITE_PROJECT_SERVICE_URL,
              env.VITE_GENERATION_SERVICE_URL,
            ],
          }),
          Sentry.replayIntegration({
            // Capture replays for errors in production
            maskAllText: isProduction(),
            blockAllMedia: isProduction(),
            sampleRate: isDevelopment() ? 1.0 : 0.1,
            errorSampleRate: isProduction() ? 1.0 : 0.5,
          }),
        ],

        // Debug in development
        debug: isDevelopment(),
      })

      this.initialized = true
      console.log('✅ Sentry initialized successfully')
    } catch (error) {
      console.error('❌ Failed to initialize Sentry:', error)
    }
  }

  /**
   * Report an application error to Sentry
   */
  static reportError(error: AppError, context?: Record<string, any>): void {
    if (!this.initialized) {
      this.initialize()
    }

    // Don't report certain error types to reduce noise
    if (this.shouldIgnoreError(error)) {
      return
    }

    Sentry.withScope(scope => {
      // Set error context
      scope.setTag('errorCategory', error.category)
      scope.setLevel(this.getSentryLevel(error.severity))

      // Add user context
      scope.setContext('error', {
        category: error.category,
        severity: error.severity,
        statusCode: error.statusCode,
        retryable: error.retryable,
        userMessage: error.userMessage,
        timestamp: error.timestamp.toISOString(),
      })

      // Add request context for HTTP errors
      if (error.context) {
        scope.setContext('request', error.context)
      }

      // Add additional context
      if (context) {
        scope.setContext('additional', context)
      }

      // Set fingerprint for grouping
      if (error.code) {
        scope.setFingerprint([error.category, error.code])
      } else {
        scope.setFingerprint([error.category, error.message])
      }

      // Report the error
      Sentry.captureException(error.originalError || error)
    })

    // Log to console in development
    if (isDevelopment()) {
      console.group('🐛 Error reported to Sentry')
      console.error('Error:', error)
      console.log('Context:', context)
      console.groupEnd()
    }
  }

  /**
   * Report a message to Sentry
   */
  static reportMessage(
    message: string,
    level: 'info' | 'warning' | 'error' = 'info',
    context?: Record<string, any>,
  ): void {
    if (!this.initialized) {
      this.initialize()
    }

    Sentry.withScope(scope => {
      scope.setLevel(level)

      if (context) {
        scope.setContext('message', context)
      }

      Sentry.captureMessage(message)
    })
  }

  /**
   * Set user context for error tracking
   */
  static setUser(user: {
    id?: string
    email?: string
    username?: string
  }): void {
    if (!this.initialized) {
      return
    }

    Sentry.setUser(user)
  }

  /**
   * Clear user context
   */
  static clearUser(): void {
    if (!this.initialized) {
      return
    }

    Sentry.setUser(null)
  }

  /**
   * Add breadcrumb for debugging
   */
  static addBreadcrumb(
    message: string,
    category: string,
    data?: Record<string, any>,
  ): void {
    if (!this.initialized) {
      return
    }

    Sentry.addBreadcrumb({
      message,
      category,
      data,
      timestamp: Date.now() / 1000,
    })
  }

  /**
   * Filter errors before sending to Sentry
   */
  private static beforeSend(event: Sentry.Event): Sentry.Event | null {
    // Don't report in development unless explicitly enabled
    if (isDevelopment() && !localStorage.getItem('sentry-debug')) {
      return null
    }

    // Filter out certain error messages
    const message = event.message || event.exception?.values?.[0]?.value || ''

    // Ignore common browser errors
    const ignoredMessages = [
      'Script error',
      'Non-Error promise rejection captured',
      'ResizeObserver loop limit exceeded',
      'Network request failed',
    ]

    if (ignoredMessages.some(ignored => message.includes(ignored))) {
      return null
    }

    return event
  }

  /**
   * Check if error should be ignored
   */
  private static shouldIgnoreError(error: AppError): boolean {
    // Don't report validation errors (user input issues)
    if (error.category === 'validation') {
      return true
    }

    // Don't report 404 errors (expected in some cases)
    if (error.category === 'not_found') {
      return true
    }

    // Don't report cancelled requests
    if (error.code === 'ERR_CANCELED') {
      return true
    }

    return false
  }

  /**
   * Convert error severity to Sentry level
   */
  private static getSentryLevel(severity: string): Sentry.SeverityLevel {
    switch (severity) {
      case 'low':
        return 'info'
      case 'medium':
        return 'warning'
      case 'high':
        return 'error'
      case 'critical':
        return 'fatal'
      default:
        return 'error'
    }
  }
}
