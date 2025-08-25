import { useState } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Slider,
  FormControl,
  Switch,
  Stack,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Divider,
  Paper,
  LinearProgress,
} from '@mui/material'
import {
  AutoAwesome as AIIcon,
  Tune as TuneIcon,
  Speed as SpeedIcon,
  Save as SaveIcon,
  RestartAlt as ResetIcon,
} from '@mui/icons-material'
import { useForm, Controller } from 'react-hook-form'

import { useToastHelpers } from '@/shared/ui/components/toast'

interface AIModelConfig {
  model: string
  temperature: number
  maxTokens: number
  topP: number
  frequencyPenalty: number
  presencePenalty: number
  autoGenerate: boolean
  qualityMode: 'fast' | 'balanced' | 'quality'
  language: string
  genre: string[]
  customPrompts: boolean
  saveHistory: boolean
}

interface ModelInfo {
  name: string
  description: string
  status: 'available' | 'premium' | 'experimental'
  performance: number
  creativity: number
}

const AVAILABLE_MODELS: ModelInfo[] = [
  {
    name: 'gpt-4',
    description: '가장 강력한 모델로 높은 품질의 스크립트 생성',
    status: 'premium',
    performance: 95,
    creativity: 90,
  },
  {
    name: 'gpt-3.5-turbo',
    description: '빠르고 효율적인 스크립트 생성에 최적화',
    status: 'available',
    performance: 85,
    creativity: 80,
  },
  {
    name: 'claude-2',
    description: '긴 형식의 스크립트 생성에 특화',
    status: 'available',
    performance: 88,
    creativity: 85,
  },
  {
    name: 'experimental-v1',
    description: '실험적인 창작 기능을 포함한 모델',
    status: 'experimental',
    performance: 75,
    creativity: 95,
  },
]


