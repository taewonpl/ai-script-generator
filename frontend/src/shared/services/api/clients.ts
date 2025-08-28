/**
 * Unified API clients with consistent routing for dev/prod environments
 * Implements request_id/trace_id injection and proper SSE support
 */

import axios from 'axios'
import type { AxiosInstance, AxiosRequestConfig } from 'axios'
// UUID generation using crypto API (no external dependency)
const generateUUID = (): string => {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  // Fallback for older browsers
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = Math.random() * 16 | 0
    const v = c === 'x' ? r : (r & 0x3 | 0x8)
    return v.toString(16)
  })
}

/**
 * Environment-based base URLs
 */
const DEV = import.meta.env.DEV

export const API_BASES = {
  core: DEV ? '/api/core/api/v1' : '/api/v1',
  project: DEV ? '/api/project/api/v1' : '/api/v1', 
  generation: DEV ? '/api/generation/api/v1' : '/api/v1',
} as const

/**
 * Request/Trace ID utilities
 */
export const newRid = (): string => generateUUID()
export const newTraceId = (): string => generateUUID()

export const withIds = (headers: Record<string, string> = {}): Record<string, string> => ({
  'X-Request-Id': newRid(),
  'X-Trace-Id': newTraceId(),
  'X-Client-Version': import.meta.env.VITE_APP_VERSION || '1.0.0',
  'X-Client-Environment': import.meta.env.VITE_ENV || 'development',
  ...headers,
})

/**
 * Create API client with ID injection
 */
function createAPIClient(baseURL: string, serviceName: string): AxiosInstance {
  const client = axios.create({
    baseURL,
    withCredentials: true,
    timeout: 30000,
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
  })

  // Request interceptor - inject IDs and log
  client.interceptors.request.use((config) => {
    // Inject request and trace IDs
    const idsHeaders = withIds(config.headers as Record<string, string>)
    Object.assign(config.headers, idsHeaders)
    
    // Enhanced logging for end-to-end tracing (always log in dev, structured in prod)
    const logData = {
      service: serviceName.toLowerCase(),
      method: config.method?.toUpperCase(),
      url: config.url,
      baseURL: config.baseURL,
      fullUrl: `${config.baseURL || ''}${config.url || ''}`,
      requestId: config.headers['X-Request-Id'],
      traceId: config.headers['X-Trace-Id'],
      timestamp: new Date().toISOString(),
    }
    
    if (DEV) {
      console.log(`📤 ${serviceName} API Request:`, logData)
    } else {
      // Production: structured logging for observability
      console.log(JSON.stringify({
        level: 'info',
        event: 'api_request',
        ...logData
      }))
    }
    
    return config
  })

  // Response interceptor - log response
  client.interceptors.response.use(
    (response) => {
      const logData = {
        service: serviceName.toLowerCase(),
        status: response.status,
        method: response.config.method?.toUpperCase(),
        url: response.config.url,
        fullUrl: `${response.config.baseURL || ''}${response.config.url || ''}`,
        requestId: response.config.headers['X-Request-Id'] || response.headers['x-request-id'],
        traceId: response.config.headers['X-Trace-Id'] || response.headers['x-trace-id'],
        responseTime: response.headers['x-response-time'],
        timestamp: new Date().toISOString(),
      }
      
      if (DEV) {
        console.log(`📥 ${serviceName} API Response:`, logData)
      } else {
        console.log(JSON.stringify({
          level: 'info',
          event: 'api_response',
          ...logData
        }))
      }
      return response
    },
    (error) => {
      const logData = {
        service: serviceName.toLowerCase(),
        status: error.response?.status || 0,
        method: error.config?.method?.toUpperCase(),
        url: error.config?.url,
        fullUrl: `${error.config?.baseURL || ''}${error.config?.url || ''}`,
        error: error.message,
        requestId: error.config?.headers['X-Request-Id'],
        traceId: error.config?.headers['X-Trace-Id'],
        timestamp: new Date().toISOString(),
      }
      
      if (DEV) {
        console.error(`❌ ${serviceName} API Error:`, logData)
      } else {
        console.error(JSON.stringify({
          level: 'error',
          event: 'api_error',
          ...logData
        }))
      }
      return Promise.reject(error)
    }
  )

  return client
}

