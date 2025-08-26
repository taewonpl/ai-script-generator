import { http, HttpResponse } from 'msw'

export const handlers = [
  // Project Service handlers
  http.get('/project-api/v1/projects', () => {
    return HttpResponse.json({
      success: true,
      data: [
        {
          id: '1',
          name: 'Sample Project',
          type: 'drama',
          status: 'active',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ],
    })
  }),

  http.get('/project-api/v1/projects/:id', ({ params }) => {
    return HttpResponse.json({
      success: true,
      data: {
        id: params.id,
        name: 'Sample Project',
        type: 'drama',
        status: 'active',
        description: 'A sample project for testing',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    })
  }),

  // Generation Service handlers
  http.get('/api/v1/health', () => {
    return HttpResponse.json({
      status: 'healthy',
      service: 'generation-service',
      version: '1.0.0',
    })
  }),

  http.post('/api/v1/generate', async ({ request: _request }) => {
    return HttpResponse.json({
      success: true,
      data: {
        generation_id: 'gen-123',
        status: 'processing',
        created_at: new Date().toISOString(),
      },
    })
  }),

  // Health check handlers
  http.get('/project-api/v1/health', () => {
    return HttpResponse.json({
      status: 'healthy',
      service: 'project-service',
      version: '1.0.0',
    })
  }),
]
