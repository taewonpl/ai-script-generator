import { StrictMode } from 'react'
import { BrowserRouter } from 'react-router-dom'
import { ThemeProvider } from '@mui/material/styles'
import { CssBaseline } from '@mui/material'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import * as Sentry from '@sentry/react'

import { theme } from '@/shared/ui/theme'
import { AppRouter } from './providers/router'
import { env, isProduction } from '@/shared/config/env'

// Configure Sentry
if (env.VITE_SENTRY_DSN) {
  Sentry.init({
    dsn: env.VITE_SENTRY_DSN,
    environment: env.VITE_ENV,
    release: env.VITE_APP_VERSION,
    tracesSampleRate: env.VITE_SENTRY_TRACES_SAMPLE_RATE,
    profilesSampleRate: isProduction() ? 0.1 : 1.0,
    beforeSend: event => {
      // Filter out development errors in production
      if (
        isProduction() &&
        event.exception?.values?.[0]?.value?.includes('ChunkLoadError')
      ) {
        return null
      }
      return event
    },
    integrations: [
      Sentry.browserTracingIntegration(),
      Sentry.replayIntegration({
        maskAllText: isProduction(),
        maskAllInputs: true,
        blockAllMedia: true,
      }),
    ],
    initialScope: {
      tags: {
        component: 'frontend',
        version: env.VITE_APP_VERSION,
      },
    },
  })
}

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
})

function App() {
  return (
    <StrictMode>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider theme={theme}>
          <CssBaseline />
          <BrowserRouter>
            <AppRouter />
          </BrowserRouter>
          {env.VITE_ENABLE_DEVTOOLS && (
            <ReactQueryDevtools initialIsOpen={false} />
          )}
        </ThemeProvider>
      </QueryClientProvider>
    </StrictMode>
  )
}

export default App
