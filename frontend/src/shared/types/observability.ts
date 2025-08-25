/**
 * TypeScript definitions for unified error handling and observability system
 * Mirrors the Python backend StandardErrorResponse format
 */

// HTTP Status Code constants matching Python backend
export const HttpStatusCode = {
  // Success
  SUCCESS: 200,
  CREATED: 201,
  ACCEPTED: 202,
  NO_CONTENT: 204,

  // Client Errors
  BAD_REQUEST: 400, // Validation failures
  UNAUTHORIZED: 401, // Authentication required
  FORBIDDEN: 403, // Authorization failed
  NOT_FOUND: 404, // Resource not found (project/episode)
  METHOD_NOT_ALLOWED: 405,
  CONFLICT: 409, // Episode number conflicts
  UNPROCESSABLE_ENTITY: 422, // Business rule violations
  TOO_MANY_REQUESTS: 429, // Rate limiting

  // Server Errors
  INTERNAL_SERVER_ERROR: 500, // Internal server errors
  BAD_GATEWAY: 502, // Upstream service errors
  SERVICE_UNAVAILABLE: 503, // External service outages (OpenAI, ChromaDB)
  GATEWAY_TIMEOUT: 504, // Service timeout
} as const

export type HttpStatusCodeType =
  (typeof HttpStatusCode)[keyof typeof HttpStatusCode]

// Standardized error codes matching Python backend
export const ErrorCode = {
  // Validation Errors (400)
  VALIDATION_FAILED: 'VALIDATION_FAILED',
  INVALID_REQUEST_FORMAT: 'INVALID_REQUEST_FORMAT',
  MISSING_REQUIRED_FIELD: 'MISSING_REQUIRED_FIELD',
  INVALID_FIELD_VALUE: 'INVALID_FIELD_VALUE',

  // Authentication/Authorization Errors (401/403)
  AUTHENTICATION_REQUIRED: 'AUTHENTICATION_REQUIRED',
  INVALID_TOKEN: 'INVALID_TOKEN',
  TOKEN_EXPIRED: 'TOKEN_EXPIRED',
  INSUFFICIENT_PERMISSIONS: 'INSUFFICIENT_PERMISSIONS',

  // Resource Not Found Errors (404)
  PROJECT_NOT_FOUND: 'PROJECT_NOT_FOUND',
  EPISODE_NOT_FOUND: 'EPISODE_NOT_FOUND',
  GENERATION_JOB_NOT_FOUND: 'GENERATION_JOB_NOT_FOUND',
  USER_NOT_FOUND: 'USER_NOT_FOUND',

  // Conflict Errors (409)
  EPISODE_NUMBER_CONFLICT: 'EPISODE_NUMBER_CONFLICT',
  PROJECT_NAME_CONFLICT: 'PROJECT_NAME_CONFLICT',
  RESOURCE_ALREADY_EXISTS: 'RESOURCE_ALREADY_EXISTS',

  // Business Rule Violations (422)
  INVALID_GENERATION_PROMPT: 'INVALID_GENERATION_PROMPT',
  EPISODE_LIMIT_EXCEEDED: 'EPISODE_LIMIT_EXCEEDED',
  PROJECT_ARCHIVED: 'PROJECT_ARCHIVED',
  GENERATION_IN_PROGRESS: 'GENERATION_IN_PROGRESS',

  // Rate Limiting (429)
  RATE_LIMIT_EXCEEDED: 'RATE_LIMIT_EXCEEDED',
  DAILY_QUOTA_EXCEEDED: 'DAILY_QUOTA_EXCEEDED',
  CONCURRENT_LIMIT_EXCEEDED: 'CONCURRENT_LIMIT_EXCEEDED',

  // Internal Server Errors (500)
  INTERNAL_ERROR: 'INTERNAL_ERROR',
  DATABASE_ERROR: 'DATABASE_ERROR',
  CONFIGURATION_ERROR: 'CONFIGURATION_ERROR',
  EPISODE_SAVE_FAILED: 'EPISODE_SAVE_FAILED',
  GENERATION_FAILED: 'GENERATION_FAILED',

  // External Service Errors (503)
  OPENAI_SERVICE_UNAVAILABLE: 'OPENAI_SERVICE_UNAVAILABLE',
  CHROMADB_CONNECTION_FAILED: 'CHROMADB_CONNECTION_FAILED',
  EXTERNAL_API_ERROR: 'EXTERNAL_API_ERROR',
  SERVICE_DEGRADED: 'SERVICE_DEGRADED',

  // Network/Timeout Errors (504)
  REQUEST_TIMEOUT: 'REQUEST_TIMEOUT',
  GENERATION_TIMEOUT: 'GENERATION_TIMEOUT',
  DATABASE_TIMEOUT: 'DATABASE_TIMEOUT',
} as const

