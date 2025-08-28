/**
 * Memory state management hook with multi-tab synchronization
 * Handles conversation memory, entity memory, and conflict resolution
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'

import { api } from '@/shared/api/client'
import { useToastHelpers } from '@/shared/ui/components/toast'

export interface ConversationTurn {
  turn_id: string
  source: 'ui' | 'api' | 'sse'
  job_id?: string
  selection?: Record<string, any>
  content: string
  content_hash: string
  created_at: string
}

export interface EntityMemory {
  rename_map: Record<string, string>
  style_flags: string[]
  facts: string[]
}

export interface MemoryState {
  project_id: string
  episode_id?: string
  history: ConversationTurn[]
  last_seq: number
  entity_memory: EntityMemory
  history_compacted: boolean
  memory_enabled: boolean
  history_depth: number
  memory_version: number
  created_at: string
  updated_at: string
}

export interface MemoryMetrics {
  turnsCount: number
  entityRenames: number
  entityFacts: number
  styleFlags: number
  tokensUsed: number
  compressionRecommended: boolean
}

export interface UseMemoryStateOptions {
  projectId: string
  episodeId?: string
  enableBroadcast?: boolean
  autoSync?: boolean
  throttleMs?: number
}

export interface UseMemoryStateReturn {
  // State
  memoryState: MemoryState | null
  metrics: MemoryMetrics
  loading: boolean
  error: string | null
  
  // Actions
  toggleMemory: (enabled: boolean) => Promise<void>
  setHistoryDepth: (depth: number) => Promise<void>
  addTurn: (content: string, source: 'ui' | 'api' | 'sse', selection?: Record<string, any>) => Promise<void>
  clearMemory: (options: { clearHistory: boolean; clearEntityMemory: boolean }) => Promise<void>
  compressMemory: () => Promise<void>
  
  // Sync
  syncWithServer: () => Promise<void>
  hasConflicts: boolean
}

// Rate limiting for write operations (max 2 per second)
const WRITE_RATE_LIMIT_MS = 500
const writeTimestamps = new Map<string, number>()

function checkWriteRateLimit(key: string): boolean {
  const now = Date.now()
  const lastWrite = writeTimestamps.get(key) || 0
  
  if (now - lastWrite < WRITE_RATE_LIMIT_MS) {
    return false // Rate limited
  }
  
  writeTimestamps.set(key, now)
  return true
}

/**
 * Memory state management hook
 */
