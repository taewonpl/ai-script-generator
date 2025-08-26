import { http, HttpResponse } from 'msw'
import type {
  Project,
  Episode,
  GenerationRequest,
  GenerationResponse,
} from '@/shared/types/project'
import { sseHandlers } from './sseHandlers'

// Mock 데이터
const mockProjects: Project[] = [
  {
    id: 'project-1',
    name: 'test-drama',
    title: '테스트 드라마',
    type: 'drama',
    status: 'active',
    tone: '로맨틱하고 감동적인',
    systemPrompt:
      '당신은 전문적인 드라마 작가입니다. 자연스럽고 현실적인 대화를 작성해주세요.',
    progress_percentage: 45,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-15T10:30:00Z',
  },
  {
    id: 'project-2',
    name: 'comedy-show',
    title: '코미디 쇼',
    type: 'comedy',
    status: 'draft',
    tone: '유머러스하고 밝은',
    systemPrompt:
      '당신은 코미디 작가입니다. 재미있고 유머러스한 대화를 작성해주세요.',
    progress_percentage: 12,
    created_at: '2024-01-05T00:00:00Z',
    updated_at: '2024-01-10T14:20:00Z',
  },
]

const mockEpisodes: Record<string, Episode[]> = {
  'project-1': [
    {
      id: 'ep-1',
      number: 1,
      title: '첫 만남',
      description: '남녀 주인공이 우연히 만나는 첫 번째 에피소드',
      status: 'ready',
      script: {
        markdown: `# 첫 만남

## 씬 1: 카페 앞

**수진** (20대 후반, 급하게 걷고 있다)
카페 문을 열려다가 안에서 나오는 **민호**와 부딪힌다.

**수진**: 아, 죄송해요!

**민호** (30대 초반, 따뜻한 미소)
괜찮아요. 다치신 건 아니죠?

**수진**: 네, 괜찮아요. 정말 죄송해요.

*두 사람의 눈이 마주친다. 잠시 정적이 흐른다.*

**민호**: 혹시... 커피 한 잔 어떠세요? 사과의 의미로.

**수진** (당황하며)
아, 아니에요. 제가 부딪힌 건데...

**민호**: 그럼 제가 사과드리는 마음으로. 어떠세요?

*수진이 망설이다가 작은 미소를 짓는다.*

**수진**: 그럼... 감사히.`,
        tokens: 245,
      },
      createdAt: '2024-01-01T00:00:00Z',
      updatedAt: '2024-01-03T16:45:00Z',
    },
    {
      id: 'ep-2',
      number: 2,
      title: '오해와 갈등',
      description: '서로에 대한 오해로 인한 갈등이 시작되는 에피소드',
      status: 'generating',
      createdAt: '2024-01-02T00:00:00Z',
    },
    {
      id: 'ep-3',
      number: 3,
      title: '진실 발견',
      description: '숨겨진 진실을 발견하게 되는 에피소드',
      status: 'draft',
      createdAt: '2024-01-03T00:00:00Z',
    },
  ],
  'project-2': [
    {
      id: 'ep-c1',
      number: 1,
      title: '첫 방송',
      description: '코미디 쇼의 첫 방송 에피소드',
      status: 'draft',
      createdAt: '2024-01-05T00:00:00Z',
    },
  ],
}