/**
 * Unified API clients
 */
export const coreServiceClient = createAPIClient(API_BASES.core, 'Core')
export const projectServiceClient = createAPIClient(API_BASES.project, 'Project')
export const generationServiceClient = createAPIClient(API_BASES.generation, 'Generation')

/**
 * Legacy exports for backward compatibility
 */
export const generationApi = generationServiceClient
export const projectApi = projectServiceClient
export const client = coreServiceClient

/**
 * HTTP Helper Wrappers - Return T instead of AxiosResponse<T>
 * Prevents regression cases like useJobControl where response.data was forgotten
 */

// Core Service HTTP Helpers
export const coreHttp = {
  get: async <T>(url: string, config?: AxiosRequestConfig): Promise<T> =>
    coreServiceClient.get<T>(url, config).then(r => r.data),
  post: async <T, B = unknown>(url: string, body?: B, config?: AxiosRequestConfig): Promise<T> =>
    coreServiceClient.post<T>(url, body, config).then(r => r.data),
  put: async <T, B = unknown>(url: string, body?: B, config?: AxiosRequestConfig): Promise<T> =>
    coreServiceClient.put<T>(url, body, config).then(r => r.data),
  patch: async <T, B = unknown>(url: string, body?: B, config?: AxiosRequestConfig): Promise<T> =>
    coreServiceClient.patch<T>(url, body, config).then(r => r.data),
  delete: async <T>(url: string, config?: AxiosRequestConfig): Promise<T> =>
    coreServiceClient.delete<T>(url, config).then(r => r.data),
}

// Project Service HTTP Helpers
export const projectHttp = {
  get: async <T>(url: string, config?: AxiosRequestConfig): Promise<T> =>
    projectServiceClient.get<T>(url, config).then(r => r.data),
  post: async <T, B = unknown>(url: string, body?: B, config?: AxiosRequestConfig): Promise<T> =>
    projectServiceClient.post<T>(url, body, config).then(r => r.data),
  put: async <T, B = unknown>(url: string, body?: B, config?: AxiosRequestConfig): Promise<T> =>
    projectServiceClient.put<T>(url, body, config).then(r => r.data),
  patch: async <T, B = unknown>(url: string, body?: B, config?: AxiosRequestConfig): Promise<T> =>
    projectServiceClient.patch<T>(url, body, config).then(r => r.data),
  delete: async <T>(url: string, config?: AxiosRequestConfig): Promise<T> =>
    projectServiceClient.delete<T>(url, config).then(r => r.data),
}

// Generation Service HTTP Helpers
export const generationHttp = {
  get: async <T>(url: string, config?: AxiosRequestConfig): Promise<T> =>
    generationServiceClient.get<T>(url, config).then(r => r.data),
  post: async <T, B = unknown>(url: string, body?: B, config?: AxiosRequestConfig): Promise<T> =>
    generationServiceClient.post<T>(url, body, config).then(r => r.data),
  put: async <T, B = unknown>(url: string, body?: B, config?: AxiosRequestConfig): Promise<T> =>
    generationServiceClient.put<T>(url, body, config).then(r => r.data),
  patch: async <T, B = unknown>(url: string, body?: B, config?: AxiosRequestConfig): Promise<T> =>
    generationServiceClient.patch<T>(url, body, config).then(r => r.data),
  delete: async <T>(url: string, config?: AxiosRequestConfig): Promise<T> =>
    generationServiceClient.delete<T>(url, config).then(r => r.data),
}

// Log configuration in development
if (DEV) {
  console.group('🔗 API Clients Configuration')
  console.log('Core Service:', API_BASES.core)
  console.log('Project Service:', API_BASES.project)
  console.log('Generation Service:', API_BASES.generation)
  console.groupEnd()
}