export function useMemoryState(options: UseMemoryStateOptions): UseMemoryStateReturn {
  const {
    projectId,
    episodeId,
    enableBroadcast = true,
    autoSync = true,
    throttleMs = 1000,
  } = options
  
  const queryClient = useQueryClient()
  const { showError, showWarning } = useToastHelpers()
  
  // State
  const [memoryState, setMemoryState] = useState<MemoryState | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [hasConflicts, setHasConflicts] = useState(false)
  
  // Refs for managing intervals and broadcast
  const broadcastChannel = useRef<BroadcastChannel | null>(null)
  const syncInterval = useRef<NodeJS.Timeout | null>(null)
  const throttleTimeout = useRef<NodeJS.Timeout | null>(null)
  
  // Generate memory key for storage and broadcast
  const memoryKey = `${projectId}:${episodeId || 'default'}`
  
  // Initialize broadcast channel for multi-tab sync
  useEffect(() => {
    if (!enableBroadcast) return
    
    const channel = new BroadcastChannel(`memory-${memoryKey}`)
    broadcastChannel.current = channel
    
    channel.addEventListener('message', (event) => {
      const { type, data } = event.data
      
      switch (type) {
        case 'memory-updated':
          // Another tab updated memory, sync if version is different
          if (data.memory_version > (memoryState?.memory_version || 0)) {
            syncWithServer()
          }
          break
          
        case 'memory-conflict':
          setHasConflicts(true)
          showWarning('다른 탭과 메모리 동기화 중입니다. 잠시만 기다려주세요.')
          break
          
        case 'memory-cleared':
          // Another tab cleared memory, sync to get latest state
          syncWithServer()
          break
      }
    })
    
    return () => {
      channel.close()
      broadcastChannel.current = null
    }
  }, [memoryKey, enableBroadcast, memoryState?.memory_version])
  
  // Auto-sync with server
  useEffect(() => {
    if (!autoSync || !memoryState?.memory_enabled) return
    
    syncInterval.current = setInterval(() => {
      syncWithServer()
    }, throttleMs)
    
    return () => {
      if (syncInterval.current) {
        clearInterval(syncInterval.current)
        syncInterval.current = null
      }
    }
  }, [autoSync, memoryState?.memory_enabled, throttleMs])
  
  // Broadcast memory updates to other tabs
  const broadcastUpdate = useCallback((type: string, data: any) => {
    if (broadcastChannel.current) {
      broadcastChannel.current.postMessage({ type, data })
    }
  }, [])
  
  // Load initial memory state
  const loadMemoryState = useCallback(async () => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await api.post('/api/generation/memory/state', {
        project_id: projectId,
        episode_id: episodeId,
        memory_enabled: false, // Default to disabled
        history_depth: 5,
      })
      
      setMemoryState(response.data.generation_state)
    } catch (err: any) {
      console.error('Failed to load memory state:', err)
      setError('메모리 상태를 불러오는데 실패했습니다.')
    } finally {
      setLoading(false)
    }
  }, [projectId, episodeId])
  
  // Sync with server
  const syncWithServer = useCallback(async () => {
    if (!memoryState) return
    
    try {
      const response = await api.post('/api/generation/memory/state', {
        project_id: projectId,
        episode_id: episodeId,
        memory_enabled: memoryState.memory_enabled,
        history_depth: memoryState.history_depth,
      })
      
      const serverState = response.data.generation_state
      
      // Check for version conflicts
      if (serverState.memory_version > memoryState.memory_version) {
        setMemoryState(serverState)
        setHasConflicts(false)
        
        // Broadcast sync to other tabs
        broadcastUpdate('memory-updated', serverState)
      }
    } catch (err: any) {
      console.error('Sync failed:', err)
      // Don't show error for sync failures unless critical
    }
  }, [memoryState, projectId, episodeId, broadcastUpdate])
  
  // Toggle memory enabled/disabled
  const toggleMemory = useCallback(async (enabled: boolean) => {
    if (!checkWriteRateLimit(memoryKey)) {
      showError('메모리 변경이 너무 빠릅니다. 잠시 후 다시 시도하세요.')
      return
    }
    
    setLoading(true)
    setError(null)
    
    try {
      const response = await api.put('/api/generation/memory/state', {
        memory_enabled: enabled,
        expected_version: memoryState?.memory_version,
      }, {
        params: { project_id: projectId, episode_id: episodeId },
      })
      
      const newState = response.data.generation_state
      setMemoryState(newState)
      
      // Broadcast to other tabs
      broadcastUpdate('memory-updated', newState)
      
      // Handle conflicts
      if (response.data.conflicts_resolved) {
        setHasConflicts(true)
        showWarning('메모리가 다른 탭과 동기화되었습니다.')
      }
    } catch (err: any) {
      console.error('Toggle memory failed:', err)
      setError('메모리 설정 변경에 실패했습니다.')
      throw err
    } finally {
      setLoading(false)
    }
  }, [memoryKey, memoryState, projectId, episodeId, broadcastUpdate, showError, showWarning])
  
  // Set history depth
  const setHistoryDepth = useCallback(async (depth: number) => {
    if (!checkWriteRateLimit(memoryKey)) {
      showError('메모리 변경이 너무 빠릅니다. 잠시 후 다시 시도하세요.')
      return
    }
    
    setLoading(true)
    setError(null)
    
    try {
      const response = await api.put('/api/generation/memory/state', {
        history_depth: depth,
        expected_version: memoryState?.memory_version,
      }, {
        params: { project_id: projectId, episode_id: episodeId },
      })
      
      const newState = response.data.generation_state
      setMemoryState(newState)
      
      broadcastUpdate('memory-updated', newState)
      
      if (response.data.conflicts_resolved) {
        setHasConflicts(true)
        showWarning('메모리가 다른 탭과 동기화되었습니다.')
      }
    } catch (err: any) {
      console.error('Set history depth failed:', err)
      setError('히스토리 설정 변경에 실패했습니다.')
      throw err
    } finally {
      setLoading(false)
    }
  }, [memoryKey, memoryState, projectId, episodeId, broadcastUpdate, showError, showWarning])
  
  // Add conversation turn
  const addTurn = useCallback(async (content: string, source: 'ui' | 'api' | 'sse', selection?: Record<string, any>) => {
    if (!memoryState?.memory_enabled) return
    
    if (!checkWriteRateLimit(memoryKey)) {
      console.warn('Rate limit exceeded for adding turn')
      return
    }
    
    // Throttle turn additions to avoid spam
    if (throttleTimeout.current) {
      clearTimeout(throttleTimeout.current)
    }
    
    throttleTimeout.current = setTimeout(async () => {
      try {
        const response = await api.post('/api/generation/memory/turns', {
          content,
          source,
          selection,
          expected_version: memoryState.memory_version,
        }, {
          params: { project_id: projectId, episode_id: episodeId },
        })
        
        const newState = response.data.generation_state
        setMemoryState(newState)
        
        broadcastUpdate('memory-updated', newState)
        
        if (response.data.conflicts_resolved) {
          setHasConflicts(true)
        }
      } catch (err: any) {
        console.error('Add turn failed:', err)
        // Silent failure for turn additions to avoid spam
      }
    }, 300) // 300ms throttle
  }, [memoryKey, memoryState, projectId, episodeId, broadcastUpdate])
  
  // Clear memory
  const clearMemory = useCallback(async (options: { clearHistory: boolean; clearEntityMemory: boolean }) => {
    if (!checkWriteRateLimit(memoryKey)) {
      showError('메모리 변경이 너무 빠릅니다. 잠시 후 다시 시도하세요.')
      return
    }
    
    setLoading(true)
    setError(null)
    
    try {
      const response = await api.delete('/api/generation/memory/clear', {
        params: { project_id: projectId, episode_id: episodeId },
        data: {
          clear_history: options.clearHistory,
          clear_entity_memory: options.clearEntityMemory,
          reset_version: true,
          reason: 'User requested memory clear',
        },
      })
      
      // Reload state after clearing
      await loadMemoryState()
      
      broadcastUpdate('memory-cleared', { timestamp: Date.now() })
    } catch (err: any) {
      console.error('Clear memory failed:', err)
      setError('메모리 삭제에 실패했습니다.')
      throw err
    } finally {
      setLoading(false)
    }
  }, [memoryKey, projectId, episodeId, loadMemoryState, broadcastUpdate, showError])
  
  // Compress memory
  const compressMemory = useCallback(async () => {
    if (!memoryState?.memory_enabled) return
    
    setLoading(true)
    setError(null)
    
    try {
      const response = await api.post('/api/generation/memory/compress', {
        force_compression: false,
      }, {
        params: { project_id: projectId, episode_id: episodeId },
      })
      
      if (response.data.compressed) {
        // Reload state to get compressed version
        await syncWithServer()
        
        broadcastUpdate('memory-updated', { 
          compressed: true,
          tokens_saved: response.data.result?.tokens_saved || 0
        })
      }
    } catch (err: any) {
      console.error('Compress memory failed:', err)
      setError('메모리 압축에 실패했습니다.')
      throw err
    } finally {
      setLoading(false)
    }
  }, [memoryState, projectId, episodeId, syncWithServer, broadcastUpdate])
  
  // Calculate metrics
  const metrics: MemoryMetrics = {
    turnsCount: memoryState?.history.length || 0,
    entityRenames: Object.keys(memoryState?.entity_memory.rename_map || {}).length,
    entityFacts: memoryState?.entity_memory.facts.length || 0,
    styleFlags: memoryState?.entity_memory.style_flags.length || 0,
    tokensUsed: 0, // Would calculate from content
    compressionRecommended: (memoryState?.history.length || 0) > (memoryState?.history_depth || 5) * 2,
  }
  
  // Load initial state on mount
  useEffect(() => {
    loadMemoryState()
  }, [loadMemoryState])
  
  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (syncInterval.current) {
        clearInterval(syncInterval.current)
      }
      if (throttleTimeout.current) {
        clearTimeout(throttleTimeout.current)
      }
      if (broadcastChannel.current) {
        broadcastChannel.current.close()
      }
    }
  }, [])
  
  return {
    // State
    memoryState,
    metrics,
    loading,
    error,
    
    // Actions
    toggleMemory,
    setHistoryDepth,
    addTurn,
    clearMemory,
    compressMemory,
    
    // Sync
    syncWithServer,
    hasConflicts,
  }
}