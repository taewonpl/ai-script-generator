import type { Project, Episode } from '@/shared/types/project'
import { toMarkdownText } from '@/features/script-generation/types/content'

/**
 * 이전 스크립트 내용과 새로운 청크를 연결하는 함수
 * @param prev 이전 내용
 * @param chunk 새로운 청크
 * @returns 연결된 내용
 */
export const previewConcat = (prev: string, chunk: string): string =>
  prev ? prev + '\n' + chunk : chunk

/**
 * 다음 에피소드 번호를 계산하는 함수
 * @param episodes 기존 에피소드 목록
 * @returns 다음 에피소드 번호
 */
export const nextEpisodeNumber = (episodes: Episode[]): number =>
  Math.max(0, ...episodes.map(e => e.number)) + 1

/**
 * 자동 에피소드 제목 생성 함수
 * @param projectTitle 프로젝트 제목
 * @param episodeNumber 에피소드 번호
 * @returns 생성된 제목
 */
export const autoEpisodeTitle = (
  projectTitle: string,
  episodeNumber: number,
): string => `${projectTitle} - Ep. ${episodeNumber}`

/**
 * 스크립트 생성 정책 파라미터 상수
 */
export const GENERATION_POLICY = {
  LENGTH: '2 pages', // 고정값

  /**
   * 프로젝트의 톤을 가져오는 함수
   * @param project 프로젝트 객체
   * @returns 프로젝트 톤
   */
  getTone: (project: Project): string => project.tone || '',

  /**
   * 프로젝트의 시스템 프롬프트를 가져오는 함수 (항상 최신)
   * @param project 프로젝트 객체
   * @returns 시스템 프롬프트
   */
  getSystemPrompt: (project: Project): string => project.systemPrompt || '',
} as const

/**
 * 에피소드 상태별 라벨을 반환하는 함수
 * @param status 에피소드 상태
 * @returns 한국어 라벨
 */
export const getEpisodeStatusLabel = (status: Episode['status']): string => {
  const statusLabels = {
    draft: '초안',
    ready: '준비완료',
    generating: '생성중',
    failed: '실패',
  } as const

  return statusLabels[status]
}

/**
 * 스크립트 생성에 사용할 프롬프트를 구성하는 함수
 * @param project 프로젝트 정보
 * @param episode 에피소드 정보
 * @param customPrompt 커스텀 프롬프트 (선택사항)
 * @returns 완성된 프롬프트
 */
export const buildGenerationPrompt = (
  project: Project,
  episode: Episode,
  customPrompt?: string,
): string => {
  const systemPrompt = GENERATION_POLICY.getSystemPrompt(project)
  const tone = GENERATION_POLICY.getTone(project)
  const length = GENERATION_POLICY.LENGTH

  const basePrompt = `
${systemPrompt}

**프로젝트 정보:**
- 제목: ${project.title}
- 톤: ${tone}
- 분량: ${length}

**에피소드 정보:**
- 번호: ${episode.number}
- 제목: ${episode.title}
- 설명: ${episode.description || '설명 없음'}

${customPrompt ? `**추가 요청사항:**\n${customPrompt}\n` : ''}

위 정보를 바탕으로 ${length} 분량의 스크립트를 작성해주세요.
  `.trim()

  return basePrompt
}

/**
 * 토큰 수를 추정하는 함수 (간단한 추정)
 * @param text 텍스트
 * @returns 추정된 토큰 수
 */
export const estimateTokens = (text: string): number => {
  // 빈 문자열 처리
  if (!text || text.trim().length === 0) {
    return 0
  }

  // 간단한 토큰 추정: 단어 수 * 1.3 (한국어 특성 고려)
  const wordCount = text.trim().split(/\s+/).length
  return Math.round(wordCount * 1.3)
}

/**
 * 스크립트 진행률을 계산하는 함수
 * @param episodes 에피소드 목록
 * @returns 진행률 (0-100)
 */
export const calculateScriptProgress = (episodes: Episode[]): number => {
  if (episodes.length === 0) return 0

  const completedCount = episodes.filter(
    ep => ep.status === 'ready' && toMarkdownText(ep.script || ''),
  ).length

  return Math.round((completedCount / episodes.length) * 100)
}
