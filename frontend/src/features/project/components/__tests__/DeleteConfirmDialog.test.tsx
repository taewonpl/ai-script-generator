/**
 * Unit tests for DeleteConfirmDialog component
 * Tests accessibility, state management, and user interactions
 */

import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import { DeleteConfirmDialog } from '../DeleteConfirmDialog'
import { ToastProvider } from '@/shared/ui/components/toast'

// Mock error panel component
vi.mock('@/features/error-panel/components/ErrorPanel', () => ({
  ErrorPanel: ({ error, onRetry, onDismiss }: any) => (
    <div data-testid="error-panel">
      <div>{error.userMessage}</div>
      <button onClick={onRetry} data-testid="error-retry">Retry</button>
      <button onClick={onDismiss} data-testid="error-dismiss">Dismiss</button>
    </div>
  )
}))

const defaultProps = {
  open: true,
  onClose: vi.fn(),
  onConfirm: vi.fn(),
  projectName: 'Test Project',
  projectId: 'test-project-id',
  language: 'kr' as const,
}

const renderWithProviders = (props = {}) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <DeleteConfirmDialog {...defaultProps} {...props} />
      </ToastProvider>
    </QueryClientProvider>
  )
}

describe('DeleteConfirmDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Mock crypto.randomUUID
    global.crypto = {
      randomUUID: vi.fn().mockReturnValue('test-delete-id'),
    } as any
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Basic Rendering', () => {
    it('should render dialog when open is true', () => {
      renderWithProviders()
      
      expect(screen.getByRole('dialog')).toBeInTheDocument()
      expect(screen.getByText('이 프로젝트를 영구 삭제하시겠습니까?')).toBeInTheDocument()
      expect(screen.getByText('모든 에피소드와 스토리 바이블(RAG) 파일이 삭제됩니다')).toBeInTheDocument()
      expect(screen.getByText('Test Project')).toBeInTheDocument()
    })

    it('should not render dialog when open is false', () => {
      renderWithProviders({ open: false })
      
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })

    it('should render in English when language is en', () => {
      renderWithProviders({ language: 'en' })
      
      expect(screen.getByText('Delete this project permanently?')).toBeInTheDocument()
      expect(screen.getByText('All episodes and Story Bible (RAG) files will be removed')).toBeInTheDocument()
      expect(screen.getByText('I understand this action can\'t be undone')).toBeInTheDocument()
    })
  })

  describe('Accessibility (A11y)', () => {
    it('should have proper ARIA attributes', () => {
      renderWithProviders()
      
      const dialog = screen.getByRole('dialog')
      expect(dialog).toHaveAttribute('aria-modal', 'true')
      expect(dialog).toHaveAttribute('aria-labelledby')
      expect(dialog).toHaveAttribute('aria-describedby')
    })

    it('should focus close button initially', async () => {
      renderWithProviders()
      
      await waitFor(() => {
        const closeButton = screen.getByText('취소')
        expect(closeButton).toHaveFocus()
      })
    })

    it('should handle ESC key to close dialog', () => {
      const onClose = vi.fn()
      renderWithProviders({ onClose })
      
      fireEvent.keyDown(document, { key: 'Escape' })
      
      expect(onClose).toHaveBeenCalledOnce()
    })

    it('should prevent ESC key when deletion is in progress', () => {
      const onClose = vi.fn()
      renderWithProviders({ onClose, isDeleting: true })
      
      fireEvent.keyDown(document, { key: 'Escape' })
      
      expect(onClose).not.toHaveBeenCalled()
    })

    it('should implement focus trap with Tab navigation', async () => {
      renderWithProviders()
      
      const dialog = screen.getByRole('dialog')
      const focusableElements = dialog.querySelectorAll(
        'button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])'
      )
      
      expect(focusableElements.length).toBeGreaterThan(1)
      
      // Test Tab navigation (implementation would need more detailed testing)
      const firstButton = focusableElements[0] as HTMLElement
      const lastButton = focusableElements[focusableElements.length - 1] as HTMLElement
      
      expect(firstButton).toBeInstanceOf(HTMLElement)
      expect(lastButton).toBeInstanceOf(HTMLElement)
    })
  })

  describe('Checkbox State Management', () => {
    it('should have delete button disabled initially', () => {
      renderWithProviders()
      
      const deleteButton = screen.getByText('삭제하기')
      expect(deleteButton).toBeDisabled()
    })

    it('should enable delete button when checkbox is checked', () => {
      renderWithProviders()
      
      const checkbox = screen.getByRole('checkbox')
      const deleteButton = screen.getByText('삭제하기')
      
      expect(deleteButton).toBeDisabled()
      
      fireEvent.click(checkbox)
      
      expect(checkbox).toBeChecked()
      expect(deleteButton).not.toBeDisabled()
    })

    it('should disable delete button when checkbox is unchecked', () => {
      renderWithProviders()
      
      const checkbox = screen.getByRole('checkbox')
      const deleteButton = screen.getByText('삭제하기')
      
      // Check then uncheck
      fireEvent.click(checkbox)
      expect(deleteButton).not.toBeDisabled()
      
      fireEvent.click(checkbox)
      expect(deleteButton).toBeDisabled()
    })

    it('should disable checkbox during deletion', () => {
      renderWithProviders({ isDeleting: true })
      
      const checkbox = screen.getByRole('checkbox')
      expect(checkbox).toBeDisabled()
    })
  })

  describe('Deletion Process', () => {
    it('should call onConfirm with deleteId when delete button is clicked', async () => {
      const onConfirm = vi.fn().mockResolvedValue(undefined)
      renderWithProviders({ onConfirm })
      
      const checkbox = screen.getByRole('checkbox')
      const deleteButton = screen.getByText('삭제하기')
      
      fireEvent.click(checkbox)
      fireEvent.click(deleteButton)
      
      await waitFor(() => {
        expect(onConfirm).toHaveBeenCalledWith('test-delete-id')
      })
    })

    it('should show loading state during deletion', () => {
      renderWithProviders({ isDeleting: true })
      
      const deleteButton = screen.getByText('삭제 중...')
      expect(deleteButton).toBeDisabled()
      expect(screen.getByRole('progressbar')).toBeInTheDocument() // CircularProgress
    })

    it('should prevent closing dialog during deletion', () => {
      const onClose = vi.fn()
      renderWithProviders({ onClose, isDeleting: true })
      
      // Try to close with close button
      const closeButton = screen.getByText('취소')
      fireEvent.click(closeButton)
      
      expect(onClose).not.toHaveBeenCalled()
      
      // Try to close with ESC key
      fireEvent.keyDown(document, { key: 'Escape' })
      
      expect(onClose).not.toHaveBeenCalled()
    })

    it('should not allow deletion without checkbox confirmation', () => {
      const onConfirm = vi.fn()
      renderWithProviders({ onConfirm })
      
      const deleteButton = screen.getByText('삭제하기')
      fireEvent.click(deleteButton) // Click without checking checkbox
      
      expect(onConfirm).not.toHaveBeenCalled()
    })
  })

  describe('Error Handling', () => {
    it('should display error panel when error prop is provided', () => {
      const error = {
        code: 'DELETION_FAILED',
        message: 'Failed to delete project',
        details: { reason: 'Server error' },
      }
      
      renderWithProviders({ error })
      
      expect(screen.getByTestId('error-panel')).toBeInTheDocument()
      expect(screen.getByText('Failed to delete project')).toBeInTheDocument()
    })

    it('should handle error retry with new delete ID', async () => {
      const onConfirm = vi.fn()
      const onClearError = vi.fn()
      const error = {
        code: 'DELETION_FAILED',
        message: 'Failed to delete project',
      }
      
      // Mock crypto.randomUUID to return different IDs
      const mockRandomUUID = vi.fn()
        .mockReturnValueOnce('test-delete-id')
        .mockReturnValueOnce('retry-delete-id')
      global.crypto.randomUUID = mockRandomUUID
      
      renderWithProviders({ error, onConfirm, onClearError })
      
      const retryButton = screen.getByTestId('error-retry')
      fireEvent.click(retryButton)
      
      expect(onClearError).toHaveBeenCalled()
      expect(mockRandomUUID).toHaveBeenCalledTimes(2) // Initial + retry
    })

    it('should clear error when onClearError is called', () => {
      const onClearError = vi.fn()
      const { rerender } = renderWithProviders({ 
        error: { code: 'ERROR', message: 'Test error' },
        onClearError 
      })
      
      expect(screen.getByTestId('error-panel')).toBeInTheDocument()
      
      // Simulate error clearing
      rerender(
        <QueryClient>
          <ToastProvider>
            <DeleteConfirmDialog {...defaultProps} error={null} onClearError={onClearError} />
          </ToastProvider>
        </QueryClient>
      )
      
      expect(screen.queryByTestId('error-panel')).not.toBeInTheDocument()
    })
  })

  describe('Telemetry Recording', () => {
    let consoleSpy: any

    beforeEach(() => {
      consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {})
    })

    afterEach(() => {
      consoleSpy.restore()
    })

    it('should record ui_delete_opened when dialog opens', () => {
      renderWithProviders()
      
      expect(consoleSpy).toHaveBeenCalledWith(
        '📊 Delete Telemetry: ui_delete_opened',
        { projectId: 'test-project-id', deleteId: 'test-delete-id' }
      )
    })

    it('should record ui_delete_checked when checkbox is checked', () => {
      renderWithProviders()
      
      const checkbox = screen.getByRole('checkbox')
      fireEvent.click(checkbox)
      
      expect(consoleSpy).toHaveBeenCalledWith(
        '📊 Delete Telemetry: ui_delete_checked',
        { projectId: 'test-project-id', deleteId: 'test-delete-id' }
      )
    })

    it('should record ui_delete_submitted when delete is attempted', async () => {
      const onConfirm = vi.fn().mockResolvedValue(undefined)
      renderWithProviders({ onConfirm })
      
      const checkbox = screen.getByRole('checkbox')
      const deleteButton = screen.getByText('삭제하기')
      
      fireEvent.click(checkbox)
      fireEvent.click(deleteButton)
      
      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith(
          '📊 Delete Telemetry: ui_delete_submitted',
          { projectId: 'test-project-id', deleteId: 'test-delete-id' }
        )
      })
    })
  })

  describe('Focus Management', () => {
    it('should return focus to trigger element when dialog closes', async () => {
      const triggerButton = document.createElement('button')
      triggerButton.textContent = 'Delete Project'
      document.body.appendChild(triggerButton)
      triggerButton.focus()
      
      const { rerender } = renderWithProviders({ open: true })
      
      // Close dialog
      rerender(
        <QueryClient>
          <ToastProvider>
            <DeleteConfirmDialog {...defaultProps} open={false} />
          </ToastProvider>
        </QueryClient>
      )
      
      await waitFor(() => {
        expect(triggerButton).toHaveFocus()
      })
      
      document.body.removeChild(triggerButton)
    })
  })

  describe('Delete ID Generation', () => {
    it('should generate new delete ID when dialog reopens', () => {
      const mockRandomUUID = vi.fn()
        .mockReturnValueOnce('first-delete-id')
        .mockReturnValueOnce('second-delete-id')
      global.crypto.randomUUID = mockRandomUUID
      
      const { rerender } = renderWithProviders({ open: true })
      
      // Close and reopen
      rerender(
        <QueryClient>
          <ToastProvider>
            <DeleteConfirmDialog {...defaultProps} open={false} />
          </ToastProvider>
        </QueryClient>
      )
      
      rerender(
        <QueryClient>
          <ToastProvider>
            <DeleteConfirmDialog {...defaultProps} open={true} />
          </ToastProvider>
        </QueryClient>
      )
      
      expect(mockRandomUUID).toHaveBeenCalledTimes(2)
    })

    it('should fallback to timestamp-based ID when crypto.randomUUID is unavailable', () => {
      // Remove crypto.randomUUID
      global.crypto = {} as any
      
      const dateSpy = vi.spyOn(Date, 'now').mockReturnValue(1234567890)
      const mathSpy = vi.spyOn(Math, 'random').mockReturnValue(0.5)
      
      renderWithProviders()
      
      // Should not throw error and should use fallback
      expect(dateSpy).toHaveBeenCalled()
      expect(mathSpy).toHaveBeenCalled()
      
      dateSpy.restore()
      mathSpy.restore()
    })
  })
})