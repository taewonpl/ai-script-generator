/**
 * Edge case tests for MemoryControls component
 * Tests UI behavior for complex scenarios and error conditions
 */

import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import MemoryControls from '../MemoryControls'
import type { MemoryControlsProps, MemoryState } from '../MemoryControls'

// Mock toast helpers
const mockShowSuccess = vi.fn()
const mockShowError = vi.fn()

vi.mock('@/shared/ui/components/toast', () => ({
  useToastHelpers: () => ({
    showSuccess: mockShowSuccess,
    showError: mockShowError,
  }),
}))

describe('MemoryControls Edge Cases', () => {
  let queryClient: QueryClient
  let mockProps: MemoryControlsProps
  
  const createMemoryState = (overrides: Partial<MemoryState> = {}): MemoryState => ({
    enabled: false,
    historyDepth: 5,
    turnsCount: 0,
    entityRenames: 0,
    entityFacts: 0,
    styleFlags: 0,
    memoryVersion: 1,
    tokensUsed: 0,
    compressionRecommended: false,
    ...overrides,
  })
  
  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    })
    
    mockProps = {
      memoryState: createMemoryState(),
      onMemoryToggle: vi.fn().mockResolvedValue(undefined),
      onHistoryDepthChange: vi.fn().mockResolvedValue(undefined),
      onClearMemory: vi.fn().mockResolvedValue(undefined),
      onCompressMemory: vi.fn().mockResolvedValue(undefined),
      loading: false,
    }
    
    // Clear mocks
    vi.clearAllMocks()
  })
  
  const renderWithQueryClient = (component: React.ReactElement) => {
    return render(
      <QueryClientProvider client={queryClient}>
        {component}
      </QueryClientProvider>
    )
  }

  describe('High-frequency operations', () => {
    it('should handle rapid memory toggle attempts gracefully', async () => {
      const mockToggle = vi.fn().mockImplementation(() => 
        new Promise(resolve => setTimeout(resolve, 100)) // 100ms delay
      )
      
      mockProps.onMemoryToggle = mockToggle
      renderWithQueryClient(<MemoryControls {...mockProps} />)
      
      const toggle = screen.getByRole('checkbox')
      
      // Simulate rapid clicking
      for (let i = 0; i < 5; i++) {
        fireEvent.click(toggle)
      }
      
      // Should only trigger one toggle due to async handling
      await waitFor(() => {
        expect(mockToggle).toHaveBeenCalledTimes(1)
      }, { timeout: 500 })
    })
    
    it('should show rate limit error for rapid setting changes', async () => {
      const mockError = new Error('Rate limit exceeded')
      mockProps.onHistoryDepthChange = vi.fn().mockRejectedValue(mockError)
      
      renderWithQueryClient(<MemoryControls {...mockProps} />)
      
      // Open settings dialog
      const settingsButton = screen.getByRole('button', { name: /메모리 설정/i })
      fireEvent.click(settingsButton)
      
      // Change slider rapidly
      const slider = screen.getByRole('slider')
      fireEvent.change(slider, { target: { value: 8 } })
      
      // Save settings
      const saveButton = screen.getByRole('button', { name: /저장/i })
      fireEvent.click(saveButton)
      
      await waitFor(() => {
        expect(mockShowError).toHaveBeenCalledWith('히스토리 설정 저장에 실패했습니다.')
      })
    })
  })

  describe('Memory state edge cases', () => {
    it('should display correct status for empty but enabled memory', () => {
      const emptyMemoryState = createMemoryState({
        enabled: true,
        turnsCount: 0,
        entityRenames: 0,
        entityFacts: 0,
      })
      
      mockProps.memoryState = emptyMemoryState
      renderWithQueryClient(<MemoryControls {...mockProps} />)
      
      expect(screen.getByText('Context: Empty')).toBeInTheDocument()
    })
    
    it('should handle very large memory counts gracefully', () => {
      const largeMemoryState = createMemoryState({
        enabled: true,
        turnsCount: 999,
        entityRenames: 150,
        entityFacts: 75,
        styleFlags: 25,
        tokensUsed: 50000,
      })
      
      mockProps.memoryState = largeMemoryState
      renderWithQueryClient(<MemoryControls {...mockProps} />)
      
      // Click to expand details
      const statusChip = screen.getByText(/Context:/)
      fireEvent.click(statusChip)
      
      expect(screen.getByText('대화 턴: 999')).toBeInTheDocument()
      expect(screen.getByText('이름 변경: 150')).toBeInTheDocument()
      expect(screen.getByText('저장된 정보: 75')).toBeInTheDocument()
      expect(screen.getByText('토큰 사용량: ~50000')).toBeInTheDocument()
    })
    
    it('should show compression recommendation for large memory', () => {
      const memoryNeedingCompression = createMemoryState({
        enabled: true,
        turnsCount: 25,
        compressionRecommended: true,
      })
      
      mockProps.memoryState = memoryNeedingCompression
      renderWithQueryClient(<MemoryControls {...mockProps} />)
      
      // Should show compress button
      const compressButton = screen.getByRole('button', { name: /메모리 압축으로 토큰 절약/i })
      expect(compressButton).toBeInTheDocument()
      
      // Click to expand details and see recommendation
      const statusChip = screen.getByText(/Context:/)
      fireEvent.click(statusChip)
      
      expect(screen.getByText(/메모리 압축을 권장합니다/)).toBeInTheDocument()
    })
  })

  describe('Error handling and recovery', () => {
    it('should handle memory toggle failure with proper error message', async () => {
      const mockToggle = vi.fn().mockRejectedValue(new Error('Network error'))
      mockProps.onMemoryToggle = mockToggle
      
      renderWithQueryClient(<MemoryControls {...mockProps} />)
      
      const toggle = screen.getByRole('checkbox')
      fireEvent.click(toggle)
      
      await waitFor(() => {
        expect(mockShowError).toHaveBeenCalledWith('메모리 설정 변경에 실패했습니다.')
      })
    })
    
    it('should revert slider value on history depth save failure', async () => {
      mockProps.memoryState = createMemoryState({ enabled: true, historyDepth: 5 })
      mockProps.onHistoryDepthChange = vi.fn().mockRejectedValue(new Error('Save failed'))
      
      renderWithQueryClient(<MemoryControls {...mockProps} />)
      
      // Open settings
      const settingsButton = screen.getByRole('button', { name: /메모리 설정/i })
      fireEvent.click(settingsButton)
      
      // Change slider
      const slider = screen.getByRole('slider')
      fireEvent.change(slider, { target: { value: 8 } })
      
      // Attempt to save
      const saveButton = screen.getByRole('button', { name: /저장/i })
      fireEvent.click(saveButton)
      
      await waitFor(() => {
        expect(mockShowError).toHaveBeenCalledWith('히스토리 설정 저장에 실패했습니다.')
      })
      
      // Reopen settings to check slider reverted
      fireEvent.click(settingsButton)
      const revertedSlider = screen.getByRole('slider')
      expect(revertedSlider).toHaveValue('5') // Reverted to original value
    })
    
    it('should handle compression failure gracefully', async () => {
      mockProps.memoryState = createMemoryState({ 
        enabled: true, 
        compressionRecommended: true 
      })
      mockProps.onCompressMemory = vi.fn().mockRejectedValue(new Error('Compression failed'))
      
      renderWithQueryClient(<MemoryControls {...mockProps} />)
      
      const compressButton = screen.getByRole('button', { name: /메모리 압축으로 토큰 절약/i })
      fireEvent.click(compressButton)
      
      await waitFor(() => {
        expect(mockShowError).toHaveBeenCalledWith('메모리 압축에 실패했습니다.')
      })
    })
  })

  describe('Memory clear dialog edge cases', () => {
    beforeEach(() => {
      mockProps.memoryState = createMemoryState({ enabled: true })
    })
    
    it('should show updated confirmation message with rollback info', async () => {
      renderWithQueryClient(<MemoryControls {...mockProps} />)
      
      // Open settings to access clear button
      const settingsButton = screen.getByRole('button', { name: /메모리 설정/i })
      fireEvent.click(settingsButton)
      
      const clearButton = screen.getByRole('button', { name: /메모리 삭제/i })
      fireEvent.click(clearButton)
      
      // Check updated confirmation message
      expect(screen.getByText(/이 에피소드의 기억된 맥락을 삭제할까요\? 60초 후 되돌릴 수 없습니다\./)).toBeInTheDocument()
      expect(screen.getByText(/삭제된 메모리는 60초 후 복구할 수 없습니다\./)).toBeInTheDocument()
    })
    
    it('should show updated success message with rollback info', async () => {
      mockProps.onClearMemory = vi.fn().mockResolvedValue(undefined)
      
      renderWithQueryClient(<MemoryControls {...mockProps} />)
      
      // Navigate to clear dialog
      const settingsButton = screen.getByRole('button', { name: /메모리 설정/i })
      fireEvent.click(settingsButton)
      
      const clearButton = screen.getByRole('button', { name: /메모리 삭제/i })
      fireEvent.click(clearButton)
      
      const confirmButton = screen.getByRole('button', { name: /삭제/i })
      fireEvent.click(confirmButton)
      
      await waitFor(() => {
        expect(mockShowSuccess).toHaveBeenCalledWith('메모리가 삭제되었습니다. 60초 내에 되돌릴 수 있습니다.')
      })
    })
    
    it('should handle partial memory clear options', async () => {
      const mockClear = vi.fn().mockResolvedValue(undefined)
      mockProps.onClearMemory = mockClear
      
      renderWithQueryClient(<MemoryControls {...mockProps} />)
      
      // Open clear dialog
      const settingsButton = screen.getByRole('button', { name: /메모리 설정/i })
      fireEvent.click(settingsButton)
      
      const clearButton = screen.getByRole('button', { name: /메모리 삭제/i })
      fireEvent.click(clearButton)
      
      // Uncheck entity memory deletion (keep only history clear)
      const entitySwitch = screen.getByLabelText(/엔터티 메모리 삭제/)
      fireEvent.click(entitySwitch)
      
      const confirmButton = screen.getByRole('button', { name: /삭제/i })
      fireEvent.click(confirmButton)
      
      await waitFor(() => {
        expect(mockClear).toHaveBeenCalledWith({
          clearHistory: true,
          clearEntityMemory: false,
        })
      })
    })
  })

  describe('Accessibility and interaction', () => {
    it('should maintain keyboard navigation for all controls', () => {
      mockProps.memoryState = createMemoryState({ enabled: true, compressionRecommended: true })
      renderWithQueryClient(<MemoryControls {...mockProps} />)
      
      // Test tab order
      const toggle = screen.getByRole('checkbox')
      const statusChip = screen.getByRole('button', { name: /Context:/ })
      const settingsButton = screen.getByRole('button', { name: /메모리 설정/i })
      const compressButton = screen.getByRole('button', { name: /메모리 압축으로 토큰 절약/i })
      
      // All controls should be focusable
      expect(toggle).not.toHaveAttribute('tabindex', '-1')
      expect(statusChip).not.toHaveAttribute('tabindex', '-1')
      expect(settingsButton).not.toHaveAttribute('tabindex', '-1')
      expect(compressButton).not.toHaveAttribute('tabindex', '-1')
    })
    
    it('should provide proper ARIA labels and roles', () => {
      mockProps.memoryState = createMemoryState({ enabled: true })
      renderWithQueryClient(<MemoryControls {...mockProps} />)
      
      const toggle = screen.getByRole('checkbox')
      expect(toggle).toHaveAccessibleName()
      
      const settingsButton = screen.getByRole('button', { name: /메모리 설정/i })
      expect(settingsButton).toHaveAttribute('aria-label')
    })
    
    it('should disable controls appropriately during loading', () => {
      mockProps.loading = true
      mockProps.memoryState = createMemoryState({ enabled: true })
      renderWithQueryClient(<MemoryControls {...mockProps} />)
      
      const toggle = screen.getByRole('checkbox')
      const settingsButton = screen.getByRole('button', { name: /메모리 설정/i })
      
      expect(toggle).toBeDisabled()
      expect(settingsButton).toBeDisabled()
    })
  })

  describe('Tooltip improvements', () => {
    it('should show updated tooltip text for memory toggle', async () => {
      renderWithQueryClient(<MemoryControls {...mockProps} />)
      
      const toggle = screen.getByRole('checkbox').closest('label')
      expect(toggle).toBeInTheDocument()
      
      // Hover to trigger tooltip
      if (toggle) {
        fireEvent.mouseEnter(toggle)
      }
      
      await waitFor(() => {
        expect(screen.getByText('최근 맥락을 유지해 일관성을 높입니다. 토큰 사용량이 증가할 수 있습니다.')).toBeInTheDocument()
      })
    })
  })

  describe('Multi-tab scenario simulation', () => {
    it('should handle rapid state changes from external sources', () => {
      const { rerender } = renderWithQueryClient(<MemoryControls {...mockProps} />)
      
      // Simulate rapid state updates from other tabs
      const states = [
        createMemoryState({ enabled: true, memoryVersion: 2, turnsCount: 5 }),
        createMemoryState({ enabled: false, memoryVersion: 3, turnsCount: 5 }),
        createMemoryState({ enabled: true, memoryVersion: 4, turnsCount: 8 }),
      ]
      
      states.forEach((state, index) => {
        const updatedProps = { ...mockProps, memoryState: state }
        rerender(
          <QueryClientProvider client={queryClient}>
            <MemoryControls {...updatedProps} />
          </QueryClientProvider>
        )
        
        // Verify UI reflects the latest state
        const toggle = screen.getByRole('checkbox')
        expect(toggle.checked).toBe(state.enabled)
        
        if (state.enabled && state.turnsCount > 0) {
          expect(screen.getByText(new RegExp(`Context:.*${state.turnsCount} turns`))).toBeInTheDocument()
        }
      })
    })
  })
})