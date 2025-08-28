/**
 * React Router integration for SSE cleanup on route changes with work protection
 * Ensures SSE connections are properly closed when navigating away
 */

import { useEffect, useRef } from 'react'
import { useLocation } from 'react-router-dom'

interface SSECleanupItem {
  id: string
  disconnect: () => void
  description?: string
  scopeId?: string
  canContinueInBackground?: boolean
}

/**
 * Hook to register SSE connections for automatic cleanup on route changes
 * 
 * Usage:
 * ```tsx
 * const sseCleanup = useSSECleanup()
 * 
 * // Register SSE connection
 * useEffect(() => {
 *   const connection = new SSEConnection(jobId, handleMessage)
 *   connection.connect()
 *   
 *   sseCleanup.register(jobId, () => connection.disconnect(), 'Generation job SSE')
 *   
 *   return () => {
 *     sseCleanup.unregister(jobId)
 *     connection.disconnect()
 *   }
 * }, [jobId])
 * ```
 */
export function useSSECleanup() {
  const location = useLocation()
  const connectionsRef = useRef<Map<string, SSECleanupItem>>(new Map())
  const previousLocationRef = useRef(location.pathname)

  // Clean up all SSE connections on route change
  useEffect(() => {
    const currentPath = location.pathname
    const previousPath = previousLocationRef.current

    if (currentPath !== previousPath && connectionsRef.current.size > 0) {
      console.log(`🛤️ Route change detected: ${previousPath} → ${currentPath}`)
      console.log(`🔌 Cleaning up ${connectionsRef.current.size} SSE connections...`)

      // Clean up all registered connections
      const cleanupPromises: Promise<void>[] = []
      connectionsRef.current.forEach((item, id) => {
        cleanupPromises.push(
          Promise.resolve().then(() => {
            try {
              console.log(`🧹 Cleaning up SSE connection: ${id} (${item.description || 'unnamed'})`)
              item.disconnect()
            } catch (error) {
              console.error(`❌ Error cleaning up SSE connection ${id}:`, error)
            }
          })
        )
      })

      // Wait for all cleanups to complete, then clear the registry
      Promise.allSettled(cleanupPromises).then((results) => {
        const successful = results.filter(r => r.status === 'fulfilled').length
        const failed = results.filter(r => r.status === 'rejected').length
        
        console.log(`✅ SSE cleanup completed: ${successful} successful, ${failed} failed`)
        connectionsRef.current.clear()

        // Record route change cleanup metrics
        if (import.meta.env.DEV || window.location.hostname !== 'localhost') {
          console.log('📊 Recording route change cleanup metrics')
        }
      })
    }

    previousLocationRef.current = currentPath
  }, [location.pathname])

  // Clean up all connections on unmount
  useEffect(() => {
    return () => {
      if (connectionsRef.current.size > 0) {
        console.log('🧹 Component unmount: cleaning up SSE connections')
        connectionsRef.current.forEach((item, id) => {
          try {
            item.disconnect()
          } catch (error) {
            console.error(`❌ Error during unmount cleanup of SSE ${id}:`, error)
          }
        })
        connectionsRef.current.clear()
      }
    }
  }, [])

  const register = (
    id: string, 
    disconnect: () => void, 
    description?: string, 
    options?: { scopeId?: string; canContinueInBackground?: boolean }
  ) => {
    connectionsRef.current.set(id, { 
      id, 
      disconnect, 
      description,
      scopeId: options?.scopeId,
      canContinueInBackground: options?.canContinueInBackground,
    })
    
    if (import.meta.env.DEV) {
      console.log(`📡 Registered SSE connection for cleanup: ${id} (${description || 'unnamed'}, scope: ${options?.scopeId || 'default'})`)
    }
  }

  const unregister = (id: string) => {
    const removed = connectionsRef.current.delete(id)
    
    if (import.meta.env.DEV && removed) {
      console.log(`📡 Unregistered SSE connection: ${id}`)
    }
    
    return removed
  }

  const getActiveConnections = () => {
    return Array.from(connectionsRef.current.entries()).map(([id, item]) => ({
      id,
      description: item.description,
      scopeId: item.scopeId,
      canContinueInBackground: item.canContinueInBackground,
    }))
  }

  const forceCleanup = () => {
    console.log(`🚨 Force cleanup requested for ${connectionsRef.current.size} connections`)
    
    connectionsRef.current.forEach((item, id) => {
      try {
        item.disconnect()
        console.log(`🧹 Force cleaned up: ${id}`)
      } catch (error) {
        console.error(`❌ Error during force cleanup of ${id}:`, error)
      }
    })
    
    connectionsRef.current.clear()
  }

  return {
    register,
    unregister,
    getActiveConnections,
    forceCleanup,
    activeConnectionCount: connectionsRef.current.size,
  }
}

/**
 * Enhanced version for global SSE cleanup management
 * Provides app-level SSE connection tracking and cleanup
 */
class SSECleanupManager {
  private static instance: SSECleanupManager | null = null
  private connections = new Map<string, SSECleanupItem>()

  static getInstance(): SSECleanupManager {
    if (!this.instance) {
      this.instance = new SSECleanupManager()
    }
    return this.instance
  }

  register(id: string, disconnect: () => void, description?: string, options?: { scopeId?: string; canContinueInBackground?: boolean }): void {
    this.connections.set(id, { 
      id, 
      disconnect, 
      description,
      scopeId: options?.scopeId,
      canContinueInBackground: options?.canContinueInBackground,
    })
    console.log(`🌐 Global SSE registered: ${id} (${description || 'unnamed'}, scope: ${options?.scopeId || 'default'})`)
  }

  unregister(id: string): boolean {
    const removed = this.connections.delete(id)
    if (removed) {
      console.log(`🌐 Global SSE unregistered: ${id}`)
    }
    return removed
  }

  cleanup(reason = 'manual'): void {
    if (this.connections.size === 0) {
      console.log('🌐 No SSE connections to clean up')
      return
    }

    console.log(`🌐 Global SSE cleanup (${reason}): ${this.connections.size} connections`)
    
    this.connections.forEach((item, id) => {
      try {
        item.disconnect()
        console.log(`🧹 Global cleanup: ${id}`)
      } catch (error) {
        console.error(`❌ Global cleanup error for ${id}:`, error)
      }
    })

    this.connections.clear()
  }

  getStatus() {
    return {
      activeConnections: this.connections.size,
      connections: Array.from(this.connections.entries()).map(([id, item]) => ({
        id,
        description: item.description,
        scopeId: item.scopeId,
        canContinueInBackground: item.canContinueInBackground,
      })),
    }
  }
}

export const globalSSECleanup = SSECleanupManager.getInstance()

// Global cleanup on page unload/refresh
if (typeof window !== 'undefined') {
  window.addEventListener('beforeunload', () => {
    globalSSECleanup.cleanup('page_unload')
  })

  // Cleanup on browser back/forward navigation
  window.addEventListener('popstate', () => {
    console.log('🔄 Browser navigation detected, cleaning up SSE connections')
    globalSSECleanup.cleanup('browser_navigation')
  })
}