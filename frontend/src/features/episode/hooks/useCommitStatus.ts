/**
 * Hook for managing episode commit status and history
 * Tracks last committed timestamp and provides status information
 */

import { useCallback } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'

import { getEpisodeCommits, type EpisodeCommit } from '@/shared/services/api/feedback'

export interface CommitStatus {
  /** Last commit timestamp if any */
  lastCommittedAt: string | null
  /** Total number of commits for this episode */
  commitCount: number
  /** Whether this episode has been committed before */
  hasCommits: boolean
  /** Latest commit ID if any */
  latestCommitId: string | null
  /** Whether the commit data is loading */
  isLoading: boolean
  /** Error if commit data failed to load */
  error: Error | null
  /** Refresh commit status */
  refresh: () => Promise<void>
  /** Update commit status optimistically */
  updateCommitStatus: (commitId: string, timestamp: string) => void
}

/**
 * Hook to manage episode commit status
 * @param episodeId - Episode UUID
 * @param enabled - Whether to fetch commit data
 */
export function useCommitStatus(
  episodeId: string,
  enabled: boolean = true
): CommitStatus {
  const queryClient = useQueryClient()
  
  // Query for episode commits
  const {
    data: commitsData,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['episode-commits', episodeId],
    queryFn: () => getEpisodeCommits(episodeId),
    enabled,
    staleTime: 30000, // 30 seconds
    refetchOnWindowFocus: false,
  })

  // Refresh function
  const refresh = useCallback(async () => {
    await refetch()
  }, [refetch])

  // Update commit status when new commit is made (exposed for external use)
  const updateCommitStatus = useCallback(
    (commitId: string, timestamp: string) => {
      // Optimistically update the query cache
      queryClient.setQueryData(['episode-commits', episodeId], (oldData: any) => {
        if (!oldData) return oldData
        
        const newCommit: EpisodeCommit = {
          commit_id: commitId,
          event_type: 'commit_positive',
          client_timestamp: timestamp,
          server_timestamp: timestamp,
          request_id: '',
          trace_id: '',
          created_at: timestamp,
        }
        
        return {
          ...oldData,
          commits: [newCommit, ...oldData.commits],
          total: oldData.total + 1,
        }
      })
      
      // Refresh from server to ensure consistency
      setTimeout(() => refresh(), 1000)
    },
    [queryClient, episodeId, refresh]
  )

  // Derived state
  const commits = commitsData?.commits || []
  const latestCommit = commits[0] || null
  const lastCommittedAt = latestCommit?.server_timestamp || null
  const commitCount = commitsData?.total || 0
  const hasCommits = commitCount > 0
  const latestCommitId = latestCommit?.commit_id || null

  return {
    lastCommittedAt,
    commitCount,
    hasCommits,
    latestCommitId,
    isLoading,
    error: error as Error | null,
    refresh,
    updateCommitStatus, // Expose for external use
  }
}

/**
 * Format commit timestamp for display
 * @param timestamp - ISO timestamp string
 * @param language - Display language
 */
export function formatCommitTimestamp(
  timestamp: string | null,
  language: 'kr' | 'en' = 'kr'
): string {
  if (!timestamp) return ''
  
  try {
    const date = new Date(timestamp)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMinutes = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMinutes / 60)
    const diffDays = Math.floor(diffHours / 24)
    
    if (language === 'kr') {
      if (diffMinutes < 1) return '방금 전'
      if (diffMinutes < 60) return `${diffMinutes}분 전`
      if (diffHours < 24) return `${diffHours}시간 전`
      if (diffDays < 7) return `${diffDays}일 전`
      return date.toLocaleDateString('ko-KR', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    } else {
      if (diffMinutes < 1) return 'just now'
      if (diffMinutes < 60) return `${diffMinutes}m ago`
      if (diffHours < 24) return `${diffHours}h ago`
      if (diffDays < 7) return `${diffDays}d ago`
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    }
  } catch {
    return ''
  }
}