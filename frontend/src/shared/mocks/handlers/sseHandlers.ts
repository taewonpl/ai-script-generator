import { http, HttpResponse } from 'msw'
import type { GenerationRequest } from '@/shared/types/project'

// 진행 중인 생성 작업들을 추적
const activeGenerations = new Map<
  string,
  {
    jobId: string
    projectId: string
    request: GenerationRequest
    startTime: number
    cancelled: boolean
  }
>()

// SSE 연결들을 추적
const sseConnections = new Map<
  string,
  {
    controller: ReadableStreamDefaultController
    interval: NodeJS.Timeout
  }
>()

/**
 * SSE 메시지 포맷팅
 */
const formatSSEMessage = (type: string, data: unknown, jobId: string) => {
  const message = {
    type,
    timestamp: new Date().toISOString(),
    jobId,
    data,
  }
  return `data: ${JSON.stringify(message)}\n\n`
}

/**
 * 생성 시뮬레이션 함수
 */
const simulateGeneration = (
  jobId: string,
  controller: ReadableStreamDefaultController,
  request: GenerationRequest,
) => {
  let progress = 0
  let previewContent = ''
  let stage = 0

  const stages = [
    {
      name: 'preparing',
      duration: 2000,
      message: 'AI가 스크립트 구조를 설계하고 있습니다...',
    },
    {
      name: 'generating',
      duration: 8000,
      message: '캐릭터 대화를 생성하고 있습니다...',
    },
    {
      name: 'processing',
      duration: 4000,
      message: '스토리 흐름을 다듬고 있습니다...',
    },
    {
      name: 'finalizing',
      duration: 2000,
      message: '최종 검토 및 완성 중입니다...',
    },
  ]

  const mockScriptContent = [
    '# 스크립트 제목\n\n',
    '## 씬 1: 오프닝\n\n',
    '**주인공** (화면 중앙에 등장)\n',
    '안녕하세요, 오늘도 멋진 하루가 시작되었네요.\n\n',
    '**내레이션**\n',
    '이것은 AI가 생성한 스크립트입니다.\n\n',
    '## 씬 2: 전개\n\n',
    '**주인공** (미소를 지으며)\n',
    '이 스토리는 ' + request.tone + ' 톤으로 진행됩니다.\n\n',
    '**동료** (등장하며)\n',
    '정말 흥미로운 설정이군요!\n\n',
    '## 씬 3: 마무리\n\n',
    '**주인공** (결의에 찬 표정으로)\n',
    '우리의 여정은 이제 시작입니다.\n\n',
    '*- 끝 -* \n\n',
    `총 분량: ${request.length}\n`,
    `톤: ${request.tone}`,
  ]

  let contentIndex = 0

  const interval = setInterval(
    () => {
      const generation = activeGenerations.get(jobId)
      if (!generation || generation.cancelled) {
        clearInterval(interval)
        sseConnections.delete(jobId)
        return
      }

      // Heartbeat 전송
      if (Math.random() < 0.3) {
        controller.enqueue(
          formatSSEMessage(
            'heartbeat',
            {
              timestamp: new Date().toISOString(),
              jobId,
            },
            jobId,
          ),
        )
      }

      // 진행률 업데이트
      progress = Math.min(100, progress + Math.random() * 15)

      controller.enqueue(
        formatSSEMessage(
          'progress',
          {
            percentage: Math.floor(progress),
            message: stages[stage]?.message || '생성 중...',
            stage: stages[stage]?.name || 'generating',
          },
          jobId,
        ),
      )

      // 미리보기 콘텐츠 추가
      if (contentIndex < mockScriptContent.length && Math.random() < 0.7) {
        const chunk = mockScriptContent[contentIndex]
        previewContent += chunk
        contentIndex++

        controller.enqueue(
          formatSSEMessage(
            'preview',
            {
              content: chunk,
              isPartial: contentIndex < mockScriptContent.length,
              wordCount: previewContent.split(/\s+/).length,
              estimatedTokens: Math.floor(previewContent.length / 4),
            },
            jobId,
          ),
        )
      }

      // 스테이지 진행
      if (progress > (stage + 1) * 25 && stage < stages.length - 1) {
        stage++
      }

      // 완료 조건
      if (progress >= 100 && contentIndex >= mockScriptContent.length) {
        clearInterval(interval)

        controller.enqueue(
          formatSSEMessage(
            'completed',
            {
              episodeId: `episode-${Date.now()}`,
              script: {
                markdown: previewContent,
                tokens: Math.floor(previewContent.length / 4),
                wordCount: previewContent.split(/\s+/).length,
              },
              duration: Date.now() - generation.startTime,
            },
            jobId,
          ),
        )

        // 연결 정리
        setTimeout(() => {
          try {
            controller.close()
          } catch (e) {
            // 이미 닫힌 경우 무시
          }
          sseConnections.delete(jobId)
          activeGenerations.delete(jobId)
        }, 1000)
      }
    },
    500 + Math.random() * 1000,
  ) // 0.5-1.5초 간격

  // 20% 확률로 실패 시뮬레이션
  if (Math.random() < 0.2) {
    setTimeout(
      () => {
        if (
          activeGenerations.has(jobId) &&
          !activeGenerations.get(jobId)?.cancelled
        ) {
          clearInterval(interval)
          controller.enqueue(
            formatSSEMessage(
              'failed',
              {
                error: 'API 요청 한도 초과',
                code: 'RATE_LIMIT_EXCEEDED',
                details: { retryAfter: 60 },
                retryable: true,
              },
              jobId,
            ),
          )

          setTimeout(() => {
            try {
              controller.close()
            } catch (e) {
              // 이미 닫힌 경우 무시
            }
            sseConnections.delete(jobId)
            activeGenerations.delete(jobId)
          }, 1000)
        }
      },
      3000 + Math.random() * 5000,
    )
  }

  return interval
}

