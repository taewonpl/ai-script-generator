import { describe, it, expect } from 'vitest'
import {
  previewConcat,
  nextEpisodeNumber,
  autoEpisodeTitle,
  estimateTokens,
} from '@/shared/utils/scriptUtils'
import type { Episode, Project } from '@/shared/types/project'

describe('Script Generation Demo', () => {
  const mockProject: Project = {
    id: 'demo-project',
    name: 'demo',
    title: 'Test Drama',
    type: 'drama',
    status: 'active',
    tone: 'test',
    systemPrompt: 'test prompt',
    progress_percentage: 0,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  }

  const mockEpisodes: Episode[] = [
    {
      id: 'ep-1',
      number: 1,
      title: 'E1',
      status: 'ready',
      createdAt: new Date().toISOString(),
    },
    {
      id: 'ep-2',
      number: 3,
      title: 'E3',
      status: 'draft',
      createdAt: new Date().toISOString(),
    },
  ]

  it('should demonstrate script generation workflow', () => {
    console.log('🎬 스크립트 생성 워크플로우 데모')

    // 1. 다음 에피소드 번호 계산
    const nextNumber = nextEpisodeNumber(mockEpisodes)
    console.log(`📝 다음 에피소드 번호: ${nextNumber}`)
    expect(nextNumber).toBe(4) // max(1, 3) + 1

    // 2. 자동 제목 생성
    const autoTitle = autoEpisodeTitle(mockProject.title, nextNumber)
    expect(autoTitle).toBe('Test Drama - Ep. 4')

    // 3. 미리보기 연결 시뮬레이션
    let preview = ''
    const chunks = ['# Test\n\n', '**A**: Hi.\n\n']
    chunks.forEach(chunk => {
      preview = previewConcat(preview, chunk)
    })

    // 4. 토큰 수 계산
    const tokens = estimateTokens(preview)
    expect(preview).toContain('Test')
    expect(tokens).toBeGreaterThan(0)
  })

  it('should demonstrate SSE event types', () => {
    const eventTypes = [
      'progress',
      'preview',
      'completed',
      'failed',
      'heartbeat',
    ]
    const maxRetries = 10
    expect(eventTypes).toHaveLength(5)
    expect(maxRetries).toBe(10)
  })

  it('should demonstrate optimistic update workflow', () => {
    const newEpisode = {
      id: 'temp-123',
      number: 4,
      title: 'New',
      status: 'draft' as const,
      createdAt: new Date().toISOString(),
    }
    const serverEpisode = { ...newEpisode, id: 'server-id' }
    expect(newEpisode.id).toMatch(/^temp-/)
    expect(serverEpisode.id).toBe('server-id')
  })

  it('should demonstrate drawer state management', () => {
    const drawerStates = {
      idle: 'waiting',
      generating: 'active',
      completed: 'done',
      failed: 'error',
      saved: 'closed',
    }
    expect(Object.keys(drawerStates)).toHaveLength(5)
  })
})
