import {
  Box,
  Button,
  Card,
  CardContent,
  CardHeader,
  Stack,
  Typography,
  Divider,
  Alert,
  Chip,
} from '@mui/material'
import {
  Save as SaveIcon,
  Cancel as CancelIcon,
  PlayArrow as PlayIcon,
  Schedule as ScheduleIcon,
} from '@mui/icons-material'

import { FormProvider, useFormContext } from '@/shared/ui/forms/FormProvider'
import { FormTextField, FormTextArea } from '@/shared/ui/forms/FormTextField'
import { FormSelect } from '@/shared/ui/forms/FormSelect'
import { FormDatePicker } from '@/shared/ui/forms/FormDatePicker'
import { FormAutocomplete } from '@/shared/ui/forms/FormAutocomplete'
import { EpisodeCreateSchema } from '../../../shared/lib/validation/schemas'
import type { EpisodeCreateFormData } from '../../../shared/lib/validation/schemas'
import { useToastHelpers } from '@/shared/ui/components/toast'

interface EpisodeCreateFormProps {
  projectId: string
  projectName?: string
  onSubmit: (data: EpisodeCreateFormData) => Promise<void>
  onCancel?: () => void
  initialData?: Partial<EpisodeCreateFormData>
  loading?: boolean
  suggestedEpisodeNumber?: number
  existingCharacters?: string[]
  existingLocations?: string[]
}

// Episode mood options
const MOOD_OPTIONS = [
  { value: 'light', label: '밝은' },
  { value: 'serious', label: '진지한' },
  { value: 'dramatic', label: '극적인' },
  { value: 'comedic', label: '코믹한' },
  { value: 'suspenseful', label: '긴장감 있는' },
  { value: 'romantic', label: '로맨틱한' },
]

// Common themes
const THEME_SUGGESTIONS = [
  { value: 'family', label: '가족' },
  { value: 'friendship', label: '우정' },
  { value: 'love', label: '사랑' },
  { value: 'betrayal', label: '배신' },
  { value: 'revenge', label: '복수' },
  { value: 'forgiveness', label: '용서' },
  { value: 'sacrifice', label: '희생' },
  { value: 'growth', label: '성장' },
  { value: 'loss', label: '상실' },
  { value: 'hope', label: '희망' },
]

/**
 * Episode duration formatter
 */
function formatDuration(minutes: number): string {
  if (minutes < 60) {
    return `${minutes}분`
  }
  const hours = Math.floor(minutes / 60)
  const remainingMinutes = minutes % 60
  return `${hours}시간 ${remainingMinutes}분`
}

/**
 * Episode summary card
 */
function EpisodeSummary({ projectName }: { projectName?: string }) {
  const { watch } = useFormContext<EpisodeCreateFormData>()

  const title = watch('title')
  // episodeNumber는 서버에서 자동 할당되므로 제거
  const seasonNumber = watch('seasonNumber')
  const duration = watch('duration')

  return (
    <Card variant="outlined" sx={{ bgcolor: 'background.paper' }}>
      <CardContent>
        <Stack spacing={1}>
          <Typography variant="h6" color="primary">
            {title || '새 에피소드'}
          </Typography>

          <Stack direction="row" spacing={1} flexWrap="wrap">
            {projectName && (
              <Chip label={projectName} size="small" color="default" />
            )}

            {seasonNumber && (
              <Chip label={`시즌 ${seasonNumber}`} size="small" color="info" />
            )}

            <Chip label="새 에피소드" size="small" color="primary" />

            {duration && (
              <Chip
                icon={<ScheduleIcon />}
                label={formatDuration(duration)}
                size="small"
                color="secondary"
              />
            )}
          </Stack>
        </Stack>
      </CardContent>
    </Card>
  )
}

/**
 * Episode create form content
 */
