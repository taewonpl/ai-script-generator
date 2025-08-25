import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';

const handlers = [
  // existing endpoints...
  // Add missing endpoints (from CI logs)
  http.post('/api/projects/:id/episodes', ({ params }) => {
    const { id } = params as { id: string };
    return HttpResponse.json({ data: { episodeId: 'ep-1', projectId: id, number: 1 } }, { status: 201 });
  }),
  http.put('/api/episodes/:episodeId/script', ({ params }) => {
    const { episodeId } = params as { episodeId: string };
    return HttpResponse.json({ data: { episodeId, updated: true } }, { status: 200 });
  }),
  http.post('/api/projects/invalid-project/episodes', () =>
    HttpResponse.json({ error: { code: 'NOT_FOUND', message: 'invalid project' } }, { status: 404 })
  ),
];

export const server = setupServer(...handlers);
beforeAll(() => server.listen({ onUnhandledRequest: 'bypass' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());