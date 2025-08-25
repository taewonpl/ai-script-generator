import { useMemo, useCallback, useState } from 'react'
import { JobProgressIndicator } from './JobProgressIndicator'
import { env } from '@/shared/config/env'

import type { CompletedEventData } from '@/shared/types/generation'

type GenerationResult = CompletedEventData['result']

export interface ScriptGenerationProgressProps {
  jobId: string
  projectId: string
  episodeNumber?: number
  onComplete?: (result: GenerationResult) => void
  onError?: (error: string) => void
  onCancel?: () => void
}

/**
 * Specialized progress indicator for script generation jobs
 *
 * This component provides:
 * - Real-time progress updates via SSE
 * - Script generation specific messaging
 * - Integration with generation service
 * - Automatic cleanup on completion
 */
export function ScriptGenerationProgress({
  jobId,
  projectId: _projectId,
  episodeNumber,
  onComplete,
  onError,
  onCancel,
}: ScriptGenerationProgressProps) {
  // Build SSE URL for generation service
  const sseUrl = useMemo(() => {
    const baseUrl = env.VITE_GENERATION_SERVICE_URL
    return `${baseUrl}/api/v1/jobs/${jobId}/stream`
  }, [jobId])

  // Generate title based on context
  const title = useMemo(() => {
    if (episodeNumber) {
      return `Generating Episode ${episodeNumber} Script`
    }
    return 'Generating Script'
  }, [episodeNumber])

  // Handle completion with cleanup
  const handleComplete = useCallback(
    (result: GenerationResult) => {
      console.log('✅ Script generation completed:', result)
      onComplete?.(result)
    },
    [onComplete],
  )

  // Handle errors
  const handleError = useCallback(
    (error: string) => {
      console.error('❌ Script generation failed:', error)
      onError?.(error)
    },
    [onError],
  )

  // Handle cancellation
  const handleCancel = useCallback(() => {
    console.log('🛑 Script generation canceled')
    onCancel?.()
  }, [onCancel])

  return (
    <JobProgressIndicator
      jobId={jobId}
      sseUrl={sseUrl}
      title={title}
      onComplete={handleComplete as any}
      onError={handleError}
      onCancel={handleCancel}
      showConnectionStatus={true}
      autoConnect={true}
    />
  )
}

/**
 * Example usage component for demonstration
 */
export function ScriptGenerationProgressExample() {
  const [jobId, setJobId] = useState<string>('demo-job-123')
  const [showProgress, setShowProgress] = useState(false)

  const startGeneration = () => {
    // In real usage, you would start a generation job here
    setJobId(`job-${Date.now()}`)
    setShowProgress(true)
  }

  const handleComplete = (result: GenerationResult) => {
    console.log('Generation completed:', result)
    setShowProgress(false)
    // Navigate to script editor or show success message
  }

  const handleError = (error: string) => {
    console.error('Generation failed:', error)
    setShowProgress(false)
    // Show error message to user
  }

  const handleCancel = () => {
    console.log('Generation canceled')
    setShowProgress(false)
    // Return to previous screen
  }

  return (
    <div style={{ padding: '20px', maxWidth: '600px' }}>
      <h2>Script Generation Progress Demo</h2>

      {!showProgress ? (
        <button onClick={startGeneration}>Start Script Generation</button>
      ) : (
        <ScriptGenerationProgress
          jobId={jobId}
          projectId="demo-project-123"
          episodeNumber={1}
          onComplete={handleComplete}
          onError={handleError}
          onCancel={handleCancel}
        />
      )}
    </div>
  )
}