export type ErrorCodeType = (typeof ErrorCode)[keyof typeof ErrorCode]

// Error detail interface matching Python backend
export interface ErrorDetail {
  code: ErrorCodeType
  message: string
  details?: Record<string, unknown>
  traceId?: string
  timestamp: string // ISO string format
}

// Standardized error response matching Python backend
export interface StandardErrorResponse {
  success: false
  error: ErrorDetail
}

// Standardized success response matching Python backend
export interface StandardSuccessResponse<T = unknown> {
  success: true
  data?: T
  message?: string
  traceId?: string
  timestamp: string // ISO string format
}

// Union type for all API responses
export type APIResponse<T = unknown> =
  | StandardSuccessResponse<T>
  | StandardErrorResponse

// Tracing header constants
export const TraceHeaders = {
  TRACE_ID: 'X-Trace-Id',
  JOB_ID: 'X-Job-Id',
  PROJECT_ID: 'X-Project-Id',
  USER_ID: 'X-User-Id',

  // Response headers
  PROCESSING_TIME: 'X-Processing-Time',
  SERVICE: 'X-Service',
} as const

// Trace context interface
export interface TraceContext {
  traceId: string
  jobId?: string
  projectId?: string
  userId?: string
  service?: string
  requestTimestamp: string
  requestPath?: string
  requestMethod?: string
  metadata?: Record<string, unknown>
}

// Idempotency key interface
export interface IdempotencyKey {
  key: string
  createdAt: string
  expiresAt: string
}

// Log level enum matching Python backend
export const LogLevel = {
  TRACE: 'TRACE',
  DEBUG: 'DEBUG',
  INFO: 'INFO',
  WARNING: 'WARNING',
  ERROR: 'ERROR',
  CRITICAL: 'CRITICAL',
} as const

export type LogLevelType = (typeof LogLevel)[keyof typeof LogLevel]

// Structured log entry interface
export interface StructuredLogEntry {
  timestamp: string
  level: LogLevelType
  service: string
  traceId?: string
  jobId?: string
  projectId?: string
  message: string
  metadata?: Record<string, unknown>
  durationMs?: number
  errorCode?: string
  errorType?: string
  stackTrace?: string
}

// Health status interface
export interface DependencyHealth {
  name: string
  status: 'healthy' | 'degraded' | 'unhealthy'
  responseTime?: number
  message?: string
}

export interface ServiceHealth {
  status: 'healthy' | 'degraded' | 'unhealthy'
  service: string
  timestamp: string
  version: string
  dependencies: DependencyHealth[]
}

// Metrics interfaces
export interface RequestMetrics {
  endpoint: string
  method: string
  responseTime: number
  statusCode: number
  timestamp: string
}

export interface ErrorMetrics {
  service: string
  endpoint: string
  errorCode: ErrorCodeType
  count: number
  timestamp: string
}

export interface PerformanceMetrics {
  operation: string
  averageResponseTime: number
  p95ResponseTime: number
  p99ResponseTime: number
  requestCount: number
  errorRate: number
  timestamp: string
}

