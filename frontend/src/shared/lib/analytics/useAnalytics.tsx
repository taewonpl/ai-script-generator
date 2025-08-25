import React, { useCallback, useEffect, useRef } from 'react'
import { useLocation } from 'react-router-dom'
import type { AnalyticsEvent } from './index'
import { analytics } from './index'

export interface UseAnalyticsOptions {
  trackPageViews?: boolean
  userId?: string
}

export const useAnalytics = (options: UseAnalyticsOptions = {}) => {
  const { trackPageViews = true, userId } = options
  const location = useLocation()
  const previousPathRef = useRef<string>()

  // Set user ID if provided
  useEffect(() => {
    if (userId) {
      analytics.setUserId(userId)
    }
    return () => {
      if (userId) {
        analytics.clearUser()
      }
    }
  }, [userId])

  // Track page views automatically
  useEffect(() => {
    if (trackPageViews && location.pathname !== previousPathRef.current) {
      analytics.trackPageView(location.pathname, document.title)
      previousPathRef.current = location.pathname
    }
  }, [location.pathname, trackPageViews])

  // Track custom events
  const track = useCallback((event: Omit<AnalyticsEvent, 'userId'>) => {
    analytics.track(event)
  }, [])

  // Track user actions with common patterns
  const trackClick = useCallback(
    (element: string, properties?: Record<string, any>) => {
      analytics.trackUserAction('click', 'interaction', {
        element,
        ...properties,
      })
    },
    [],
  )

  const trackFormSubmit = useCallback(
    (formName: string, success: boolean, properties?: Record<string, any>) => {
      analytics.trackUserAction('form_submit', 'form', {
        formName,
        success,
        ...properties,
      })
    },
    [],
  )

  const trackSearch = useCallback(
    (query: string, results: number, properties?: Record<string, any>) => {
      analytics.trackUserAction('search', 'search', {
        query,
        results,
        ...properties,
      })
    },
    [],
  )

  const trackFeature = useCallback(
    (feature: string, action: string, properties?: Record<string, any>) => {
      analytics.trackFeatureUsage(feature, action, properties)
    },
    [],
  )

  const trackError = useCallback(
    (error: Error, context?: Record<string, any>) => {
      analytics.trackError(error, context)
    },
    [],
  )

  return {
    track,
    trackClick,
    trackFormSubmit,
    trackSearch,
    trackFeature,
    trackError,
    analytics,
  }
}

// Higher-order component for automatic analytics tracking
export const withAnalytics = <P extends object>(
  WrappedComponent: React.ComponentType<P>,
  analyticsConfig?: UseAnalyticsOptions,
) => {
  const WithAnalyticsComponent = (props: P) => {
    const analytics = useAnalytics(analyticsConfig)

    return <WrappedComponent {...props} analytics={analytics} />
  }

  WithAnalyticsComponent.displayName = `withAnalytics(${WrappedComponent.displayName || WrappedComponent.name})`

  return WithAnalyticsComponent
}

export default useAnalytics
