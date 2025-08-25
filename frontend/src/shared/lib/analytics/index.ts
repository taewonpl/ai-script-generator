import * as Sentry from '@sentry/react'
import { onCLS, onFCP, onINP, onLCP, onTTFB } from 'web-vitals'
import { env } from '@/shared/config/env'

export interface AnalyticsEvent {
  action: string
  category: string
  label?: string
  value?: number
  userId?: string
  properties?: Record<string, any>
}

export interface PerformanceMetric {
  name: string
  value: number
  delta: number
  id: string
  navigationType: 'navigate' | 'reload' | 'back-forward' | 'prerender'
}

class Analytics {
  private initialized = false
  private userId?: string

  initialize() {
    if (this.initialized) return

    this.initializeWebVitals()
    this.initialized = true
  }

  setUserId(userId: string) {
    this.userId = userId

    // Set user context for Sentry
    Sentry.setUser({
      id: userId,
    })
  }

  clearUser() {
    this.userId = undefined
    Sentry.setUser(null)
  }

  track(event: AnalyticsEvent) {
    const enrichedEvent = {
      ...event,
      userId: this.userId,
      timestamp: Date.now(),
    }

    // Send to Sentry as breadcrumb for debugging
    Sentry.addBreadcrumb({
      category: event.category,
      message: event.action,
      level: 'info',
      data: enrichedEvent,
    })

    // Custom event tracking for debugging
    if (env.VITE_ENV === 'development') {
      console.log('📊 Analytics Event:', enrichedEvent)
    }

    // Send to external analytics if configured
    if (env.VITE_ANALYTICS_TRACKING_ID) {
      this.sendToGoogleAnalytics(enrichedEvent)
    }
  }

  private sendToGoogleAnalytics(event: AnalyticsEvent) {
    // Google Analytics 4 event tracking
    if (typeof window !== 'undefined' && (window as any).gtag) {
      ;(window as any).gtag('event', event.action, {
        event_category: event.category,
        event_label: event.label,
        value: event.value,
        custom_parameter_user_id: event.userId,
        ...event.properties,
      })
    }
  }

  private initializeWebVitals() {
    const handleMetric = (metric: PerformanceMetric) => {
      // Send performance metrics to Sentry
      Sentry.addBreadcrumb({
        category: 'performance',
        message: `${metric.name}: ${metric.value}`,
        level: 'info',
        data: metric,
      })

      // Track critical performance issues
      if (metric.name === 'LCP' && metric.value > 2500) {
        Sentry.captureMessage(
          `Poor LCP performance: ${metric.value}ms`,
          'warning',
        )
      }

      if (metric.name === 'INP' && metric.value > 200) {
        Sentry.captureMessage(
          `Poor INP performance: ${metric.value}ms`,
          'warning',
        )
      }

      if (metric.name === 'CLS' && metric.value > 0.1) {
        Sentry.captureMessage(
          `Poor CLS performance: ${metric.value}`,
          'warning',
        )
      }

      // Log in development
      if (env.VITE_ENV === 'development') {
        console.log('📈 Performance Metric:', metric)
      }

      // Send to analytics
      this.track({
        action: 'performance_metric',
        category: 'performance',
        label: metric.name,
        value: Math.round(metric.value),
        properties: {
          delta: metric.delta,
          navigationType: metric.navigationType,
        },
      })
    }

    // Collect Core Web Vitals
    onCLS(handleMetric)
    onFCP(handleMetric)
    onINP(handleMetric)
    onLCP(handleMetric)
    onTTFB(handleMetric)
  }

  // Specific tracking methods for common events
  trackPageView(page: string, title?: string) {
    this.track({
      action: 'page_view',
      category: 'navigation',
      label: page,
      properties: { title },
    })
  }

  trackUserAction(
    action: string,
    category: string,
    properties?: Record<string, any>,
  ) {
    this.track({
      action,
      category,
      properties,
    })
  }

  trackError(error: Error, context?: Record<string, any>) {
    Sentry.captureException(error, {
      contexts: {
        error_context: context,
      },
      tags: {
        error_type: 'client_error',
      },
    })

    this.track({
      action: 'error_occurred',
      category: 'error',
      label: error.message,
      properties: {
        stack: error.stack,
        ...context,
      },
    })
  }

  trackAPICall(
    endpoint: string,
    method: string,
    status: number,
    duration: number,
  ) {
    const isError = status >= 400

    if (isError) {
      Sentry.addBreadcrumb({
        category: 'http',
        message: `${method} ${endpoint} - ${status}`,
        level: 'error',
        data: { method, endpoint, status, duration },
      })
    }

    this.track({
      action: 'api_call',
      category: 'api',
      label: `${method} ${endpoint}`,
      value: duration,
      properties: {
        status,
        method,
        endpoint,
        isError,
      },
    })
  }

  trackFeatureUsage(
    feature: string,
    action: string,
    properties?: Record<string, any>,
  ) {
    this.track({
      action,
      category: 'feature_usage',
      label: feature,
      properties,
    })
  }
}

// Singleton instance
export const analytics = new Analytics()

// Initialize analytics on module load
if (typeof window !== 'undefined') {
  analytics.initialize()
}

// Note: AnalyticsEvent and PerformanceMetric are already exported as interfaces above
