import { useState } from 'react'
import type { ReactNode, KeyboardEvent } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Stack,
  TextField,
  Chip,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Button,
  IconButton,
  Tooltip,
} from '@mui/material'
import {
  ExpandMore as ExpandMoreIcon,
  Edit as EditIcon,
  AutoAwesome as MagicIcon,
  Person as CharacterIcon,
  LocationOn as LocationIcon,
  Psychology as ThemeIcon,
  Help as HelpIcon,
} from '@mui/icons-material'

import type { GenerationConfig } from '../types'

interface PromptStepProps {
  config: Partial<GenerationConfig>
  onConfigChange: (updates: Partial<GenerationConfig>) => void
  projectData?: {
    name: string
    description?: string
    type: string
  }
  episodeData?: {
    title: string
    description?: string
    characters?: string[]
    locations?: string[]
    themes?: string[]
  }
}

// Example prompts for different genres
const EXAMPLE_PROMPTS = {
  drama:
    '한 가족이 경제적 어려움을 극복해가는 과정에서 서로에게 의지하며 진정한 유대감을 찾아가는 이야기를 써주세요.',
  comedy:
    '평범한 직장인이 갑작스럽게 CEO가 되면서 벌어지는 좌충우돌 코미디 상황들을 그려주세요.',
  action:
    '특수요원이 인질을 구출하기 위해 적의 본거지에 잠입하는 긴장감 넘치는 액션 시퀀스를 작성해주세요.',
  romance:
    '우연히 만난 두 사람이 서로를 알아가며 사랑에 빠지는 달콤한 로맨스 스토리를 만들어주세요.',
  thriller:
    '연쇄 살인 사건을 추적하는 형사가 범인과의 심리적 대결을 벌이는 스릴러를 써주세요.',
  mystery:
    '사라진 보석을 찾기 위해 탐정이 단서를 하나씩 추적해가는 미스터리를 작성해주세요.',
}

// Prompt enhancement tips
const PROMPT_TIPS = [
  {
    title: '구체적인 상황 설정',
    description: '시간, 장소, 등장인물의 관계를 명확히 제시하세요.',
    example:
      '"카페에서 만난 두 사람" → "비 오는 화요일 저녁, 작은 재즈카페에서 우연히 만난 옛 연인"',
  },
  {
    title: '감정과 동기',
    description: '인물의 내적 갈등이나 욕구를 포함하세요.',
    example:
      '"주인공이 결정한다" → "복수심에 불타는 주인공이 용서와 복수 사이에서 고민한다"',
  },
  {
    title: '장면의 분위기',
    description: '원하는 톤과 무드를 구체적으로 표현하세요.',
    example:
      '"긴장감 있게" → "숨막히는 정적 속에서 시계 초침 소리만 들리는 긴장감"',
  },
]

/**
 * Character/Location/Theme chip input component
 */
function ChipInput({
  label,
  value,
  onChange,
  placeholder,
  icon,
  suggestions = [],
}: {
  label: string
  value: string[]
  onChange: (values: string[]) => void
  placeholder: string
  icon: ReactNode
  suggestions?: string[]
}) {
  const [inputValue, setInputValue] = useState('')

  const handleAddChip = (newValue: string) => {
    if (newValue.trim() && !value.includes(newValue.trim())) {
      onChange([...value, newValue.trim()])
    }
    setInputValue('')
  }

  const handleRemoveChip = (chipToRemove: string) => {
    onChange(value.filter(item => item !== chipToRemove))
  }

  const handleKeyPress = (event: KeyboardEvent) => {
    if (event.key === 'Enter') {
      event.preventDefault()
      handleAddChip(inputValue)
    }
  }

  return (
    <Box>
      <Typography
        variant="subtitle1"
        gutterBottom
        display="flex"
        alignItems="center"
        gap={1}
      >
        {icon}
        {label}
      </Typography>

      <TextField
        fullWidth
        size="small"
        value={inputValue}
        onChange={e => setInputValue(e.target.value)}
        onKeyPress={handleKeyPress}
        placeholder={placeholder}
        onBlur={() => {
          if (inputValue.trim()) {
            handleAddChip(inputValue)
          }
        }}
      />

      <Box mt={1}>
        <Stack direction="row" spacing={0.5} flexWrap="wrap">
          {value.map(item => (
            <Chip
              key={item}
              label={item}
              onDelete={() => handleRemoveChip(item)}
              size="small"
              color="primary"
              variant="outlined"
            />
          ))}
        </Stack>
      </Box>

      {suggestions.length > 0 && (
        <Box mt={1}>
          <Typography variant="caption" color="textSecondary" gutterBottom>
            추천:
          </Typography>
          <Stack direction="row" spacing={0.5} flexWrap="wrap">
            {suggestions
              .filter(suggestion => !value.includes(suggestion))
              .slice(0, 5)
              .map(suggestion => (
                <Chip
                  key={suggestion}
                  label={suggestion}
                  onClick={() => handleAddChip(suggestion)}
                  size="small"
                  variant="outlined"
                  clickable
                />
              ))}
          </Stack>
        </Box>
      )}
    </Box>
  )
}

