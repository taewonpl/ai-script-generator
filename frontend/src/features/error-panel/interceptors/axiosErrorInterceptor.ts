/**
 * Axios interceptor for standardized error handling
 * Automatically adapts responses/errors to StandardErrorFormat → ErrorPanel
 */

import type { AxiosInstance, AxiosResponse, AxiosError, InternalAxiosRequestConfig } from 'axios'
import { adaptError } from '../adapters/errorAdapter'
import type { StandardErrorFormat } from '../types/standardError'

export interface ErrorInterceptorConfig {
  onError?: (error: StandardErrorFormat) => void
  enableLogging?: boolean
  excludeEndpoints?: string[]
}

/**
 * Enhanced Axios request config with error context
 */
interface EnhancedAxiosRequestConfig extends InternalAxiosRequestConfig {
  _errorContext?: {
    startTime: number
    endpoint: string
    method: string
    requestId?: string
    traceId?: string
  }
}

/**
 * Setup standardized error interceptor for Axios instance
 */
export function setupErrorInterceptor(
  axiosInstance: AxiosInstance, 
  config: ErrorInterceptorConfig = {}
): () => void {
  const { onError, enableLogging = true, excludeEndpoints = [] } = config

  // Request interceptor - capture context
  const requestInterceptorId = axiosInstance.interceptors.request.use(
    (requestConfig: EnhancedAxiosRequestConfig) => {
      const endpoint = requestConfig.url || ''
      const method = requestConfig.method?.toUpperCase() || 'GET'

      // Skip excluded endpoints
      if (excludeEndpoints.some(excluded => endpoint.includes(excluded))) {
        return requestConfig
      }

      // Add error context for response handling
      requestConfig._errorContext = {
        startTime: Date.now(),
        endpoint,
        method,
        requestId: requestConfig.headers?.['x-request-id'] || 
                   requestConfig.headers?.['Request-ID'],
        traceId: requestConfig.headers?.['x-trace-id'] || 
                 requestConfig.headers?.['Trace-ID'],
      }

      if (enableLogging) {
        console.log(`🔄 ${method} ${endpoint} - Request started`)
      }

      return requestConfig
    },
    (error) => {
      if (enableLogging) {
        console.error('❌ Request interceptor error:', error)
      }
      return Promise.reject(error)
    }
  )

  // Response interceptor - handle errors
  const responseInterceptorId = axiosInstance.interceptors.response.use(
    (response: AxiosResponse) => {
      const config = response.config as EnhancedAxiosRequestConfig
      const context = config._errorContext

      if (enableLogging && context) {
        const duration = Date.now() - context.startTime
        console.log(`✅ ${context.method} ${context.endpoint} - ${response.status} (${duration}ms)`)
      }

      return response
    },
    (error: AxiosError) => {
      const config = error.config as EnhancedAxiosRequestConfig
      const context = config?._errorContext

      if (enableLogging && context) {
        const duration = Date.now() - context.startTime
        const status = error.response?.status || 0
        console.error(`❌ ${context.method} ${context.endpoint} - ${status} (${duration}ms)`, error)
      }

      // Skip excluded endpoints
      if (context && excludeEndpoints.some(excluded => context.endpoint.includes(excluded))) {
        return Promise.reject(error)
      }

      // Adapt error to standardized format
      const standardError = adaptError(error, {
        endpoint: context?.endpoint,
        method: context?.method,
        requestId: context?.requestId,
        traceId: context?.traceId,
      })

      // Call error handler if provided
      if (onError) {
        onError(standardError)
      }

      // Attach standardized error to original error for downstream handling
      ;(error as any)._standardError = standardError

      return Promise.reject(error)
    }
  )

  // Return cleanup function
  return () => {
    axiosInstance.interceptors.request.eject(requestInterceptorId)
    axiosInstance.interceptors.response.eject(responseInterceptorId)
  }
}

/**
 * Extract standardized error from Axios error
 */
export function getStandardError(axiosError: AxiosError): StandardErrorFormat | null {
  return (axiosError as any)._standardError || null
}

/**
 * Hook to setup error interceptor with cleanup
 */
export function useAxiosErrorInterceptor(
  axiosInstance: AxiosInstance,
  config: ErrorInterceptorConfig = {}
): void {
  // This would be implemented as a React hook in the actual usage
  // For now, just call setup directly
  const cleanup = setupErrorInterceptor(axiosInstance, config)
  
  // In a real React hook, you would use useEffect for cleanup
  return cleanup as any
}