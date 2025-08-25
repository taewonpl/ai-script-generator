import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { Episode, CreateEpisodeRequest } from '@/shared/types/project'
import { nextEpisodeNumber, autoEpisodeTitle } from '@/shared/utils/scriptUtils'

/**
 * 낙관적 업데이트를 포함한 에피소드 관리 훅
 */
export function useOptimisticEpisodes(projectId: string) {
  const queryClient = useQueryClient()
  const episodesQueryKey = ['episodes', projectId]

  // 에피소드 생성 mutation (낙관적 업데이트)
  const createEpisodeMutation = useMutation({
    mutationFn: async (request: CreateEpisodeRequest) => {
      const response = await fetch(`/api/projects/${projectId}/episodes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      })

      if (!response.ok) {
        throw new Error(`Failed to create episode: ${response.statusText}`)
      }

      const result = await response.json()
      return result.data as Episode
    },

    // 낙관적 업데이트: 요청 전에 UI 먼저 업데이트
    onMutate: async newEpisode => {
      // 진행 중인 쿼리 취소
      await queryClient.cancelQueries({ queryKey: episodesQueryKey })

      // 이전 데이터 백업
      const previousEpisodes =
        queryClient.getQueryData<Episode[]>(episodesQueryKey) || []

      // 낙관적으로 새 에피소드 추가
      const optimisticEpisode: Episode = {
        id: `temp-${Date.now()}`, // 임시 ID
        number: newEpisode.number,
        title: newEpisode.title,
        ...(newEpisode.description !== undefined && {
          description: newEpisode.description,
        }),
        status: 'draft',
        createdAt: new Date().toISOString(),
      }

      queryClient.setQueryData<Episode[]>(episodesQueryKey, [
        ...previousEpisodes,
        optimisticEpisode,
      ])

      // 롤백용 컨텍스트 반환
      return { previousEpisodes, optimisticEpisode }
    },

    // 성공 시: 서버 데이터로 낙관적 데이터 교체
    onSuccess: (serverEpisode, _variables, context) => {
      queryClient.setQueryData<Episode[]>(episodesQueryKey, episodes => {
        if (!episodes || !context) return episodes

        return episodes.map(episode =>
          episode.id === context.optimisticEpisode.id ? serverEpisode : episode,
        )
      })

      // 프로젝트 진행률 업데이트
      queryClient.invalidateQueries({ queryKey: ['project', projectId] })
    },

    // 실패 시: 이전 상태로 롤백
    onError: (error, _variables, context) => {
      if (context?.previousEpisodes) {
        queryClient.setQueryData(episodesQueryKey, context.previousEpisodes)
      }
      console.error('Failed to create episode:', error)
    },

    // 완료 후: 관련 쿼리 갱신
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: episodesQueryKey })
    },
  })

  // 에피소드 업데이트 mutation (낙관적 업데이트)
  const updateEpisodeMutation = useMutation({
    mutationFn: async ({
      episodeId,
      updates,
    }: {
      episodeId: string
      updates: Partial<Episode>
    }) => {
      const response = await fetch(`/api/episodes/${episodeId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      })

      if (!response.ok) {
        throw new Error(`Failed to update episode: ${response.statusText}`)
      }

      const result = await response.json()
      return result.data as Episode
    },

    onMutate: async ({ episodeId, updates }) => {
      await queryClient.cancelQueries({ queryKey: episodesQueryKey })

      const previousEpisodes =
        queryClient.getQueryData<Episode[]>(episodesQueryKey) || []

      // 낙관적 업데이트
      queryClient.setQueryData<Episode[]>(episodesQueryKey, episodes => {
        if (!episodes) return episodes

        return episodes.map(episode =>
          episode.id === episodeId
            ? { ...episode, ...updates, updatedAt: new Date().toISOString() }
            : episode,
        )
      })

      return { previousEpisodes, episodeId, updates }
    },

    onSuccess: serverEpisode => {
      queryClient.setQueryData<Episode[]>(episodesQueryKey, episodes => {
        if (!episodes) return episodes

        return episodes.map(episode =>
          episode.id === serverEpisode.id ? serverEpisode : episode,
        )
      })
    },

    onError: (error, _variables, context) => {
      if (context?.previousEpisodes) {
        queryClient.setQueryData(episodesQueryKey, context.previousEpisodes)
      }
      console.error('Failed to update episode:', error)
    },

    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: episodesQueryKey })
      queryClient.invalidateQueries({ queryKey: ['project', projectId] })
    },
  })

  // 에피소드 삭제 mutation (낙관적 업데이트)
  const deleteEpisodeMutation = useMutation({
    mutationFn: async (episodeId: string) => {
      const response = await fetch(`/api/episodes/${episodeId}`, {
        method: 'DELETE',
      })

      if (!response.ok) {
        throw new Error(`Failed to delete episode: ${response.statusText}`)
      }

      return { success: true }
    },

    onMutate: async episodeId => {
      await queryClient.cancelQueries({ queryKey: episodesQueryKey })

      const previousEpisodes =
        queryClient.getQueryData<Episode[]>(episodesQueryKey) || []

      // 낙관적으로 에피소드 제거
      queryClient.setQueryData<Episode[]>(
        episodesQueryKey,
        episodes => episodes?.filter(ep => ep.id !== episodeId) || [],
      )

      return { previousEpisodes, episodeId }
    },

    onError: (error, _variables, context) => {
      if (context?.previousEpisodes) {
        queryClient.setQueryData(episodesQueryKey, context.previousEpisodes)
      }
      console.error('Failed to delete episode:', error)
    },

    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: episodesQueryKey })
      queryClient.invalidateQueries({ queryKey: ['project', projectId] })
    },
  })

  // 스크립트 저장 mutation (낙관적 업데이트)
  const saveScriptMutation = useMutation({
    mutationFn: async ({
      episodeId,
      script,
    }: {
      episodeId: string
      script: { markdown: string; tokens: number }
    }) => {
      const response = await fetch(`/api/episodes/${episodeId}/script`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ script }),
      })

      if (!response.ok) {
        throw new Error(`Failed to save script: ${response.statusText}`)
      }

      const result = await response.json()
      return result.data as Episode
    },

    onMutate: async ({ episodeId, script }) => {
      await queryClient.cancelQueries({ queryKey: episodesQueryKey })

      const previousEpisodes =
        queryClient.getQueryData<Episode[]>(episodesQueryKey) || []

      // 낙관적으로 스크립트 저장
      queryClient.setQueryData<Episode[]>(episodesQueryKey, episodes => {
        if (!episodes) return episodes

        return episodes.map(episode =>
          episode.id === episodeId
            ? {
                ...episode,
                script,
                status: 'ready' as const,
                updatedAt: new Date().toISOString(),
              }
            : episode,
        )
      })

      return { previousEpisodes, episodeId }
    },

    onSuccess: serverEpisode => {
      queryClient.setQueryData<Episode[]>(episodesQueryKey, episodes => {
        if (!episodes) return episodes

        return episodes.map(episode =>
          episode.id === serverEpisode.id ? serverEpisode : episode,
        )
      })
    },

    onError: (error, _variables, context) => {
      if (context?.previousEpisodes) {
        queryClient.setQueryData(episodesQueryKey, context.previousEpisodes)
      }
      console.error('Failed to save script:', error)
    },

    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: episodesQueryKey })
      queryClient.invalidateQueries({ queryKey: ['project', projectId] })
    },
  })

  // 유틸리티 함수들
  const getNextEpisodeNumber = () => {
    const episodes = queryClient.getQueryData<Episode[]>(episodesQueryKey) || []
    return nextEpisodeNumber(episodes)
  }

  const createAutoEpisode = (projectTitle: string) => {
    const episodeNumber = getNextEpisodeNumber()
    const title = autoEpisodeTitle(projectTitle, episodeNumber)

    return createEpisodeMutation.mutateAsync({
      projectId,
      number: episodeNumber,
      title,
      description: `${projectTitle}의 ${episodeNumber}번째 에피소드`,
    })
  }

  return {
    // Mutations
    createEpisode: createEpisodeMutation.mutateAsync,
    updateEpisode: updateEpisodeMutation.mutateAsync,
    deleteEpisode: deleteEpisodeMutation.mutateAsync,
    saveScript: saveScriptMutation.mutateAsync,

    // 유틸리티
    getNextEpisodeNumber,
    createAutoEpisode,

    // 상태
    isCreating: createEpisodeMutation.isPending,
    isUpdating: updateEpisodeMutation.isPending,
    isDeleting: deleteEpisodeMutation.isPending,
    isSaving: saveScriptMutation.isPending,

    // 에러
    createError: createEpisodeMutation.error?.message || null,
    updateError: updateEpisodeMutation.error?.message || null,
    deleteError: deleteEpisodeMutation.error?.message || null,
    saveError: saveScriptMutation.error?.message || null,
  }
}
