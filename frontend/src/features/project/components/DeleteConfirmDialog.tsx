/**
 * Production-grade Delete Confirmation Dialog with A11y
 * Handles project deletion with idempotency, business logic guards, and accessibility
 */

import { useState, useEffect, useRef, useCallback } from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Checkbox,
  FormControlLabel,
  Alert,
  Box,
  CircularProgress,
} from '@mui/material'
import {
  DeleteForever as DeleteIcon,
  Warning as WarningIcon,
} from '@mui/icons-material'

// import { useToastHelpers } from '@/shared/ui/components/toast' // Reserved for future use
import { ErrorPanel } from '@/features/error-panel/components/ErrorPanel'
import { useErrorPanel } from '@/features/error-panel/hooks/useErrorPanel'
import type { ApiError } from '@/shared/api/types'

export interface DeleteConfirmDialogProps {
  /** Whether the dialog is open */
  open: boolean
  /** Function to close the dialog */
  onClose: () => void
  /** Function called when deletion is confirmed */
  onConfirm: (deleteId: string) => Promise<void>
  /** Project name to display in dialog */
  projectName: string
  /** Project ID for logging */
  projectId: string
  /** Language for UI text */
  language?: 'kr' | 'en'
  /** Whether deletion is currently in progress */
  isDeleting?: boolean
  /** Error that occurred during deletion */
  error?: ApiError | null
  /** Clear error state */
  onClearError?: () => void
}

/**
 * Production-grade delete confirmation dialog with comprehensive A11y support
 */