function EpisodeCreateFormContent({
  existingCharacters = [],
  existingLocations = [],
}: {
  existingCharacters: string[]
  existingLocations: string[]
}) {
  const { control } = useFormContext<EpisodeCreateFormData>()

  // Convert to autocomplete options
  const characterOptions = existingCharacters.map(char => ({
    value: char,
    label: char,
  }))
  const locationOptions = existingLocations.map(loc => ({
    value: loc,
    label: loc,
  }))

  return (
    <Stack spacing={3}>
      {/* Episode Basic Info */}
      <Card variant="outlined">
        <CardHeader title="기본 정보" />
        <CardContent>
          <Stack spacing={2}>
            <FormTextField
              name="title"
              label="에피소드 제목"
              placeholder="예: 첫 번째 만남"
              required
              autoFocus
              control={control}
            />

            <Alert severity="info" sx={{ mb: 2 }}>
              에피소드 번호는 생성 시 자동으로 할당됩니다.
            </Alert>

            <Box display="flex" gap={2}>
              <FormTextField
                name="seasonNumber"
                label="시즌 번호"
                type="text"
                inputMode="numeric"
                pattern="[0-9]*"
                helperText="없으면 시즌 1로 설정"
                control={control}
              />

              <FormTextField
                name="duration"
                label="런타임 (분)"
                type="text"
                inputMode="numeric"
                pattern="[0-9]*"
                placeholder="60"
                helperText="예상 런타임"
                control={control}
              />
            </Box>

            <FormTextArea
              name="description"
              label="에피소드 설명"
              placeholder="이 에피소드에서 일어날 주요 사건들을 간단히 설명해주세요..."
              rows={3}
              control={control}
            />
          </Stack>
        </CardContent>
      </Card>

      {/* Creative Elements */}
      <Card variant="outlined">
        <CardHeader title="창작 요소" />
        <CardContent>
          <Stack spacing={2}>
            <FormSelect
              name="mood"
              label="에피소드 무드"
              options={MOOD_OPTIONS}
              emptyOption
              emptyOptionLabel="선택하세요"
              helperText="이 에피소드의 전반적인 분위기"
              control={control}
            />

            <FormAutocomplete
              name="themes"
              label="주제"
              options={THEME_SUGGESTIONS}
              multiple
              freeSolo
              placeholder="이 에피소드에서 다룰 주제들을 선택하거나 추가하세요"
              helperText="여러 개 선택 가능"
              control={control}
            />

            <Box display="flex" gap={2}>
              <FormTextField
                name="writer"
                label="작가"
                placeholder="작가명"
                fullWidth
                control={control}
              />

              <FormTextField
                name="director"
                label="감독"
                placeholder="감독명"
                fullWidth
                control={control}
              />
            </Box>
          </Stack>
        </CardContent>
      </Card>

      {/* Characters and Locations */}
      <Card variant="outlined">
        <CardHeader title="등장인물 및 장소" />
        <CardContent>
          <Stack spacing={2}>
            <FormAutocomplete
              name="characters"
              label="등장인물"
              options={characterOptions}
              multiple
              freeSolo
              placeholder="이 에피소드에 등장할 인물들을 선택하거나 추가하세요"
              helperText="기존 인물 목록에서 선택하거나 새로운 인물을 추가할 수 있습니다"
              control={control}
            />

            <FormAutocomplete
              name="locations"
              label="촬영 장소"
              options={locationOptions}
              multiple
              freeSolo
              placeholder="이 에피소드의 주요 촬영 장소들을 선택하거나 추가하세요"
              helperText="기존 장소 목록에서 선택하거나 새로운 장소를 추가할 수 있습니다"
              control={control}
            />
          </Stack>
        </CardContent>
      </Card>

      {/* Schedule */}
      <Card variant="outlined">
        <CardHeader title="일정" />
        <CardContent>
          <Stack spacing={2}>
            <FormDatePicker
              name="airDate"
              label="방송 예정일"
              helperText="언제 방송될 예정인지 선택해주세요 (선택사항)"
              control={control}
            />
          </Stack>
        </CardContent>
      </Card>

      {/* Notes */}
      <Card variant="outlined">
        <CardHeader title="추가 노트" />
        <CardContent>
          <FormTextArea
            name="notes"
            label="제작 노트"
            placeholder="스크립트 생성에 도움이 될 추가적인 정보나 특별히 고려해야 할 사항들을 적어주세요..."
            rows={4}
            helperText="스타일, 톤, 특별한 요구사항 등을 자유롭게 기록하세요"
            control={control}
          />
        </CardContent>
      </Card>
    </Stack>
  )
}

