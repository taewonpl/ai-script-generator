import { setupServer } from 'msw/node'
import { scriptHandlers } from './handlers/scriptHandlers'

// Node.js 환경용 MSW 서버 설정 (테스트용)
export const server = setupServer(...scriptHandlers)

// 에러 처리 설정
server.events.on('request:start', ({ request }) => {
  console.log('MSW intercepted:', request.method, request.url)
})

server.events.on('request:match', ({ request }) => {
  console.log('MSW matched:', request.method, request.url)
})

server.events.on('request:unhandled', ({ request }) => {
  console.log('MSW unhandled:', request.method, request.url)
})
