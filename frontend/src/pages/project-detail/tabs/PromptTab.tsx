import { useState, useEffect } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Alert,
  Stack,
  Chip,
  CircularProgress,
} from '@mui/material'
import SaveIcon from '@mui/icons-material/Save'
import AIIcon from '@mui/icons-material/AutoAwesome'
import InfoIcon from '@mui/icons-material/Info'

import { useToastHelpers } from '@/shared/ui/components/toast'

interface PromptTabProps {
  projectId: string
}

interface SystemPrompt {
  id: string
  version: string
  content: string
  isActive: boolean
  updatedAt: string
}

export function PromptTab({ projectId }: PromptTabProps) {
  const [promptContent, setPromptContent] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [hasChanges, setHasChanges] = useState(false)
  const [currentPrompt, setCurrentPrompt] = useState<SystemPrompt | null>(null)

  const { showSuccess, showError } = useToastHelpers()

  // 현재 시스템 프롬프트 로드
  useEffect(() => {
    const loadCurrentPrompt = async () => {
      try {
        setIsLoading(true)
        // Mock 데이터 - 실제로는 API 호출
        const mockPrompt: SystemPrompt = {
          id: `prompt-${projectId}`,
          version: '1.2.0',
          content: `당신은 전문적인 드라마 작가입니다. 다음 조건에 맞춰 고품질 스크립트를 작성해주세요:

1. 자연스럽고 현실적인 대화
2. 등장인물의 성격과 배경에 맞는 말투
3. 적절한 감정 표현과 갈등 구조
4. 시청자의 몰입을 높이는 전개

추가 지침:
- 각 씬은 명확한 목적을 가져야 합니다
- 대화는 스토리를 전진시켜야 합니다
- 감정의 변화를 자연스럽게 표현하세요
- 시각적 연출을 위한 동작 묘사를 포함하세요`,
          isActive: true,
          updatedAt: new Date().toISOString(),
        }

        setCurrentPrompt(mockPrompt)
        setPromptContent(mockPrompt.content)
      } catch {
        showError('시스템 프롬프트를 불러오는데 실패했습니다.')
      } finally {
        setIsLoading(false)
      }
    }

    loadCurrentPrompt()
  }, [projectId, showError])

  // 프롬프트 내용 변경 감지
  useEffect(() => {
    if (currentPrompt) {
      setHasChanges(promptContent !== currentPrompt.content)
    }
  }, [promptContent, currentPrompt])

  // 저장 처리
  const handleSave = async () => {
    if (!hasChanges || !currentPrompt) return

    setIsSaving(true)
    try {
      // Mock 저장 - 실제로는 API 호출
      await new Promise(resolve => setTimeout(resolve, 1000))

      const updatedPrompt = {
        ...currentPrompt,
        content: promptContent,
        version: incrementVersion(currentPrompt.version),
        updatedAt: new Date().toISOString(),
      }

      setCurrentPrompt(updatedPrompt)
      setHasChanges(false)
      showSuccess(
        '시스템 프롬프트가 저장되었습니다. 새로운 스크립트 생성부터 적용됩니다.',
      )
    } catch {
      showError('저장 중 오류가 발생했습니다.')
    } finally {
      setIsSaving(false)
    }
  }

  // 버전 증가 헬퍼
  const incrementVersion = (version: string): string => {
    const parts = version.split('.')
    const patch = parseInt(parts[2] || '0') + 1
    return `${parts[0]}.${parts[1]}.${patch}`
  }

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Box>
      <Box display="flex" flexWrap="wrap" gap={3}>
        {/* 시스템 프롬프트 에디터 */}
        <Box flex="1 1 65%" minWidth="400px">
          <Card>
            <CardContent>
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  mb: 3,
                }}
              >
                <Typography
                  variant="h6"
                  sx={{ display: 'flex', alignItems: 'center', gap: 1 }}
                >
                  <AIIcon color="primary" />
                  시스템 프롬프트 편집
                </Typography>

                <Stack direction="row" spacing={1} alignItems="center">
                  {currentPrompt && (
                    <Chip
                      label={`v${currentPrompt.version}`}
                      size="small"
                      color="primary"
                      variant="outlined"
                    />
                  )}
                  {hasChanges && (
                    <Chip label="변경됨" size="small" color="warning" />
                  )}
                </Stack>
              </Box>

              <Alert severity="info" sx={{ mb: 3 }}>
                <Typography variant="body2">
                  <strong>항상 최신 버전 사용:</strong> 저장 즉시 새로운
                  스크립트 생성에 적용됩니다.
                </Typography>
              </Alert>

              <TextField
                multiline
                fullWidth
                rows={16}
                value={promptContent}
                onChange={e => setPromptContent(e.target.value)}
                placeholder="시스템 프롬프트를 입력하세요..."
                variant="outlined"
                sx={{
                  mb: 3,
                  '& .MuiOutlinedInput-root': {
                    fontFamily: 'monospace',
                    fontSize: '0.875rem',
                  },
                }}
                aria-label="시스템 프롬프트 내용"
              />

              <Box
                sx={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <Typography variant="body2" color="text.secondary">
                  {promptContent.length} 글자
                </Typography>

                <Button
                  variant="contained"
                  startIcon={
                    isSaving ? <CircularProgress size={16} /> : <SaveIcon />
                  }
                  onClick={handleSave}
                  disabled={!hasChanges || isSaving}
                >
                  {isSaving ? '저장 중...' : '저장'}
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Box>

        {/* 버전 정보 및 도움말 */}
        <Box flex="1 1 30%" minWidth="300px">
          <Stack spacing={3}>
            {/* 현재 버전 정보 */}
            {currentPrompt && (
              <Card>
                <CardContent>
                  <Typography
                    variant="h6"
                    gutterBottom
                    sx={{ display: 'flex', alignItems: 'center', gap: 1 }}
                  >
                    <InfoIcon color="primary" />
                    버전 정보
                  </Typography>

                  <Stack spacing={2}>
                    <Box>
                      <Typography variant="subtitle2" color="text.secondary">
                        현재 버전
                      </Typography>
                      <Typography variant="body1" fontWeight="bold">
                        v{currentPrompt.version}
                      </Typography>
                    </Box>

                    <Box>
                      <Typography variant="subtitle2" color="text.secondary">
                        마지막 업데이트
                      </Typography>
                      <Typography variant="body2">
                        {new Date(currentPrompt.updatedAt).toLocaleDateString(
                          'ko-KR',
                        )}
                      </Typography>
                    </Box>

                    <Alert severity="success">
                      <Typography variant="body2">
                        <strong>자동 적용:</strong> 저장 후 즉시 모든 새로운
                        스크립트 생성에 적용됩니다.
                      </Typography>
                    </Alert>
                  </Stack>
                </CardContent>
              </Card>
            )}

            {/* 작성 가이드 */}
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  작성 가이드
                </Typography>

                <Stack spacing={1}>
                  <Typography variant="body2">
                    <strong>• 명확한 역할 정의:</strong> AI의 역할과 전문성을
                    명시하세요
                  </Typography>
                  <Typography variant="body2">
                    <strong>• 구체적인 조건:</strong> 원하는 스타일과 규칙을
                    상세히 작성하세요
                  </Typography>
                  <Typography variant="body2">
                    <strong>• 품질 기준:</strong> 출력물의 품질 기준을
                    제시하세요
                  </Typography>
                  <Typography variant="body2">
                    <strong>• 형식 안내:</strong> 원하는 출력 형식을 설명하세요
                  </Typography>
                </Stack>
              </CardContent>
            </Card>
          </Stack>
        </Box>
      </Box>
    </Box>
  )
}
