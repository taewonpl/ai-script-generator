import { describe, it, expect } from 'vitest'
import type { Project, Episode } from '@/shared/types/project'
import {
  previewConcat,
  nextEpisodeNumber,
  autoEpisodeTitle,
  GENERATION_POLICY,
  getEpisodeStatusLabel,
  buildGenerationPrompt,
  estimateTokens,
  calculateScriptProgress,
} from '../scriptUtils'

// Mock 데이터
const mockProject: Project = {
  id: 'project-1',
  name: 'test-project',
  title: '테스트 드라마',
  type: 'drama',
  status: 'active',
  tone: '로맨틱하고 감동적인',
  systemPrompt: '당신은 전문적인 드라마 작가입니다.',
  progress_percentage: 50,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-02T00:00:00Z',
}

const mockEpisodes: Episode[] = [
  {
    id: 'ep-1',
    number: 1,
    title: '첫 만남',
    description: '주인공들의 첫 만남',
    status: 'ready',
    script: {
      markdown: '# 첫 만남\n주인공들이 만난다.',
      tokens: 100,
    },
    createdAt: '2024-01-01T00:00:00Z',
  },
  {
    id: 'ep-2',
    number: 2,
    title: '갈등',
    status: 'draft',
    createdAt: '2024-01-02T00:00:00Z',
  },
  {
    id: 'ep-3',
    number: 5,
    title: '해결',
    status: 'generating',
    createdAt: '2024-01-03T00:00:00Z',
  },
]

describe('scriptUtils', () => {
  describe('previewConcat', () => {
    it('should concatenate prev and chunk with newline when prev exists', () => {
      const result = previewConcat('기존 내용', '새로운 내용')
      expect(result).toBe('기존 내용\n새로운 내용')
    })

    it('should return chunk when prev is empty', () => {
      const result = previewConcat('', '새로운 내용')
      expect(result).toBe('새로운 내용')
    })

    it('should return chunk when prev is falsy', () => {
      const result = previewConcat(null as any, '새로운 내용')
      expect(result).toBe('새로운 내용')
    })
  })

  describe('nextEpisodeNumber', () => {
    it('should return 1 for empty episodes array', () => {
      const result = nextEpisodeNumber([])
      expect(result).toBe(1)
    })

    it('should return max episode number + 1', () => {
      const result = nextEpisodeNumber(mockEpisodes)
      expect(result).toBe(6) // max(1, 2, 5) + 1 = 6
    })

    it('should handle single episode', () => {
      const singleEpisode = mockEpisodes.slice(0, 1)
      const result = nextEpisodeNumber(singleEpisode)
      expect(result).toBe(2)
    })
  })

  describe('autoEpisodeTitle', () => {
    it('should generate correct episode title format', () => {
      const result = autoEpisodeTitle('테스트 드라마', 3)
      expect(result).toBe('테스트 드라마 - Ep. 3')
    })

    it('should handle single digit episode numbers', () => {
      const result = autoEpisodeTitle('드라마', 1)
      expect(result).toBe('드라마 - Ep. 1')
    })

    it('should handle double digit episode numbers', () => {
      const result = autoEpisodeTitle('드라마', 15)
      expect(result).toBe('드라마 - Ep. 15')
    })
  })

  describe('GENERATION_POLICY', () => {
    it('should have correct LENGTH constant', () => {
      expect(GENERATION_POLICY.LENGTH).toBe('2 pages')
    })

    it('should return project tone', () => {
      const result = GENERATION_POLICY.getTone(mockProject)
      expect(result).toBe('로맨틱하고 감동적인')
    })

    it('should return project system prompt', () => {
      const result = GENERATION_POLICY.getSystemPrompt(mockProject)
      expect(result).toBe('당신은 전문적인 드라마 작가입니다.')
    })
  })

  describe('getEpisodeStatusLabel', () => {
    it('should return correct Korean labels for all statuses', () => {
      expect(getEpisodeStatusLabel('draft')).toBe('초안')
      expect(getEpisodeStatusLabel('ready')).toBe('준비완료')
      expect(getEpisodeStatusLabel('generating')).toBe('생성중')
      expect(getEpisodeStatusLabel('failed')).toBe('실패')
    })
  })

  describe('buildGenerationPrompt', () => {
    it('should build correct prompt without custom prompt', () => {
      const episode = mockEpisodes[0]!
      const result = buildGenerationPrompt(mockProject, episode)

      expect(result).toContain('당신은 전문적인 드라마 작가입니다.')
      expect(result).toContain('제목: 테스트 드라마')
      expect(result).toContain('톤: 로맨틱하고 감동적인')
      expect(result).toContain('분량: 2 pages')
      expect(result).toContain('번호: 1')
      expect(result).toContain('제목: 첫 만남')
      expect(result).toContain('설명: 주인공들의 첫 만남')
    })

    it('should build correct prompt with custom prompt', () => {
      const episode = mockEpisodes[0]!
      const customPrompt = '더 감동적으로 작성해주세요'
      const result = buildGenerationPrompt(mockProject, episode, customPrompt)

      expect(result).toContain('추가 요청사항:')
      expect(result).toContain('더 감동적으로 작성해주세요')
    })

    it('should handle episode without description', () => {
      const episode = mockEpisodes[1]! // description이 없는 에피소드
      const result = buildGenerationPrompt(mockProject, episode)

      expect(result).toContain('설명: 설명 없음')
    })
  })

  describe('estimateTokens', () => {
    it('should estimate tokens correctly for Korean text', () => {
      const text = '안녕하세요 테스트입니다'
      const result = estimateTokens(text)
      expect(result).toBe(3) // 2 words * 1.3 = 2.6 -> rounded to 3
    })

    it('should handle empty string', () => {
      const result = estimateTokens('')
      expect(result).toBe(0)
    })

    it('should handle longer text', () => {
      const text = '이것은 긴 텍스트입니다 토큰 수를 계산하는 테스트입니다'
      const result = estimateTokens(text)
      expect(result).toBe(9) // 7 words * 1.3 = 9.1 -> rounded to 9
    })
  })

  describe('calculateScriptProgress', () => {
    it('should return 0 for empty episodes array', () => {
      const result = calculateScriptProgress([])
      expect(result).toBe(0)
    })

    it('should calculate correct progress percentage', () => {
      const result = calculateScriptProgress(mockEpisodes)
      // 3개 에피소드 중 1개만 ready + script 있음
      expect(result).toBe(33) // 1/3 * 100 = 33.33 -> rounded to 33
    })

    it('should only count ready episodes with scripts', () => {
      const episodesWithScripts: Episode[] = [
        {
          ...mockEpisodes[0]!,
          status: 'ready',
          script: { markdown: 'content', tokens: 100 },
        },
        {
          ...mockEpisodes[1]!,
          status: 'ready',
          // script is optional, so omitted instead of undefined
        },
        {
          ...mockEpisodes[2]!,
          status: 'draft',
          script: { markdown: 'content', tokens: 100 }, // ready가 아님
        },
      ]

      const result = calculateScriptProgress(episodesWithScripts)
      expect(result).toBe(33) // 1/3 * 100
    })

    it('should return 100 when all episodes are completed', () => {
      const completedEpisodes: Episode[] = mockEpisodes.map(ep => ({
        ...ep,
        status: 'ready' as const,
        script: { markdown: 'content', tokens: 100 },
      }))

      const result = calculateScriptProgress(completedEpisodes)
      expect(result).toBe(100)
    })
  })
})
