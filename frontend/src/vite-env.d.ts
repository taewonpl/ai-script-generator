/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_CORE_SERVICE_URL: string
  readonly VITE_PROJECT_SERVICE_URL: string
  readonly VITE_GENERATION_SERVICE_URL: string
  readonly VITE_SENTRY_DSN?: string
  readonly VITE_SENTRY_TRACES_SAMPLE_RATE?: string
  readonly VITE_ENV: 'development' | 'production' | 'test'
  readonly VITE_APP_VERSION?: string
  readonly VITE_ENABLE_DEVTOOLS?: string
  readonly VITE_ENABLE_MSW?: string
  readonly VITE_ANALYTICS_TRACKING_ID?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
