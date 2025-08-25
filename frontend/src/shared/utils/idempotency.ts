/**
 * Frontend idempotency key management for safe API retries
 */

import type { IdempotencyKey } from '../types/observability'

// Generate idempotency key
export function createIdempotencyKey(): string {
  const timestamp = Date.now().toString(36)
  const random = crypto
    .getRandomValues(new Uint8Array(8))
    .reduce((str, byte) => str + byte.toString(36), '')

  return `idem_${timestamp}_${random}`
}

// Generate UUID v4 for idempotency
export function generateIdempotencyUUID(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return `idem_${crypto.randomUUID()}`
  }

  // Fallback for older browsers
  return (
    'idem_' +
    'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
      const r = (Math.random() * 16) | 0
      const v = c === 'x' ? r : (r & 0x3) | 0x8
      return v.toString(16)
    })
  )
}

// Idempotency manager for client-side key management
export class IdempotencyManager {
  private keyStorage = new Map<string, IdempotencyKey>()
  private static readonly STORAGE_KEY = 'ai-script-idempotency-keys'
  private static readonly DEFAULT_EXPIRY_MS = 60 * 60 * 1000 // 1 hour
  private static readonly MAX_KEYS = 100 // Limit memory usage

  constructor() {
    this.loadFromStorage()
    this.startCleanupInterval()
  }

  // Generate and store a new idempotency key
  createKey(
    operation: string,
    expiryMs: number = IdempotencyManager.DEFAULT_EXPIRY_MS,
  ): string {
    const key = createIdempotencyKey()
    const now = Date.now()

    const idempotencyKey: IdempotencyKey = {
      key,
      createdAt: new Date(now).toISOString(),
      expiresAt: new Date(now + expiryMs).toISOString(),
    }

    // Store with operation as identifier
    this.keyStorage.set(`${operation}:${key}`, idempotencyKey)

    // Cleanup if too many keys
    this.cleanupExpiredKeys()
    if (this.keyStorage.size > IdempotencyManager.MAX_KEYS) {
      this.cleanupOldestKeys()
    }

    this.saveToStorage()

    return key
  }

  // Get existing key for an operation (if still valid)
  getValidKey(operation: string): string | null {
    const now = Date.now()

    for (const [storageKey, idempotencyKey] of this.keyStorage.entries()) {
      if (storageKey.startsWith(`${operation}:`)) {
        const expiresAt = new Date(idempotencyKey.expiresAt).getTime()

        if (now < expiresAt) {
          return idempotencyKey.key
        } else {
          // Remove expired key
          this.keyStorage.delete(storageKey)
        }
      }
    }

    return null
  }

  // Get or create key for an operation
  getOrCreateKey(operation: string, expiryMs?: number): string {
    const existingKey = this.getValidKey(operation)
    if (existingKey) {
      return existingKey
    }

    return this.createKey(operation, expiryMs)
  }

  // Invalidate a key after successful operation
  invalidateKey(key: string): void {
    for (const [storageKey, idempotencyKey] of this.keyStorage.entries()) {
      if (idempotencyKey.key === key) {
        this.keyStorage.delete(storageKey)
        break
      }
    }

    this.saveToStorage()
  }

  // Check if a key is still valid
  isKeyValid(key: string): boolean {
    const now = Date.now()

    for (const idempotencyKey of this.keyStorage.values()) {
      if (idempotencyKey.key === key) {
        const expiresAt = new Date(idempotencyKey.expiresAt).getTime()
        return now < expiresAt
      }
    }

    return false
  }

  // Clean up expired keys
  private cleanupExpiredKeys(): void {
    const now = Date.now()
    const keysToDelete: string[] = []

    for (const [storageKey, idempotencyKey] of this.keyStorage.entries()) {
      const expiresAt = new Date(idempotencyKey.expiresAt).getTime()
      if (now >= expiresAt) {
        keysToDelete.push(storageKey)
      }
    }

    keysToDelete.forEach(key => this.keyStorage.delete(key))
  }

  // Clean up oldest keys to prevent memory bloat
  private cleanupOldestKeys(): void {
    const entries = Array.from(this.keyStorage.entries())

    // Sort by creation time (oldest first)
    entries.sort((a, b) => {
      const aTime = new Date(a[1].createdAt).getTime()
      const bTime = new Date(b[1].createdAt).getTime()
      return aTime - bTime
    })

    // Remove oldest 20% of keys
    const toRemove = Math.floor(entries.length * 0.2)
    for (let i = 0; i < toRemove; i++) {
      this.keyStorage.delete(entries[i][0])
    }
  }

  // Start periodic cleanup
  private startCleanupInterval(): void {
    // Clean up expired keys every 5 minutes
    setInterval(
      () => {
        this.cleanupExpiredKeys()
        this.saveToStorage()
      },
      5 * 60 * 1000,
    )
  }

  // Persist keys to localStorage
  private saveToStorage(): void {
    if (typeof localStorage === 'undefined') return

    try {
      const serialized = Array.from(this.keyStorage.entries())
      localStorage.setItem(
        IdempotencyManager.STORAGE_KEY,
        JSON.stringify(serialized),
      )
    } catch (error) {
      console.debug('Failed to save idempotency keys to storage:', error)
    }
  }

  // Load keys from localStorage
  private loadFromStorage(): void {
    if (typeof localStorage === 'undefined') return

    try {
      const data = localStorage.getItem(IdempotencyManager.STORAGE_KEY)
      if (!data) return

      const serialized = JSON.parse(data) as [string, IdempotencyKey][]
      this.keyStorage = new Map(serialized)

      // Clean up expired keys on load
      this.cleanupExpiredKeys()
    } catch (error) {
      console.debug('Failed to load idempotency keys from storage:', error)
      // Clear corrupted data
      localStorage.removeItem(IdempotencyManager.STORAGE_KEY)
    }
  }

