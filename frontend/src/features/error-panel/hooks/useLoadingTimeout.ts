/**
 * Hook for loading with timeout logic
 */

import { useState, useEffect } from 'react'

/**
 * Hook for loading with timeout logic
 */
export function useLoadingTimeout(
  isLoading: boolean,
  timeoutDelay: number = 8000
) {
  const [hasTimedOut, setHasTimedOut] = useState(false)

  useEffect(() => {
    if (!isLoading) {
      setHasTimedOut(false)
      return
    }

    const timer = setTimeout(() => {
      if (isLoading) {
        setHasTimedOut(true)
      }
    }, timeoutDelay)

    return () => clearTimeout(timer)
  }, [isLoading, timeoutDelay])

  return { hasTimedOut }
}