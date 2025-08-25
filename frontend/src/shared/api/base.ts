import axios from 'axios'
import type {
  AxiosInstance,
  AxiosRequestConfig,
  AxiosResponse,
  AxiosError,
} from 'axios'
import type { APIResponse, APIError } from '@/shared/types/api'
import { env } from '@/shared/config/env'

// Type guard for error responses
function isErrorResponse(data: unknown): data is {
  message?: string
  detail?: string
  code?: string
  errors?: unknown
  details?: unknown
} {
  return typeof data === 'object' && data !== null
}

// Type guards for API response structures
export function isApiResponseWithData<T>(data: unknown): data is { data: T } {
  return typeof data === 'object' && data !== null && 'data' in data
}

export function validateApiResponse<T>(response: unknown): T {
  if (!isApiResponseWithData<T>(response)) {
    throw new Error('Invalid API response format')
  }
  return response.data
}

export class APIClient {
  private client: AxiosInstance
  private retryAttempts: number = 3
  private retryDelay: number = 1000

  constructor(baseURL: string, serviceName: string) {
    this.client = axios.create({
      baseURL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
        'X-Service': serviceName,
      },
    })

    this.setupInterceptors()
  }

  private setupInterceptors() {
    // Request interceptor for auth
    this.client.interceptors.request.use(
      config => {
        const token = localStorage.getItem('authToken')
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      error => Promise.reject(error),
    )

    // Response interceptor for standardized error handling
    this.client.interceptors.response.use(
      (response: AxiosResponse<APIResponse>) => {
        return response
      },
      async (error: AxiosError) => {
        const originalRequest = error.config as AxiosRequestConfig & {
          _retry?: boolean
          _retryCount?: number
        }

        // Handle authentication errors
        if (error.response?.status === 401) {
          localStorage.removeItem('authToken')
          window.location.href = '/login'
          return Promise.reject(error)
        }

        // Implement retry logic for specific errors
        if (this.shouldRetry(error) && !originalRequest._retry) {
          originalRequest._retry = true
          originalRequest._retryCount = (originalRequest._retryCount || 0) + 1

          if (originalRequest._retryCount <= this.retryAttempts) {
            await this.delay(this.retryDelay * originalRequest._retryCount)
            return this.client.request(originalRequest)
          }
        }

        return Promise.reject(this.handleError(error))
      },
    )
  }

  private shouldRetry(error: AxiosError): boolean {
    // Retry on network errors, timeouts, and 5xx status codes
    if (!error.response) return true // Network error
    if (error.code === 'ECONNABORTED') return true // Timeout
    if (error.response.status >= 500) return true // Server error
    if (error.response.status === 429) return true // Rate limit
    return false
  }

  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms))
  }

  private handleError(error: AxiosError): APIError {
    const apiError: APIError = {
      message: 'An unexpected error occurred',
      status: error.response?.status,
    }

    if (error.response?.data) {
      const responseData = error.response.data as unknown
      if (isErrorResponse(responseData)) {
        apiError.message =
          responseData.message || responseData.detail || error.message
        apiError.code = responseData.code
        apiError.details = responseData.errors || responseData.details
      } else {
        apiError.message = error.message
      }
    } else if (error.request) {
      apiError.message = 'Network error - please check your connection'
    } else {
      apiError.message = error.message
    }

    return apiError
  }

  // HTTP Methods
  async get<T>(
    url: string,
    config?: AxiosRequestConfig,
  ): Promise<APIResponse<T>> {
    const response = await this.client.get<APIResponse<T>>(url, config)
    return response.data
  }

  async post<T>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig,
  ): Promise<APIResponse<T>> {
    const response = await this.client.post<APIResponse<T>>(url, data, config)
    return response.data
  }

  async put<T>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig,
  ): Promise<APIResponse<T>> {
    const response = await this.client.put<APIResponse<T>>(url, data, config)
    return response.data
  }

  async patch<T>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig,
  ): Promise<APIResponse<T>> {
    const response = await this.client.patch<APIResponse<T>>(url, data, config)
    return response.data
  }

  async delete<T>(
    url: string,
    config?: AxiosRequestConfig,
  ): Promise<APIResponse<T>> {
    const response = await this.client.delete<APIResponse<T>>(url, config)
    return response.data
  }

  // File upload
  async uploadFile<T>(
    url: string,
    file: File,
    onUploadProgress?: (progress: number) => void,
  ): Promise<APIResponse<T>> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await this.client.post<APIResponse<T>>(url, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: progressEvent => {
        if (onUploadProgress && progressEvent.total) {
          const progress = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total,
          )
          onUploadProgress(progress)
        }
      },
    })

    return response.data
  }

  // WebSocket connection helper
  createWebSocket(endpoint: string): WebSocket {
    const wsUrl = this.client.defaults.baseURL?.replace('http', 'ws') + endpoint
    const token = localStorage.getItem('authToken')
    const url = token ? `${wsUrl}?token=${token}` : wsUrl

    return new WebSocket(url)
  }
}

// Service URLs from validated environment variables
export const SERVICE_URLS = {
  CORE: env.VITE_CORE_SERVICE_URL,
  PROJECT: env.VITE_PROJECT_SERVICE_URL,
  GENERATION: env.VITE_GENERATION_SERVICE_URL,
} as const
