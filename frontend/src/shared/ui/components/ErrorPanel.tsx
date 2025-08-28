/**
 * Re-export ErrorPanel from features for easy access in shared UI
 */

export { ErrorPanel, RetryButton } from '../../../features/error-panel'
export { useErrorPanel, useErrorPanelWithQuery } from '../../../features/error-panel/hooks/useErrorPanel'
export type { 
  ErrorPanelProps,
  DetailedError,
  ErrorType,
  Language,
  RetryConfig,
} from '../../../features/error-panel'