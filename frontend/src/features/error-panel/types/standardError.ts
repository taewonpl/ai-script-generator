/**
 * Standardized error format (superset)
 * Adapts all types of errors (standard server response, HTML/text/network) to this format
 */

export interface StandardErrorFormat {
  error_type: string                    // fallback: "unknown_error"
  http_status: number                   // fallback: 0 for network
  hint?: string                         // user-friendly guidance
  endpoint?: string                     // e.g., "/api/project/api/v1/projects?page=1"
  method?: string                       // "GET", "POST", etc.
  request_id?: string                   // uuid-or-absent
  trace_id?: string                     // trace-or-absent
  timestamp: string                     // ISO 8601 format
  raw_message?: string                  // first 200 chars
  is_offline: boolean                   // navigator.onLine status
  // Additional metadata for debugging
  user_agent?: string
  url?: string
  masked_data?: Record<string, any>     // sanitized context
}

/**
 * Sensitive data patterns to mask
 */
export const SENSITIVE_PATTERNS = [
  // Tokens and API keys
  /Bearer\s+[A-Za-z0-9\-._~+/]+/gi,
  /token["':\s]*["']*([A-Za-z0-9\-._~+/]{10,})["']*\s*/gi,
  /key["':\s]*["']*([A-Za-z0-9\-._~+/]{10,})["']*\s*/gi,
  /secret["':\s]*["']*([A-Za-z0-9\-._~+/]{10,})["']*\s*/gi,
  
  // Email addresses
  /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g,
  
  // Internal paths (macOS/Windows/Linux)
  // eslint-disable-next-line no-useless-escape
  /\/Users\/[^\/\s]+/g,
  // eslint-disable-next-line no-useless-escape
  /\/home\/[^\/\s]+/g,
   
  /C:\\Users\\[^\\s]+/g,
  
  // Cookies
  /Set-Cookie:\s*[^;\n]+/gi,
  /Cookie:\s*[^;\n]+/gi,
  
  // IP addresses (basic pattern)
  /\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b/g,
]

/**
 * Mask sensitive information in text
 */
export function maskSensitiveData(text: string): string {
  let maskedText = text

  SENSITIVE_PATTERNS.forEach(pattern => {
    maskedText = maskedText.replace(pattern, (match) => {
      // Keep first 3 and last 3 characters, mask the middle
      if (match.length <= 6) {
        return '*'.repeat(match.length)
      }
      return match.substring(0, 3) + '*'.repeat(match.length - 6) + match.substring(match.length - 3)
    })
  })

  return maskedText
}

/**
 * Retry configuration with automatic backoff
 */
export interface StandardRetryConfig {
  maxAutoRetries: number      // Maximum automatic retries (default: 2)
  autoDelays: number[]        // Delays in ms: [0, 500, 1500] with jitter
  jitterRange: number         // Jitter range in ms (default: 250)
  resetOnManual: boolean      // Reset counter on manual retry (default: true)
  offlineRetry: boolean       // Auto retry when coming back online (default: true)
}

export const DEFAULT_RETRY_CONFIG: StandardRetryConfig = {
  maxAutoRetries: 2,
  autoDelays: [0, 500, 1500],
  jitterRange: 250,
  resetOnManual: true,
  offlineRetry: true,
}

/**
 * Add jitter to delay
 */
export function addJitter(baseDelay: number, jitterRange: number): number {
  const jitter = (Math.random() - 0.5) * jitterRange * 2
  return Math.max(0, Math.floor(baseDelay + jitter))
}

/**
 * Check if error is retryable based on type and status
 */
export function isRetryableError(errorType: string, httpStatus: number): boolean {
  // Network errors are always retryable
  if (httpStatus === 0 || errorType === 'network_error') {
    return true
  }
  
  // Server errors (5xx) are retryable
  if (httpStatus >= 500) {
    return true
  }
  
  // Rate limiting is retryable
  if (httpStatus === 429 || errorType === 'rate_limit_error') {
    return true
  }
  
  // Timeout errors are retryable
  if (httpStatus === 408 || errorType === 'timeout_error') {
    return true
  }
  
  // Client errors (4xx) are typically not retryable
  return false
}