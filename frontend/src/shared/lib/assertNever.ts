/**
 * Exhaustiveness check utility for TypeScript discriminated unions
 * 
 * This function ensures compile-time safety by catching cases where
 * a discriminated union is not fully handled. If all cases are covered,
 * TypeScript will infer the parameter as `never`, making the function safe.
 * If a case is missed, TypeScript will show a compile error.
 * 
 * @param x - Should be `never` if all union cases are handled
 * @throws Error with details about the unhandled case
 * @returns never (function always throws)
 * 
 * @example
 * ```typescript
 * function handleEvent(event: SSEEventData) {
 *   if (isProgressEvent(event)) {
 *     // handle progress
 *   } else if (isCompletedEvent(event)) {
 *     // handle completed
 *   } else {
 *     // If we add a new event type but forget to handle it,
 *     // TypeScript will error here because event is not `never`
 *     assertNever(event)
 *   }
 * }
 * ```
 */
export function assertNever(x: never): never {
  throw new Error(
    `Unhandled discriminated union case. This should never happen at runtime. ` +
    `If you see this error, a new case was added to the union but not handled in the switch/if statements. ` +
    `Case details: ${JSON.stringify(x)}`
  )
}

/**
 * Alternative exhaustiveness check for switch statements
 * More descriptive error messages for switch case scenarios
 * 
 * @param value - The unhandled union value
 * @param context - Description of where this occurred
 * @throws Error with context about the unhandled switch case
 * @returns never
 * 
 * @example
 * ```typescript
 * switch (event.type) {
 *   case 'progress':
 *     return handleProgress(event)
 *   case 'completed':
 *     return handleCompleted(event)
 *   default:
 *     return assertUnreachable(event, 'SSE event handler')
 * }
 * ```
 */
export function assertUnreachable(value: never, context = 'switch statement'): never {
  throw new Error(
    `Unreachable code in ${context}. This indicates a missing case in a discriminated union. ` +
    `Add handling for: ${JSON.stringify(value)}`
  )
}

/**
 * Development-only exhaustiveness check
 * Only throws in development, logs warning in production
 * Use when you want graceful degradation instead of crashes
 * 
 * @param x - Should be `never` if all cases are handled
 * @param fallback - Optional fallback value to return in production
 * @returns never in dev, fallback value in production
 */
export function assertNeverDev<T = void>(x: never, fallback?: T): T {
  const error = new Error(
    `Development exhaustiveness check failed: ${JSON.stringify(x)}`
  )
  
  if (import.meta.env.DEV) {
    throw error
  } else {
    // Production: log but don't crash
    console.error('Exhaustiveness check failed (would crash in dev):', error)
    return fallback as T
  }
}