export function AIModelSettings() {
  const { showSuccess, showError } = useToastHelpers()

  // Mock current settings - replace with actual API call
  const [currentSettings] = useState<AIModelConfig>({
    model: 'gpt-3.5-turbo',
    temperature: 0.7,
    maxTokens: 2048,
    topP: 0.9,
    frequencyPenalty: 0.0,
    presencePenalty: 0.0,
    autoGenerate: false,
    qualityMode: 'balanced',
    language: 'ko',
    genre: ['드라마', '코미디'],
    customPrompts: true,
    saveHistory: true,
  })

  const {
    control,
    handleSubmit,
    reset,
    watch,
    formState: { isDirty },
  } = useForm<AIModelConfig>({
    defaultValues: currentSettings,
  })

  const selectedModel = watch('model')
  const temperature = watch('temperature')
  const qualityMode = watch('qualityMode')

  const handleSave = async (data: AIModelConfig) => {
    try {
      // TODO: Implement API call to save AI settings
      console.log('Save AI settings:', data)
      showSuccess('AI 설정이 저장되었습니다.')
    } catch (error) {
      showError('AI 설정 저장에 실패했습니다.')
    }
  }

  const handleReset = () => {
    reset(currentSettings)
    showSuccess('설정이 초기화되었습니다.')
  }

  const getModelInfo = (modelName: string) => {
    return AVAILABLE_MODELS.find(model => model.name === modelName)
  }

  const getTemperatureLabel = (value: number) => {
    if (value < 0.3) return '매우 일관적'
    if (value < 0.7) return '균형잡힌'
    if (value < 1.0) return '창의적'
    return '매우 창의적'
  }

  const getQualityModeDescription = (mode: string) => {
    switch (mode) {
      case 'fast':
        return '빠른 생성 (30초 내외)'
      case 'balanced':
        return '균형잡힌 품질 (1-2분)'
      case 'quality':
        return '최고 품질 (3-5분)'
      default:
        return ''
    }
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
        {/* Model Selection */}
        <Box sx={{ flex: '1 1 100%' }}>
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
                {AVAILABLE_MODELS.map(model => (
                  <Box
                    key={model.name}
                    sx={{ flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 8px)' } }}
                  >
                    <Controller
                      name="model"
                      control={control}
                      render={({ field }) => (
                        <Card
                          variant="outlined"
                          sx={{
                            cursor: 'pointer',
                            border:
                              field.value === model.name
                                ? '2px solid'
                                : '1px solid',
                            borderColor:
                              field.value === model.name
                                ? 'primary.main'
                                : 'grey.300',
                            '&:hover': { borderColor: 'primary.light' },
                          }}
                          onClick={() => field.onChange(model.name)}
                        >
                          <CardContent>
                            <Box
                              display="flex"
                              justifyContent="space-between"
                              alignItems="start"
                              mb={1}
                            >
                              <Typography variant="subtitle1" fontWeight="bold">
                                {model.name}
                              </Typography>
                              <Chip
                                label={
                                  model.status === 'premium'
                                    ? '프리미엄'
                                    : model.status === 'experimental'
                                      ? '실험적'
                                      : '사용가능'
                                }
                                size="small"
                                color={
                                  model.status === 'premium'
                                    ? 'warning'
                                    : model.status === 'experimental'
                                      ? 'info'
                                      : 'success'
                                }
                              />
                            </Box>
                            <Typography
                              variant="body2"
                              color="textSecondary"
                              mb={2}
                            >
                              {model.description}
                            </Typography>
                            <Stack spacing={1}>
                              <Box>
                                <Box
                                  display="flex"
                                  justifyContent="space-between"
                                  alignItems="center"
                                >
                                  <Typography variant="caption">
                                    성능
                                  </Typography>
                                  <Typography variant="caption">
                                    {model.performance}%
                                  </Typography>
                                </Box>
                                <LinearProgress
                                  variant="determinate"
                                  value={model.performance}
                                  sx={{ height: 4 }}
                                />
                              </Box>
                              <Box>
                                <Box
                                  display="flex"
                                  justifyContent="space-between"
                                  alignItems="center"
                                >
                                  <Typography variant="caption">
                                    창의성
                                  </Typography>
                                  <Typography variant="caption">
                                    {model.creativity}%
                                  </Typography>
                                </Box>
                                <LinearProgress
                                  variant="determinate"
                                  value={model.creativity}
                                  color="secondary"
                                  sx={{ height: 4 }}
                                />
                              </Box>
                            </Stack>
                          </CardContent>
                        </Card>
                      )}
                    />
                  </Box>
                ))}
              </Box>
            </CardContent>
          </Card>
        </Box>

        {/* Advanced Parameters */}
        <Box sx={{ flex: { xs: '1 1 100%', md: '1 1 calc(66.667% - 16px)' } }}>
          <Card>
            <CardContent>
              <Typography
                variant="h6"
                gutterBottom
                display="flex"
                alignItems="center"
                gap={1}
              >
                <TuneIcon color="primary" />
                고급 매개변수
              </Typography>

              <form onSubmit={handleSubmit(handleSave)}>
                <Stack spacing={4}>
                  {/* Temperature */}
                  <Box>
                    <Typography variant="subtitle2" gutterBottom>
                      창의성 수준 (Temperature): {temperature}
                    </Typography>
                    <Typography variant="body2" color="textSecondary" mb={2}>
                      {getTemperatureLabel(temperature)}
                    </Typography>
                    <Controller
                      name="temperature"
                      control={control}
                      render={({ field }) => (
                        <Slider
                          {...field}
                          min={0}
                          max={1.0}
                          step={0.1}
                          marks={[
                            { value: 0, label: '일관적' },
                            { value: 0.5, label: '균형' },
                            { value: 1.0, label: '창의적' },
                          ]}
                        />
                      )}
                    />
                  </Box>

                  {/* Max Tokens */}
                  <Controller
                    name="maxTokens"
                    control={control}
                    render={({ field }) => (
                      <TextField
                        {...field}
                        label="최대 토큰 수"
                        type="number"
                        fullWidth
                        helperText="생성될 텍스트의 최대 길이를 설정합니다"
                        inputProps={{ min: 256, max: 4096 }}
                      />
                    )}
                  />

                  {/* Top P */}
                  <Box>
                    <Typography variant="subtitle2" gutterBottom>
                      Top P: {watch('topP')}
                    </Typography>
                    <Typography variant="body2" color="textSecondary" mb={2}>
                      단어 선택의 다양성을 조절합니다
                    </Typography>
                    <Controller
                      name="topP"
                      control={control}
                      render={({ field }) => (
                        <Slider {...field} min={0.1} max={1.0} step={0.1} />
                      )}
                    />
                  </Box>

                  {/* Penalties */}
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
                    <Box
                      sx={{
                        flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 8px)' },
                      }}
                    >
                      <Box>
                        <Typography variant="subtitle2" gutterBottom>
                          빈도 페널티: {watch('frequencyPenalty')}
                        </Typography>
                        <Controller
                          name="frequencyPenalty"
                          control={control}
                          render={({ field }) => (
                            <Slider
                              {...field}
                              min={-2.0}
                              max={2.0}
                              step={0.1}
                            />
                          )}
                        />
                      </Box>
                    </Box>
                    <Box
                      sx={{
                        flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 8px)' },
                      }}
                    >
                      <Box>
                        <Typography variant="subtitle2" gutterBottom>
                          존재 페널티: {watch('presencePenalty')}
                        </Typography>
                        <Controller
                          name="presencePenalty"
                          control={control}
                          render={({ field }) => (
                            <Slider
                              {...field}
                              min={-2.0}
                              max={2.0}
                              step={0.1}
                            />
                          )}
                        />
                      </Box>
                    </Box>
                  </Box>
                </Stack>
              </form>
            </CardContent>
          </Card>
        </Box>

        {/* Generation Settings */}
        <Box sx={{ flex: { xs: '1 1 100%', md: '1 1 calc(33.333% - 16px)' } }}>
          <Stack spacing={3}>
            <Card>
              <CardContent>
                <Typography
                  variant="h6"
                  gutterBottom
                  display="flex"
                  alignItems="center"
                  gap={1}
                >
                  <SpeedIcon color="primary" />
                  생성 설정
                </Typography>

                <Stack spacing={2}>
                  <Controller
                    name="qualityMode"
                    control={control}
                    render={({ field }) => (
                      <FormControl fullWidth>
                        <TextField
                          {...field}
                          select
                          label="품질 모드"
                          SelectProps={{ native: true }}
                          helperText={getQualityModeDescription(qualityMode)}
                        >
                          <option value="fast">빠른 생성</option>
                          <option value="balanced">균형 모드</option>
                          <option value="quality">고품질 모드</option>
                        </TextField>
                      </FormControl>
                    )}
                  />

                  <Controller
                    name="language"
                    control={control}
                    render={({ field }) => (
                      <TextField
                        {...field}
                        select
                        label="주요 언어"
                        fullWidth
                        SelectProps={{ native: true }}
                      >
                        <option value="ko">한국어</option>
                        <option value="en">English</option>
                        <option value="ja">日本語</option>
                      </TextField>
                    )}
                  />
                </Stack>
              </CardContent>
            </Card>

            {/* Model Info */}
            {selectedModel && (
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    선택된 모델 정보
                  </Typography>
                  {(() => {
                    const modelInfo = getModelInfo(selectedModel)
                    return modelInfo ? (
                      <Stack spacing={2}>
                        <Typography variant="body2">
                          {modelInfo.description}
                        </Typography>
                        <Box>
                          <Typography variant="caption" display="block">
                            성능: {modelInfo.performance}%
                          </Typography>
                          <LinearProgress
                            variant="determinate"
                            value={modelInfo.performance}
                            sx={{ mb: 1, height: 6 }}
                          />
                          <Typography variant="caption" display="block">
                            창의성: {modelInfo.creativity}%
                          </Typography>
                          <LinearProgress
                            variant="determinate"
                            value={modelInfo.creativity}
                            color="secondary"
                            sx={{ height: 6 }}
                          />
                        </Box>
                      </Stack>
                    ) : null
                  })()}
                </CardContent>
              </Card>
            )}
          </Stack>
        </Box>

        {/* Additional Settings */}
        <Box sx={{ flex: '1 1 100%' }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                추가 설정
              </Typography>

              <List>
                <ListItem>
                  <ListItemText
                    primary="자동 생성"
                    secondary="에피소드 생성 시 자동으로 스크립트 생성을 시작합니다"
                  />
                  <ListItemSecondaryAction>
                    <Controller
                      name="autoGenerate"
                      control={control}
                      render={({ field }) => (
                        <Switch {...field} checked={field.value} />
                      )}
                    />
                  </ListItemSecondaryAction>
                </ListItem>
                <Divider />
                <ListItem>
                  <ListItemText
                    primary="사용자 정의 프롬프트"
                    secondary="고급 사용자를 위한 커스텀 프롬프트 기능을 활성화합니다"
                  />
                  <ListItemSecondaryAction>
                    <Controller
                      name="customPrompts"
                      control={control}
                      render={({ field }) => (
                        <Switch {...field} checked={field.value} />
                      )}
                    />
                  </ListItemSecondaryAction>
                </ListItem>
                <Divider />
                <ListItem>
                  <ListItemText
                    primary="생성 히스토리 저장"
                    secondary="AI 생성 기록을 저장하여 품질 개선에 활용합니다"
                  />
                  <ListItemSecondaryAction>
                    <Controller
                      name="saveHistory"
                      control={control}
                      render={({ field }) => (
                        <Switch {...field} checked={field.value} />
                      )}
                    />
                  </ListItemSecondaryAction>
                </ListItem>
              </List>
            </CardContent>
          </Card>
        </Box>

        {/* Action Buttons */}
        <Box sx={{ flex: '1 1 100%' }}>
          <Paper sx={{ p: 2 }}>
            <Stack direction="row" spacing={2} justifyContent="flex-end">
              <Button
                startIcon={<ResetIcon />}
                onClick={handleReset}
                disabled={!isDirty}
              >
                초기화
              </Button>
              <Button
                variant="contained"
                startIcon={<SaveIcon />}
                onClick={handleSubmit(handleSave)}
                disabled={!isDirty}
              >
                설정 저장
              </Button>
            </Stack>
          </Paper>
        </Box>
      </Box>
    </Box>
  )
}