  // Get all valid keys (for debugging)
  getValidKeys(): IdempotencyKey[] {
    const now = Date.now()
    const validKeys: IdempotencyKey[] = []

    for (const key of this.keyStorage.values()) {
      const expiresAt = new Date(key.expiresAt).getTime()
      if (now < expiresAt) {
        validKeys.push(key)
      }
    }

    return validKeys
  }

  // Clear all keys
  clearAllKeys(): void {
    this.keyStorage.clear()
    this.saveToStorage()
  }
}

// Operation-specific idempotency helpers
export class OperationIdempotency {
  private manager: IdempotencyManager

  constructor() {
    this.manager = new IdempotencyManager()
  }

  // Episode creation idempotency
  getEpisodeCreationKey(projectId: string, episodeNumber: number): string {
    const operation = `create_episode_${projectId}_${episodeNumber}`
    return this.manager.getOrCreateKey(operation)
  }

  // Generation request idempotency
  getGenerationKey(projectId: string, episodeId: string): string {
    const operation = `generate_${projectId}_${episodeId}`
    return this.manager.getOrCreateKey(operation)
  }

  // Project creation idempotency
  getProjectCreationKey(userId: string, projectName: string): string {
    const operation = `create_project_${userId}_${projectName.toLowerCase().replace(/\s+/g, '_')}`
    return this.manager.getOrCreateKey(operation)
  }

  // Generic operation key
  getOperationKey(operation: string, ...identifiers: string[]): string {
    const fullOperation = [operation, ...identifiers].join('_')
    return this.manager.getOrCreateKey(fullOperation)
  }

  // Mark operation as completed
  markCompleted(key: string): void {
    this.manager.invalidateKey(key)
  }

  // Check if operation is safe to retry
  canRetry(key: string): boolean {
    return this.manager.isKeyValid(key)
  }
}

// Request retry manager with idempotency
export class RetryManager {
  private static readonly DEFAULT_MAX_RETRIES = 3
  private static readonly DEFAULT_BASE_DELAY = 1000 // 1 second
  private static readonly DEFAULT_MAX_DELAY = 10000 // 10 seconds

  static async withRetry<T>(
    operation: () => Promise<T>,
    options: {
      maxRetries?: number
      baseDelay?: number
      maxDelay?: number
      idempotencyKey?: string
      shouldRetry?: (error: unknown) => boolean
      onRetry?: (attempt: number, error: unknown) => void
    } = {},
  ): Promise<T> {
    const {
      maxRetries = this.DEFAULT_MAX_RETRIES,
      baseDelay = this.DEFAULT_BASE_DELAY,
      maxDelay = this.DEFAULT_MAX_DELAY,
      shouldRetry = error => {
        // Retry on network errors or 5xx status codes
        if (error && typeof error === 'object' && 'statusCode' in error) {
          const statusCode = (error as { statusCode: number }).statusCode
          return statusCode >= 500 || statusCode === 429
        }
        return true // Default to retry for unknown errors
      },
      onRetry,
    } = options

    let lastError: unknown

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        return await operation()
      } catch (error) {
        lastError = error

        // Don't retry on last attempt
        if (attempt === maxRetries) {
          break
        }

        // Check if error should be retried
        if (!shouldRetry(error)) {
          break
        }

        // Call retry callback
        onRetry?.(attempt + 1, error)

        // Calculate delay with exponential backoff and jitter
        const delay = Math.min(
          baseDelay * Math.pow(2, attempt) + Math.random() * 1000,
          maxDelay,
        )

        // Wait before retry
        await new Promise(resolve => setTimeout(resolve, delay))
      }
    }

    throw lastError
  }
}

// Global idempotency manager instance
export const globalIdempotencyManager = new IdempotencyManager()
export const operationIdempotency = new OperationIdempotency()

// Hook for React components
export function useIdempotency() {
  return {
    createKey: createIdempotencyKey,
    getOperationKey:
      operationIdempotency.getOperationKey.bind(operationIdempotency),
    getEpisodeCreationKey:
      operationIdempotency.getEpisodeCreationKey.bind(operationIdempotency),
    getGenerationKey:
      operationIdempotency.getGenerationKey.bind(operationIdempotency),
    getProjectCreationKey:
      operationIdempotency.getProjectCreationKey.bind(operationIdempotency),
    markCompleted:
      operationIdempotency.markCompleted.bind(operationIdempotency),
    canRetry: operationIdempotency.canRetry.bind(operationIdempotency),
  }
}

// Helper for idempotent fetch requests
export async function idempotentFetch(
  url: string,
  options: RequestInit & {
    idempotencyKey?: string
    operation?: string
  } = {},
): Promise<Response> {
  const { idempotencyKey, operation, ...fetchOptions } = options

  let key = idempotencyKey
  if (!key && operation) {
    key = operationIdempotency.getOperationKey(operation, url)
  }
  if (!key && fetchOptions.method === 'POST') {
    key = createIdempotencyKey()
  }

  const headers = new Headers(fetchOptions.headers)
  if (key) {
    headers.set('Idempotency-Key', key)
  }

  const response = await fetch(url, {
    ...fetchOptions,
    headers,
  })

  // Mark as completed on success
  if (response.ok && key) {
    operationIdempotency.markCompleted(key)
  }

  return response
}
