/**
 * Episode Commit Button with production-grade state management
 * Handles positive feedback submission with idempotency and UX
 */

import { useState, useCallback, useEffect } from 'react'
import {
  Button,
  Tooltip,
  CircularProgress,
  Box,
} from '@mui/material'
import {
  CheckCircle as CommitIcon,
  Block as BlockedIcon,
} from '@mui/icons-material'

import { useToastHelpers } from '@/shared/ui/components/toast'
import { ErrorPanel } from '@/features/error-panel/components/ErrorPanel'
import { useErrorPanel } from '@/features/error-panel/hooks/useErrorPanel'
import { submitBehaviorFeedback, generateCommitId } from '@/shared/services/api/feedback'
import type { ApiError } from '@/shared/api/types'
import { commitMetrics } from '@/shared/services/metrics/commitMetrics'

export interface CommitButtonProps {
  projectId: string
  episodeId: string
  /** Whether SSE generation is currently in progress */
  isGenerating: boolean
  /** Whether there are unsaved changes in the editor */
  hasUnsavedChanges: boolean
  /** Callback when commit is successful */
  onCommitSuccess: (commitId: string, timestamp: string) => void
  /** Callback when commit fails */
  onCommitError?: (error: ApiError) => void
  /** Language for UI text */
  language?: 'kr' | 'en'
  /** Custom className */
  className?: string
  /** Show in compact mode */
  compact?: boolean
}

/**
 * Commit button for episode editor with production-grade state management
 */
