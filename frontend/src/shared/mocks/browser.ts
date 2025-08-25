import { setupWorker } from 'msw/browser'
import { scriptHandlers } from './handlers/scriptHandlers'

// MSW 워커 설정
export const worker = setupWorker(...scriptHandlers)

// 개발 환경에서만 MSW 시작
export const startMocks = async () => {
  if (import.meta.env.DEV) {
    await worker.start({
      onUnhandledRequest: 'bypass',
      serviceWorker: {
        url: '/mockServiceWorker.js',
      },
    })
    console.log('🔶 MSW enabled')
  }
}
