/**
 * RAG Pipeline Types
 * Type definitions for the RAG document processing system
 */

export type RAGJobStatus = 
  | 'queued'
  | 'uploading' 
  | 'extracting'
  | 'ocr'
  | 'chunking'
  | 'embedding'
  | 'indexed'
  | 'failed_extract'
  | 'failed_ocr'
  | 'failed_embed'
  | 'failed_store'
  | 'canceled'

export interface RAGJobMetadata {
  file_name: string
  file_size: number
  file_type: string
  file_sha256: string
  pages_total?: number
  pages_processed?: number
  pages_failed?: number
  text_length?: number
  chunks_total?: number
  chunks_indexed?: number
  ocr_confidence?: number
  extraction_method?: 'text' | 'ocr' | 'hybrid'
  error_code?: string
  error_message?: string
  retry_count: number
  started_at?: string
  ended_at?: string
  request_id?: string
  trace_id?: string
}

export interface RAGIngestRequest {
  project_id: string
  file_id: string
  chunk_size?: number
  chunk_overlap?: number
  force_ocr?: boolean
}

export interface RAGIngestResponse {
  job_id: string
  status: RAGJobStatus
  progress_pct: number
  is_duplicate: boolean
  existing_document_id?: string
  request_id: string
  trace_id: string
}

export interface RAGJobStatusResponse {
  job_id: string
  status: RAGJobStatus
  progress_pct: number
  current_step: string
  document_id?: string
  chunks_indexed?: number
  error_code?: string
  error_message?: string
  retry_count: number
  started_at?: string
  ended_at?: string
  estimated_remaining_seconds?: number
}

export interface RAGDocument {
  id: string
  project_id: string
  name: string
  file_sha256: string
  file_size: number
  file_type: string
  status: RAGJobStatus
  chunks_count: number
  embed_version: string
  uploaded_at: string
  indexed_at?: string
  metadata: Record<string, any>
}

export interface RAGDocumentsResponse {
  documents: RAGDocument[]
  total: number
  indexed_count: number
  processing_count: number
  failed_count: number
}

export interface RAGError {
  code: string
  message: string
  status?: number
  details?: Record<string, any>
}