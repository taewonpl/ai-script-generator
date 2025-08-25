import {
  Box,
  Card,
  CardContent,
  Typography,
  Stack,
  RadioGroup,
  FormControlLabel,
  Radio,
  Slider,
  Chip,
  Alert,
  Divider,
  Badge,
} from '@mui/material'
import {
  Psychology as AIIcon,
  Palette as StyleIcon,
  Speed as SpeedIcon,
  Star as QualityIcon,
  AttachMoney as CostIcon,
} from '@mui/icons-material'

import type { AIModelOption, GenerationConfig } from '../types'

interface ConfigurationStepProps {
  config: Partial<GenerationConfig>
  onConfigChange: (updates: Partial<GenerationConfig>) => void
  availableModels: AIModelOption[]
}

// Predefined options
const GENRE_OPTIONS = [
  {
    value: 'drama',
    label: '드라마',
    description: '감정적이고 현실적인 이야기',
  },
  { value: 'comedy', label: '코미디', description: '유머와 재미를 중심으로' },
  {
    value: 'action',
    label: '액션',
    description: '역동적이고 긴장감 있는 장면',
  },
  { value: 'romance', label: '로맨스', description: '사랑과 관계를 중심으로' },
  { value: 'thriller', label: '스릴러', description: '긴장감과 서스펜스' },
  { value: 'fantasy', label: '판타지', description: '마법과 상상의 세계' },
  { value: 'mystery', label: '미스터리', description: '수수께끼와 추리' },
]

const TONE_OPTIONS = [
  {
    value: 'light',
    label: '밝고 경쾌한',
    description: '유쾌하고 긍정적인 분위기',
  },
  {
    value: 'serious',
    label: '진지한',
    description: '무게감 있고 사려 깊은 톤',
  },
  {
    value: 'dramatic',
    label: '극적인',
    description: '감정적 기복이 큰 드라마틱한 톤',
  },
  {
    value: 'humorous',
    label: '유머러스한',
    description: '위트와 유머가 가득한 톤',
  },
  {
    value: 'dark',
    label: '어둡고 무거운',
    description: '심각하고 우울한 분위기',
  },
  {
    value: 'inspiring',
    label: '감동적인',
    description: '희망과 용기를 주는 톤',
  },
]

const LENGTH_OPTIONS = [
  {
    value: 'short',
    label: '짧게 (10-15분)',
    tokens: 2000,
    description: '간단한 장면이나 컨셉',
  },
  {
    value: 'medium',
    label: '보통 (20-30분)',
    tokens: 4000,
    description: '일반적인 에피소드',
  },
  {
    value: 'long',
    label: '길게 (45-60분)',
    tokens: 8000,
    description: '상세한 장편 에피소드',
  },
]

const LANGUAGE_OPTIONS = [
  { value: 'ko', label: '한국어', flag: '🇰🇷' },
  { value: 'en', label: 'English', flag: '🇺🇸' },
  { value: 'ja', label: '日本語', flag: '🇯🇵' },
]

/**
 * AI Model Selection Card
 */
function AIModelCard({
  model,
  selected,
  onSelect,
}: {
  model: AIModelOption
  selected: boolean
  onSelect: () => void
}) {
  const getSpeedColor = (speed: string) => {
    switch (speed) {
      case 'fast':
        return 'success'
      case 'medium':
        return 'warning'
      case 'slow':
        return 'error'
      default:
        return 'default'
    }
  }

  const getQualityColor = (quality: string) => {
    switch (quality) {
      case 'premium':
        return 'success'
      case 'high':
        return 'info'
      case 'standard':
        return 'default'
      default:
        return 'default'
    }
  }

  return (
    <Card
      variant="outlined"
      sx={{
        cursor: 'pointer',
        transition: 'all 0.2s',
        '&:hover': {
          bgcolor: 'action.hover',
          transform: 'translateY(-2px)',
          boxShadow: 2,
        },
        bgcolor: selected ? 'action.selected' : 'background.paper',
        border: selected ? '2px solid' : '1px solid',
        borderColor: selected ? 'primary.main' : 'divider',
      }}
      onClick={onSelect}
    >
      <CardContent>
        <Box
          display="flex"
          alignItems="center"
          justifyContent="space-between"
          mb={1}
        >
          <Typography variant="h6" fontWeight="bold">
            {model.name}
          </Typography>
          <Badge color="primary" variant="dot" invisible={!selected}>
            <Chip label={model.provider} size="small" variant="outlined" />
          </Badge>
        </Box>

        <Typography variant="body2" color="textSecondary" mb={2}>
          {model.description}
        </Typography>

        <Stack direction="row" spacing={1} flexWrap="wrap" mb={2}>
          <Chip
            icon={<SpeedIcon />}
            label={`속도: ${model.speed}`}
            size="small"
            color={getSpeedColor(model.speed) as any}
            variant="outlined"
          />
          <Chip
            icon={<QualityIcon />}
            label={`품질: ${model.quality}`}
            size="small"
            color={getQualityColor(model.quality) as any}
            variant="outlined"
          />
          {model.pricing && (
            <Chip
              icon={<CostIcon />}
              label={`$${model.pricing.outputCost}/1K토큰`}
              size="small"
              variant="outlined"
            />
          )}
        </Stack>

        <Box>
          <Typography variant="caption" color="textSecondary">
            지원 기능: {model.capabilities.join(', ')}
          </Typography>
        </Box>
      </CardContent>
    </Card>
  )
}