/**
 * Step 3: Detailed Prompt Input
 */
export function PromptStep({
  config,
  onConfigChange,
  projectData,
  episodeData,
}: PromptStepProps) {
  const [showAdvanced, setShowAdvanced] = useState(false)

  const examplePrompt = config.genre
    ? EXAMPLE_PROMPTS[config.genre as keyof typeof EXAMPLE_PROMPTS]
    : ''

  const generateSmartPrompt = () => {
    let prompt = ''

    if (projectData) {
      prompt += `"${projectData.name}" 프로젝트의 `
      if (episodeData) {
        prompt += `"${episodeData.title}" 에피소드를 위한 스크립트를 작성해주세요.\n\n`
      } else {
        prompt += `새로운 에피소드 스크립트를 작성해주세요.\n\n`
      }
    }

    if (config.genre && config.tone) {
      const genreLabel = config.genre
      const toneLabel = config.tone
      prompt += `장르는 ${genreLabel}이고, ${toneLabel} 톤으로 작성해주세요.\n\n`
    }

    if (episodeData?.description) {
      prompt += `에피소드 설명: ${episodeData.description}\n\n`
    }

    if (config.characters && config.characters.length > 0) {
      prompt += `주요 등장인물: ${config.characters.join(', ')}\n`
    }

    if (config.locations && config.locations.length > 0) {
      prompt += `주요 장소: ${config.locations.join(', ')}\n`
    }

    if (config.themes && config.themes.length > 0) {
      prompt += `다루고 싶은 주제: ${config.themes.join(', ')}\n\n`
    }

    prompt +=
      '구체적인 장면과 대화를 포함하여 생생하고 몰입감 있는 스크립트를 작성해주세요.'

    onConfigChange({ prompt })
  }

  const currentCharCount = config.prompt?.length || 0
  const maxCharCount = 2000

  return (
    <Stack spacing={3}>
      {/* Header */}
      <Box>
        <Typography variant="h5" gutterBottom>
          상세 프롬프트 입력
        </Typography>
        <Typography variant="body1" color="textSecondary">
          AI가 생성할 스크립트에 대한 상세한 지시사항을 입력해주세요.
        </Typography>
      </Box>

      {/* Project/Episode Context */}
      {(projectData || episodeData) && (
        <Alert severity="info">
          <Typography variant="subtitle2" gutterBottom>
            현재 컨텍스트:
          </Typography>
          {projectData && (
            <Typography variant="body2">
              📁 프로젝트: {projectData.name} ({projectData.type})
            </Typography>
          )}
          {episodeData && (
            <Typography variant="body2">
              🎬 에피소드: {episodeData.title}
            </Typography>
          )}
        </Alert>
      )}

      {/* Smart Prompt Generator */}
      <Card>
        <CardContent>
          <Box
            display="flex"
            alignItems="center"
            justifyContent="space-between"
            mb={2}
          >
            <Typography variant="h6" display="flex" alignItems="center" gap={1}>
              <MagicIcon color="primary" />
              스마트 프롬프트 생성
            </Typography>
            <Button
              variant="outlined"
              startIcon={<MagicIcon />}
              onClick={generateSmartPrompt}
              size="small"
            >
              자동 생성
            </Button>
          </Box>
          <Typography variant="body2" color="textSecondary">
            현재 설정을 바탕으로 최적화된 프롬프트를 자동으로 생성합니다.
          </Typography>
        </CardContent>
      </Card>

      {/* Main Prompt Input */}
      <Card>
        <CardContent>
          <Box
            display="flex"
            alignItems="center"
            justifyContent="between"
            mb={2}
          >
            <Typography variant="h6" display="flex" alignItems="center" gap={1}>
              <EditIcon color="primary" />
              메인 프롬프트
            </Typography>
            <Tooltip title="좋은 프롬프트 작성 팁을 보려면 클릭하세요">
              <IconButton size="small">
                <HelpIcon />
              </IconButton>
            </Tooltip>
          </Box>

          <TextField
            fullWidth
            multiline
            rows={8}
            value={config.prompt || ''}
            onChange={e => onConfigChange({ prompt: e.target.value })}
            placeholder="AI가 생성할 스크립트에 대해 상세히 설명해주세요. 예를 들어: 장면 설정, 인물들의 관계, 원하는 분위기, 특별한 요구사항 등을 포함할 수 있습니다."
            helperText={`${currentCharCount}/${maxCharCount} 글자`}
            error={currentCharCount > maxCharCount}
          />

          {examplePrompt && !config.prompt && (
            <Box mt={2}>
              <Typography variant="subtitle2" gutterBottom>
                예시 프롬프트:
              </Typography>
              <Card variant="outlined" sx={{ bgcolor: 'grey.50' }}>
                <CardContent sx={{ py: 2 }}>
                  <Typography variant="body2" style={{ fontStyle: 'italic' }}>
                    {examplePrompt}
                  </Typography>
                  <Button
                    size="small"
                    onClick={() => onConfigChange({ prompt: examplePrompt })}
                    sx={{ mt: 1 }}
                  >
                    이 예시 사용하기
                  </Button>
                </CardContent>
              </Card>
            </Box>
          )}
        </CardContent>
      </Card>

      {/* Advanced Settings */}
      <Accordion
        expanded={showAdvanced}
        onChange={(_, expanded) => setShowAdvanced(expanded)}
      >
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="h6">고급 설정 (선택사항)</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Stack spacing={3}>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
              {/* Characters */}
              <Box
                sx={{
                  flex: { xs: '1 1 100%', md: '1 1 calc(33.333% - 16px)' },
                }}
              >
                <ChipInput
                  label="등장인물"
                  value={config.characters || []}
                  onChange={characters => onConfigChange({ characters })}
                  placeholder="등장인물 이름을 입력하세요"
                  icon={<CharacterIcon />}
                  suggestions={episodeData?.characters || []}
                />
              </Box>

              {/* Locations */}
              <Box
                sx={{
                  flex: { xs: '1 1 100%', md: '1 1 calc(33.333% - 16px)' },
                }}
              >
                <ChipInput
                  label="주요 장소"
                  value={config.locations || []}
                  onChange={locations => onConfigChange({ locations })}
                  placeholder="장소를 입력하세요"
                  icon={<LocationIcon />}
                  suggestions={episodeData?.locations || []}
                />
              </Box>

              {/* Themes */}
              <Box
                sx={{
                  flex: { xs: '1 1 100%', md: '1 1 calc(33.333% - 16px)' },
                }}
              >
                <ChipInput
                  label="주제/테마"
                  value={config.themes || []}
                  onChange={themes => onConfigChange({ themes })}
                  placeholder="다루고 싶은 주제를 입력하세요"
                  icon={<ThemeIcon />}
                  suggestions={
                    episodeData?.themes || [
                      '가족',
                      '사랑',
                      '우정',
                      '성장',
                      '갈등',
                    ]
                  }
                />
              </Box>
            </Box>

            {/* Special Instructions */}
            <Box>
              <Typography variant="subtitle1" gutterBottom>
                특별 지시사항
              </Typography>
              <TextField
                fullWidth
                multiline
                rows={3}
                value={config.specialInstructions || ''}
                onChange={e =>
                  onConfigChange({ specialInstructions: e.target.value })
                }
                placeholder="특별한 스타일 요구사항, 피해야 할 내용, 특정 형식 등을 입력하세요"
                helperText="예: '대화 중심으로 작성', '액션 시퀀스 최소화', '감정적 장면 강조' 등"
              />
            </Box>
          </Stack>
        </AccordionDetails>
      </Accordion>

      {/* Prompt Writing Tips */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            💡 효과적인 프롬프트 작성 팁
          </Typography>
          <Stack spacing={2}>
            {PROMPT_TIPS.map((tip, index) => (
              <Box key={index}>
                <Typography variant="subtitle2" color="primary">
                  {tip.title}
                </Typography>
                <Typography variant="body2" color="textSecondary" gutterBottom>
                  {tip.description}
                </Typography>
                <Typography
                  variant="caption"
                  sx={{
                    fontStyle: 'italic',
                    bgcolor: 'grey.100',
                    p: 1,
                    borderRadius: 1,
                    display: 'block',
                  }}
                >
                  {tip.example}
                </Typography>
              </Box>
            ))}
          </Stack>
        </CardContent>
      </Card>

      {/* Final Summary */}
      {config.prompt && (
        <Alert severity="success">
          <Typography variant="subtitle2" gutterBottom>
            프롬프트 준비 완료!
          </Typography>
          <Typography variant="body2">
            {config.prompt.length > 100
              ? `"${config.prompt.substring(0, 100)}..."`
              : config.prompt}
          </Typography>
          <Box mt={1}>
            <Stack direction="row" spacing={1} flexWrap="wrap">
              <Chip
                label={`${config.prompt.split(' ').length}개 단어`}
                size="small"
              />
              <Chip label={`${config.prompt.length}자`} size="small" />
              {(config.characters?.length || 0) > 0 && (
                <Chip
                  label={`${config.characters?.length}명 등장인물`}
                  size="small"
                />
              )}
              {(config.locations?.length || 0) > 0 && (
                <Chip
                  label={`${config.locations?.length}개 장소`}
                  size="small"
                />
              )}
              {(config.themes?.length || 0) > 0 && (
                <Chip label={`${config.themes?.length}개 주제`} size="small" />
              )}
            </Stack>
          </Box>
        </Alert>
      )}
    </Stack>
  )
}
