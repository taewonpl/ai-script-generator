import { useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useWebSocket } from './useWebSocket'
import type { GenerationUpdate, SystemUpdate } from '@/shared/types/api'
import { generationKeys } from './useGeneration'
import { projectKeys } from './useProjects'
import { coreKeys } from './useCore'

// Real-time generation updates
export function useRealTimeGenerationUpdates(generationId?: string) {
  const queryClient = useQueryClient()

  const { isConnected } = useWebSocket(
    generationId ? `/ws/generations/${generationId}` : '',
    {
      onMessage: (data: GenerationUpdate) => {
        if (!generationId) return

        // Update generation status in cache
        queryClient.setQueryData(
          generationKeys.detail(generationId),
          (old: any) => {
            if (!old) return old
            return {
              ...old,
              data: {
                ...old.data,
                status: data.status,
                progress: data.progress,
                updated_at: new Date().toISOString(),
                ...(data.error && { error_message: data.error }),
              },
            }
          },
        )

        // If generation is completed or failed, invalidate related queries
        if (data.status === 'completed' || data.status === 'failed') {
          queryClient.invalidateQueries({ queryKey: generationKeys.active() })
          queryClient.invalidateQueries({
            queryKey: generationKeys.completed(),
          })
          queryClient.invalidateQueries({ queryKey: generationKeys.user() })
          queryClient.invalidateQueries({ queryKey: generationKeys.queue() })
        }
      },
      onConnect: () => {
        console.log(`Connected to generation ${generationId} updates`)
      },
    },
  )

  return { isConnected }
}

// Real-time system status updates
export function useRealTimeSystemUpdates() {
  const queryClient = useQueryClient()

  const { isConnected } = useWebSocket('/ws/system', {
    onMessage: (data: SystemUpdate) => {
      switch (data.type) {
        case 'service_status':
          // Update specific service status
          queryClient.setQueryData(coreKeys.systemStatus(), (old: any) => {
            if (!old) return old
            return {
              ...old,
              data: {
                ...old.data,
                services: old.data.services.map((service: any) =>
                  service.service === data.data.service
                    ? { ...service, ...data.data }
                    : service,
                ),
              },
            }
          })
          break

        case 'metrics':
          // Update system metrics
          queryClient.setQueryData(coreKeys.systemStatus(), (old: any) => {
            if (!old) return old
            return {
              ...old,
              data: {
                ...old.data,
                metrics: data.data,
              },
            }
          })
          break

        case 'alert':
          // Add new alert
          queryClient.setQueryData(coreKeys.systemStatus(), (old: any) => {
            if (!old) return old
            return {
              ...old,
              data: {
                ...old.data,
                alerts: [data.data, ...old.data.alerts],
              },
            }
          })
          break
      }
    },
  })

  return { isConnected }
}

// Real-time project updates
export function useRealTimeProjectUpdates(projectId?: string) {
  const queryClient = useQueryClient()

  const { isConnected } = useWebSocket(
    projectId ? `/ws/projects/${projectId}` : '',
    {
      onMessage: (data: any) => {
        if (!projectId) return

        switch (data.type) {
          case 'project_updated':
            // Update project in cache
            queryClient.setQueryData(
              projectKeys.detail(projectId),
              (old: any) => {
                if (!old) return old
                return {
                  ...old,
                  data: { ...old.data, ...data.data },
                }
              },
            )

            // Invalidate project lists
            queryClient.invalidateQueries({ queryKey: projectKeys.lists() })
            break

          case 'episode_added':
          case 'episode_updated':
          case 'episode_deleted':
            // Invalidate episodes data
            queryClient.invalidateQueries({
              queryKey: ['episodes', 'list', projectId],
            })

            // Update project episode count
            queryClient.invalidateQueries({
              queryKey: projectKeys.detail(projectId),
            })
            break

          case 'script_added':
          case 'script_updated':
          case 'script_deleted':
            // Invalidate scripts data
            queryClient.invalidateQueries({
              queryKey: ['scripts', 'list', projectId],
            })

            // Update project script count
            queryClient.invalidateQueries({
              queryKey: projectKeys.detail(projectId),
            })
            break
        }
      },
    },
  )

  return { isConnected }
}

// Real-time queue updates
export function useRealTimeQueueUpdates() {
  const queryClient = useQueryClient()

  const { isConnected } = useWebSocket('/ws/queue', {
    onMessage: (data: any) => {
      switch (data.type) {
        case 'queue_updated':
          // Update queue status
          queryClient.setQueryData(generationKeys.queue(), (old: any) => {
            if (!old) return old
            return {
              ...old,
              data: { ...old.data, ...data.data },
            }
          })
          break

        case 'generation_started':
          // Move generation from queue to active
          queryClient.invalidateQueries({ queryKey: generationKeys.queue() })
          queryClient.invalidateQueries({ queryKey: generationKeys.active() })
          break

        case 'generation_completed':
        case 'generation_failed':
          // Update generation status and refresh relevant queries
          if (data.generation_id) {
            queryClient.setQueryData(
              generationKeys.detail(data.generation_id),
              (old: any) => {
                if (!old) return old
                return {
                  ...old,
                  data: {
                    ...old.data,
                    status:
                      data.type === 'generation_completed'
                        ? 'completed'
                        : 'failed',
                    ...(data.error && { error_message: data.error }),
                    completed_at: new Date().toISOString(),
                  },
                }
              },
            )

            queryClient.invalidateQueries({ queryKey: generationKeys.active() })
            queryClient.invalidateQueries({
              queryKey: generationKeys.completed(),
            })
            queryClient.invalidateQueries({ queryKey: generationKeys.queue() })
          }
          break
      }
    },
  })

  return { isConnected }
}

// Composite hook for all real-time updates
export function useRealTimeUpdates(
  config: {
    enableSystemUpdates?: boolean
    enableQueueUpdates?: boolean
    projectId?: string
    generationId?: string
  } = {},
) {
  const {
    enableSystemUpdates = true,
    enableQueueUpdates = true,
    projectId,
    generationId,
  } = config

  const systemConnection = enableSystemUpdates
    ? useRealTimeSystemUpdates()
    : null
  const queueConnection = enableQueueUpdates ? useRealTimeQueueUpdates() : null
  const projectConnection = projectId
    ? useRealTimeProjectUpdates(projectId)
    : null
  const generationConnection = generationId
    ? useRealTimeGenerationUpdates(generationId)
    : null

  const isConnected = [
    systemConnection?.isConnected,
    queueConnection?.isConnected,
    projectConnection?.isConnected,
    generationConnection?.isConnected,
  ]
    .filter(Boolean)
    .every(Boolean)

  return {
    isConnected,
    connections: {
      system: systemConnection?.isConnected ?? false,
      queue: queueConnection?.isConnected ?? false,
      project: projectConnection?.isConnected ?? false,
      generation: generationConnection?.isConnected ?? false,
    },
  }
}

// Hook for monitoring connection health
export function useConnectionHealth() {
  const queryClient = useQueryClient()

  useEffect(() => {
    const handleOnline = () => {
      // Invalidate all queries when coming back online
      queryClient.invalidateQueries()
    }

    const handleOffline = () => {
      // Pause queries when offline
      queryClient
        .getQueryCache()
        .findAll()
        .forEach(query => {
          query.cancel()
        })
    }

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [queryClient])

  return {
    isOnline: navigator.onLine,
  }
}
