/**
 * Event Batching Manager
 * Handles batching, backoff, offline queuing, and visibility-aware timing
 */

import type { SubmitFeedbackRequest } from '@/shared/services/api/feedback'

interface BatchingConfig {
  maxBatchSize: number
  flushIntervalMs: number
  maxRetries: number
  baseDelayMs: number
  maxDelayMs: number
  jitterRatio: number
  maxOfflineQueueSize: number
  retentionDays: number
}

interface QueuedEvent {
  event: SubmitFeedbackRequest
  timestamp: number
  retryCount: number
  nextRetryAt: number
}

interface VisibilityTracker {
  isVisible: boolean
  lastVisibilityChange: number
  accumulatedTime: number
  startTime: number
}

class EventBatchingManager {
  private static instance: EventBatchingManager
  private config: BatchingConfig
  private queue: QueuedEvent[] = []
  private isOnline: boolean = navigator.onLine
  private visibilityTracker: VisibilityTracker
  private dbName = 'behavioral_analytics'
  private dbVersion = 1

  private constructor() {
    this.config = {
      maxBatchSize: 20,
      flushIntervalMs: 8000, // 8 seconds with jitter
      maxRetries: 3,
      baseDelayMs: 1000,
      maxDelayMs: 30000,
      jitterRatio: 0.1,
      maxOfflineQueueSize: 1000,
      retentionDays: 180,
    }

    this.visibilityTracker = {
      isVisible: document.visibilityState === 'visible',
      lastVisibilityChange: performance.now(),
      accumulatedTime: 0,
      startTime: performance.now(),
    }

    this.initializeEventListeners()
    this.initializeOfflineStorage()
    this.startFlushTimer()
  }

  public static getInstance(): EventBatchingManager {
    if (!EventBatchingManager.instance) {
      EventBatchingManager.instance = new EventBatchingManager()
    }
    return EventBatchingManager.instance
  }

  /**
   * Add event to batch queue
   */
  public async enqueueEvent(event: SubmitFeedbackRequest): Promise<void> {
    const queuedEvent: QueuedEvent = {
      event,
      timestamp: Date.now(),
      retryCount: 0,
      nextRetryAt: 0,
    }

    this.queue.push(queuedEvent)

    // Persist to offline storage
    await this.persistEvent(queuedEvent)

    // Flush if batch is full
    if (this.queue.length >= this.config.maxBatchSize) {
      await this.flushQueue()
    }
  }

  /**
   * Get visibility-aware time spent
   */
  public getVisibilityAwareTime(): number {
    const now = performance.now()
    let totalTime = this.visibilityTracker.accumulatedTime

    if (this.visibilityTracker.isVisible) {
      totalTime += now - this.visibilityTracker.lastVisibilityChange
    }

    return totalTime / 1000 // Convert to seconds
  }

  /**
   * Initialize event listeners
   */
  private initializeEventListeners(): void {
    // Online/offline detection
    window.addEventListener('online', () => {
      this.isOnline = true
      this.flushQueue()
    })
    
    window.addEventListener('offline', () => {
      this.isOnline = false
    })

    // Visibility tracking
    document.addEventListener('visibilitychange', () => {
      this.handleVisibilityChange()
    })

    // Page unload - use sendBeacon
    window.addEventListener('beforeunload', () => {
      this.flushWithBeacon()
    })

    window.addEventListener('pagehide', () => {
      this.flushWithBeacon()
    })

    // Focus/blur for additional visibility tracking
    window.addEventListener('blur', () => {
      this.handleVisibilityChange(false)
    })

    window.addEventListener('focus', () => {
      this.handleVisibilityChange(true)
    })
  }

  /**
   * Handle visibility changes for accurate time tracking
   */
  private handleVisibilityChange(forcedState?: boolean): void {
    const now = performance.now()
    const wasVisible = this.visibilityTracker.isVisible
    const isVisible = forcedState ?? document.visibilityState === 'visible'

    if (wasVisible && !isVisible) {
      // Became hidden - accumulate visible time
      this.visibilityTracker.accumulatedTime += 
        now - this.visibilityTracker.lastVisibilityChange
    }

    this.visibilityTracker.isVisible = isVisible
    this.visibilityTracker.lastVisibilityChange = now
  }

  /**
   * Initialize offline storage using IndexedDB
   */
  private async initializeOfflineStorage(): Promise<void> {
    if (typeof window === 'undefined' || !window.indexedDB) {
      return // Not available in this environment
    }

    try {
      await this.openDatabase()
      await this.loadPersistedEvents()
      await this.cleanupOldEvents()
    } catch (error) {
      console.warn('Failed to initialize offline storage:', error)
    }
  }

  /**
   * Open IndexedDB database
   */
  private openDatabase(): Promise<IDBDatabase> {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, this.dbVersion)
      
      request.onerror = () => reject(request.error)
      request.onsuccess = () => resolve(request.result)
      
      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result
        
