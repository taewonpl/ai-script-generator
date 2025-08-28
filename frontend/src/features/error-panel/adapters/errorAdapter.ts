/**
 * Error adapter - converts any error format to StandardErrorFormat
 * Handles server responses, HTML/text/network errors
 */

import type { AxiosError } from 'axios'
import type { StandardErrorFormat } from '../types/standardError'
import { maskSensitiveData } from '../types/standardError'

/**
 * Adapt any error to StandardErrorFormat
 */
export function adaptError(
  error: unknown,
  context: {
    endpoint?: string
    method?: string
    requestId?: string
    traceId?: string
  } = {}
): StandardErrorFormat {
  const timestamp = new Date().toISOString()
  const isOffline = !navigator.onLine

  // Handle Axios errors (HTTP requests)
  if (isAxiosError(error)) {
    return adaptAxiosError(error, context, timestamp, isOffline)
  }

  // Handle standard Error objects
  if (error instanceof Error) {
    return adaptGenericError(error, context, timestamp, isOffline)
  }

  // Handle string errors
  if (typeof error === 'string') {
    return adaptStringError(error, context, timestamp, isOffline)
  }

  // Handle unknown error types
  return adaptUnknownError(error, context, timestamp, isOffline)
}

/**
 * Adapt Axios errors to StandardErrorFormat
 */
function adaptAxiosError(
  error: AxiosError,
  context: any,
  timestamp: string,
  isOffline: boolean
): StandardErrorFormat {
  const status = error.response?.status || 0
  const data = error.response?.data
  const config = error.config

  // Determine error type based on status and response
  let errorType = mapStatusToErrorType(status)
  
  // Override if offline
  if (isOffline) {
    errorType = 'network_error'
  }

  // Extract endpoint and method from config
  const endpoint = config?.url || context.endpoint
  const method = config?.method?.toUpperCase() || context.method

  // Handle different response formats
  let hint: string | undefined
  let rawMessage: string | undefined

  if (typeof data === 'object' && data) {
    // Standard API error response
    hint = (data as any).message || (data as any).error?.message
    rawMessage = JSON.stringify(data).substring(0, 200)
  } else if (typeof data === 'string') {
    // HTML or text response
    const isHtml = data.trim().startsWith('<')
    if (isHtml) {
      // Extract title from HTML
      const titleMatch = data.match(/<title>(.*?)<\/title>/i)
      hint = titleMatch ? titleMatch[1] : 'Server returned HTML error page'
      rawMessage = data.substring(0, 200)
    } else {
      hint = data.substring(0, 100)
      rawMessage = data.substring(0, 200)
    }
  } else {
    hint = error.message
    rawMessage = error.message
  }

  return {
    error_type: errorType,
    http_status: status,
    hint: maskSensitiveData(hint || ''),
    endpoint,
    method,
    request_id: context.requestId || extractRequestId(error.response?.headers),
    trace_id: context.traceId || extractTraceId(error.response?.headers),
    timestamp,
    raw_message: maskSensitiveData(rawMessage || ''),
    is_offline: isOffline,
    user_agent: navigator.userAgent,
    url: window.location.href,
    masked_data: {
      code: error.code,
      response: data,
      headers: error.response?.headers,
    },
  }
}

/**
 * Adapt generic Error to StandardErrorFormat
 */
function adaptGenericError(
  error: Error,
  context: any,
  timestamp: string,
  isOffline: boolean
): StandardErrorFormat {
  const errorType = classifyGenericError(error)

  return {
    error_type: errorType,
    http_status: 0,
    hint: error.message,
    endpoint: context.endpoint,
    method: context.method,
    request_id: context.requestId,
    trace_id: context.traceId,
    timestamp,
    raw_message: maskSensitiveData(error.message.substring(0, 200)),
    is_offline: isOffline,
    user_agent: navigator.userAgent,
    url: window.location.href,
    masked_data: {
      name: error.name,
      stack: maskSensitiveData(error.stack?.substring(0, 500) || ''),
    },
  }
}

/**
 * Adapt string error to StandardErrorFormat
 */
