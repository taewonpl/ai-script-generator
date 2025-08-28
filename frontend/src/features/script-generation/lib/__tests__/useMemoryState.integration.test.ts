/**
 * Integration tests for useMemoryState multi-tab scenarios
 * Tests BroadcastChannel synchronization and conflict resolution
 */

import { renderHook, act, waitFor } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'

import { useMemoryState } from '../useMemoryState'
import type { UseMemoryStateOptions } from '../useMemoryState'

// Mock API client
const mockApiPost = vi.fn()
const mockApiPut = vi.fn()
const mockApiDelete = vi.fn()

vi.mock('@/shared/api/client', () => ({
  api: {
    post: mockApiPost,
    put: mockApiPut,
    delete: mockApiDelete,
  },
}))

// Mock toast helpers
vi.mock('@/shared/ui/components/toast', () => ({
  useToastHelpers: () => ({
    showError: vi.fn(),
    showWarning: vi.fn(),
  }),
}))

// Mock BroadcastChannel
class MockBroadcastChannel {
  private listeners: ((event: { data: any }) => void)[] = []
  private static channels: Map<string, MockBroadcastChannel[]> = new Map()
  
  constructor(private name: string) {
    const existing = MockBroadcastChannel.channels.get(name) || []
    existing.push(this)
    MockBroadcastChannel.channels.set(name, existing)
  }
  
  addEventListener(type: string, listener: (event: { data: any }) => void) {
    if (type === 'message') {
      this.listeners.push(listener)
    }
  }
  
  postMessage(data: any) {
    // Simulate broadcasting to all other channels with same name
    const channels = MockBroadcastChannel.channels.get(this.name) || []
    channels.forEach(channel => {
      if (channel !== this) {
        channel.listeners.forEach(listener => {
          // Simulate async message delivery
          setTimeout(() => listener({ data }), 0)
        })
      }
    })
  }
  
  close() {
    const channels = MockBroadcastChannel.channels.get(this.name) || []
    const index = channels.indexOf(this)
    if (index > -1) {
      channels.splice(index, 1)
      if (channels.length === 0) {
        MockBroadcastChannel.channels.delete(this.name)
      } else {
        MockBroadcastChannel.channels.set(this.name, channels)
      }
    }
  }
  
  static reset() {
    this.channels.clear()
  }
}

// @ts-ignore
global.BroadcastChannel = MockBroadcastChannel

