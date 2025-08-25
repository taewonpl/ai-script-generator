/**
 * Enhanced API client with unified error handling, tracing, and observability
 */

import type {
  AxiosInstance,
  AxiosResponse,
  AxiosError,
  InternalAxiosRequestConfig,
} from 'axios'

// Extend Axios request config to include custom metadata
interface ExtendedAxiosRequestConfig extends InternalAxiosRequestConfig {
  metadata?: {
    requestContext?: any
    [key: string]: unknown
  }
}
import axios from 'axios'
import type {
  StandardErrorResponse,
  StandardSuccessResponse,
  TraceContext,
  ErrorCodeType,
} from '../types/observability'
import {
  TraceHeaders,
  HttpStatusCode,
  getErrorMessage,
} from '../types/observability'
import { createLogger } from '../utils/logger'
import { generateTraceId, generateRequestId } from '../utils/tracing'
import { createIdempotencyKey } from '../utils/idempotency'

const logger = createLogger('api-client')

interface APIClientConfig {
  baseURL: string
  timeout?: number
  enableTracing?: boolean
  enableIdempotency?: boolean
  service?: string
}

interface RequestContext {
  traceContext: TraceContext
  startTime: Date
  idempotencyKey?: string
}

class APIClient {
  private client: AxiosInstance
  // private _idempotencyManager: IdempotencyManager // Currently unused
  private config: APIClientConfig

  constructor(config: APIClientConfig) {
    this.config = {
      timeout: 30000,
      enableTracing: true,
      enableIdempotency: true,
      service: 'frontend',
      ...config,
    }

    // this._idempotencyManager = new IdempotencyManager()  // Currently unused

    this.client = axios.create({
      baseURL: config.baseURL,
      timeout: this.config.timeout,
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
    })

    this.setupInterceptors()
  }

  private setupInterceptors(): void {
    // Request interceptor for tracing and idempotency
    this.client.interceptors.request.use(
      (config: ExtendedAxiosRequestConfig) => {
        const requestContext = this.createRequestContext(config)

        // Store request context for response interceptor
        config.metadata = { requestContext }

        // Inject tracing headers
        if (this.config.enableTracing) {
          this.injectTracingHeaders(config, requestContext.traceContext)
        }

        // Add idempotency key for POST requests
        if (
          this.config.enableIdempotency &&
          config.method?.toLowerCase() === 'post'
        ) {
          if (!config.headers['Idempotency-Key']) {
            requestContext.idempotencyKey = createIdempotencyKey()
            config.headers['Idempotency-Key'] = requestContext.idempotencyKey
          }
        }

        // Log API request started
        logger.logEvent('API_REQUEST_STARTED', {
          method: config.method?.toUpperCase(),
          url: config.url,
          traceId: requestContext.traceContext.traceId,
          idempotencyKey: requestContext.idempotencyKey,
        })

        return config
      },
      error => {
        logger.logError('Request interceptor error', error)
        return Promise.reject(error)
      },
    )

    // Response interceptor for error handling and metrics
    this.client.interceptors.response.use(
      (response: AxiosResponse) => {
        const config = response.config as ExtendedAxiosRequestConfig
        const requestContext = config.metadata?.requestContext as RequestContext
        if (requestContext) {
          this.logSuccessfulRequest(response, requestContext)
        }

        return response
      },
      (error: AxiosError) => {
        const config = error.config as ExtendedAxiosRequestConfig | undefined
        const requestContext = config?.metadata
          ?.requestContext as RequestContext
        if (requestContext) {
          this.logFailedRequest(error, requestContext)
        }

        // Transform error to standardized format
        const standardizedError = this.transformError(error)
        return Promise.reject(standardizedError)
      },
    )
  }

  private createRequestContext(
    config: ExtendedAxiosRequestConfig,
  ): RequestContext {
    const traceContext: TraceContext = {
      traceId: generateTraceId(),
      service: this.config.service!,
      requestTimestamp: new Date().toISOString(),
      requestPath: config.url,
      requestMethod: config.method?.toUpperCase(),
      metadata: {
        userAgent: navigator.userAgent,
        requestId: generateRequestId(),
      },
    }

    // Extract existing trace context from headers if available
    if (config.headers) {
      const existingTraceId = config.headers[TraceHeaders.TRACE_ID] as string
      const existingJobId = config.headers[TraceHeaders.JOB_ID] as string
      const existingProjectId = config.headers[
        TraceHeaders.PROJECT_ID
      ] as string

      if (existingTraceId) {
        traceContext.traceId = existingTraceId
      }
      if (existingJobId) {
        traceContext.jobId = existingJobId
      }
      if (existingProjectId) {
        traceContext.projectId = existingProjectId
      }
    }

    return {
      traceContext,
      startTime: new Date(),
    }
  }