function adaptStringError(
  error: string,
  context: any,
  timestamp: string,
  isOffline: boolean
): StandardErrorFormat {
  return {
    error_type: 'unknown_error',
    http_status: 0,
    hint: error.substring(0, 100),
    endpoint: context.endpoint,
    method: context.method,
    request_id: context.requestId,
    trace_id: context.traceId,
    timestamp,
    raw_message: maskSensitiveData(error.substring(0, 200)),
    is_offline: isOffline,
    user_agent: navigator.userAgent,
    url: window.location.href,
  }
}

/**
 * Adapt unknown error to StandardErrorFormat
 */
function adaptUnknownError(
  error: unknown,
  context: any,
  timestamp: string,
  isOffline: boolean
): StandardErrorFormat {
  const errorString = String(error)

  return {
    error_type: 'unknown_error',
    http_status: 0,
    hint: errorString.substring(0, 100),
    endpoint: context.endpoint,
    method: context.method,
    request_id: context.requestId,
    trace_id: context.traceId,
    timestamp,
    raw_message: maskSensitiveData(errorString.substring(0, 200)),
    is_offline: isOffline,
    user_agent: navigator.userAgent,
    url: window.location.href,
    masked_data: {
      type: typeof error,
      value: errorString.substring(0, 100),
    },
  }
}

/**
 * Map HTTP status to error type
 */
function mapStatusToErrorType(status: number): string {
  if (status === 0) return 'network_error'
  if (status === 400) return 'validation_error'
  if (status === 401 || status === 403) return 'authorization_error'
  if (status === 404) return 'validation_error'
  if (status === 408) return 'timeout_error'
  if (status === 429) return 'rate_limit_error'
  if (status >= 500) return 'server_unavailable'
  return 'unknown_error'
}

/**
 * Classify generic JavaScript errors
 */
function classifyGenericError(error: Error): string {
  const message = error.message.toLowerCase()
  const name = error.name.toLowerCase()

  if (name === 'networkerror' || message.includes('network')) {
    return 'network_error'
  }
  if (name === 'timeouterror' || message.includes('timeout')) {
    return 'timeout_error'
  }
  if (message.includes('fetch') || message.includes('connection')) {
    return 'network_error'
  }
  if (name === 'validationerror' || message.includes('validation')) {
    return 'validation_error'
  }

  return 'unknown_error'
}

/**
 * Extract request ID from headers
 */
function extractRequestId(headers?: Record<string, any>): string | undefined {
  if (!headers) return undefined
  
  return headers['x-request-id'] || 
         headers['request-id'] ||
         headers['X-Request-ID'] ||
         headers['Request-ID']
}

/**
 * Extract trace ID from headers
 */
function extractTraceId(headers?: Record<string, any>): string | undefined {
  if (!headers) return undefined
  
  return headers['x-trace-id'] || 
         headers['trace-id'] ||
         headers['X-Trace-ID'] ||
         headers['Trace-ID']
}

/**
 * Type guard for Axios errors
 */
function isAxiosError(error: unknown): error is AxiosError {
  return error != null && typeof error === 'object' && 'isAxiosError' in error
}

/**
 * Create copyable error details text
 */
export function createCopyableErrorText(error: StandardErrorFormat): string {
  const parts = [
    '=== Error Details ===',
    `Type: ${error.error_type}`,
    `HTTP Status: ${error.http_status}`,
    `Timestamp: ${error.timestamp}`,
  ]

  if (error.request_id) {
    parts.push(`Request ID: ${error.request_id}`)
  }

  if (error.trace_id) {
    parts.push(`Trace ID: ${error.trace_id}`)
  }

  if (error.endpoint) {
    parts.push(`Endpoint: ${error.method || 'GET'} ${error.endpoint}`)
  }

  parts.push(`Offline: ${error.is_offline ? 'Yes' : 'No'}`)

  if (error.hint) {
    parts.push('', '=== User Message ===', error.hint)
  }

  if (error.raw_message && error.raw_message !== error.hint) {
    parts.push('', '=== Raw Message ===', error.raw_message)
  }

  parts.push('', '=== Environment ===')
  parts.push(`URL: ${error.url}`)
  parts.push(`User Agent: ${error.user_agent}`)

  if (error.masked_data) {
    parts.push('', '=== Technical Details ===')
    if (typeof error.masked_data === 'string') {
      parts.push(error.masked_data)
    } else {
      parts.push(JSON.stringify(error.masked_data, null, 2))
    }
  }

  return parts.join('\n')
}