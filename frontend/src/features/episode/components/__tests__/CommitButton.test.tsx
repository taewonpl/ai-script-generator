/**
 * Unit tests for CommitButton component
 * Tests state logic, user interactions, and error handling
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import { CommitButton } from '../CommitButton'
import * as feedbackApi from '@/shared/services/api/feedback'
import * as commitMetrics from '@/shared/services/metrics/commitMetrics'
import { ToastProvider } from '@/shared/ui/components/toast'

// Mock dependencies
vi.mock('@/shared/services/api/feedback')
vi.mock('@/shared/services/metrics/commitMetrics')
vi.mock('@/features/error-panel/components/ErrorPanel', () => ({
  ErrorPanel: ({ error, onRetry, onDismiss }: any) => (
    <div data-testid="error-panel">
      <div>{error.userMessage}</div>
      <button onClick={onRetry} data-testid="retry-button">Retry</button>
      <button onClick={onDismiss} data-testid="dismiss-button">Dismiss</button>
    </div>
  )
}))

const mockSubmitFeedback = vi.mocked(feedbackApi.submitFeedback)
const mockGenerateCommitId = vi.mocked(feedbackApi.generateCommitId)
const mockCommitMetrics = vi.mocked(commitMetrics.commitMetrics)

const defaultProps = {
  projectId: 'test-project-id',
  episodeId: 'test-episode-id',
  isGenerating: false,
  hasUnsavedChanges: false,
  onCommitSuccess: vi.fn(),
  onCommitError: vi.fn(),
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
        <CommitButton {...defaultProps} {...props} />
      </ToastProvider>
    </QueryClientProvider>
  )
}

describe('CommitButton', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGenerateCommitId.mockReturnValue('test-commit-id')
    mockCommitMetrics.startCommitTimer.mockReturnValue({
      stopTimer: vi.fn().mockReturnValue(150) // 150ms latency
    })
  })

  describe('Button States', () => {
    it('should be enabled when no blocking conditions exist', () => {
      renderWithProviders()
      
      const button = screen.getByRole('button', { name: /확정하기/i })
      expect(button).not.toBeDisabled()
    })

    it('should be disabled when generation is in progress', () => {
      renderWithProviders({ isGenerating: true })
      
      const button = screen.getByRole('button', { name: /확정하기/i })
      expect(button).toBeDisabled()
    })

    it('should be disabled when there are unsaved changes', () => {
      renderWithProviders({ hasUnsavedChanges: true })
      
      const button = screen.getByRole('button', { name: /확정하기/i })
      expect(button).toBeDisabled()
    })

    it('should show correct tooltip for different states', async () => {
      const { rerender } = renderWithProviders()
      
      // Normal state
      let button = screen.getByRole('button', { name: /확정하기/i })
      fireEvent.mouseOver(button)
      await waitFor(() => {
        expect(screen.getByText(/이 버전을 골든 데이터셋에 확정합니다/)).toBeInTheDocument()
      })

      // Generation in progress
      rerender(
        <QueryClientProvider client={new QueryClient()}>
          <ToastProvider>
            <CommitButton {...defaultProps} isGenerating={true} />
          </ToastProvider>
        </QueryClientProvider>
      )
      
      button = screen.getByRole('button', { name: /확정하기/i })
      fireEvent.mouseOver(button)
      await waitFor(() => {
        expect(screen.getByText(/생성 중에는 확정할 수 없습니다/)).toBeInTheDocument()
      })

      // Unsaved changes
      rerender(
        <QueryClientProvider client={new QueryClient()}>
          <ToastProvider>
            <CommitButton {...defaultProps} hasUnsavedChanges={true} />
          </ToastProvider>
        </QueryClientProvider>
      )
      
      button = screen.getByRole('button', { name: /확정하기/i })
      fireEvent.mouseOver(button)
      await waitFor(() => {
        expect(screen.getByText(/먼저 저장하세요/)).toBeInTheDocument()
      })
    })
  })

  describe('Successful Commits', () => {
    it('should handle successful commit', async () => {
      const onCommitSuccess = vi.fn()
      mockSubmitFeedback.mockResolvedValue({
        stored: true,
        commit_id: 'test-commit-id',
        timestamp: '2024-01-01T10:00:00Z',
        request_id: 'req-1',
        trace_id: 'trace-1'
      })

      renderWithProviders({ onCommitSuccess })
      
      const button = screen.getByRole('button', { name: /확정하기/i })
      fireEvent.click(button)

      // Should show loading state
      await waitFor(() => {
        expect(screen.getByText(/확정 중.../)).toBeInTheDocument()
      })

      // Should complete successfully
      await waitFor(() => {
        expect(onCommitSuccess).toHaveBeenCalledWith('test-commit-id', '2024-01-01T10:00:00Z')
      })

      // Should record success metrics
      expect(mockCommitMetrics.recordCommitSuccess).toHaveBeenCalledWith(
        'test-episode-id',
        'test-project-id',
        150,
        false
      )
    })

    it('should handle duplicate commit', async () => {
      const onCommitSuccess = vi.fn()
      mockSubmitFeedback.mockResolvedValue({
        stored: false,
        commit_id: 'test-commit-id',
        timestamp: '2024-01-01T10:00:00Z',
        request_id: 'req-1',
        trace_id: 'trace-1'
      })

      renderWithProviders({ onCommitSuccess })
      
      const button = screen.getByRole('button', { name: /확정하기/i })
      fireEvent.click(button)

      await waitFor(() => {
        expect(mockCommitMetrics.recordCommitSuccess).toHaveBeenCalledWith(
          'test-episode-id',
          'test-project-id',
          150,
          true // isDuplicate
        )
      })
    })
  })

  describe('Error Handling', () => {
    it('should handle rate limiting error', async () => {
      const rateLimitError = {
        status: 429,
        code: 'RATE_LIMITED',
        message: 'Rate limit exceeded',
        detail: 'Please wait 2.1 seconds'
      }
      
      mockSubmitFeedback.mockRejectedValue(rateLimitError)

      renderWithProviders()
      
      const button = screen.getByRole('button', { name: /확정하기/i })
      fireEvent.click(button)

      await waitFor(() => {
        expect(screen.getByTestId('error-panel')).toBeInTheDocument()
        expect(screen.getByText(/확정 실패/)).toBeInTheDocument()
      })

      // Should record failure metrics
      expect(mockCommitMetrics.recordCommitFailure).toHaveBeenCalledWith(
        'test-episode-id',
        'test-project-id',
        'rate_limited',
        150
      )
    })

    it('should handle validation error', async () => {
      const validationError = {
        status: 404,
        code: 'PROJECT_NOT_FOUND',
        message: 'Project does not exist'
      }
      
      mockSubmitFeedback.mockRejectedValue(validationError)

      renderWithProviders()
      
      const button = screen.getByRole('button', { name: /확정하기/i })
      fireEvent.click(button)

      await waitFor(() => {
        expect(mockCommitMetrics.recordCommitFailure).toHaveBeenCalledWith(
          'test-episode-id',
          'test-project-id',
          'validation_failed',
          150
        )
      })
    })

    it('should handle server error', async () => {
      const serverError = {
        status: 500,
        code: 'INTERNAL_ERROR',
        message: 'Internal server error'
      }
      
      mockSubmitFeedback.mockRejectedValue(serverError)

      renderWithProviders()
      
      const button = screen.getByRole('button', { name: /확정하기/i })
      fireEvent.click(button)

      await waitFor(() => {
        expect(mockCommitMetrics.recordCommitFailure).toHaveBeenCalledWith(
          'test-episode-id',
          'test-project-id',
          'server_error',
          150
        )
      })
    })

    it('should allow retry with new commit ID', async () => {
      let callCount = 0
      mockSubmitFeedback.mockImplementation(() => {
        callCount++
        if (callCount === 1) {
          return Promise.reject({ status: 500, message: 'Server error' })
        }
        return Promise.resolve({
          stored: true,
          commit_id: 'new-commit-id',
          timestamp: '2024-01-01T10:00:00Z',
          request_id: 'req-2',
          trace_id: 'trace-2'
        })
      })

      mockGenerateCommitId.mockReturnValueOnce('first-commit-id')
                          .mockReturnValueOnce('new-commit-id')

      renderWithProviders()
      
      const button = screen.getByRole('button', { name: /확정하기/i })
      fireEvent.click(button)

      // Wait for error panel to appear
      await waitFor(() => {
        expect(screen.getByTestId('error-panel')).toBeInTheDocument()
      })

      // Click retry
      const retryButton = screen.getByTestId('retry-button')
      fireEvent.click(retryButton)

      // Should succeed on retry
      await waitFor(() => {
        expect(mockSubmitFeedback).toHaveBeenCalledTimes(2)
        expect(mockGenerateCommitId).toHaveBeenCalledTimes(2)
      })
    })
  })

  describe('Keyboard Shortcuts', () => {
    it('should handle Cmd+Enter shortcut', async () => {
      mockSubmitFeedback.mockResolvedValue({
        stored: true,
        commit_id: 'test-commit-id',
        timestamp: '2024-01-01T10:00:00Z',
        request_id: 'req-1',
        trace_id: 'trace-1'
      })

      renderWithProviders()

      // Simulate Cmd+Enter
      fireEvent.keyDown(window, { key: 'Enter', metaKey: true })

      await waitFor(() => {
        expect(mockSubmitFeedback).toHaveBeenCalled()
      })
    })

    it('should handle Ctrl+Enter shortcut', async () => {
      mockSubmitFeedback.mockResolvedValue({
        stored: true,
        commit_id: 'test-commit-id',
        timestamp: '2024-01-01T10:00:00Z',
        request_id: 'req-1',
        trace_id: 'trace-1'
      })

      renderWithProviders()

      // Simulate Ctrl+Enter
      fireEvent.keyDown(window, { key: 'Enter', ctrlKey: true })

      await waitFor(() => {
        expect(mockSubmitFeedback).toHaveBeenCalled()
      })
    })

    it('should not trigger shortcut when disabled', () => {
      renderWithProviders({ isGenerating: true })

      fireEvent.keyDown(window, { key: 'Enter', metaKey: true })

      expect(mockSubmitFeedback).not.toHaveBeenCalled()
    })
  })

  describe('Double-click Prevention', () => {
    it('should prevent double-click by generating new commit ID only once per attempt', async () => {
      mockSubmitFeedback.mockResolvedValue({
        stored: true,
        commit_id: 'test-commit-id',
        timestamp: '2024-01-01T10:00:00Z',
        request_id: 'req-1',
        trace_id: 'trace-1'
      })

      renderWithProviders()
      
      const button = screen.getByRole('button', { name: /확정하기/i })
      
      // Rapid double click
      fireEvent.click(button)
      fireEvent.click(button)
      fireEvent.click(button)

      // Should only call submitFeedback once
      await waitFor(() => {
        expect(mockSubmitFeedback).toHaveBeenCalledTimes(1)
        expect(mockGenerateCommitId).toHaveBeenCalledTimes(1)
      })
    })
  })

  describe('Language Support', () => {
    it('should show English text when language is en', () => {
      renderWithProviders({ language: 'en' })
      
      const button = screen.getByRole('button', { name: /Commit this version/i })
      expect(button).toBeInTheDocument()
    })

    it('should show Korean text when language is kr', () => {
      renderWithProviders({ language: 'kr' })
      
      const button = screen.getByRole('button', { name: /확정하기/i })
      expect(button).toBeInTheDocument()
    })
  })

  describe('Compact Mode', () => {
    it('should render in compact mode', () => {
      renderWithProviders({ compact: true })
      
      const button = screen.getByRole('button', { name: /확정하기/i })
      expect(button).toHaveClass('MuiButton-sizeSmall')
    })
  })
})