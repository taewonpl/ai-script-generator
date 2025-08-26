/**
 * Error handling types and utilities
 */

export type ErrorCategory =
  | 'network'
  | 'server'
  | 'validation'
  | 'authorization'
  | 'not_found'
  | 'rate_limit'
  | 'unknown'

export type ErrorSeverity = 'low' | 'medium' | 'high' | 'critical'

export interface AppError extends Error {
  category: ErrorCategory
  severity: ErrorSeverity
  code?: string
  statusCode?: number
  originalError?: Error
  context?: Record<string, any>
  userMessage?: string
  retryable?: boolean
  timestamp: Date
}

export interface ValidationError {
  field: string
  message: string
  code?: string
  value?: any
}

export interface ErrorInfo {
  category: ErrorCategory
  severity: ErrorSeverity
  title: string
  message: string
  action?: string
  retryable: boolean
}

export interface RetryOptions {
  maxRetries: number
  retryDelay: number
  exponentialBackoff: boolean
}