  private injectTracingHeaders(
    config: ExtendedAxiosRequestConfig,
    traceContext: TraceContext,
  ): void {
    if (!config.headers) {
      config.headers = {} as any
    }

    config.headers[TraceHeaders.TRACE_ID] = traceContext.traceId

    if (traceContext.jobId) {
      config.headers[TraceHeaders.JOB_ID] = traceContext.jobId
    }

    if (traceContext.projectId) {
      config.headers[TraceHeaders.PROJECT_ID] = traceContext.projectId
    }

    if (traceContext.userId) {
      config.headers[TraceHeaders.USER_ID] = traceContext.userId
    }
  }

  private logSuccessfulRequest(
    response: AxiosResponse,
    requestContext: RequestContext,
  ): void {
    const duration = Date.now() - requestContext.startTime.getTime()
    const responseTraceId =
      response.headers[TraceHeaders.TRACE_ID.toLowerCase()]
    const processingTime =
      response.headers[TraceHeaders.PROCESSING_TIME.toLowerCase()]

    logger.logEvent('API_REQUEST_COMPLETED', {
      method: requestContext.traceContext.requestMethod,
      url: requestContext.traceContext.requestPath,
      statusCode: response.status,
      durationMs: duration,
      serverProcessingMs: processingTime ? parseInt(processingTime) : undefined,
      traceId: requestContext.traceContext.traceId,
      responseTraceId,
      success: true,
    })

    // Track performance metrics
    logger.logPerformance('api_request', duration, true, {
      endpoint: requestContext.traceContext.requestPath,
      method: requestContext.traceContext.requestMethod,
      statusCode: response.status,
    })
  }

  private logFailedRequest(
    error: AxiosError,
    requestContext: RequestContext,
  ): void {
    const duration = Date.now() - requestContext.startTime.getTime()
    const statusCode = error.response?.status || 0
    const errorData = error.response?.data as StandardErrorResponse

    logger.logEvent('API_REQUEST_FAILED', {
      method: requestContext.traceContext.requestMethod,
      url: requestContext.traceContext.requestPath,
      statusCode,
      durationMs: duration,
      traceId: requestContext.traceContext.traceId,
      errorCode: errorData?.error?.code,
      errorMessage: errorData?.error?.message || error.message,
      success: false,
    })

    // Log error details
    logger.logError('API request failed', error, {
      endpoint: requestContext.traceContext.requestPath,
      method: requestContext.traceContext.requestMethod,
      statusCode,
      traceId: requestContext.traceContext.traceId,
    })
  }

  private transformError(error: AxiosError): StandardizedAPIError {
    if (error.response?.data) {
      // Server returned structured error
      const errorResponse = error.response.data as StandardErrorResponse
      if (errorResponse.error) {
        return new StandardizedAPIError(
          errorResponse.error.code,
          errorResponse.error.message,
          error.response.status || HttpStatusCode.INTERNAL_SERVER_ERROR,
          errorResponse.error.details,
          errorResponse.error.traceId,
        )
      }
    }

    // Network or client-side error
    if (error.code === 'ECONNABORTED' || error.code === 'TIMEOUT') {
      return new StandardizedAPIError(
        'REQUEST_TIMEOUT',
        '요청 시간이 초과되었습니다.',
        HttpStatusCode.GATEWAY_TIMEOUT,
      )
    }

    if (!error.response) {
      // Network error
      return new StandardizedAPIError(
        'REQUEST_TIMEOUT',
        '네트워크 연결을 확인해주세요.',
        0,
      )
    }

    // Unknown server error
    return new StandardizedAPIError(
      'INTERNAL_ERROR',
      '서버 오류가 발생했습니다.',
      error.response.status || HttpStatusCode.INTERNAL_SERVER_ERROR,
    )
  }

  // HTTP Methods with proper typing and error handling

