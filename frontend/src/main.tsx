// Validate environment variables first (before any other imports)
import '@/shared/config/env'

import { createRoot } from 'react-dom/client'
import { ErrorProvider } from '@/app/providers/ErrorProvider'
import { ToastProvider } from '@/shared/ui/components/toast'
import { SentryReporter } from './shared/lib/errors'
import App from '@/app'
import { env } from '@/shared/config/env'

// Initialize Sentry error reporting
SentryReporter.initialize()

// Enable MSW in development
if (env.VITE_ENABLE_MSW && env.VITE_ENV === 'development') {
  import('@/shared/lib/msw/browser').then(({ worker }) => {
    worker.start({
      onUnhandledRequest: 'bypass',
    })
  })
}

const container = document.getElementById('root')
if (!container) throw new Error('Root element not found')

const root = createRoot(container)

// Wrap App with error handling providers
root.render(
  <ErrorProvider>
    <ToastProvider>
      <App />
    </ToastProvider>
  </ErrorProvider>,
)