export const scriptHandlers = [
  // 프로젝트 목록 조회
  http.get('/api/projects', () => {
    return HttpResponse.json({
      success: true,
      data: mockProjects,
    })
  }),

  // 특정 프로젝트 조회
  http.get('/api/projects/:projectId', ({ params }) => {
    const { projectId } = params
    const project = mockProjects.find(p => p.id === projectId)

    if (!project) {
      return HttpResponse.json(
        { success: false, error: 'Project not found' },
        { status: 404 },
      )
    }

    return HttpResponse.json({
      success: true,
      data: project,
    })
  }),

  // 프로젝트의 에피소드 목록 조회
  http.get('/api/projects/:projectId/episodes', ({ params }) => {
    const { projectId } = params
    const episodes = mockEpisodes[projectId as string] || []

    return HttpResponse.json({
      success: true,
      data: episodes,
    })
  }),

  // 특정 에피소드 조회
  http.get('/api/episodes/:episodeId', ({ params }) => {
    const { episodeId } = params

    for (const projectEpisodes of Object.values(mockEpisodes)) {
      const episode = projectEpisodes.find(ep => ep.id === episodeId)
      if (episode) {
        return HttpResponse.json({
          success: true,
          data: episode,
        })
      }
    }

    return HttpResponse.json(
      { success: false, error: 'Episode not found' },
      { status: 404 },
    )
  }),

  // 스크립트 생성 요청
  http.post('/api/generate-script', async ({ request }) => {
    const body = (await request.json()) as GenerationRequest
    const { projectId, episodeNumber } = body as any

    // 프로젝트 확인
    const project = mockProjects.find(p => p.id === projectId)
    if (!project) {
      return HttpResponse.json(
        { success: false, error: 'Project not found' },
        { status: 404 },
      )
    }

    // 에피소드 확인
    const episodes = mockEpisodes[projectId] || []
    const episode = episodes.find(ep => ep.number === episodeNumber)
    if (!episode) {
      return HttpResponse.json(
        { success: false, error: 'Episode not found' },
        { status: 404 },
      )
    }

    // 생성 시뮬레이션 (랜덤하게 성공/실패)
    const isSuccess = Math.random() > 0.2 // 80% 성공률

    if (!isSuccess) {
      return HttpResponse.json({
        success: false,
        data: {
          episodeId: episode.id,
          status: 'error',
          error: 'Script generation failed due to API limits',
        } as GenerationResponse,
      })
    }

    // 성공 시 Mock 스크립트 생성
    const mockScript = `# ${episode.title}

## 개요
${episode.description}

## 씬 1
*${project.tone} 분위기로 시작되는 첫 번째 씬*

**등장인물**: 주인공들이 등장한다.

**주인공**: 이번 에피소드의 시작이군요.

**상대방**: 네, ${project.tone} 스토리가 펼쳐질 것 같아요.

*${project.tone} 톤이 유지되며 스토리가 전개된다.*

## 씬 2
*갈등이 고조되는 부분*

**주인공**: 이 상황을 어떻게 해결해야 할까요?

**상대방**: 함께 해결해 나가봅시다.

*${project.systemPrompt}의 가이드라인에 따라 자연스러운 대화가 이어진다.*

## 마무리
${episode.title}가 마무리되며 다음 에피소드에 대한 기대감을 남긴다.`

    // 에피소드 상태 업데이트 (실제로는 데이터베이스 업데이트)
    episode.status = 'ready'
    episode.script = {
      markdown: mockScript,
      tokens: Math.floor(mockScript.length / 4), // 간단한 토큰 추정
    }
    episode.updatedAt = new Date().toISOString()

    return HttpResponse.json({
      success: true,
      data: {
        episodeId: episode.id,
        status: 'success',
        script: episode.script,
      } as GenerationResponse,
    })
  }),

  // 에피소드 생성
  http.post(
    '/api/projects/:projectId/episodes',
    async ({ params, request }) => {
      const { projectId } = params
      const body = (await request.json()) as {
        number: number
        title: string
        description?: string
      }

      if (!mockEpisodes[projectId as string]) {
        mockEpisodes[projectId as string] = []
      }

      const newEpisode: Episode = {
        id: `ep-${Date.now()}`,
        number: body.number,
        title: body.title,
        description: body.description,
        status: 'draft',
        createdAt: new Date().toISOString(),
      }

      mockEpisodes[projectId as string].push(newEpisode)

      return HttpResponse.json({
        success: true,
        data: newEpisode,
      })
    },
  ),

  // 에피소드 업데이트
  http.put('/api/episodes/:episodeId', async ({ params, request }) => {
    const { episodeId } = params
    const body = (await request.json()) as Partial<Episode>

    for (const projectEpisodes of Object.values(mockEpisodes)) {
      const episodeIndex = projectEpisodes.findIndex(ep => ep.id === episodeId)
      if (episodeIndex !== -1) {
        projectEpisodes[episodeIndex] = {
          ...projectEpisodes[episodeIndex],
          ...body,
          updatedAt: new Date().toISOString(),
        }

        return HttpResponse.json({
          success: true,
          data: projectEpisodes[episodeIndex],
        })
      }
    }

    return HttpResponse.json(
      { success: false, error: 'Episode not found' },
      { status: 404 },
    )
  }),

  // SSE 핸들러들 포함
  ...sseHandlers,
]
