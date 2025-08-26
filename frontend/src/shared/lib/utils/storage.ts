/**
 * Safe localStorage wrapper with error handling
 */
export const storage = {
  get: <T>(key: string, defaultValue?: T): T | null => {
    try {
      const item = localStorage.getItem(key)
      if (item === null) return defaultValue ?? null
      return JSON.parse(item)
    } catch {
      return defaultValue ?? null
    }
  },

  set: <T>(key: string, value: T): void => {
    try {
      localStorage.setItem(key, JSON.stringify(value))
    } catch {
      // Handle localStorage quota exceeded or other errors
      console.warn(`Failed to save to localStorage: ${key}`)
    }
  },

  remove: (key: string): void => {
    try {
      localStorage.removeItem(key)
    } catch {
      console.warn(`Failed to remove from localStorage: ${key}`)
    }
  },

  clear: (): void => {
    try {
      localStorage.clear()
    } catch {
      console.warn('Failed to clear localStorage')
    }
  },
}

/**
 * Session storage wrapper
 */
export const sessionStorage = {
  get: <T>(key: string, defaultValue?: T): T | null => {
    try {
      const item = window.sessionStorage.getItem(key)
      if (item === null) return defaultValue ?? null
      return JSON.parse(item)
    } catch {
      return defaultValue ?? null
    }
  },

  set: <T>(key: string, value: T): void => {
    try {
      window.sessionStorage.setItem(key, JSON.stringify(value))
    } catch {
      console.warn(`Failed to save to sessionStorage: ${key}`)
    }
  },

  remove: (key: string): void => {
    try {
      window.sessionStorage.removeItem(key)
    } catch {
      console.warn(`Failed to remove from sessionStorage: ${key}`)
    }
  },
}
