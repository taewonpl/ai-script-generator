/**
 * Error mapping utilities to convert various error formats to DetailedError
 */

import type { StandardizedAPIError } from '@/shared/api/client'
import type { AppError } from '@/shared/lib/errors/types'
import type { DetailedError, ErrorType } from '../types'

/**
 * Map HTTP status codes to error types
 */
function mapHttpStatusToErrorType(status: number): ErrorType {
  if (status === 0) return 'network_error'
  if (status >= 400 && status < 500) {
    switch (status) {
      case 401:
      case 403:
        return 'authorization_error'
      case 429:
        return 'rate_limit_error'
      case 408:
        return 'timeout_error'
      default:
        return 'validation_error'
    }
  }
  if (status >= 500) {
    switch (status) {
      case 503:
        return 'server_unavailable'
      case 504:
        return 'timeout_error'
      default:
        return 'server_unavailable'
    }
  }
  return 'unknown_error'
}

/**
 * Map error category from existing error classifier to error type
 */
function mapCategoryToErrorType(category: string): ErrorType {
  switch (category) {
    case 'network':
      return 'network_error'
    case 'server':
      return 'server_unavailable'
    case 'validation':
      return 'validation_error'
    case 'authorization':
      return 'authorization_error'
    case 'rate_limit':
      return 'rate_limit_error'
    case 'not_found':
      return 'validation_error'
    default:
      return 'unknown_error'
  }
}

/**
 * Convert StandardizedAPIError to DetailedError
 */
export function fromStandardizedAPIError(error: StandardizedAPIError): DetailedError {
  const errorType = mapHttpStatusToErrorType(error.statusCode)
  
  return {
    error_type: errorType,
    http_status: error.statusCode,
    hint: error.getUserFriendlyMessage(),
    traceId: error.traceId,
    requestId: error.details?.requestId as string,
    timestamp: new Date().toISOString(),
    userMessage: error.getUserFriendlyMessage(),
    technicalMessage: error.message,
    retryable: error.isRetryable(),
    context: {
      errorCode: error.code,
      details: error.details,
      stack: error.stack,
    },
  }
}

/**
 * Convert AppError to DetailedError
 */
export function fromAppError(error: AppError): DetailedError {
  const errorType = mapCategoryToErrorType(error.category)
  
  return {
    error_type: errorType,
    http_status: error.statusCode || 0,
    hint: error.userMessage,
    traceId: error.context?.traceId as string,
    requestId: error.context?.requestId as string,
    timestamp: error.timestamp.toISOString(),
    userMessage: error.userMessage || error.message,
    technicalMessage: error.message,
    retryable: error.retryable || false,
    context: {
      category: error.category,
      severity: error.severity,
      code: error.code,
      context: error.context,
      originalError: error.originalError?.message,
      stack: error.stack,
    },
  }
}

/**
 * Convert generic Error to DetailedError
 */
export function fromGenericError(error: Error): DetailedError {
  const isNetworkError = 
    error.message.includes('fetch') ||
    error.message.includes('network') ||
    error.message.includes('connection')
  
  const isTimeoutError = 
    error.message.includes('timeout') ||
    error.message.includes('aborted')

  const errorType: ErrorType = isNetworkError 
    ? 'network_error'
    : isTimeoutError 
    ? 'timeout_error' 
    : 'unknown_error'

  return {
    error_type: errorType,
    http_status: 0,
    timestamp: new Date().toISOString(),
    userMessage: error.message,
    technicalMessage: error.message,
    retryable: isNetworkError || isTimeoutError,
    context: {
      name: error.name,
      stack: error.stack,
    },
  }
}

/**
 * Convert any error to DetailedError with automatic detection
 */
export function toDetailedError(error: unknown): DetailedError {
  // Handle StandardizedAPIError
  if (error instanceof Error && 'code' in error && 'statusCode' in error) {
    return fromStandardizedAPIError(error as StandardizedAPIError)
  }
  
  // Handle AppError
  if (error && typeof error === 'object' && 'category' in error && 'severity' in error) {
    return fromAppError(error as AppError)
  }
  
  // Handle generic Error
  if (error instanceof Error) {
    return fromGenericError(error)
  }
  
  // Handle string errors
  if (typeof error === 'string') {
    return fromGenericError(new Error(error))
  }
  
  // Handle unknown error types
  return fromGenericError(new Error(`Unknown error: ${String(error)}`))
}

/**
 * Create error details string for copying to clipboard
 */
export function createCopyableErrorDetails(error: DetailedError): string {
  const sections = []
  
  // Basic error info
  sections.push('=== Error Details ===')
  sections.push(`Type: ${error.error_type}`)
  sections.push(`HTTP Status: ${error.http_status}`)
  sections.push(`Timestamp: ${error.timestamp}`)
  
  if (error.traceId) {
    sections.push(`Trace ID: ${error.traceId}`)
  }
  
  if (error.requestId) {
    sections.push(`Request ID: ${error.requestId}`)
  }
  
  // User message
  sections.push('')
  sections.push('=== User Message ===')
  sections.push(error.userMessage)
  
  if (error.hint) {
    sections.push('')
    sections.push('=== Hint ===')
    sections.push(error.hint)
  }
  
  // Technical details
  if (error.technicalMessage && error.technicalMessage !== error.userMessage) {
    sections.push('')
    sections.push('=== Technical Message ===')
    sections.push(error.technicalMessage)
  }
  
  // Context
  if (error.context) {
    sections.push('')
    sections.push('=== Context ===')
    sections.push(JSON.stringify(error.context, null, 2))
  }
  
  // Environment info
  sections.push('')
  sections.push('=== Environment ===')
  sections.push(`URL: ${window.location.href}`)
  sections.push(`User Agent: ${navigator.userAgent}`)
  sections.push(`Timestamp: ${new Date().toISOString()}`)
  
  return sections.join('\n')
}