  async get<T>(url: string, config?: RequestConfig): Promise<T> {
    const response = await this.client.get<StandardSuccessResponse<T>>(
      url,
      config,
    )
    return this.extractData(response)
  }

  async post<T>(
    url: string,
    data?: unknown,
    config?: RequestConfig,
  ): Promise<T> {
    const response = await this.client.post<StandardSuccessResponse<T>>(
      url,
      data,
      config,
    )
    return this.extractData(response)
  }

  async put<T>(
    url: string,
    data?: unknown,
    config?: RequestConfig,
  ): Promise<T> {
    const response = await this.client.put<StandardSuccessResponse<T>>(
      url,
      data,
      config,
    )
    return this.extractData(response)
  }

  async patch<T>(
    url: string,
    data?: unknown,
    config?: RequestConfig,
  ): Promise<T> {
    const response = await this.client.patch<StandardSuccessResponse<T>>(
      url,
      data,
      config,
    )
    return this.extractData(response)
  }

  async delete<T>(url: string, config?: RequestConfig): Promise<T> {
    const response = await this.client.delete<StandardSuccessResponse<T>>(url, {
      ...config,
      data: config?.data, // Pass data for DELETE with body
    })
    return this.extractData(response)
  }

  // Idempotent POST requests
  async postIdempotent<T>(
    url: string,
    data: unknown,
    idempotencyKey?: string,
    config?: RequestConfig,
  ): Promise<T> {
    const key = idempotencyKey || createIdempotencyKey()

    const requestConfig = {
      ...config,
      headers: {
        ...config?.headers,
        'Idempotency-Key': key,
      },
    }

    return this.post<T>(url, data, requestConfig)
  }

  // Request with trace context
  async withTraceContext<T>(
    method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE',
    url: string,
    traceContext: Partial<TraceContext>,
    data?: unknown,
    config?: RequestConfig,
  ): Promise<T> {
    const requestConfig = {
      ...config,
      headers: {
        ...config?.headers,
        ...(traceContext.traceId && {
          [TraceHeaders.TRACE_ID]: traceContext.traceId,
        }),
        ...(traceContext.jobId && {
          [TraceHeaders.JOB_ID]: traceContext.jobId,
        }),
        ...(traceContext.projectId && {
          [TraceHeaders.PROJECT_ID]: traceContext.projectId,
        }),
        ...(traceContext.userId && {
          [TraceHeaders.USER_ID]: traceContext.userId,
        }),
      },
    }

    switch (method) {
      case 'GET':
        return this.get<T>(url, requestConfig)
      case 'POST':
        return this.post<T>(url, data, requestConfig)
      case 'PUT':
        return this.put<T>(url, data, requestConfig)
      case 'PATCH':
        return this.patch<T>(url, data, requestConfig)
      case 'DELETE':
        return this.delete<T>(url, requestConfig)
      default:
        throw new Error(`Unsupported HTTP method: ${method}`)
    }
  }

  private extractData<T>(
    response: AxiosResponse<StandardSuccessResponse<T>>,
  ): T {
    const data = response.data

    // Handle both wrapped and unwrapped responses
    if (data && typeof data === 'object' && 'success' in data && data.success) {
      return data.data as T
    }

    // Fallback for non-standard responses
    return response.data as unknown as T
  }

  // Health check method
  async healthCheck(): Promise<{ status: string; timestamp: string }> {
    return this.get('/health')
  }

  // Get client configuration
  getConfig(): APIClientConfig {
    return { ...this.config }
  }

  // Update base URL
  setBaseURL(baseURL: string): void {
    this.client.defaults.baseURL = baseURL
    this.config.baseURL = baseURL
  }
}

// Standardized API Error class
export class StandardizedAPIError extends Error {
  public code: ErrorCodeType
  public statusCode: number
  public details?: Record<string, unknown>
  public traceId?: string

  constructor(
    code: ErrorCodeType,
    message: string,
    statusCode: number,
    details?: Record<string, unknown>,
    traceId?: string,
  ) {
    super(message)
    this.name = 'StandardizedAPIError'
    this.code = code
    this.statusCode = statusCode
    this.details = details
    this.traceId = traceId
  }

  // Check if error is retryable
  isRetryable(): boolean {
    return this.statusCode >= 500 || this.statusCode === 429
  }

  // Check if error is a client error
  isClientError(): boolean {
    return this.statusCode >= 400 && this.statusCode < 500
  }

