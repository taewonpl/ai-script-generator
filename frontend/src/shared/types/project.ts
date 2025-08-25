export interface Project {
  id: string
  name: string
  title: string
  type: 'drama' | 'comedy' | 'documentary' | 'variety'
  status: 'draft' | 'active' | 'paused' | 'completed'
  tone: string
  systemPrompt: string
  progress_percentage: number
  created_at: string
  updated_at: string
}

export interface Episode {
  id: string
  number: number // 필드명을 number로 통일
  title: string
  description?: string
  status: 'draft' | 'ready' | 'generating' | 'failed'
  script?: {
    markdown: string
    tokens?: number
  }
  createdAt: string
  updatedAt?: string
}

export interface GenerationRequest {
  projectId: string
  number: number
  customPrompt?: string
}

export interface GenerationResponse {
  episodeId: string
  status: 'success' | 'error'
  script?: {
    markdown: string
    tokens: number
  }
  error?: string
}

// 프로젝트 생성/수정을 위한 타입
export interface CreateProjectRequest {
  name: string
  title: string
  type: Project['type']
  tone: string
  systemPrompt: string
}

export interface UpdateProjectRequest extends Partial<CreateProjectRequest> {
  id: string
}

// 에피소드 생성/수정을 위한 타입
export interface CreateEpisodeRequest {
  projectId: string
  number: number
  title: string
  description?: string
}

export interface UpdateEpisodeRequest
  extends Partial<Omit<CreateEpisodeRequest, 'projectId'>> {
  id: string
}
