import type { AxiosError } from 'axios'
import type { ErrorCategory, ErrorSeverity, ErrorInfo } from './types'

// Create AppError interface for runtime use
interface AppError extends Error {
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

/**
 * Classify and create user-friendly error messages
 */
export class ErrorClassifier {
  /**
   * Classify an error and return structured error information
   */
  static classify(error: Error | AxiosError | any): AppError {
    const timestamp = new Date()

    // Handle Axios errors (HTTP requests)
    if (this.isAxiosError(error)) {
      return this.classifyAxiosError(error, timestamp)
    }

    // Handle network errors
    if (this.isNetworkError(error)) {
      return this.createAppError({
        error,
        category: 'network',
        severity: 'high',
        userMessage: '인터넷 연결을 확인해주세요',
        retryable: true,
        timestamp,
      })
    }

    // Handle validation errors
    if (this.isValidationError(error)) {
      return this.createAppError({
        error,
        category: 'validation',
        severity: 'medium',
        userMessage: error.message,
        retryable: false,
        timestamp,
      })
    }

    // Default unknown error
    return this.createAppError({
      error,
      category: 'unknown',
      severity: 'medium',
      userMessage: '예상치 못한 오류가 발생했습니다',
      retryable: false,
      timestamp,
    })
  }

  /**
   * Get user-friendly error information
   */
  static getErrorInfo(error: AppError): ErrorInfo {
    const baseInfo = this.getErrorInfoByCategory(error.category)

    return {
      ...baseInfo,
      message: error.userMessage || baseInfo.message,
      retryable: error.retryable ?? baseInfo.retryable,
    }
  }

  /**
   * Classify Axios errors (HTTP requests)
   */
  private static classifyAxiosError(
    error: AxiosError,
    timestamp: Date,
  ): AppError {
    const status = error.response?.status
    const data = error.response?.data as any

    // Network error (no response)
    if (!error.response) {
      return this.createAppError({
        error,
        category: 'network',
        severity: 'high',
        userMessage: '인터넷 연결을 확인해주세요',
        retryable: true,
        statusCode: 0,
        timestamp,
      })
    }

    // Status code specific handling
    switch (status) {
      case 400:
        return this.createAppError({
          error,
          category: 'validation',
          severity: 'medium',
          userMessage: data?.message || '요청이 올바르지 않습니다',
          retryable: false,
          statusCode: status,
          timestamp,
        })

      case 401:
        return this.createAppError({
          error,
          category: 'authorization',
          severity: 'high',
          userMessage: '로그인이 필요합니다',
          retryable: false,
          statusCode: status,
          timestamp,
        })

      case 403:
        return this.createAppError({
          error,
          category: 'authorization',
          severity: 'high',
          userMessage: '접근 권한이 없습니다',
          retryable: false,
          statusCode: status,
          timestamp,
        })

      case 404:
        return this.createAppError({
          error,
          category: 'not_found',
          severity: 'medium',
          userMessage: '요청한 리소스를 찾을 수 없습니다',
          retryable: false,
          statusCode: status,
          timestamp,
        })

      case 429:
        return this.createAppError({
          error,
          category: 'rate_limit',
          severity: 'medium',
          userMessage: '요청이 너무 많습니다. 잠시 후 다시 시도해주세요',
          retryable: true,
          statusCode: status,
          timestamp,
        })

      case 500:
      case 502:
      case 503:
      case 504:
        return this.createAppError({
          error,
          category: 'server',
          severity: 'high',
          userMessage:
            '서버에 일시적 문제가 발생했습니다. 잠시 후 다시 시도해주세요',
          retryable: true,
          statusCode: status,
          timestamp,
        })

      default:
        return this.createAppError({
          error,
          category: 'server',
          severity: 'medium',
          userMessage: data?.message || '서버 오류가 발생했습니다',
          retryable: status >= 500,
          statusCode: status,
          timestamp,
        })
    }
  }

  /**
   * Get error information by category
   */
  private static getErrorInfoByCategory(
    category: ErrorCategory,
  ): Omit<ErrorInfo, 'message' | 'retryable'> {
    switch (category) {
      case 'network':
        return {
          category,
          severity: 'high',
          title: '네트워크 오류',
          action: '인터넷 연결 확인',
        }

      case 'server':
        return {
          category,
          severity: 'high',
          title: '서버 오류',
          action: '잠시 후 다시 시도',
        }

      case 'validation':
        return {
          category,
          severity: 'medium',
          title: '입력 오류',
          action: '입력 내용 확인',
        }

      case 'authorization':
        return {
          category,
          severity: 'high',
          title: '인증 오류',
          action: '로그인 필요',
        }

      case 'not_found':
        return {
          category,
          severity: 'medium',
          title: '리소스 없음',
          action: 'URL 확인',
        }

      case 'rate_limit':
        return {
          category,
          severity: 'medium',
          title: '요청 제한',
          action: '잠시 후 재시도',
        }

      default:
        return {
          category: 'unknown',
          severity: 'medium',
          title: '알 수 없는 오류',
          action: '새로고침 시도',
        }
    }
  }

  /**
   * Create AppError instance
   */
  private static createAppError({
    error,
    category,
    severity,
    userMessage,
    retryable,
    statusCode,
    timestamp,
  }: {
    error: Error
    category: ErrorCategory
    severity: ErrorSeverity
    userMessage: string
    retryable: boolean
    statusCode?: number
    timestamp: Date
  }): AppError {
    const appError = new Error(error.message) as AppError

    appError.category = category
    appError.severity = severity
    appError.userMessage = userMessage
    appError.retryable = retryable
    appError.statusCode = statusCode
    appError.originalError = error
    appError.timestamp = timestamp
    appError.name = 'AppError'

    // Add context from Axios error
    if (this.isAxiosError(error)) {
      appError.context = {
        url: error.config?.url,
        method: error.config?.method,
        response: error.response?.data,
      }
      appError.code = error.code
    }

    return appError
  }

  /**
   * Type guards
   */
  private static isAxiosError(error: any): error is AxiosError {
    return error?.isAxiosError === true
  }

  private static isNetworkError(error: any): boolean {
    return (
      error?.code === 'NETWORK_ERROR' ||
      error?.message?.includes('Network Error') ||
      error?.message?.includes('ERR_NETWORK')
    )
  }

  private static isValidationError(error: any): boolean {
    return (
      error?.name === 'ValidationError' ||
      error?.name === 'ZodError' ||
      error?.message?.includes('validation')
    )
  }
}