// Common error messages matching Python backend
export const COMMON_ERROR_MESSAGES: Record<ErrorCodeType, string> = {
  PROJECT_NOT_FOUND: '요청한 프로젝트를 찾을 수 없습니다.',
  EPISODE_NOT_FOUND: '요청한 에피소드를 찾을 수 없습니다.',
  GENERATION_JOB_NOT_FOUND: '요청한 생성 작업을 찾을 수 없습니다.',
  EPISODE_NUMBER_CONFLICT: '해당 에피소드 번호가 이미 존재합니다.',
  EPISODE_SAVE_FAILED: '에피소드 저장 중 오류가 발생했습니다.',
  GENERATION_FAILED: '콘텐츠 생성 중 오류가 발생했습니다.',
  CHROMADB_CONNECTION_FAILED: '벡터 데이터베이스 연결에 실패했습니다.',
  OPENAI_SERVICE_UNAVAILABLE: 'AI 서비스가 일시적으로 이용할 수 없습니다.',
  VALIDATION_FAILED: '입력 데이터 검증에 실패했습니다.',
  RATE_LIMIT_EXCEEDED: '요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요.',
  INTERNAL_ERROR: '내부 서버 오류가 발생했습니다.',
  INVALID_REQUEST_FORMAT: '잘못된 요청 형식입니다.',
  MISSING_REQUIRED_FIELD: '필수 입력 항목이 누락되었습니다.',
  INVALID_FIELD_VALUE: '입력값이 유효하지 않습니다.',
  AUTHENTICATION_REQUIRED: '인증이 필요합니다.',
  INVALID_TOKEN: '유효하지 않은 토큰입니다.',
  TOKEN_EXPIRED: '토큰이 만료되었습니다.',
  INSUFFICIENT_PERMISSIONS: '권한이 부족합니다.',
  USER_NOT_FOUND: '사용자를 찾을 수 없습니다.',
  PROJECT_NAME_CONFLICT: '동일한 이름의 프로젝트가 이미 존재합니다.',
  RESOURCE_ALREADY_EXISTS: '리소스가 이미 존재합니다.',
  INVALID_GENERATION_PROMPT: '유효하지 않은 생성 프롬프트입니다.',
  EPISODE_LIMIT_EXCEEDED: '에피소드 생성 한도를 초과했습니다.',
  PROJECT_ARCHIVED: '보관된 프로젝트는 수정할 수 없습니다.',
  GENERATION_IN_PROGRESS: '이미 생성 작업이 진행 중입니다.',
  DAILY_QUOTA_EXCEEDED: '일일 할당량을 초과했습니다.',
  CONCURRENT_LIMIT_EXCEEDED: '동시 요청 한도를 초과했습니다.',
  DATABASE_ERROR: '데이터베이스 오류가 발생했습니다.',
  CONFIGURATION_ERROR: '설정 오류가 발생했습니다.',
  EXTERNAL_API_ERROR: '외부 API 오류가 발생했습니다.',
  SERVICE_DEGRADED: '서비스가 일시적으로 불안정합니다.',
  REQUEST_TIMEOUT: '요청 시간이 초과되었습니다.',
  GENERATION_TIMEOUT: '생성 작업 시간이 초과되었습니다.',
  DATABASE_TIMEOUT: '데이터베이스 응답 시간이 초과되었습니다.',
}

// Utility function to get error message
export function getErrorMessage(
  code: ErrorCodeType,
  customMessage?: string,
): string {
  return (
    customMessage ||
    COMMON_ERROR_MESSAGES[code] ||
    '알 수 없는 오류가 발생했습니다.'
  )
}

// Event types for consistent logging
export const EventTypes = {
  // CRUD Operations
  CREATE: 'CREATE',
  READ: 'READ',
  UPDATE: 'UPDATE',
  DELETE: 'DELETE',

  // Generation Lifecycle
  GENERATION_STARTED: 'GENERATION_STARTED',
  GENERATION_PROGRESS: 'GENERATION_PROGRESS',
  GENERATION_COMPLETED: 'GENERATION_COMPLETED',
  GENERATION_FAILED: 'GENERATION_FAILED',
  GENERATION_CANCELLED: 'GENERATION_CANCELLED',

  // SSE Events
  SSE_CONNECTION_OPENED: 'SSE_CONNECTION_OPENED',
  SSE_CONNECTION_CLOSED: 'SSE_CONNECTION_CLOSED',
  SSE_CONNECTION_ERROR: 'SSE_CONNECTION_ERROR',
  SSE_MESSAGE_SENT: 'SSE_MESSAGE_SENT',

  // API Events
  API_REQUEST_STARTED: 'API_REQUEST_STARTED',
  API_REQUEST_COMPLETED: 'API_REQUEST_COMPLETED',
  API_REQUEST_FAILED: 'API_REQUEST_FAILED',

  // System Events
  SERVICE_STARTED: 'SERVICE_STARTED',
  SERVICE_STOPPED: 'SERVICE_STOPPED',
  HEALTH_CHECK: 'HEALTH_CHECK',
} as const

export type EventType = (typeof EventTypes)[keyof typeof EventTypes]