export function CommitButton({
  projectId,
  episodeId,
  isGenerating,
  hasUnsavedChanges,
  onCommitSuccess,
  onCommitError,
  language = 'kr',
  className,
  compact = false,
}: CommitButtonProps) {
  const [isCommitting, setIsCommitting] = useState(false)
  const [currentCommitId, setCurrentCommitId] = useState<string | null>(null)
  const { showSuccess } = useToastHelpers()
  
  // Error panel for handling commit failures
  const errorPanel = useErrorPanel({
    language,
    autoShow: true,
    showInToast: false,
    retryConfig: {
      maxRetries: 3,
      baseDelay: 2000,
      exponentialBackoff: true,
      jitter: true,
    },
  })

  // Button state logic
  const isDisabled = isGenerating || hasUnsavedChanges || isCommitting
  
  // Tooltip messages based on state
  const getTooltipMessage = useCallback(() => {
    if (isCommitting) {
      return language === 'kr' ? '확정 중...' : 'Committing...'
    }
    if (isGenerating) {
      return language === 'kr' ? '생성 중에는 확정할 수 없습니다' : 'Cannot commit during generation'
    }
    if (hasUnsavedChanges) {
      return language === 'kr' ? '먼저 저장하세요' : 'Please save first'
    }
    return language === 'kr' ? '이 버전을 골든 데이터셋에 확정합니다' : 'Commit this version to golden dataset'
  }, [isCommitting, isGenerating, hasUnsavedChanges, language])

  // Button text
  const buttonText = language === 'kr' ? '확정하기(+1)' : 'Commit this version (+1)'

  // Handle commit submission
  const handleCommit = useCallback(async () => {
    if (isDisabled) return
    
    // Start metrics timer
    const timer = commitMetrics.startCommitTimer()
    
    try {
      setIsCommitting(true)
      
      // Generate new commit ID to prevent double-click issues
      const commitId = generateCommitId()
      setCurrentCommitId(commitId)
      
      // Use the hardened feedback submission
      const response = await submitBehaviorFeedback(
        'commit_positive',
        projectId,
        episodeId,
        undefined, // No behavior context for simple commits
        undefined  // No additional content data
      )
      const latency = timer.stopTimer(true, !response.stored)
      
      if (response.stored) {
        // Success - commit was stored
        commitMetrics.recordCommitSuccess(episodeId, projectId, latency, false)
        
        const successMessage = language === 'kr' 
          ? '확정되었습니다. 골든 데이터셋에 포함됩니다'
          : 'Committed successfully. Included in golden dataset'
        
        showSuccess(successMessage)
        onCommitSuccess(response.commit_id, response.timestamp)
        
        // Hide any previous errors
        if (errorPanel.isVisible) {
          errorPanel.hideError()
        }
      } else {
        // Duplicate commit - show info message
        commitMetrics.recordCommitSuccess(episodeId, projectId, latency, true)
        
        const duplicateMessage = language === 'kr'
          ? '이미 확정된 버전입니다'
          : 'This version is already committed'
        
        showSuccess(duplicateMessage) // Using success toast for duplicate (not an error)
      }
      
    } catch (error) {
      const latency = timer.stopTimer(false)
      console.error('Commit submission failed:', error)
      
      const apiError = error as ApiError
      
      // Record metrics based on error type (assume status from HTTP response)
      const httpStatus = (error as any)?.status || 500
      let errorType: 'rate_limited' | 'validation_failed' | 'server_error' = 'server_error'
      if (httpStatus === 429) {
        errorType = 'rate_limited'
      } else if (httpStatus === 400 || httpStatus === 404) {
        errorType = 'validation_failed'
      }
      
      commitMetrics.recordCommitFailure(episodeId, projectId, errorType, latency)
      
      // Show error panel with retry capability
      const errorDetails = {
        error_type: 'commit_failed' as const,
        http_status: httpStatus,
        hint: language === 'kr' 
          ? '확정 중 오류가 발생했습니다. 다시 시도해주세요.'
          : 'Failed to commit. Please try again.',
        timestamp: new Date().toISOString(),
        userMessage: apiError.message || (language === 'kr' ? '확정 실패' : 'Commit failed'),
        technicalMessage: apiError.details ? JSON.stringify(apiError.details) : apiError.message,
        retryable: true,
        context: {
          projectId,
          episodeId,
          commitId: currentCommitId,
          errorCode: apiError.code,
          latency,
        },
      }
      
      errorPanel.showError(errorDetails, async () => {
        // Retry with new commit ID to avoid duplicate issues
        setCurrentCommitId(null)
        await handleCommit()
      })
      
      onCommitError?.(apiError)
      
    } finally {
      setIsCommitting(false)
    }
  }, [
    isDisabled,
    projectId,
    episodeId,
    currentCommitId,
    language,
    showSuccess,
    onCommitSuccess,
    onCommitError,
    errorPanel,
  ])

  // Keyboard shortcut: Cmd/Ctrl + Enter
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
        event.preventDefault()
        handleCommit()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleCommit])

  return (
    <Box className={className}>
      {/* Error Panel */}
      {errorPanel.isVisible && errorPanel.error && (
        <Box mb={2}>
          <ErrorPanel
            error={errorPanel.error}
            onRetry={errorPanel.currentRetryFn}
            onDismiss={errorPanel.hideError}
            language={language}
            compact={compact}
            showTechnicalDetails={true}
          />
        </Box>
      )}

      {/* Commit Button */}
      <Tooltip title={getTooltipMessage()}>
        <span>
          <Button
            variant="contained"
            color="primary"
            onClick={handleCommit}
            disabled={isDisabled}
            startIcon={
              isCommitting ? (
                <CircularProgress size={16} color="inherit" />
              ) : isDisabled ? (
                <BlockedIcon />
              ) : (
                <CommitIcon />
              )
            }
            size={compact ? 'small' : 'medium'}
            sx={{
              minWidth: compact ? 120 : 160,
              fontWeight: 600,
              '&.Mui-disabled': {
                backgroundColor: 'action.disabledBackground',
                color: 'text.disabled',
              },
              '&:not(.Mui-disabled)': {
                backgroundColor: 'success.main',
                '&:hover': {
                  backgroundColor: 'success.dark',
                },
              },
            }}
          >
            {isCommitting ? (
              language === 'kr' ? '확정 중...' : 'Committing...'
            ) : (
              buttonText
            )}
          </Button>
        </span>
      </Tooltip>
    </Box>
  )
}

export default CommitButton