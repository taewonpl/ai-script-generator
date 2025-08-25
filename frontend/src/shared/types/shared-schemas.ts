/**
 * Shared Type Definitions - Auto-generated from Python Schemas
 *
 * DO NOT EDIT MANUALLY
 * This file is generated from the Python backend schemas to ensure type safety
 * across the entire application stack.
 *
 * Source: ai_script_core.schemas
 * Generated: 2025-01-22
 */

import type { ProjectType, ProjectStatus } from './api'

// =============================================================================
// Base Types from Python Backend
// =============================================================================

export interface BaseSchema {
  // Base interface for all schema types
}

export interface IDMixin {
  id: string
}

export interface TimestampMixin {
  createdAt: string
  updatedAt?: string
}

// =============================================================================
// Generation Status (from common.py) - USE api.ts instead
// =============================================================================

// export type GenerationStatus - REMOVED: conflicts with api.ts

// =============================================================================
// AI Model Configuration (from generation.py)
// =============================================================================

export interface AIModelConfigDTO extends BaseSchema {
  modelName: string // AI 모델명 (예: gpt-4, claude-3)
  provider: string // AI 서비스 제공업체
  temperature?: number // 창의성 온도 (0.0-2.0)
  maxTokens?: number // 최대 토큰 수 (100-8000)
  topP?: number // Top-p 샘플링 (0.0-1.0)
  frequencyPenalty?: number // 빈도 패널티 (-2.0-2.0)
  presencePenalty?: number // 존재 패널티 (-2.0-2.0)
  extraParams?: Record<string, unknown> // 추가 매개변수
}

export type SupportedAIModel =
  | 'gpt-3.5-turbo'
  | 'gpt-4'
  | 'gpt-4-turbo'
  | 'gpt-4o'
  | 'claude-3-haiku'
  | 'claude-3-sonnet'
  | 'claude-3-opus'
  | 'claude-3-5-sonnet'

// =============================================================================
// RAG Configuration (from generation.py)
// =============================================================================

export interface RAGConfigDTO extends BaseSchema {
  enabled?: boolean // RAG 활성화 여부

  // 검색 설정
  searchTopK?: number // 검색할 상위 문서 수 (1-20)
  similarityThreshold?: number // 유사도 임계값 (0.0-1.0)

  // 임베딩 설정
  embeddingModel?: string // 임베딩 모델
  chunkSize?: number // 문서 청크 크기 (100-4000)
  chunkOverlap?: number // 청크 간 겹침 크기 (0-1000)

  // 지식베이스 설정
  knowledgeBaseIds?: string[] // 사용할 지식베이스 ID 목록
  includeMetadata?: boolean // 메타데이터 포함 여부

  // 필터링
  documentTypes?: string[] // 문서 타입 필터
  dateRange?: {
    from?: string
    to?: string
  } // 날짜 범위 필터
  tags?: string[] // 태그 필터
}

// =============================================================================
// Generation Request/Response (from generation.py)
// =============================================================================

export type GenerationType =
  | 'script'
  | 'character'
  | 'scene'
  | 'dialogue'
  | 'synopsis'
  | 'treatment'
  | 'outline'
  | 'logline'
  | 'pitch'
  | 'revision'

export interface GenerationRequestDTO extends BaseSchema, IDMixin {
  projectId: string // 프로젝트 ID
  episodeId?: string // 에피소드 ID (선택적)

  // 생성 타입 및 목적
  generationType: GenerationType // 생성 타입
  purpose: string // 생성 목적 설명

  // 프롬프트 및 컨텍스트
  prompt: string // 메인 프롬프트 (10-10000자)
  systemPrompt?: string // 시스템 프롬프트 (최대 2000자)
  context?: string // 추가 컨텍스트 (최대 5000자)

  // 스타일 및 톤
  styleGuide?: string // 스타일 가이드
  tone?: string // 톤 (formal, casual, dramatic 등)
  genreHints?: string[] // 장르 힌트

  // AI 및 RAG 설정
  aiConfig: AIModelConfigDTO // AI 모델 설정
  ragConfig?: RAGConfigDTO // RAG 설정

  // 메타데이터
  priority?: number // 우선순위 (0-10)
  deadline?: string // 완료 기한
  callbackUrl?: string // 완료 시 호출할 콜백 URL
}

export interface GenerationMetadataDTO extends BaseSchema {
  // AI 모델 정보
  modelUsed: string // 사용된 AI 모델
  modelVersion?: string // 모델 버전

  // 성능 메트릭
  generationTimeMs: number // 생성 시간(밀리초)
  tokenUsage: {
    promptTokens: number
    completionTokens: number
    totalTokens: number
  } // 토큰 사용량
  costEstimate?: number // 예상 비용 (USD)