        if (!db.objectStoreNames.contains('events')) {
          const store = db.createObjectStore('events', { keyPath: 'id', autoIncrement: true })
          store.createIndex('timestamp', 'timestamp', { unique: false })
          store.createIndex('event_id', 'event.event_id', { unique: false })
        }
      }
    })
  }

  /**
   * Persist event to IndexedDB
   */
  private async persistEvent(queuedEvent: QueuedEvent): Promise<void> {
    if (typeof window === 'undefined' || !window.indexedDB) return

    try {
      const db = await this.openDatabase()
      const transaction = db.transaction(['events'], 'readwrite')
      const store = transaction.objectStore('events')
      
      await new Promise<void>((resolve, reject) => {
        const request = store.add(queuedEvent)
        request.onsuccess = () => resolve()
        request.onerror = () => reject(request.error)
      })
      
      db.close()
    } catch (error) {
      console.warn('Failed to persist event:', error)
    }
  }

  /**
   * Load persisted events from IndexedDB
   */
  private async loadPersistedEvents(): Promise<void> {
    if (typeof window === 'undefined' || !window.indexedDB) return

    try {
      const db = await this.openDatabase()
      const transaction = db.transaction(['events'], 'readonly')
      const store = transaction.objectStore('events')
      
      const events = await new Promise<QueuedEvent[]>((resolve, reject) => {
        const request = store.getAll()
        request.onsuccess = () => resolve(request.result || [])
        request.onerror = () => reject(request.error)
      })
      
      // Add to queue (limit by max queue size)
      const eventsToLoad = events
        .slice(-this.config.maxOfflineQueueSize)
        .filter(event => this.isEventValid(event))
      
      this.queue.push(...eventsToLoad)
      
      db.close()
    } catch (error) {
      console.warn('Failed to load persisted events:', error)
    }
  }

  /**
   * Cleanup old events from IndexedDB
   */
  private async cleanupOldEvents(): Promise<void> {
    if (typeof window === 'undefined' || !window.indexedDB) return

    try {
      const db = await this.openDatabase()
      const transaction = db.transaction(['events'], 'readwrite')
      const store = transaction.objectStore('events')
      const index = store.index('timestamp')
      
      const cutoffTime = Date.now() - (this.config.retentionDays * 24 * 60 * 60 * 1000)
      const range = IDBKeyRange.upperBound(cutoffTime)
      
      await new Promise<void>((resolve, reject) => {
        const request = index.openCursor(range)
        request.onsuccess = (event) => {
          const cursor = (event.target as IDBRequest).result
          if (cursor) {
            cursor.delete()
            cursor.continue()
          } else {
            resolve()
          }
        }
        request.onerror = () => reject(request.error)
      })
      
      db.close()
    } catch (error) {
      console.warn('Failed to cleanup old events:', error)
    }
  }

  /**
   * Check if event is still valid (not expired)
   */
  private isEventValid(queuedEvent: QueuedEvent): boolean {
    const maxAge = this.config.retentionDays * 24 * 60 * 60 * 1000
    return (Date.now() - queuedEvent.timestamp) < maxAge
  }

  /**
   * Flush queue using sendBeacon for page unload
   */
  private flushWithBeacon(): void {
    if (this.queue.length === 0 || !this.isOnline) return

    const batch = this.queue.splice(0, this.config.maxBatchSize)
    const payload = JSON.stringify({ events: batch.map(q => q.event) })

    try {
      navigator.sendBeacon('/api/feedback/batch', payload)
    } catch (error) {
      // Fallback to fetch with keepalive
      fetch('/api/feedback/batch', {
        method: 'POST',
        body: payload,
        headers: { 'Content-Type': 'application/json' },
        keepalive: true,
      }).catch(() => {
        // Silent fail - events will be retried on next session
      })
    }
  }

  /**
   * Flush queue with retry logic
   */
  private async flushQueue(): Promise<void> {
    if (this.queue.length === 0 || !this.isOnline) return

    const now = Date.now()
    const readyEvents = this.queue.filter(event => event.nextRetryAt <= now)
    
    if (readyEvents.length === 0) return

    const batch = readyEvents.splice(0, this.config.maxBatchSize)
    
    try {
      const response = await fetch('/api/feedback/batch', {
        method: 'POST',
        body: JSON.stringify({ events: batch.map(q => q.event) }),
        headers: { 'Content-Type': 'application/json' },
      })

      if (response.ok) {
        // Remove successful events from queue
        batch.forEach(event => {
          const index = this.queue.indexOf(event)
          if (index > -1) {
            this.queue.splice(index, 1)
          }
        })
      } else {
        throw new Error(`HTTP ${response.status}`)
      }
    } catch (error) {
      // Apply exponential backoff with jitter
      batch.forEach(event => {
        event.retryCount++
        
        if (event.retryCount < this.config.maxRetries) {
          const delay = Math.min(
            this.config.baseDelayMs * Math.pow(2, event.retryCount - 1),
            this.config.maxDelayMs
          )
          
          const jitter = delay * this.config.jitterRatio * Math.random()
          event.nextRetryAt = Date.now() + delay + jitter
        } else {
          // Max retries exceeded - remove from queue
          const index = this.queue.indexOf(event)
          if (index > -1) {
            this.queue.splice(index, 1)
          }
        }
      })
    }
  }

  /**
   * Start periodic flush timer
   */
  private startFlushTimer(): void {
    const scheduleNext = () => {
      const interval = this.config.flushIntervalMs
      const jitter = interval * this.config.jitterRatio * Math.random()
      
      window.setTimeout(() => {
        this.flushQueue().finally(scheduleNext)
      }, interval + jitter)
    }

    scheduleNext()
  }

  /**
   * Get queue statistics
   */
  public getStatistics() {
    const now = Date.now()
    const pendingRetries = this.queue.filter(e => e.nextRetryAt > now).length
    
    return {
      queueSize: this.queue.length,
      pendingRetries,
      isOnline: this.isOnline,
      visibilityAwareTime: this.getVisibilityAwareTime(),
      isVisible: this.visibilityTracker.isVisible,
    }
  }
}

export const eventBatchingManager = EventBatchingManager.getInstance()