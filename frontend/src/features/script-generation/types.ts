/**
 * Script generation types and interfaces
 */

export interface ProjectOption {
  id: string
  name: string
  type: string
  description?: string
  episodeCount?: number
}

export interface EpisodeOption {
  id: string
  title: string
  number: number
  seasonNumber?: number
  duration?: number
  description?: string
  status?: string
}

export interface AIModelOption {
  id: string
  name: string
  description: string
  provider: string
  capabilities: string[]
  speed: 'fast' | 'medium' | 'slow'
  quality: 'standard' | 'high' | 'premium'
  maxTokens: number
  pricing?: {
    inputCost: number
    outputCost: number
    currency: string
  }
}

export interface GenerationConfig {
  // Step 1: Selection
  projectId: string
  episodeId?: string

  // Step 2: AI Configuration
  aiModel: string
  genre?: string
  tone: string
  language: string
  length: 'short' | 'medium' | 'long'
  style?: string

  // Step 3: Detailed Prompt
  prompt: string
  characters?: string[]
  locations?: string[]
  themes?: string[]
  specialInstructions?: string

  // Advanced settings
  temperature?: number
  maxTokens?: number
  topP?: number
  frequencyPenalty?: number
  presencePenalty?: number
}

export interface GenerationJob {
  id: string
  status: 'queued' | 'streaming' | 'completed' | 'failed' | 'canceled' // Match Python GenerationJobStatus
  config: GenerationConfig
  progress: number
  currentStep: string // Match Python field name
  estimatedTime?: number
  result?: GenerationResult
  error?: string
  createdAt: Date
  completedAt?: Date
}

export interface GenerationResult {
  id: string
  jobId: string
  title: string
  content: string
  metadata: {
    wordCount: number
    characterCount: number
    estimatedDuration: number
    scenes: number
    aiModel: string
    generatedAt: Date
  }
  quality: {
    score: number
    aspects: {
      coherence: number
      creativity: number
      dialogue: number
      pacing: number
      characterization: number
    }
  }
  suggestions?: string[]
}

export type WizardStep =
  | 'selection'
  | 'configuration'
  | 'prompt'
  | 'generation'
  | 'results'

export interface WizardState {
  currentStep: WizardStep
  canProceed: boolean
  canGoBack: boolean
  config: Partial<GenerationConfig>
  job?: GenerationJob
  result?: GenerationResult
}