/**
 * Episode creation form
 */
export function EpisodeCreateForm({
  projectId,
  projectName,
  onSubmit,
  onCancel,
  initialData = {},
  loading = false,
  suggestedEpisodeNumber: _suggestedEpisodeNumber = 1,
  existingCharacters = [],
  existingLocations = [],
}: EpisodeCreateFormProps) {
  const { showSuccess } = useToastHelpers()

  const defaultValues: Partial<EpisodeCreateFormData> = {
    projectId,
    title: '',
    // number는 서버에서 자동 할당되므로 제거
    seasonNumber: 1,
    description: '',
    duration: undefined,
    airDate: undefined,
    writer: '',
    director: '',
    characters: [],
    locations: [],
    mood: undefined,
    themes: [],
    notes: '',
    ...initialData,
  }

  const handleSubmit = async (data: EpisodeCreateFormData) => {
    // Ensure projectId is set
    const submitData = { ...data, projectId }
    await onSubmit(submitData)
    showSuccess('에피소드가 성공적으로 생성되었습니다!')
  }

  return (
    <FormProvider
      schema={EpisodeCreateSchema}
      defaultValues={defaultValues}
      onSubmit={handleSubmit}
      options={{
        autoSave: true,
        autoSaveKey: `episode-create-form-${projectId}`,
        autoSaveDelay: 2000,
        confirmOnLeave: true,
        resetOnSuccess: true,
      }}
      config={{
        showErrorToasts: true,
        validateOnChange: true,
        validateOnBlur: true,
      }}
    >
      <Box maxWidth="800px" mx="auto" p={3}>
        <Stack spacing={3}>
          {/* Header */}
          <Box>
            <Typography variant="h4" component="h1" gutterBottom>
              새 에피소드 만들기
            </Typography>
            <Typography variant="body1" color="textSecondary">
              {projectName && `${projectName} 프로젝트에 `}
              새로운 에피소드를 추가합니다.
            </Typography>
          </Box>

          <Divider />

          {/* Episode Summary */}
          <EpisodeSummary {...(projectName && { projectName })} />

          {/* Form Content */}
          <EpisodeCreateFormContent
            existingCharacters={existingCharacters}
            existingLocations={existingLocations}
          />

          {/* AI Generation Tip */}
          <Alert severity="info" icon={<PlayIcon />}>
            <Typography variant="body2">
              <strong>AI 스크립트 생성 팁:</strong> 상세한 정보를 제공할수록 더
              정확하고 창의적인 스크립트를 생성할 수 있습니다. 특히 등장인물,
              무드, 주제는 스크립트 품질에 큰 영향을 줍니다.
            </Typography>
          </Alert>

          {/* Form Actions */}
          <FormActions {...(onCancel && { onCancel })} loading={loading} />
        </Stack>
      </Box>
    </FormProvider>
  )
}

/**
 * Form action buttons
 */
function FormActions({
  onCancel,
  loading,
}: {
  onCancel?: () => void
  loading: boolean
}) {
  const { submitForm, isSubmitting, isDirty } = useFormContext()

  return (
    <Card variant="outlined">
      <CardContent>
        <Stack
          direction="row"
          spacing={2}
          justifyContent="flex-end"
          alignItems="center"
        >
          {onCancel && (
            <Button
              variant="outlined"
              startIcon={<CancelIcon />}
              onClick={onCancel}
              disabled={isSubmitting || loading}
            >
              취소
            </Button>
          )}

          <Button
            variant="contained"
            startIcon={<SaveIcon />}
            onClick={submitForm}
            disabled={isSubmitting || loading || !isDirty}
            color="primary"
          >
            {isSubmitting ? '생성 중...' : '에피소드 생성'}
          </Button>
        </Stack>
      </CardContent>
    </Card>
  )
}