export const sseHandlers = [
  // 생성 시작
  http.post(
    '/api/projects/:projectId/generations',
    async ({ params, request }) => {
      const { projectId } = params
      const body = (await request.json()) as GenerationRequest
      const idempotencyKey = request.headers.get('Idempotency-Key')

      // 중복 생성 방지
      if (idempotencyKey) {
        for (const [existingJobId, job] of activeGenerations.entries()) {
          if (job.projectId === projectId && !job.cancelled) {
            return HttpResponse.json({
              success: true,
              data: { jobId: existingJobId },
            })
          }
        }
      }

      const jobId = `job-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`

      activeGenerations.set(jobId, {
        jobId,
        projectId: projectId as string,
        request: body,
        startTime: Date.now(),
        cancelled: false,
      })

      return HttpResponse.json({
        success: true,
        data: { jobId },
      })
    },
  ),

  // 생성 취소
  http.delete('/api/generations/:jobId', ({ params }) => {
    const { jobId } = params

    const generation = activeGenerations.get(jobId as string)
    if (generation) {
      generation.cancelled = true

      // SSE 연결 정리
      const connection = sseConnections.get(jobId as string)
      if (connection) {
        clearInterval(connection.interval)
        try {
          connection.controller.close()
        } catch (e) {
          // 이미 닫힌 경우 무시
        }
        sseConnections.delete(jobId as string)
      }

      activeGenerations.delete(jobId as string)
    }

    return HttpResponse.json({
      success: true,
      data: { cancelled: true },
    })
  }),

  // SSE 스트림
  http.get('/api/generations/:jobId/events', ({ params }) => {
    const { jobId } = params

    const generation = activeGenerations.get(jobId as string)
    if (!generation) {
      return new HttpResponse(null, { status: 404 })
    }

    const stream = new ReadableStream({
      start(controller) {
        // 초기 연결 메시지
        controller.enqueue('event: connected\n')
        controller.enqueue(
          `data: {"type":"connected","jobId":"${jobId}","timestamp":"${new Date().toISOString()}"}\n\n`,
        )

        // 생성 시뮬레이션 시작
        const interval = simulateGeneration(
          jobId as string,
          controller,
          generation.request,
        )

        // 연결 정보 저장
        sseConnections.set(jobId as string, {
          controller,
          interval,
        })
      },

      cancel() {
        // 클라이언트가 연결을 끊은 경우
        const connection = sseConnections.get(jobId as string)
        if (connection) {
          clearInterval(connection.interval)
          sseConnections.delete(jobId as string)
        }
      },
    })

    return new HttpResponse(stream, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        Connection: 'keep-alive',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Cache-Control',
      },
    })
  }),
]