  // RAG 정보 (사용된 경우)
  ragUsed?: boolean // RAG 사용 여부
  retrievedDocsCount?: number // 검색된 문서 수
  avgSimilarityScore?: number // 평균 유사도 점수

  // 품질 메트릭
  contentLength?: number // 생성된 내용 길이
  readabilityScore?: number // 가독성 점수
  coherenceScore?: number // 일관성 점수

  // 처리 정보
  retryCount?: number // 재시도 횟수
  processingNode?: string // 처리 노드 ID

  // 추가 메타데이터
  extraMetadata?: Record<string, unknown> // 추가 메타데이터
}

export interface GenerationResponseDTO
  extends BaseSchema,
    IDMixin,
    TimestampMixin {
  requestId: string // 원본 요청 ID
  projectId: string // 프로젝트 ID
  episodeId?: string // 에피소드 ID

  // 상태 및 결과
  status: ProjectStatus // 생성 상태
  progressPercentage?: number // 진행률 (0.0-100.0)

  // 생성된 내용
  content?: string // 생성된 주요 내용
  title?: string // 생성된 제목
  summary?: string // 내용 요약

  // 구조화된 결과 (타입에 따라 다름)
  structuredResult?: Record<string, unknown> // 구조화된 생성 결과

  // 메타데이터
  metadata: GenerationMetadataDTO // 생성 메타데이터

  // 오류 정보
  errorMessage?: string // 오류 메시지
  errorCode?: string // 오류 코드

  // 피드백 및 평가
  qualityScore?: number // 품질 점수 (0.0-1.0)
  feedback?: string // 피드백
}

// =============================================================================
// Project Types (from project.py) - USE api.ts instead
// =============================================================================

// export type ProjectType - REMOVED: conflicts with api.ts
// export type ProjectStatus - REMOVED: conflicts with api.ts

export interface ProjectDTO extends BaseSchema, IDMixin, TimestampMixin {
  name: string // 프로젝트 명
  title?: string // 프로젝트 제목 (한국어)
  englishTitle?: string // 영문 제목
  type: ProjectType // 프로젝트 타입
  status: ProjectStatus // 프로젝트 상태

  // 설명 및 개요
  description?: string // 프로젝트 설명
  synopsis?: string // 시놉시스
  logline?: string // 로그라인

  // 제작 정보
  genre?: string[] // 장르
  targetAudience?: string // 타겟 오디언스
  duration?: number // 예상 상영시간 (분)
  episodeCount?: number // 총 에피소드 수

  // 진행률 및 통계
  progressPercentage?: number // 전체 진행률 (0.0-100.0)
  completedEpisodes?: number // 완료된 에피소드 수

  // 메타데이터
  tags?: string[] // 태그
  metadata?: Record<string, unknown> // 추가 메타데이터

  // 설정
  isPublic?: boolean // 공개 여부
  isArchived?: boolean // 아카이브 여부
}

// =============================================================================
// Episode Types (from project.py)
// =============================================================================

export interface EpisodeDTO extends BaseSchema, IDMixin, TimestampMixin {
  projectId: string // 소속 프로젝트 ID
  number: number // 에피소드 번호 (자동 생성)
  title: string // 에피소드 제목
  description?: string // 에피소드 설명

  // 스크립트 정보
  script?: {
    markdown: string // 마크다운 형식 스크립트
    tokens: number // 토큰 수
    wordCount?: number // 단어 수
    estimatedDuration?: number // 예상 상영시간 (분)
  }

  // 메타데이터
  tags?: string[] // 태그
  status?: string // 에피소드 상태

  // 생성 정보
  generatedAt?: string // AI 생성 시간
  generationMetadata?: GenerationMetadataDTO // 생성 메타데이터
  promptSnapshot?: string // 생성에 사용된 프롬프트 스냅샷

  // ChromaDB 연동
  vectorId?: string // 벡터DB ID
  embeddingVersion?: string // 임베딩 버전
}

// =============================================================================
// Common Error Types
// =============================================================================

export interface APIError {
  code: string
  message: string
  details?: Record<string, unknown>
}

export interface APIResponse<T = unknown> {
  success: boolean
  data?: T
  error?: APIError
}

// =============================================================================
// Validation Types
// =============================================================================

export interface ValidationError {
  field: string
  message: string
  value?: unknown
}

export interface ValidationResult {
  isValid: boolean
  errors: ValidationError[]
}

// =============================================================================
// Export all types for easy importing
// =============================================================================

// Note: BaseSchema, IDMixin, TimestampMixin are already exported as interfaces above
// Only re-export types that need to be available but are not already exported
// Export section removed - types are already exported where they are defined
