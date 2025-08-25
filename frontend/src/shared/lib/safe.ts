/**
 * Safe type conversion utilities to prevent undefined/null assignment errors
 */

export function ensureString(v: unknown, fallback = ''): string {
  return typeof v === 'string' ? v : fallback;
}

export function ensureNumber(v: unknown, fallback = 0): number {
  return typeof v === 'number' && Number.isFinite(v) ? v : fallback;
}

export function pickFirstString(...vals: (unknown)[]): string {
  for (const v of vals) {
    if (typeof v === 'string' && v.length > 0) {
      return v;
    }
  }
  return '';
}

export function ensureBoolean(v: unknown, fallback = false): boolean {
  return typeof v === 'boolean' ? v : fallback;
}

export function safeParseInt(v: unknown, fallback = 0): number {
  if (typeof v === 'number') return Math.floor(v);
  if (typeof v === 'string') {
    const parsed = parseInt(v, 10);
    return Number.isNaN(parsed) ? fallback : parsed;
  }
  return fallback;
}

/**
 * Safely access nested object properties
 */
export function safeGet<T>(obj: unknown, path: string, fallback: T): T {
  if (!obj || typeof obj !== 'object') return fallback;
  
  const keys = path.split('.');
  let current: any = obj;
  
  for (const key of keys) {
    if (current == null || typeof current !== 'object' || !(key in current)) {
      return fallback;
    }
    current = current[key];
  }
  
  return current ?? fallback;
}