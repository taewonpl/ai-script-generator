/**
 * Standardized i18n keys for error messages (EN/KR)
 */

export type Language = 'en' | 'ko'

export interface ErrorI18nMessages {
  // Headlines
  'error.headline.generic': Record<Language, string>
  'error.headline.offline': Record<Language, string>
  'error.headline.server_unavailable': Record<Language, string>
  'error.headline.network_error': Record<Language, string>
  'error.headline.validation_error': Record<Language, string>
  'error.headline.authorization_error': Record<Language, string>
  'error.headline.rate_limit_error': Record<Language, string>
  'error.headline.timeout_error': Record<Language, string>
  
  // Action buttons
  'error.button.retry': Record<Language, string>
  'error.button.back': Record<Language, string>
  'error.button.dismiss': Record<Language, string>
  'error.button.reload': Record<Language, string>
  
  // Details
  'error.details.title': Record<Language, string>
  'error.details.copy': Record<Language, string>
  'error.details.show': Record<Language, string>
  'error.details.hide': Record<Language, string>
  'error.details.copied': Record<Language, string>
  
  // Status messages
  'error.longwait': Record<Language, string>
  'error.retrying': Record<Language, string>
  'error.retry_count': Record<Language, string>
  'error.offline_detected': Record<Language, string>
  'error.online_restored': Record<Language, string>
  
  // Hints by error type
  'error.hint.generic': Record<Language, string>
  'error.hint.offline': Record<Language, string>
  'error.hint.server_unavailable': Record<Language, string>
  'error.hint.network_error': Record<Language, string>
  'error.hint.validation_error': Record<Language, string>
  'error.hint.authorization_error': Record<Language, string>
  'error.hint.rate_limit_error': Record<Language, string>
  'error.hint.timeout_error': Record<Language, string>
}

export const ERROR_MESSAGES: ErrorI18nMessages = {
  // Headlines
  'error.headline.generic': {
    en: "We couldn't load the data.",
    ko: "데이터를 불러오지 못했습니다.",
  },
  'error.headline.offline': {
    en: "You're offline. Check your connection.",
    ko: "오프라인 상태입니다. 인터넷 연결을 확인해 주세요.",
  },
  'error.headline.server_unavailable': {
    en: "Service temporarily unavailable",
    ko: "서비스를 일시적으로 사용할 수 없습니다.",
  },
  'error.headline.network_error': {
    en: "Connection problem",
    ko: "연결 문제가 발생했습니다.",
  },
  'error.headline.validation_error': {
    en: "Invalid input",
    ko: "입력 정보가 올바르지 않습니다.",
  },
  'error.headline.authorization_error': {
    en: "Access denied",
    ko: "접근이 거부되었습니다.",
  },
  'error.headline.rate_limit_error': {
    en: "Too many requests",
    ko: "요청이 너무 많습니다.",
  },
  'error.headline.timeout_error': {
    en: "Request timeout",
    ko: "요청 시간이 초과되었습니다.",
  },

  // Action buttons
  'error.button.retry': { en: "Retry", ko: "다시 시도" },
  'error.button.back': { en: "Go back", ko: "뒤로 가기" },
  'error.button.dismiss': { en: "Dismiss", ko: "닫기" },
  'error.button.reload': { en: "Reload page", ko: "페이지 새로고침" },

  // Details
  'error.details.title': { en: "Technical details", ko: "기술적 세부사항" },
  'error.details.copy': { en: "Copy error details", ko: "에러 상세 복사" },
  'error.details.show': { en: "View details", ko: "상세 보기" },
  'error.details.hide': { en: "Hide details", ko: "상세 숨기기" },
  'error.details.copied': { en: "Copied to clipboard", ko: "클립보드에 복사됨" },

  // Status messages
  'error.longwait': {
    en: "This is taking longer than usual.",
    ko: "예상보다 오래 걸리고 있습니다.",
  },
  'error.retrying': { en: "Retrying...", ko: "재시도 중..." },
  'error.retry_count': { en: "Attempt {count} of {max}", ko: "{count}/{max}회 시도" },
  'error.offline_detected': { en: "Offline detected", ko: "오프라인 감지됨" },
  'error.online_restored': { en: "Connection restored", ko: "연결 복원됨" },

  // Hints by error type
  'error.hint.generic': {
    en: "Please try again or contact support if the problem persists.",
    ko: "다시 시도하거나 문제가 지속되면 지원팀에 문의하세요.",
  },
  'error.hint.offline': {
    en: "Check your internet connection and try again.",
    ko: "인터넷 연결을 확인한 후 다시 시도해주세요.",
  },
  'error.hint.server_unavailable': {
    en: "Our servers are temporarily unavailable. Please try again in a few moments.",
    ko: "서버를 일시적으로 사용할 수 없습니다. 잠시 후 다시 시도해주세요.",
  },
  'error.hint.network_error': {
    en: "Unable to connect to our servers. Check your internet connection.",
    ko: "서버에 연결할 수 없습니다. 인터넷 연결을 확인해주세요.",
  },
  'error.hint.validation_error': {
    en: "Please check your input and try again.",
    ko: "입력 내용을 확인한 후 다시 시도해주세요.",
  },
  'error.hint.authorization_error': {
    en: "You don't have permission to access this resource. Please log in.",
    ko: "이 리소스에 접근할 권한이 없습니다. 로그인해주세요.",
  },
  'error.hint.rate_limit_error': {
    en: "You're making requests too quickly. Please wait a moment.",
    ko: "요청이 너무 빠릅니다. 잠시 기다려주세요.",
  },
  'error.hint.timeout_error': {
    en: "The request took too long to complete. Please try again.",
    ko: "요청 처리 시간이 초과되었습니다. 다시 시도해주세요.",
  },
}

/**
 * Get localized message by key
 */
export function getMessage(key: keyof ErrorI18nMessages, language: Language = 'ko'): string {
  return ERROR_MESSAGES[key]?.[language] || ERROR_MESSAGES['error.headline.generic'][language]
}

/**
 * Get localized message with variable substitution
 */
export function getMessageWithVars(
  key: keyof ErrorI18nMessages, 
  language: Language = 'ko',
  variables: Record<string, string | number> = {}
): string {
  let message = getMessage(key, language)
  
  // Replace variables like {count}, {max}
  Object.entries(variables).forEach(([varKey, value]) => {
    message = message.replace(new RegExp(`\\{${varKey}\\}`, 'g'), String(value))
  })
  
  return message
}