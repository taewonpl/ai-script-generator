/**
 * Error Panel feature exports
 */

// Components
export { ErrorPanel } from './components/ErrorPanel'
export { RetryButton } from './components/RetryButton'
export { EnhancedErrorFallback } from './components/EnhancedErrorFallback'
export { StandardErrorPanel } from './components/StandardErrorPanel'
export { LoadingWithTimeout } from './components/LoadingWithTimeout'
export { useLoadingTimeout } from './hooks/useLoadingTimeout'

// Hooks
export { useRetryLogic } from './hooks/useRetryLogic'
export { useErrorPanel, useErrorPanelWithQuery } from './hooks/useErrorPanel'

// Utilities
export {
  toDetailedError,
  fromStandardizedAPIError,
  fromAppError,
  fromGenericError,
  createCopyableErrorDetails,
} from './utils/errorMapping'

// Adapters
export { adaptError, createCopyableErrorText } from './adapters/errorAdapter'

// Interceptors
export { setupErrorInterceptor, getStandardError } from './interceptors/axiosErrorInterceptor'

// i18n
export { getMessage, getMessageWithVars } from './i18n/errorMessages'

// Translations (legacy)
export { getErrorTranslation, ERROR_TRANSLATIONS } from './translations'

// Types
export type {
  ErrorType,
  Language,
  DetailedError,
  RetryConfig,
  ErrorPanelProps,
  CopyableErrorInfo,
} from './types'

export type {
  StandardErrorFormat,
  StandardRetryConfig,
} from './types/standardError'