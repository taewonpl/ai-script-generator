import { z } from 'zod'

/**
 * 🔒 SECURITY NOTE:
 * Only environment variables with VITE_ prefix are exposed to the client bundle.
 * Never put sensitive data (API keys, secrets) in VITE_ variables!
 *
 * ✅ Safe: VITE_APP_VERSION, VITE_API_URL
 * ❌ Unsafe: VITE_SECRET_KEY, VITE_DATABASE_PASSWORD
 */

/**
 * Enhanced type conversion utilities for environment variables
 */

// Safe boolean parsing with multiple accepted values
const parseBoolean = (
  value: string | undefined,
  defaultValue = false,
): boolean => {
  if (!value) return defaultValue
  const normalized = value.toLowerCase().trim()
  return ['true', '1', 'yes', 'on', 'enabled'].includes(normalized)
}

// Safe number parsing with NaN validation and range clamping
const parseNumber = (
  value: string | undefined,
  defaultValue: number,
  min?: number,
  max?: number,
): number => {
  if (!value) return defaultValue

  const parsed = parseFloat(value.trim())
  if (isNaN(parsed)) {
    console.warn(
      `Invalid number in environment variable: "${value}", using default: ${defaultValue}`,
    )
    return defaultValue
  }

  // Clamp value within range if specified
  if (min !== undefined && parsed < min) return min
  if (max !== undefined && parsed > max) return max

  return parsed
}

// Sentry sample rate with strict 0-1 clamping
const parseSampleRate = (value: string | undefined): number => {
  return parseNumber(value, 1.0, 0.0, 1.0)
}

/**
 * Environment variables validation schema with enhanced type conversion
 */
const EnvSchema = z.object({
  // Required service URLs with validation
  VITE_CORE_SERVICE_URL: z.string().url('Core Service URL이 올바르지 않습니다'),
  VITE_PROJECT_SERVICE_URL: z
    .string()
    .url('Project Service URL이 올바르지 않습니다'),
  VITE_GENERATION_SERVICE_URL: z
    .string()
    .url('Generation Service URL이 올바르지 않습니다'),

  // Optional Sentry configuration
  VITE_SENTRY_DSN: z.string().url().optional(),
  VITE_SENTRY_TRACES_SAMPLE_RATE: z
    .string()
    .optional()
    .default('1.0')
    .transform(parseSampleRate),

  // Environment and versioning
  VITE_ENV: z
    .enum(['development', 'production', 'test'])
    .default('development'),
  VITE_APP_VERSION: z.string().default('1.0.0'),

  // Feature flags with enhanced boolean parsing
  VITE_ENABLE_DEVTOOLS: z
    .string()
    .optional()
    .default('true')
    .transform(val => parseBoolean(val, true)),
  VITE_ENABLE_MSW: z
    .string()
    .optional()
    .default('false')
    .transform(val => parseBoolean(val, false)),

  // Analytics
  VITE_ANALYTICS_TRACKING_ID: z.string().optional(),
})

/**
 * Parse and validate environment variables with enhanced error handling
 */
let env: z.infer<typeof EnvSchema>

try {
  env = EnvSchema.parse(import.meta.env)

  // Runtime validation logging in development
  if (import.meta.env.DEV) {
    console.info('✅ Environment variables validated successfully')
    console.debug('Environment config:', {
      environment: env.VITE_ENV,
      devtools: env.VITE_ENABLE_DEVTOOLS,
      msw: env.VITE_ENABLE_MSW,
      sentry: !!env.VITE_SENTRY_DSN,
      sampleRate: env.VITE_SENTRY_TRACES_SAMPLE_RATE,
      version: env.VITE_APP_VERSION,
    })
  }
} catch (error) {
  console.error('❌ Environment variable validation failed:', error)
  // In production, we might want to show a user-friendly error
  if (import.meta.env.PROD) {
    console.error('Application configuration error. Please contact support.')
  }
  throw error
}

// Freeze the env object to prevent runtime modifications
Object.freeze(env)

/**
 * Export validated and typed environment variables
 */
export { env }

/**
 * Type-safe environment variables interface
 */
export type Env = typeof env

/**
 * Environment detection utilities
 */
export const isProduction = (): boolean => env.VITE_ENV === 'production'
export const isDevelopment = (): boolean => env.VITE_ENV === 'development'
export const isTest = (): boolean => env.VITE_ENV === 'test'

/**
 * Feature flag utilities
 */
export const isDevtoolsEnabled = (): boolean => env.VITE_ENABLE_DEVTOOLS
export const isMSWEnabled = (): boolean =>
  env.VITE_ENABLE_MSW && isDevelopment()
export const isSentryEnabled = (): boolean => !!env.VITE_SENTRY_DSN

/**
 * Validated API endpoints
 */
export const API_URLS = {
  CORE: env.VITE_CORE_SERVICE_URL,
  PROJECT: env.VITE_PROJECT_SERVICE_URL,
  GENERATION: env.VITE_GENERATION_SERVICE_URL,
} as const

/**
 * 🚨 IMPORTANT SECURITY REMINDERS:
 *
 * 1. NEVER store secrets in VITE_ environment variables
 * 2. All VITE_ variables are bundled into the client code
 * 3. Use server-side environment variables for sensitive data
 * 4. Always validate URLs and sanitize user inputs
 * 5. Consider using different .env files for different environments
 *
 * Examples:
 * - .env.local (local development, git-ignored)
 * - .env.development (development defaults)
 * - .env.production (production defaults)
 * - .env.test (test environment)
 */
