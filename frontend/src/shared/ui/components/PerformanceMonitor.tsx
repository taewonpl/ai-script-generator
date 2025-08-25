import React, { memo, useEffect, useRef } from 'react'
import * as Sentry from '@sentry/react'
import { analytics } from '../../lib/analytics'

export interface PerformanceMonitorProps {
  name: string
  children: React.ReactNode
  threshold?: number
  trackMount?: boolean
  trackRender?: boolean
}

export const PerformanceMonitor = memo(function PerformanceMonitor({
  name,
  children,
  threshold = 100,
  trackMount = true,
  trackRender = true,
}: PerformanceMonitorProps) {
  const startTimeRef = useRef<number>()
  const renderCountRef = useRef(0)
  const mountTimeRef = useRef<number>()

  useEffect(() => {
    if (trackMount) {
      mountTimeRef.current = Date.now()
    }

    return () => {
      if (trackMount && mountTimeRef.current) {
        const mountDuration = Date.now() - mountTimeRef.current

        if (mountDuration > threshold) {
          Sentry.addBreadcrumb({
            category: 'performance',
            message: `Slow component unmount: ${name}`,
            level: 'warning',
            data: { name, mountDuration },
          })
        }

        analytics.trackUserAction('component_unmount', 'performance', {
          componentName: name,
          mountDuration,
        })
      }
    }
  }, [name, trackMount, threshold])

  // Track render performance
  useEffect(() => {
    if (trackRender) {
      if (startTimeRef.current) {
        const renderDuration = Date.now() - startTimeRef.current
        renderCountRef.current += 1

        if (renderDuration > threshold) {
          Sentry.addBreadcrumb({
            category: 'performance',
            message: `Slow render: ${name}`,
            level: 'warning',
            data: { name, renderDuration, renderCount: renderCountRef.current },
          })
        }

        analytics.trackUserAction('component_render', 'performance', {
          componentName: name,
          renderDuration,
          renderCount: renderCountRef.current,
        })
      }

      startTimeRef.current = Date.now()
    }
  })

  return <>{children}</>
})

// Higher-order component for performance monitoring
export const withPerformanceMonitoring = <P extends object>(
  WrappedComponent: React.ComponentType<P>,
  options: Omit<PerformanceMonitorProps, 'children'> = {},
) => {
  const componentName =
    options.name ||
    WrappedComponent.displayName ||
    WrappedComponent.name ||
    'Unknown'

  const WithPerformanceComponent = (props: P) => (
    <PerformanceMonitor {...options} name={componentName}>
      <WrappedComponent {...props} />
    </PerformanceMonitor>
  )

  WithPerformanceComponent.displayName = `withPerformanceMonitoring(${componentName})`

  return WithPerformanceComponent
}

// Hook for manual performance tracking
export const usePerformanceTracking = () => {
  const startTiming = (name: string) => {
    const startTime = Date.now()

    return (properties?: Record<string, any>) => {
      const duration = Date.now() - startTime

      analytics.trackUserAction('performance_timing', 'performance', {
        name,
        duration,
        ...properties,
      })

      if (duration > 1000) {
        Sentry.addBreadcrumb({
          category: 'performance',
          message: `Slow operation: ${name}`,
          level: 'warning',
          data: { name, duration, ...properties },
        })
      }

      return duration
    }
  }

  const measureAsync = async <T,>(
    name: string,
    fn: () => Promise<T>,
  ): Promise<T> => {
    const endTiming = startTiming(name)

    try {
      const result = await fn()
      endTiming({ success: true })
      return result
    } catch (error) {
      endTiming({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      })
      throw error
    }
  }

  const measureSync = <T,>(name: string, fn: () => T): T => {
    const endTiming = startTiming(name)

    try {
      const result = fn()
      endTiming({ success: true })
      return result
    } catch (error) {
      endTiming({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      })
      throw error
    }
  }

  return {
    startTiming,
    measureAsync,
    measureSync,
  }
}

export default PerformanceMonitor
