/**
 * Error Panel types and interfaces
 */

export type ErrorType = 
  | 'server_unavailable' 
  | 'network_error' 
  | 'validation_error' 
  | 'authorization_error' 
  | 'rate_limit_error'
  | 'timeout_error'
  | 'unknown_error'

export type Language = 'en' | 'kr'

export interface DetailedError {
  error_type: ErrorType
  http_status: number
  hint?: string
  traceId?: string
  requestId?: string
  timestamp: string
  userMessage: string
  technicalMessage?: string
  retryable: boolean
  context?: Record<string, any>
}

export interface RetryConfig {
  maxRetries: number
  baseDelay: number
  maxDelay: number
  exponentialBackoff: boolean
  jitter: boolean
}

export interface ErrorPanelProps {
  error: DetailedError
  onRetry?: () => Promise<void>
  onDismiss?: () => void
  language?: Language
  compact?: boolean
  showTechnicalDetails?: boolean
  retryConfig?: Partial<RetryConfig>
}

export interface CopyableErrorInfo {
  traceId?: string
  requestId?: string
  timestamp: string
  errorType: string
  httpStatus: number
  userAgent: string
  url: string
  technicalDetails?: string
}