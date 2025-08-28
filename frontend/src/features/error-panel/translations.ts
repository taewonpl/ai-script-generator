/**
 * i18n translations for error messages
 * Supporting English (EN) and Korean (KR)
 */

import type { ErrorType, Language } from './types'

export interface ErrorTranslation {
  title: string
  userMessage: string
  actionHint: string
  retryButtonText: string
  copyDetailsText: string
  copySuccessText: string
  dismissText: string
  showDetailsText: string
  hideDetailsText: string
}

type ErrorTranslations = Record<ErrorType, Record<Language, ErrorTranslation>>

export const ERROR_TRANSLATIONS: ErrorTranslations = {
  server_unavailable: {
    en: {
      title: 'Service Temporarily Unavailable',
      userMessage: 'Our AI script generation service is temporarily unavailable. This is usually resolved quickly.',
      actionHint: 'Please try again in a few moments',
      retryButtonText: 'Retry',
      copyDetailsText: 'Copy Error Details',
      copySuccessText: 'Copied to clipboard',
      dismissText: 'Dismiss',
      showDetailsText: 'Show Technical Details',
      hideDetailsText: 'Hide Technical Details',
    },
    kr: {
      title: '서비스 일시 중단',
      userMessage: 'AI 대본 생성 서비스가 일시적으로 이용할 수 없습니다. 보통 빠르게 복구됩니다.',
      actionHint: '잠시 후 다시 시도해주세요',
      retryButtonText: '다시 시도',
      copyDetailsText: '오류 상세정보 복사',
      copySuccessText: '클립보드에 복사됨',
      dismissText: '닫기',
      showDetailsText: '기술적 세부사항 보기',
      hideDetailsText: '기술적 세부사항 숨기기',
    },
  },
  network_error: {
    en: {
      title: 'Connection Problem',
      userMessage: 'Unable to connect to our servers. Please check your internet connection.',
      actionHint: 'Check your internet connection and try again',
      retryButtonText: 'Retry',
      copyDetailsText: 'Copy Error Details',
      copySuccessText: 'Copied to clipboard',
      dismissText: 'Dismiss',
      showDetailsText: 'Show Technical Details',
      hideDetailsText: 'Hide Technical Details',
    },
    kr: {
      title: '연결 문제',
      userMessage: '서버에 연결할 수 없습니다. 인터넷 연결을 확인해주세요.',
      actionHint: '인터넷 연결을 확인한 후 다시 시도해주세요',
      retryButtonText: '다시 시도',
      copyDetailsText: '오류 상세정보 복사',
      copySuccessText: '클립보드에 복사됨',
      dismissText: '닫기',
      showDetailsText: '기술적 세부사항 보기',
      hideDetailsText: '기술적 세부사항 숨기기',
    },
  },
  validation_error: {
    en: {
      title: 'Invalid Input',
      userMessage: 'The information you entered is not valid. Please check and try again.',
      actionHint: 'Review your input and correct any errors',
      retryButtonText: 'Try Again',
      copyDetailsText: 'Copy Error Details',
      copySuccessText: 'Copied to clipboard',
      dismissText: 'Dismiss',
      showDetailsText: 'Show Technical Details',
      hideDetailsText: 'Hide Technical Details',
    },
    kr: {
      title: '입력 오류',
      userMessage: '입력하신 정보가 올바르지 않습니다. 확인 후 다시 시도해주세요.',
      actionHint: '입력 내용을 검토하고 오류를 수정해주세요',
      retryButtonText: '다시 시도',
      copyDetailsText: '오류 상세정보 복사',
      copySuccessText: '클립보드에 복사됨',
      dismissText: '닫기',
      showDetailsText: '기술적 세부사항 보기',
      hideDetailsText: '기술적 세부사항 숨기기',
    },
  },
  authorization_error: {
    en: {
      title: 'Access Denied',
      userMessage: 'You don\'t have permission to access this resource. Please log in or contact support.',
      actionHint: 'Log in with appropriate credentials',
      retryButtonText: 'Retry',
      copyDetailsText: 'Copy Error Details',
      copySuccessText: 'Copied to clipboard',
      dismissText: 'Dismiss',
      showDetailsText: 'Show Technical Details',
      hideDetailsText: 'Hide Technical Details',
    },
    kr: {
      title: '접근 거부',
      userMessage: '이 리소스에 접근할 권한이 없습니다. 로그인하거나 지원팀에 문의하세요.',
      actionHint: '적절한 자격 증명으로 로그인해주세요',
      retryButtonText: '다시 시도',
      copyDetailsText: '오류 상세정보 복사',
      copySuccessText: '클립보드에 복사됨',
      dismissText: '닫기',
      showDetailsText: '기술적 세부사항 보기',
      hideDetailsText: '기술적 세부사항 숨기기',
    },
  },
  rate_limit_error: {
    en: {
      title: 'Too Many Requests',
      userMessage: 'You\'re making requests too quickly. Please wait a moment before trying again.',
      actionHint: 'Wait a few seconds and try again',
      retryButtonText: 'Retry',
      copyDetailsText: 'Copy Error Details',
      copySuccessText: 'Copied to clipboard',
      dismissText: 'Dismiss',
      showDetailsText: 'Show Technical Details',
      hideDetailsText: 'Hide Technical Details',
    },
    kr: {
      title: '요청 제한',
      userMessage: '요청이 너무 많습니다. 잠시 기다린 후 다시 시도해주세요.',
      actionHint: '몇 초 기다린 후 다시 시도해주세요',
      retryButtonText: '다시 시도',
      copyDetailsText: '오류 상세정보 복사',
      copySuccessText: '클립보드에 복사됨',
      dismissText: '닫기',
      showDetailsText: '기술적 세부사항 보기',
      hideDetailsText: '기술적 세부사항 숨기기',
    },
  },
  timeout_error: {
    en: {
      title: 'Request Timeout',
      userMessage: 'The request took too long to complete. This might be due to high server load.',
      actionHint: 'Try again in a few moments',
      retryButtonText: 'Retry',
      copyDetailsText: 'Copy Error Details',
      copySuccessText: 'Copied to clipboard',
      dismissText: 'Dismiss',
      showDetailsText: 'Show Technical Details',
      hideDetailsText: 'Hide Technical Details',
    },
    kr: {
      title: '요청 시간 초과',
      userMessage: '요청 처리 시간이 너무 오래 걸렸습니다. 서버 부하가 높을 수 있습니다.',
      actionHint: '잠시 후 다시 시도해주세요',
      retryButtonText: '다시 시도',
      copyDetailsText: '오류 상세정보 복사',
      copySuccessText: '클립보드에 복사됨',
      dismissText: '닫기',
      showDetailsText: '기술적 세부사항 보기',
      hideDetailsText: '기술적 세부사항 숨기기',
    },
  },
  unknown_error: {
    en: {
      title: 'Unexpected Error',
      userMessage: 'Something unexpected happened. Our team has been notified and is working to fix this.',
      actionHint: 'Try refreshing the page or contact support if the problem persists',
      retryButtonText: 'Retry',
      copyDetailsText: 'Copy Error Details',
      copySuccessText: 'Copied to clipboard',
      dismissText: 'Dismiss',
      showDetailsText: 'Show Technical Details',
      hideDetailsText: 'Hide Technical Details',
    },
    kr: {
      title: '예상치 못한 오류',
      userMessage: '예상치 못한 문제가 발생했습니다. 저희 팀이 이 문제를 해결하기 위해 노력하고 있습니다.',
      actionHint: '페이지를 새로고침하거나 문제가 지속되면 지원팀에 문의하세요',
      retryButtonText: '다시 시도',
      copyDetailsText: '오류 상세정보 복사',
      copySuccessText: '클립보드에 복사됨',
      dismissText: '닫기',
      showDetailsText: '기술적 세부사항 보기',
      hideDetailsText: '기술적 세부사항 숨기기',
    },
  },
}

export function getErrorTranslation(
  errorType: ErrorType, 
  language: Language = 'kr'
): ErrorTranslation {
  return ERROR_TRANSLATIONS[errorType]?.[language] || ERROR_TRANSLATIONS.unknown_error[language]
}