  // Check if error is a server error
  isServerError(): boolean {
    return this.statusCode >= 500
  }

  // Get user-friendly message
  getUserFriendlyMessage(): string {
    return getErrorMessage(this.code, this.message)
  }

  // Convert to structured log format
  toLogFormat(): Record<string, unknown> {
    return {
      errorCode: this.code,
      message: this.message,
      statusCode: this.statusCode,
      details: this.details,
      traceId: this.traceId,
      stack: this.stack,
    }
  }
}

// Request config type
interface RequestConfig {
  headers?: Record<string, string>
  timeout?: number
  params?: Record<string, unknown>
  data?: unknown // Added for DELETE requests with body
}

// Create configured API client instances
export const coreServiceClient = new APIClient({
  baseURL:
    process.env['VITE_CORE_SERVICE_URL'] || 'http://localhost:8000/api/v1',
  service: 'core-service',
})

export const projectServiceClient = new APIClient({
  baseURL:
    process.env['VITE_PROJECT_SERVICE_URL'] || 'http://localhost:8001/api/v1',
  service: 'project-service',
})

export const generationServiceClient = new APIClient({
  baseURL:
    process.env['VITE_GENERATION_SERVICE_URL'] ||
    'http://localhost:8002/api/v1',
  service: 'generation-service',
})

// Legacy client for backward compatibility
export const client = coreServiceClient

// Legacy projectApi for compatibility - will route to appropriate services
export const projectApi = {
  get: async <T>(
    url: string,
    config?: Record<string, unknown>,
  ): Promise<{ data: T }> => {
    let response

    if (
      url.includes('/projects') ||
      url.includes('/episodes') ||
      url.includes('/scripts')
    ) {
      response = await projectServiceClient.get<T>(url, config)
    } else if (
      url.includes('/generations') ||
      url.includes('/models') ||
      url.includes('/queue')
    ) {
      response = await generationServiceClient.get<T>(url, config)
    } else {
      response = await coreServiceClient.get<T>(url, config)
    }

    return { data: response }
  },

  post: async <T>(
    url: string,
    data?: unknown,
    config?: Record<string, unknown>,
  ): Promise<{ data: T }> => {
    let response

    if (
      url.includes('/projects') ||
      url.includes('/episodes') ||
      url.includes('/scripts')
    ) {
      response = await projectServiceClient.post<T>(url, data, config)
    } else if (url.includes('/generations') || url.includes('/models')) {
      response = await generationServiceClient.post<T>(url, data, config)
    } else {
      response = await coreServiceClient.post<T>(url, data, config)
    }

    return { data: response }
  },

  put: async <T>(
    url: string,
    data?: unknown,
    config?: Record<string, unknown>,
  ): Promise<{ data: T }> => {
    let response

    if (
      url.includes('/projects') ||
      url.includes('/episodes') ||
      url.includes('/scripts')
    ) {
      response = await projectServiceClient.put<T>(url, data, config)
    } else if (url.includes('/generations')) {
      response = await generationServiceClient.put<T>(url, data, config)
    } else {
      response = await coreServiceClient.put<T>(url, data, config)
    }

    return { data: response }
  },

  patch: async <T>(
    url: string,
    data?: unknown,
    config?: Record<string, unknown>,
  ): Promise<{ data: T }> => {
    let response

    if (
      url.includes('/projects') ||
      url.includes('/episodes') ||
      url.includes('/scripts')
    ) {
      response = await projectServiceClient.patch<T>(url, data, config)
    } else if (url.includes('/generations')) {
      response = await generationServiceClient.patch<T>(url, data, config)
    } else {
      response = await coreServiceClient.patch<T>(url, data, config)
    }

    return { data: response }
  },

  delete: async <T>(
    url: string,
    config?: Record<string, unknown>,
  ): Promise<{ data: T }> => {
    let response

    if (
      url.includes('/projects') ||
      url.includes('/episodes') ||
      url.includes('/scripts')
    ) {
      response = await projectServiceClient.delete<T>(url, config)
    } else if (url.includes('/generations')) {
      response = await generationServiceClient.delete<T>(url, config)
    } else {
      response = await coreServiceClient.delete<T>(url, config)
    }

    return { data: response }
  },
}

// Export generationApi for compatibility with useJobControl
export const generationApi = generationServiceClient

export { APIClient }
export type { APIClientConfig, RequestConfig }
