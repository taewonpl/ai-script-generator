import { useState, useEffect } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Stepper,
  Step,
  StepLabel,
  Button,
  Stack,
  Backdrop,
  CircularProgress,
} from '@mui/material'
import {
  NavigateBefore as BackIcon,
  NavigateNext as NextIcon,
  PlayArrow as GenerateIcon,
} from '@mui/icons-material'

import { SelectionStep } from './components/SelectionStep'
import { ConfigurationStep } from './components/ConfigurationStep'
import { PromptStep } from './components/PromptStep'
import { RealtimeProgress } from './components/RealtimeProgress'
import { GenerationResults } from './components/GenerationResults'
import { useToastHelpers } from '@/shared/ui/components/toast'
import { toMarkdownText } from './types/content'
import type {
  WizardStep,
  WizardState,
  GenerationConfig,
  ProjectOption,
  EpisodeOption,
  AIModelOption,
  GenerationJob,
  GenerationResult as LocalGenerationResult,
} from './types'
import type { GenerationResult } from '@/shared/api/streaming/types'

interface GenerationWizardProps {
  // Data loading functions
  onLoadProjects: () => Promise<ProjectOption[]>
  onLoadEpisodes: (projectId: string) => Promise<EpisodeOption[]>
  onLoadAIModels: () => Promise<AIModelOption[]>

  // Generation functions
  onStartGeneration: (config: GenerationConfig) => Promise<GenerationJob>
  onSaveResult: (
    result: LocalGenerationResult,
    editedContent: string,
    editedTitle: string,
  ) => Promise<void>

  // Navigation functions
  onCreateProject: () => void
  onCreateEpisode: () => void
  onComplete: (result: GenerationResult) => void
  onCancel?: () => void
}

// Wizard steps configuration
const WIZARD_STEPS = [
  {
    key: 'selection' as WizardStep,
    label: '프로젝트 선택',
    description: '스크립트를 생성할 프로젝트와 에피소드를 선택하세요',
  },
  {
    key: 'configuration' as WizardStep,
    label: 'AI 설정',
    description: 'AI 모델과 생성 옵션을 설정하세요',
  },
  {
    key: 'prompt' as WizardStep,
    label: '프롬프트 입력',
    description: '상세한 생성 지시사항을 입력하세요',
  },
  {
    key: 'generation' as WizardStep,
    label: '생성 진행',
    description: 'AI가 스크립트를 생성하고 있습니다',
  },
  {
    key: 'results' as WizardStep,
    label: '결과 확인',
    description: '생성된 스크립트를 확인하고 편집하세요',
  },
]

/**
 * Main AI Script Generation Wizard
 */