describe('useMemoryState Multi-Tab Integration', () => {
  let queryClient: QueryClient
  
  const defaultOptions: UseMemoryStateOptions = {
    projectId: 'test-project',
    episodeId: 'test-episode',
    enableBroadcast: true,
    autoSync: false, // Disable auto-sync to control timing
    throttleMs: 100,
  }
  
  const createWrapper = () => {
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    )
    return wrapper
  }
  
  const createMockMemoryState = (overrides: any = {}) => ({
    project_id: 'test-project',
    episode_id: 'test-episode',
    history: [],
    last_seq: 0,
    entity_memory: {
      rename_map: {},
      style_flags: [],
      facts: [],
    },
    history_compacted: false,
    memory_enabled: false,
    history_depth: 5,
    memory_version: 1,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides,
  })
  
  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    })
    
    // Reset mocks
    vi.clearAllMocks()
    MockBroadcastChannel.reset()
    
    // Setup default API responses
    mockApiPost.mockResolvedValue({
      data: { generation_state: createMockMemoryState() }
    })
  })
  
  afterEach(() => {
    MockBroadcastChannel.reset()
  })

  describe('Multi-tab memory synchronization', () => {
    it('should synchronize memory state between tabs when version changes', async () => {
      // Setup tab 1
      const { result: tab1 } = renderHook(() => useMemoryState(defaultOptions), {
        wrapper: createWrapper(),
      })
      
      // Setup tab 2
      const { result: tab2 } = renderHook(() => useMemoryState(defaultOptions), {
        wrapper: createWrapper(),
      })
      
      // Wait for initial load
      await waitFor(() => {
        expect(tab1.current.memoryState).toBeTruthy()
        expect(tab2.current.memoryState).toBeTruthy()
      })
      
      // Mock updated state for tab 1
      const updatedState = createMockMemoryState({
        memory_version: 2,
        memory_enabled: true,
        history: [{ 
          turn_id: 'turn-1', 
          content: 'New turn', 
          content_hash: 'hash-1',
          source: 'ui',
          created_at: new Date().toISOString()
        }]
      })
      
      mockApiPut.mockResolvedValue({
        data: { 
          generation_state: updatedState,
          conflicts_resolved: false
        }
      })
      
      // Tab 1 enables memory
      await act(async () => {
        await tab1.current.toggleMemory(true)
      })
      
      // Tab 2 should receive broadcast and sync
      await waitFor(() => {
        expect(tab2.current.memoryState?.memory_version).toBe(2)
        expect(tab2.current.memoryState?.memory_enabled).toBe(true)
      })
    })
    
    it('should detect and handle conflicts between tabs', async () => {
      const initialState = createMockMemoryState({ memory_version: 1 })
      
      // Tab 1 gets initial state
      const { result: tab1 } = renderHook(() => useMemoryState(defaultOptions), {
        wrapper: createWrapper(),
      })
      
      // Tab 2 gets initial state
      const { result: tab2 } = renderHook(() => useMemoryState(defaultOptions), {
        wrapper: createWrapper(),
      })
      
      await waitFor(() => {
        expect(tab1.current.memoryState).toBeTruthy()
        expect(tab2.current.memoryState).toBeTruthy()
      })
      
      // Mock conflict scenario: tab 1 succeeds with version 2
      mockApiPut.mockResolvedValueOnce({
        data: {
          generation_state: createMockMemoryState({ 
            memory_version: 2, 
            memory_enabled: true 
          }),
          conflicts_resolved: false
        }
      })
      
      // Tab 2 attempts change but gets conflict (version 3 with resolution)
      mockApiPut.mockResolvedValueOnce({
        data: {
          generation_state: createMockMemoryState({ 
            memory_version: 3, 
            history_depth: 8,
            memory_enabled: true  // Merged state
          }),
          conflicts_resolved: true  // Conflict was resolved
        }
      })
      
      // Both tabs make concurrent changes
      await act(async () => {
        await Promise.all([
          tab1.current.toggleMemory(true),
          tab2.current.setHistoryDepth(8)
        ])
      })
      
      // Tab 1 should receive the resolved state via broadcast
      await waitFor(() => {
        expect(tab1.current.memoryState?.memory_version).toBe(3)
        expect(tab1.current.memoryState?.history_depth).toBe(8)
        expect(tab1.current.memoryState?.memory_enabled).toBe(true)
      })
      
      // Tab 2 should have hasConflicts flag set
      expect(tab2.current.hasConflicts).toBe(true)
    })
    
    it('should handle memory clear broadcast across tabs', async () => {
      const { result: tab1 } = renderHook(() => useMemoryState(defaultOptions), {
        wrapper: createWrapper(),
      })
      
      const { result: tab2 } = renderHook(() => useMemoryState(defaultOptions), {
        wrapper: createWrapper(),
      })
      
      await waitFor(() => {
        expect(tab1.current.memoryState).toBeTruthy()
        expect(tab2.current.memoryState).toBeTruthy()
      })
      
      // Mock clear response
      mockApiDelete.mockResolvedValue({
        data: { success: true }
      })
      
      // Mock fresh state after clear
      const clearedState = createMockMemoryState({ 
        memory_version: 1, 
        history: [],
        entity_memory: { rename_map: {}, style_flags: [], facts: [] }
      })
      mockApiPost.mockResolvedValue({
        data: { generation_state: clearedState }
      })
      
      // Tab 1 clears memory
      await act(async () => {
        await tab1.current.clearMemory({ 
          clearHistory: true, 
          clearEntityMemory: true 
        })
      })
      
      // Tab 2 should receive broadcast and reload state
      await waitFor(() => {
        expect(tab2.current.memoryState?.history).toHaveLength(0)
        expect(Object.keys(tab2.current.memoryState?.entity_memory.rename_map || {})).toHaveLength(0)
      })
    })
  })

  describe('Rate limiting across tabs', () => {
    it('should enforce rate limits globally across tabs', async () => {
      const { result: tab1 } = renderHook(() => useMemoryState(defaultOptions), {
        wrapper: createWrapper(),
      })
      
      const { result: tab2 } = renderHook(() => useMemoryState(defaultOptions), {
        wrapper: createWrapper(),
      })
      
      await waitFor(() => {
        expect(tab1.current.memoryState).toBeTruthy()
        expect(tab2.current.memoryState).toBeTruthy()
      })
      
      // Mock successful first request
      mockApiPut.mockResolvedValueOnce({
        data: {
          generation_state: createMockMemoryState({ memory_version: 2 }),
          conflicts_resolved: false
        }
      })
      
      // Tab 1 makes first request (should succeed)
      await act(async () => {
        await tab1.current.toggleMemory(true)
      })
      
      expect(mockApiPut).toHaveBeenCalledTimes(1)
      
      // Tab 2 makes immediate follow-up request (should be rate limited)
      // Note: In real implementation, this would be prevented at the hook level
      // Here we test that rate limiting logic is applied
      let rateLimitedAttempt = false
      
      try {
        await act(async () => {
          await tab2.current.toggleMemory(false)
        })
      } catch (error: any) {
        if (error.message.includes('너무 빠른') || error.message.includes('메모리 변경이 너무 빠릅니다')) {
          rateLimitedAttempt = true
        }
      }
      
      // Should either be rate limited or only one request should have gone through
      expect(rateLimitedAttempt || mockApiPut).toHaveBeenCalledTimes(1)
    })
  })

  describe('Turn addition throttling', () => {
    it('should throttle rapid turn additions across tabs', async () => {
      const { result: tab1 } = renderHook(() => useMemoryState({
        ...defaultOptions,
        enableBroadcast: true
      }), {
        wrapper: createWrapper(),
      })
      
      const { result: tab2 } = renderHook(() => useMemoryState({
        ...defaultOptions,
        enableBroadcast: true
      }), {
        wrapper: createWrapper(),
      })
      
      // Setup memory enabled state
      await waitFor(() => {
        expect(tab1.current.memoryState).toBeTruthy()
        expect(tab2.current.memoryState).toBeTruthy()
      })
      
      // Enable memory first
      const enabledState = createMockMemoryState({ 
        memory_enabled: true,
        memory_version: 2
      })
      
      mockApiPut.mockResolvedValue({
        data: { 
          generation_state: enabledState,
          conflicts_resolved: false 
        }
      })
      
      await act(async () => {
        await tab1.current.toggleMemory(true)
      })
      
      // Mock turn addition response
      mockApiPost.mockResolvedValue({
        data: {
          generation_state: {
            ...enabledState,
            memory_version: 3,
            history: [
              { turn_id: 'turn-1', content: 'Turn 1', content_hash: 'hash-1', source: 'ui', created_at: new Date().toISOString() }
            ]
          },
          conflicts_resolved: false
        }
      })
      
      const addTurnCalls: Promise<void>[] = []
      
      // Rapid turn additions from both tabs
      for (let i = 0; i < 3; i++) {
        addTurnCalls.push(tab1.current.addTurn(`Turn ${i} from tab1`, 'ui'))
        addTurnCalls.push(tab2.current.addTurn(`Turn ${i} from tab2`, 'ui'))
      }
      
      await act(async () => {
        await Promise.allSettled(addTurnCalls)
      })
      
      // Should be throttled - not all 6 calls should hit the API
      expect(mockApiPost).toHaveBeenCalledWith(
        expect.stringContaining('/api/generation/memory/turns'),
        expect.anything(),
        expect.anything()
      )
      
      // The exact count may vary due to throttling, but should be less than 6
      const turnCalls = mockApiPost.mock.calls.filter(call => 
        call[0].includes('/turns')
      )
      expect(turnCalls.length).toBeLessThan(6)
    })
  })

  describe('Memory state consistency', () => {
    it('should maintain consistent state during rapid multi-tab operations', async () => {
      const { result: tab1 } = renderHook(() => useMemoryState(defaultOptions), {
        wrapper: createWrapper(),
      })
      
      const { result: tab2 } = renderHook(() => useMemoryState(defaultOptions), {
        wrapper: createWrapper(),
      })
      
      const { result: tab3 } = renderHook(() => useMemoryState(defaultOptions), {
        wrapper: createWrapper(),
      })
      
      await waitFor(() => {
        expect(tab1.current.memoryState).toBeTruthy()
        expect(tab2.current.memoryState).toBeTruthy()
        expect(tab3.current.memoryState).toBeTruthy()
      })
      
      // Simulate sequence of operations with version increments
      const operations = [
        { version: 2, enabled: true, depth: 5 },
        { version: 3, enabled: true, depth: 7 },
        { version: 4, enabled: false, depth: 7 },
        { version: 5, enabled: true, depth: 10 }
      ]
      
      for (let i = 0; i < operations.length; i++) {
        const op = operations[i]
        
        mockApiPut.mockResolvedValueOnce({
          data: {
            generation_state: createMockMemoryState({
              memory_version: op.version,
              memory_enabled: op.enabled,
              history_depth: op.depth
            }),
            conflicts_resolved: false
          }
        })
      }
      
      // Execute operations from different tabs
      await act(async () => {
        await tab1.current.toggleMemory(true)
      })
      
      await act(async () => {
        await tab2.current.setHistoryDepth(7)
      })
      
      await act(async () => {
        await tab3.current.toggleMemory(false)
      })
      
      await act(async () => {
        await tab1.current.setHistoryDepth(10)
      })
      
      // All tabs should eventually converge to the latest state
      await waitFor(() => {
        [tab1, tab2, tab3].forEach(tab => {
          expect(tab.current.memoryState?.memory_version).toBe(5)
          expect(tab.current.memoryState?.memory_enabled).toBe(true)
          expect(tab.current.memoryState?.history_depth).toBe(10)
        })
      })
    })
  })

  describe('Error handling in multi-tab scenarios', () => {
    it('should handle API failures gracefully without disrupting other tabs', async () => {
      const { result: tab1 } = renderHook(() => useMemoryState(defaultOptions), {
        wrapper: createWrapper(),
      })
      
      const { result: tab2 } = renderHook(() => useMemoryState(defaultOptions), {
        wrapper: createWrapper(),
      })
      
      await waitFor(() => {
        expect(tab1.current.memoryState).toBeTruthy()
        expect(tab2.current.memoryState).toBeTruthy()
      })
      
      // Tab 1 API call fails
      mockApiPut.mockRejectedValueOnce(new Error('Network error'))
      
      // Tab 2 API call succeeds
      mockApiPut.mockResolvedValueOnce({
        data: {
          generation_state: createMockMemoryState({ 
            memory_version: 2, 
            memory_enabled: true 
          }),
          conflicts_resolved: false
        }
      })
      
      // Both tabs attempt operations
      await act(async () => {
        // This should fail
        try {
          await tab1.current.toggleMemory(true)
        } catch (error) {
          // Expected to fail
        }
        
        // This should succeed
        await tab2.current.toggleMemory(true)
      })
      
      // Tab 2 should have updated state
      expect(tab2.current.memoryState?.memory_enabled).toBe(true)
      expect(tab2.current.memoryState?.memory_version).toBe(2)
      
      // Tab 1 should eventually receive the update via broadcast
      await waitFor(() => {
        expect(tab1.current.memoryState?.memory_enabled).toBe(true)
        expect(tab1.current.memoryState?.memory_version).toBe(2)
      })
    })
  })
})