export function DeleteConfirmDialog({
  open,
  onClose,
  onConfirm,
  projectName,
  projectId,
  language = 'kr',
  isDeleting = false,
  error = null,
  onClearError,
}: DeleteConfirmDialogProps) {
  const [isConfirmed, setIsConfirmed] = useState(false)
  const [deleteId, setDeleteId] = useState<string>('')
  // const { showSuccess } = useToastHelpers() // Reserved for future use
  
  // Focus management refs
  const dialogRef = useRef<HTMLDivElement>(null)
  const closeButtonRef = useRef<HTMLButtonElement>(null)
  const deleteButtonRef = useRef<HTMLButtonElement>(null)
  const checkboxRef = useRef<HTMLInputElement>(null)
  
  // Track trigger element for focus return
  const triggerElementRef = useRef<Element | null>(null)
  
  // Error panel for handling deletion failures
  const errorPanel = useErrorPanel({
    language,
    autoShow: false, // We'll show manually
    showInToast: false,
    retryConfig: {
      maxRetries: 3,
      baseDelay: 2000,
      exponentialBackoff: true,
      jitter: true,
    },
  })

  // Generate new delete ID when dialog opens
  useEffect(() => {
    if (open) {
      setDeleteId(crypto.randomUUID?.() || `del-${Date.now()}-${Math.random()}`)
      setIsConfirmed(false)
      
      // Store the currently focused element for return
      triggerElementRef.current = document.activeElement
      
      // Record telemetry
      recordTelemetry('ui_delete_opened', { projectId, deleteId })
    } else {
      // Return focus to trigger element when dialog closes
      if (triggerElementRef.current && (triggerElementRef.current as HTMLElement).focus) {
        (triggerElementRef.current as HTMLElement).focus()
      }
      triggerElementRef.current = null
    }
  }, [open, projectId])

  // Focus trap implementation
  useEffect(() => {
    if (!open) return

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        handleClose()
      }
      
      if (event.key === 'Tab') {
        const focusableElements = dialogRef.current?.querySelectorAll(
          'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
        )
        
        if (!focusableElements || focusableElements.length === 0) return
        
        const firstFocusable = focusableElements[0] as HTMLElement
        const lastFocusable = focusableElements[focusableElements.length - 1] as HTMLElement
        
        if (event.shiftKey) {
          // Shift + Tab
          if (document.activeElement === firstFocusable) {
            event.preventDefault()
            lastFocusable.focus()
          }
        } else {
          // Tab
          if (document.activeElement === lastFocusable) {
            event.preventDefault()
            firstFocusable.focus()
          }
        }
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    
    // Initial focus on close button for safety
    setTimeout(() => closeButtonRef.current?.focus(), 100)
    
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [open])

  // Handle checkbox change
  const handleCheckboxChange = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const checked = event.target.checked
    setIsConfirmed(checked)
    
    if (checked) {
      recordTelemetry('ui_delete_checked', { projectId, deleteId })
    }
  }, [projectId, deleteId])

  // Handle close
  const handleClose = useCallback(() => {
    if (isDeleting) return // Prevent closing during deletion
    onClose()
  }, [isDeleting, onClose])

  // Handle deletion confirmation
  const handleDelete = useCallback(async () => {
    if (!isConfirmed || isDeleting) return
    
    recordTelemetry('ui_delete_submitted', { projectId, deleteId })
    
    try {
      await onConfirm(deleteId)
      recordTelemetry('ui_delete_success', { projectId, deleteId })
    } catch (err) {
      const apiError = err as ApiError
      recordTelemetry('ui_delete_failed', { 
        projectId, 
        deleteId, 
        errorType: apiError.code || 'unknown' 
      })
      
      // Let parent component handle the error display
    }
  }, [isConfirmed, isDeleting, onConfirm, projectId, deleteId])

  // Handle error display
  useEffect(() => {
    if (error) {
      const errorDetails = {
        error_type: 'delete_failed' as const,
        http_status: (error as any)?.status || 500,
        hint: language === 'kr' 
          ? '프로젝트 삭제 중 오류가 발생했습니다.'
          : 'An error occurred while deleting the project.',
        timestamp: new Date().toISOString(),
        userMessage: error.message || (language === 'kr' ? '삭제 실패' : 'Deletion failed'),
        technicalMessage: error.details ? JSON.stringify(error.details) : error.message,
        retryable: true,
        context: {
          projectId,
          projectName,
          deleteId,
          errorCode: error.code,
        },
      }
      
      errorPanel.showError(errorDetails, async () => {
        onClearError?.()
        // Generate new delete ID for retry
        setDeleteId(crypto.randomUUID?.() || `del-${Date.now()}-${Math.random()}`)
        await handleDelete()
      })
    } else if (errorPanel.isVisible) {
      errorPanel.hideError()
    }
  }, [error, errorPanel, language, projectId, projectName, deleteId, onClearError, handleDelete])

  // Text content based on language
  const text = {
    title: language === 'kr' 
      ? '이 프로젝트를 영구 삭제하시겠습니까?' 
      : 'Delete this project permanently?',
    description: language === 'kr'
      ? '모든 에피소드와 스토리 바이블(RAG) 파일이 삭제됩니다'
      : 'All episodes and Story Bible (RAG) files will be removed',
    projectLabel: language === 'kr' ? '프로젝트' : 'Project',
    checkboxLabel: language === 'kr'
      ? '이 작업은 되돌릴 수 없음을 확인합니다'
      : 'I understand this action can\'t be undone',
    cancelButton: language === 'kr' ? '취소' : 'Cancel',
    deleteButton: language === 'kr' ? '삭제하기' : 'Delete',
    deletingButton: language === 'kr' ? '삭제 중...' : 'Deleting...',
  }

  const titleId = `delete-dialog-title-${projectId}`
  const descId = `delete-dialog-desc-${projectId}`

  return (
    <>
      {/* Error Panel - outside dialog to avoid z-index issues */}
      {errorPanel.isVisible && errorPanel.error && (
        <ErrorPanel
          error={errorPanel.error}
          onRetry={errorPanel.currentRetryFn}
          onDismiss={errorPanel.hideError}
          language={language}
          compact={false}
          showTechnicalDetails={true}
        />
      )}

      <Dialog
        ref={dialogRef}
        open={open}
        onClose={handleClose}
        maxWidth="sm"
        fullWidth
        disableEscapeKeyDown={isDeleting}
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descId}
        PaperProps={{
          sx: {
            borderRadius: 2,
            boxShadow: 24,
          },
        }}
      >
        <DialogTitle id={titleId} sx={{ pb: 1 }}>
          <Box display="flex" alignItems="center" gap={1}>
            <WarningIcon color="error" />
            <Typography variant="h6" component="span" color="error.main">
              {text.title}
            </Typography>
          </Box>
        </DialogTitle>

        <DialogContent>
          <Box display="flex" flexDirection="column" gap={2}>
            {/* Project info */}
            <Alert severity="warning" variant="outlined">
              <Typography variant="body2" id={descId}>
                {text.description}
              </Typography>
            </Alert>

            <Box sx={{ 
              p: 2, 
              backgroundColor: 'grey.50', 
              borderRadius: 1,
              border: '1px solid',
              borderColor: 'grey.300',
            }}>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                {text.projectLabel}:
              </Typography>
              <Typography variant="h6" sx={{ wordBreak: 'break-word' }}>
                {projectName}
              </Typography>
            </Box>

            {/* Confirmation checkbox */}
            <FormControlLabel
              control={
                <Checkbox
                  inputRef={checkboxRef}
                  checked={isConfirmed}
                  onChange={handleCheckboxChange}
                  disabled={isDeleting}
                  color="error"
                />
              }
              label={
                <Typography variant="body2" color="text.primary">
                  {text.checkboxLabel}
                </Typography>
              }
              sx={{ mt: 1 }}
            />
          </Box>
        </DialogContent>

        <DialogActions sx={{ p: 3, pt: 1 }}>
          <Button
            ref={closeButtonRef}
            onClick={handleClose}
            disabled={isDeleting}
            variant="outlined"
            size="large"
          >
            {text.cancelButton}
          </Button>
          
          <Button
            ref={deleteButtonRef}
            onClick={handleDelete}
            disabled={!isConfirmed || isDeleting}
            color="error"
            variant="contained"
            size="large"
            startIcon={
              isDeleting ? (
                <CircularProgress size={16} color="inherit" />
              ) : (
                <DeleteIcon />
              )
            }
            sx={{
              minWidth: 120,
              '&.Mui-disabled': {
                backgroundColor: 'action.disabledBackground',
                color: 'text.disabled',
              },
            }}
          >
            {isDeleting ? text.deletingButton : text.deleteButton}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  )
}

/**
 * Record telemetry for delete operations
 */
function recordTelemetry(event: string, data: Record<string, any>) {
  if (import.meta.env.DEV) {
    console.log(`📊 Delete Telemetry: ${event}`, data)
  }
  
  // In production, this would send to analytics service
  // Example: analytics.track(event, data)
}

export default DeleteConfirmDialog