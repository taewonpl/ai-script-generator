/**
 * Loading component with timeout warning
 * Shows skeleton after 200ms, timeout warning after 8s with retry option
 */

import { useState, useEffect, useCallback } from 'react'
import {
  Box,
  Skeleton,
  Alert,
  Button,
  Typography,
  LinearProgress,
} from '@mui/material'
import { Refresh as RefreshIcon } from '@mui/icons-material'

import { getMessage } from '../i18n/errorMessages'
import type { Language } from '../i18n/errorMessages'

interface LoadingWithTimeoutProps {
  isLoading: boolean
  onRetry?: () => void
  language?: Language
  skeletonDelay?: number  // Default: 200ms
  timeoutDelay?: number   // Default: 8000ms (8s)
  children?: React.ReactNode
  skeletonRows?: number
  className?: string
}

/**
 * LoadingWithTimeout - Shows skeleton loading then timeout warning
 */
export function LoadingWithTimeout({
  isLoading,
  onRetry,
  language = 'ko',
  skeletonDelay = 200,
  timeoutDelay = 8000,
  children,
  skeletonRows = 3,
  className,
}: LoadingWithTimeoutProps) {
  const [showSkeleton, setShowSkeleton] = useState(false)
  const [showTimeout, setShowTimeout] = useState(false)

  // Reset state when loading changes
  useEffect(() => {
    if (!isLoading) {
      setShowSkeleton(false)
      setShowTimeout(false)
      return
    }

    // Show skeleton after delay
    const skeletonTimer = setTimeout(() => {
      if (isLoading) {
        setShowSkeleton(true)
      }
    }, skeletonDelay)

    // Show timeout warning after longer delay
    const timeoutTimer = setTimeout(() => {
      if (isLoading) {
        setShowTimeout(true)
      }
    }, timeoutDelay)

    return () => {
      clearTimeout(skeletonTimer)
      clearTimeout(timeoutTimer)
    }
  }, [isLoading, skeletonDelay, timeoutDelay])

  const handleRetry = useCallback(() => {
    setShowTimeout(false)
    setShowSkeleton(false)
    if (onRetry) {
      onRetry()
    }
  }, [onRetry])

  // Not loading - show content
  if (!isLoading) {
    return <>{children}</>
  }

  return (
    <Box className={className}>
      {/* Timeout warning */}
      {showTimeout && (
        <Alert 
          severity="info" 
          sx={{ mb: 2 }}
          action={
            onRetry && (
              <Button
                color="inherit"
                size="small"
                startIcon={<RefreshIcon />}
                onClick={handleRetry}
              >
                {getMessage('error.button.retry', language)}
              </Button>
            )
          }
        >
          {getMessage('error.longwait', language)}
        </Alert>
      )}

      {/* Progress indicator */}
      {showTimeout && (
        <Box sx={{ mb: 2 }}>
          <LinearProgress />
        </Box>
      )}

      {/* Skeleton loading */}
      {showSkeleton && (
        <Box>
          {Array.from({ length: skeletonRows }, (_, index) => (
            <Skeleton
              key={index}
              variant="rectangular"
              height={60}
              sx={{ 
                mb: 1,
                borderRadius: 1,
                // Vary the width for more realistic skeleton
                width: index === skeletonRows - 1 ? '60%' : '100%',
              }}
            />
          ))}
        </Box>
      )}

      {/* Additional loading indicator if no skeleton shown yet */}
      {!showSkeleton && (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
          <Typography variant="body2" color="textSecondary">
            {language === 'en' ? 'Loading...' : '로딩 중...'}
          </Typography>
        </Box>
      )}
    </Box>
  )
}

export default LoadingWithTimeout