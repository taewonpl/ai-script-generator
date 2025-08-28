/**
 * Centralized API path configuration for dev/prod consistency
 * Ensures all services use the same routing logic
 */

import { env, isDevelopment } from './env'

/**
 * API path resolution based on environment
 * - Development: Use proxy paths (/api/*)  
 * - Production: Use direct service URLs
 */
export const getServicePaths = () => {
  if (isDevelopment()) {
    // Development: Use proxy paths to maintain consistency
    return {
      CORE: '/api/core/api/v1',
      PROJECT: '/api/project/api/v1', 
      GENERATION: '/api/generation/api/v1',
      // SSE paths (must match proxy configuration)
      SSE_BASE: '/api/generation/api/v1',
    }
  } else {
    // Production: Direct service URLs
    return {
      CORE: `${env.VITE_CORE_SERVICE_URL}/api/v1`,
      PROJECT: `${env.VITE_PROJECT_SERVICE_URL}/api/v1`,
      GENERATION: `${env.VITE_GENERATION_SERVICE_URL}/api/v1`,
      // Production SSE uses same base as regular API
      SSE_BASE: `${env.VITE_GENERATION_SERVICE_URL}/api/v1`,
    }
  }
}

/**
 * Get API client base URLs (for axios instances)
 */
export const getClientBaseURLs = () => {
  const paths = getServicePaths()
  return {
    core: paths.CORE,
    project: paths.PROJECT, 
    generation: paths.GENERATION,
  }
}

/**
 * Get SSE endpoint URL
 * @param jobId - Generation job ID
 * @returns Full SSE URL for the job
 */
export const getSSEUrl = (jobId: string): string => {
  const paths = getServicePaths()
  return `${paths.SSE_BASE}/jobs/${jobId}/stream`
}

/**
 * Get WebSocket URL (if needed for future use)
 * @param path - WebSocket path
 * @returns Full WebSocket URL
 */
export const getWebSocketUrl = (path: string): string => {
  const paths = getServicePaths()
  const baseUrl = paths.GENERATION.replace('http', 'ws')
  return `${baseUrl}${path}`
}

/**
 * Request ID and Trace ID generation utilities
 */
export const generateRequestId = (): string => {
  return `req_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`
}

export const generateTraceId = (): string => {
  return `trace_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`
}

/**
 * Common headers that should be added to all requests
 */
export const getCommonHeaders = (
  additionalHeaders: Record<string, string> = {}
): Record<string, string> => {
  const requestId = generateRequestId()
  const traceId = generateTraceId()
  
  return {
    'Content-Type': 'application/json',
    'X-Request-ID': requestId,
    'X-Trace-ID': traceId,
    'X-Client-Version': env.VITE_APP_VERSION,
    'X-Client-Environment': env.VITE_ENV,
    ...additionalHeaders,
  }
}

/**
 * Log API configuration in development
 */
if (isDevelopment()) {
  const paths = getServicePaths()
  console.group('🔗 API Configuration (Development Mode)')
  console.log('Core Service:', paths.CORE)
  console.log('Project Service:', paths.PROJECT) 
  console.log('Generation Service:', paths.GENERATION)
  console.log('SSE Base:', paths.SSE_BASE)
  console.groupEnd()
}