/**
 * Step 2: AI Configuration
 */
export function ConfigurationStep({
  config,
  onConfigChange,
  availableModels,
}: ConfigurationStepProps) {
  const selectedModel = availableModels.find(m => m.id === config.aiModel)
  const selectedLength = LENGTH_OPTIONS.find(l => l.value === config.length)

  const handleAdvancedChange = (
    field: keyof GenerationConfig,
    value: number,
  ) => {
    onConfigChange({ [field]: value })
  }

  return (
    <Stack spacing={3}>
      {/* Header */}
      <Box>
        <Typography variant="h5" gutterBottom>
          AI 모델 및 설정
        </Typography>
        <Typography variant="body1" color="textSecondary">
          스크립트 생성에 사용할 AI 모델과 생성 옵션을 설정해주세요.
        </Typography>
      </Box>

      {/* AI Model Selection */}
      <Card>
        <CardContent>
          <Typography
            variant="h6"
            gutterBottom
            display="flex"
            alignItems="center"
            gap={1}
          >
            <AIIcon color="primary" />
            AI 모델 선택
          </Typography>

          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
            {availableModels.map(model => (
              <Box
                key={model.id}
                sx={{
                  flex: {
                    xs: '1 1 100%',
                    sm: '1 1 calc(50% - 8px)',
                    md: '1 1 calc(33.333% - 16px)',
                  },
                }}
              >
                <AIModelCard
                  model={model}
                  selected={config.aiModel === model.id}
                  onSelect={() => onConfigChange({ aiModel: model.id })}
                />
              </Box>
            ))}
          </Box>

          {selectedModel && (
            <Alert severity="info" sx={{ mt: 2 }}>
              <Typography variant="body2">
                <strong>{selectedModel.name}</strong> 선택됨 - 최대{' '}
                {selectedModel.maxTokens.toLocaleString()}토큰까지 생성 가능
              </Typography>
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Content Settings */}
      <Card>
        <CardContent>
          <Typography
            variant="h6"
            gutterBottom
            display="flex"
            alignItems="center"
            gap={1}
          >
            <StyleIcon color="primary" />
            콘텐츠 설정
          </Typography>

          <Stack spacing={3}>
            {/* Genre */}
            <Box>
              <Typography variant="subtitle1" gutterBottom>
                장르
              </Typography>
              <RadioGroup
                row
                value={config.genre || ''}
                onChange={e => onConfigChange({ genre: e.target.value })}
              >
                <Stack direction="row" spacing={1} flexWrap="wrap">
                  {GENRE_OPTIONS.map(genre => (
                    <Card
                      key={genre.value}
                      variant="outlined"
                      sx={{
                        cursor: 'pointer',
                        minWidth: 140,
                        '&:hover': { bgcolor: 'action.hover' },
                        bgcolor:
                          config.genre === genre.value
                            ? 'action.selected'
                            : 'background.paper',
                      }}
                      onClick={() => onConfigChange({ genre: genre.value })}
                    >
                      <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                        <FormControlLabel
                          value={genre.value}
                          control={<Radio size="small" />}
                          label={
                            <Box>
                              <Typography variant="subtitle2">
                                {genre.label}
                              </Typography>
                              <Typography
                                variant="caption"
                                color="textSecondary"
                              >
                                {genre.description}
                              </Typography>
                            </Box>
                          }
                          sx={{ m: 0 }}
                        />
                      </CardContent>
                    </Card>
                  ))}
                </Stack>
              </RadioGroup>
            </Box>

            <Divider />

            {/* Tone */}
            <Box>
              <Typography variant="subtitle1" gutterBottom>
                톤 & 분위기
              </Typography>
              <RadioGroup
                value={config.tone || ''}
                onChange={e => onConfigChange({ tone: e.target.value })}
              >
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                  {TONE_OPTIONS.map(tone => (
                    <Box
                      key={tone.value}
                      sx={{
                        flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 4px)' },
                      }}
                    >
                      <Card
                        variant="outlined"
                        sx={{
                          cursor: 'pointer',
                          '&:hover': { bgcolor: 'action.hover' },
                          bgcolor:
                            config.tone === tone.value
                              ? 'action.selected'
                              : 'background.paper',
                        }}
                        onClick={() => onConfigChange({ tone: tone.value })}
                      >
                        <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                          <FormControlLabel
                            value={tone.value}
                            control={<Radio size="small" />}
                            label={
                              <Box>
                                <Typography variant="subtitle2">
                                  {tone.label}
                                </Typography>
                                <Typography
                                  variant="caption"
                                  color="textSecondary"
                                >
                                  {tone.description}
                                </Typography>
                              </Box>
                            }
                            sx={{ m: 0, width: '100%' }}
                          />
                        </CardContent>
                      </Card>
                    </Box>
                  ))}
                </Box>
              </RadioGroup>
            </Box>

            <Divider />

            {/* Length & Language */}
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
              <Box
                sx={{ flex: { xs: '1 1 100%', md: '1 1 calc(50% - 12px)' } }}
              >
                <Typography variant="subtitle1" gutterBottom>
                  스크립트 길이
                </Typography>
                <RadioGroup
                  value={config.length || 'medium'}
                  onChange={e => {
                    const tokens = LENGTH_OPTIONS.find(
                      l => l.value === e.target.value,
                    )?.tokens
                    onConfigChange({
                      length: e.target.value as any,
                      ...(tokens !== undefined && { maxTokens: tokens }),
                    })
                  }}
                >
                  {LENGTH_OPTIONS.map(length => (
                    <Card
                      key={length.value}
                      variant="outlined"
                      sx={{
                        cursor: 'pointer',
                        mb: 1,
                        '&:hover': { bgcolor: 'action.hover' },
                        bgcolor:
                          config.length === length.value
                            ? 'action.selected'
                            : 'background.paper',
                      }}
                      onClick={() =>
                        onConfigChange({
                          length: length.value as any,
                          maxTokens: length.tokens,
                        })
                      }
                    >
                      <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                        <FormControlLabel
                          value={length.value}
                          control={<Radio size="small" />}
                          label={
                            <Box>
                              <Typography variant="subtitle2">
                                {length.label}
                              </Typography>
                              <Typography
                                variant="caption"
                                color="textSecondary"
                              >
                                {length.description}
                              </Typography>
                            </Box>
                          }
                          sx={{ m: 0, width: '100%' }}
                        />
                      </CardContent>
                    </Card>
                  ))}
                </RadioGroup>
              </Box>

              <Box
                sx={{ flex: { xs: '1 1 100%', md: '1 1 calc(50% - 12px)' } }}
              >
                <Typography variant="subtitle1" gutterBottom>
                  언어
                </Typography>
                <RadioGroup
                  value={config.language || 'ko'}
                  onChange={e => onConfigChange({ language: e.target.value })}
                >
                  {LANGUAGE_OPTIONS.map(lang => (
                    <FormControlLabel
                      key={lang.value}
                      value={lang.value}
                      control={<Radio />}
                      label={
                        <Box display="flex" alignItems="center" gap={1}>
                          <Typography variant="body1">{lang.flag}</Typography>
                          <Typography variant="body1">{lang.label}</Typography>
                        </Box>
                      }
                    />
                  ))}
                </RadioGroup>
              </Box>
            </Box>
          </Stack>
        </CardContent>
      </Card>

      {/* Advanced Settings */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            고급 설정
          </Typography>

          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
            <Box sx={{ flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 12px)' } }}>
              <Typography gutterBottom>
                창의성 (Temperature): {config.temperature || 0.7}
              </Typography>
              <Slider
                value={config.temperature || 0.7}
                onChange={(_, value) =>
                  handleAdvancedChange('temperature', value as number)
                }
                min={0}
                max={1}
                step={0.1}
                marks={[
                  { value: 0, label: '보수적' },
                  { value: 0.5, label: '균형' },
                  { value: 1, label: '창의적' },
                ]}
              />
            </Box>

            <Box sx={{ flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 12px)' } }}>
              <Typography gutterBottom>
                다양성 (Top P): {config.topP || 0.9}
              </Typography>
              <Slider
                value={config.topP || 0.9}
                onChange={(_, value) =>
                  handleAdvancedChange('topP', value as number)
                }
                min={0.1}
                max={1}
                step={0.1}
                marks={[
                  { value: 0.1, label: '제한적' },
                  { value: 0.9, label: '다양함' },
                ]}
              />
            </Box>
          </Box>
        </CardContent>
      </Card>

      {/* Configuration Summary */}
      <Alert severity="success">
        <Typography variant="subtitle2" gutterBottom>
          현재 설정:
        </Typography>
        <Stack direction="row" spacing={1} flexWrap="wrap">
          {selectedModel && (
            <Chip label={`모델: ${selectedModel.name}`} size="small" />
          )}
          {config.genre && (
            <Chip
              label={`장르: ${GENRE_OPTIONS.find(g => g.value === config.genre)?.label}`}
              size="small"
            />
          )}
          {config.tone && (
            <Chip
              label={`톤: ${TONE_OPTIONS.find(t => t.value === config.tone)?.label}`}
              size="small"
            />
          )}
          {selectedLength && (
            <Chip label={`길이: ${selectedLength.label}`} size="small" />
          )}
          {config.language && (
            <Chip
              label={`언어: ${LANGUAGE_OPTIONS.find(l => l.value === config.language)?.label}`}
              size="small"
            />
          )}
        </Stack>
      </Alert>
    </Stack>
  )
}