export function GenerationWizard({
  onLoadProjects,
  onLoadEpisodes,
  onLoadAIModels,
  onStartGeneration,
  onSaveResult,
  onCreateProject,
  onCreateEpisode,
  onComplete,
  onCancel,
}: GenerationWizardProps) {
  // State
  const [wizardState, setWizardState] = useState<WizardState>({
    currentStep: 'selection',
    canProceed: false,
    canGoBack: false,
    config: {},
  })

  const [projects, setProjects] = useState<ProjectOption[]>([])
  const [episodes, setEpisodes] = useState<EpisodeOption[]>([])
  const [aiModels, setAIModels] = useState<AIModelOption[]>([])
  const [loading, setLoading] = useState(false)
  const [projectData, setProjectData] = useState<ProjectOption | null>(null)
  const [episodeData, setEpisodeData] = useState<EpisodeOption | null>(null)

  const { showError, showWarning } = useToastHelpers()

  // Load initial data
  useEffect(() => {
    loadProjects()
    loadAIModels()
  }, [])

  // Update navigation state when config changes
  useEffect(() => {
    updateNavigationState()
  }, [wizardState.config, wizardState.currentStep])

  // Load projects
  const loadProjects = async () => {
    try {
      setLoading(true)
      const loadedProjects = await onLoadProjects()
      setProjects(loadedProjects)
    } catch {
      showError('프로젝트를 불러오는데 실패했습니다.')
    } finally {
      setLoading(false)
    }
  }

  // Load episodes for selected project
  const loadEpisodes = async (projectId: string) => {
    try {
      const loadedEpisodes = await onLoadEpisodes(projectId)
      setEpisodes(loadedEpisodes)

      // Load project data for context
      const project = projects.find(p => p.id === projectId)
      setProjectData(project || null)
    } catch {
      showError('에피소드를 불러오는데 실패했습니다.')
    }
  }

  // Load AI models
  const loadAIModels = async () => {
    try {
      const models = await onLoadAIModels()
      setAIModels(models)
    } catch {
      showError('AI 모델 정보를 불러오는데 실패했습니다.')
    }
  }

  // Update wizard configuration
  const updateConfig = (updates: Partial<GenerationConfig>) => {
    setWizardState(prev => ({
      ...prev,
      config: { ...prev.config, ...updates },
    }))

    // Load episode data if episode is selected
    if (updates.episodeId) {
      const episode = episodes.find(e => e.id === updates.episodeId)
      setEpisodeData(episode || null)
    }
  }

  // Check if current step can proceed
  const updateNavigationState = () => {
    let canProceed = false
    let canGoBack = wizardState.currentStep !== 'selection'

    switch (wizardState.currentStep) {
      case 'selection':
        canProceed = !!wizardState.config.projectId
        canGoBack = false
        break

      case 'configuration':
        canProceed = !!(
          wizardState.config.aiModel &&
          wizardState.config.tone &&
          wizardState.config.language
        )
        break

      case 'prompt':
        canProceed = !!wizardState.config.prompt?.trim()
        break

      case 'generation':
        canProceed = wizardState.job?.status === 'completed'
        canGoBack = false
        break

      case 'results':
        canProceed = true
        canGoBack = false
        break
    }

    setWizardState(prev => ({
      ...prev,
      canProceed,
      canGoBack,
    }))
  }

  // Navigate to next step
  const handleNext = () => {
    const currentIndex = WIZARD_STEPS.findIndex(
      step => step.key === wizardState.currentStep,
    )
    if (currentIndex >= 0 && currentIndex < WIZARD_STEPS.length - 1) {
      const nextStep = WIZARD_STEPS[currentIndex + 1]?.key
      if (nextStep) {
        setWizardState(prev => ({
          ...prev,
          currentStep: nextStep,
        }))
      }
    }
  }

  // Navigate to previous step
  const handleBack = () => {
    const currentIndex = WIZARD_STEPS.findIndex(
      step => step.key === wizardState.currentStep,
    )
    if (currentIndex > 0) {
      const prevStep = WIZARD_STEPS[currentIndex - 1]?.key
      if (prevStep) {
        setWizardState(prev => ({
          ...prev,
          currentStep: prevStep,
        }))
      }
    }
  }

  // Start generation
  const handleStartGeneration = async () => {
    try {
      setLoading(true)
      const job = await onStartGeneration(
        wizardState.config as GenerationConfig,
      )
      setWizardState(prev => ({
        ...prev,
        currentStep: 'generation',
        job,
      }))
    } catch {
      showError('스크립트 생성을 시작할 수 없습니다.')
    } finally {
      setLoading(false)
    }
  }

  // Handle generation completion
  const handleGenerationComplete = (result: GenerationResult) => {
    // Convert streaming GenerationResult to local GenerationResult
    const markdownContent = toMarkdownText(result.script || '')
    const localResult: LocalGenerationResult = {
      id: Date.now().toString(), // Generate temporary ID
      jobId: Date.now().toString(), // Generate temporary job ID
      title: 'Generated Script',
      content: markdownContent,
      metadata: {
        wordCount: 0,
        characterCount: markdownContent.length,
        estimatedDuration: 0,
        scenes: 0,
        aiModel: 'unknown',
        generatedAt: new Date(),
      },
      quality: {
        score: 0,
        aspects: {
          coherence: 0,
          creativity: 0,
          dialogue: 0,
          pacing: 0,
          characterization: 0,
        },
      },
    }

    setWizardState(prev => ({
      ...prev,
      currentStep: 'results',
      result: localResult,
      ...(prev.job && { job: { ...prev.job, status: 'completed' } }),
    }))
  }

  // Handle generation error
  const handleGenerationError = (error: string) => {
    setWizardState(prev => ({
      ...prev,
      ...(prev.job && { job: { ...prev.job, status: 'failed', error } }),
    }))
    showError(`생성 실패: ${error}`)
  }

  // Handle generation cancellation
  const handleGenerationCancel = () => {
    setWizardState(prev => {
      const { job, ...rest } = prev
      return {
        ...rest,
        currentStep: 'prompt',
      }
    })
    showWarning('스크립트 생성이 취소되었습니다.')
  }

  // Restart generation
  const handleRestart = () => {
    setWizardState(prev => {
      const { job, result, ...rest } = prev
      return {
        ...rest,
        currentStep: 'prompt',
      }
    })
  }

  // Save result
  const handleSaveResult = async (
    editedContent: string,
    editedTitle: string,
  ) => {
    if (!wizardState.result) return

    await onSaveResult(wizardState.result, editedContent, editedTitle)

    // Convert local GenerationResult back to streaming GenerationResult for callback
    const streamingResult: GenerationResult = {
      jobId: wizardState.result.jobId,
      projectId: wizardState.config.projectId || '',
      episodeId: wizardState.config.episodeId || '',
      content: wizardState.result.content,
      script: {
        markdown: wizardState.result.content,
      },
      status: 'completed',
    }
    onComplete(streamingResult)
  }

  const currentStepIndex = WIZARD_STEPS.findIndex(
    step => step.key === wizardState.currentStep,
  )
  const currentStepConfig = WIZARD_STEPS[currentStepIndex]

  return (
    <Box maxWidth="1200px" mx="auto" p={3}>
      <Stack spacing={3}>
        {/* Header */}
        <Box textAlign="center">
          <Typography variant="h4" gutterBottom>
            ✨ AI 스크립트 생성 마법사
          </Typography>
          <Typography variant="body1" color="textSecondary">
            3단계로 간편하게 AI 스크립트를 생성하세요
          </Typography>
        </Box>

        {/* Progress Stepper */}
        <Card>
          <CardContent>
            <Stepper
              activeStep={currentStepIndex}
              orientation="horizontal"
              alternativeLabel
            >
              {WIZARD_STEPS.slice(0, 3).map((step, index) => (
                <Step key={step.key} completed={currentStepIndex > index}>
                  <StepLabel>{step.label}</StepLabel>
                </Step>
              ))}
            </Stepper>
          </CardContent>
        </Card>

        {/* Step Content */}
        <Box>
          {wizardState.currentStep === 'selection' && (
            <SelectionStep
              projects={projects}
              episodes={episodes}
              config={wizardState.config}
              onConfigChange={updateConfig}
              onLoadProjects={loadProjects}
              onLoadEpisodes={loadEpisodes}
              onCreateProject={onCreateProject}
              onCreateEpisode={onCreateEpisode}
              loading={loading}
            />
          )}

          {wizardState.currentStep === 'configuration' && (
            <ConfigurationStep
              config={wizardState.config}
              onConfigChange={updateConfig}
              availableModels={aiModels}
            />
          )}

          {wizardState.currentStep === 'prompt' && (
            <PromptStep
              config={wizardState.config}
              onConfigChange={updateConfig}
              {...(projectData && {
                projectData: {
                  name: projectData.name,
                  ...(projectData.description && {
                    description: projectData.description,
                  }),
                  type: projectData.type,
                },
              })}
              {...(episodeData && {
                episodeData: {
                  title: episodeData.title,
                  ...(episodeData.description && {
                    description: episodeData.description,
                  }),
                  characters: [],
                  locations: [],
                  themes: [],
                },
              })}
            />
          )}

          {wizardState.currentStep === 'generation' && wizardState.job && (
            <RealtimeProgress
              job={wizardState.job}
              onCancel={handleGenerationCancel}
              onRestart={handleRestart}
              onComplete={handleGenerationComplete}
              onError={handleGenerationError}
            />
          )}

          {wizardState.currentStep === 'results' &&
            wizardState.result &&
            wizardState.job && (
              <GenerationResults
                result={wizardState.result}
                job={wizardState.job}
                onSave={handleSaveResult}
                onRegenerate={handleRestart}
                onEdit={() => {}} // Handle edit mode if needed
              />
            )}
        </Box>

        {/* Navigation */}
        {wizardState.currentStep !== 'generation' &&
          wizardState.currentStep !== 'results' && (
            <Card>
              <CardContent>
                <Stack
                  direction="row"
                  spacing={2}
                  justifyContent="space-between"
                  alignItems="center"
                >
                  <Button
                    startIcon={<BackIcon />}
                    onClick={handleBack}
                    disabled={!wizardState.canGoBack}
                    variant="outlined"
                  >
                    이전
                  </Button>

                  <Typography
                    variant="body2"
                    color="textSecondary"
                    textAlign="center"
                  >
                    {currentStepConfig?.description}
                  </Typography>

                  {wizardState.currentStep === 'prompt' ? (
                    <Button
                      endIcon={<GenerateIcon />}
                      onClick={handleStartGeneration}
                      disabled={!wizardState.canProceed || loading}
                      variant="contained"
                      color="primary"
                    >
                      생성 시작
                    </Button>
                  ) : (
                    <Button
                      endIcon={<NextIcon />}
                      onClick={handleNext}
                      disabled={!wizardState.canProceed}
                      variant="contained"
                    >
                      다음
                    </Button>
                  )}
                </Stack>
              </CardContent>
            </Card>
          )}

        {/* Cancel Button */}
        {onCancel && wizardState.currentStep !== 'generation' && (
          <Box textAlign="center">
            <Button onClick={onCancel} color="secondary">
              취소
            </Button>
          </Box>
        )}

        {/* Loading Backdrop */}
        <Backdrop
          open={loading}
          sx={{ zIndex: theme => theme.zIndex.drawer + 1 }}
        >
          <CircularProgress color="inherit" />
        </Backdrop>
      </Stack>
    </Box>
  )
}
