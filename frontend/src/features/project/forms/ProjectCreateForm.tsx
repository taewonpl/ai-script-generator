import {
  Box,
  Button,
  Card,
  CardContent,
  CardHeader,
  Stack,
  Chip,
  Typography,
  Divider,
} from '@mui/material'
import {
  Save as SaveIcon,
  Cancel as CancelIcon,
  Save as AutoSaveIcon,
} from '@mui/icons-material'

import { FormProvider, useFormContext } from '@/shared/ui/forms/FormProvider'
import { FormTextField, FormTextArea } from '@/shared/ui/forms/FormTextField'
import { FormSelect } from '@/shared/ui/forms/FormSelect'
import { FormDatePicker } from '@/shared/ui/forms/FormDatePicker'
import { FormAutocomplete } from '@/shared/ui/forms/FormAutocomplete'
import { ProjectCreateSchema } from '@/shared/lib/validation/schemas'
import type { ProjectCreateFormData } from '@/shared/lib/validation/schemas'
import { useToastHelpers } from '@/shared/ui/components/toast'

interface ProjectCreateFormProps {
  onSubmit: (data: ProjectCreateFormData) => Promise<void>
  onCancel?: () => void
  initialData?: Partial<ProjectCreateFormData>
  loading?: boolean
}

// Project type options
const PROJECT_TYPE_OPTIONS = [
  { value: 'drama', label: '드라마' },
  { value: 'comedy', label: '코미디' },
  { value: 'action', label: '액션' },
  { value: 'romance', label: '로맨스' },
  { value: 'thriller', label: '스릴러' },
  { value: 'documentary', label: '다큐멘터리' },
  { value: 'animation', label: '애니메이션' },
]

// Target audience options
const TARGET_AUDIENCE_OPTIONS = [
  { value: 'all', label: '전체 관람가' },
  { value: 'kids', label: '어린이' },
  { value: 'teens', label: '청소년' },
  { value: 'adults', label: '성인' },
]

// Genre suggestions
const GENRE_SUGGESTIONS = [
  { value: 'mystery', label: '미스터리' },
  { value: 'crime', label: '범죄' },
  { value: 'fantasy', label: '판타지' },
  { value: 'sci-fi', label: 'SF' },
  { value: 'horror', label: '공포' },
  { value: 'historical', label: '사극' },
  { value: 'medical', label: '메디컬' },
  { value: 'legal', label: '법정' },
  { value: 'school', label: '학원' },
  { value: 'workplace', label: '직장' },
]

// Common tags
const COMMON_TAGS = [
  { value: 'family', label: '가족' },
  { value: 'friendship', label: '우정' },
  { value: 'love', label: '사랑' },
  { value: 'revenge', label: '복수' },
  { value: 'growth', label: '성장' },
  { value: 'mystery', label: '미스터리' },
  { value: 'adventure', label: '모험' },
  { value: 'slice-of-life', label: '일상' },
]

/**
 * Auto-save status component
 */
function AutoSaveStatus() {
  const { autoSaveStatus, lastAutoSaveTime } = useFormContext()

  if (autoSaveStatus === 'idle') return null

  const getStatusText = () => {
    switch (autoSaveStatus) {
      case 'saving':
        return '저장 중...'
      case 'saved':
        return lastAutoSaveTime
          ? `${lastAutoSaveTime.toLocaleTimeString()}에 저장됨`
          : '저장됨'
      case 'error':
        return '저장 실패'
      default:
        return ''
    }
  }

  const getStatusColor = () => {
    switch (autoSaveStatus) {
      case 'saving':
        return 'info'
      case 'saved':
        return 'success'
      case 'error':
        return 'error'
      default:
        return 'default'
    }
  }

  return (
    <Chip
      icon={<AutoSaveIcon />}
      label={getStatusText()}
      color={getStatusColor() as any}
      size="small"
      variant="outlined"
    />
  )
}

/**
 * Project create form content
 */
function ProjectCreateFormContent() {
  const { control, hasUnsavedChanges } = useFormContext<ProjectCreateFormData>()

  return (
    <Stack spacing={3}>
      {/* Basic Information */}
      <Card variant="outlined">
        <CardHeader title="기본 정보" action={<AutoSaveStatus />} />
        <CardContent>
          <Stack spacing={2}>
            <FormTextField
              name="name"
              label="프로젝트 이름"
              placeholder="예: 나의 첫 번째 드라마"
              required
              autoFocus
              control={control}
            />

            <Box display="flex" gap={2}>
              <FormSelect
                name="type"
                label="프로젝트 타입"
                options={PROJECT_TYPE_OPTIONS}
                required
                fullWidth
                control={control}
              />

              <FormSelect
                name="targetAudience"
                label="대상 연령"
                options={TARGET_AUDIENCE_OPTIONS}
                emptyOption
                emptyOptionLabel="선택하세요"
                fullWidth
                control={control}
              />
            </Box>

            <FormAutocomplete
              name="genre"
              label="장르"
              options={GENRE_SUGGESTIONS}
              freeSolo
              placeholder="장르를 선택하거나 직접 입력하세요"
              control={control}
            />

            <FormTextArea
              name="description"
              label="프로젝트 설명"
              placeholder="프로젝트에 대한 간단한 설명을 입력해주세요..."
              rows={4}
              control={control}
            />
          </Stack>
        </CardContent>
      </Card>

      {/* Schedule & Budget */}
      <Card variant="outlined">
        <CardHeader title="일정 및 예산" />
        <CardContent>
          <Stack spacing={2}>
            <Box display="flex" gap={2}>
              <FormDatePicker
                name="startDate"
                label="시작 예정일"
                fullWidth
                control={control}
              />

              <FormDatePicker
                name="endDate"
                label="완료 예정일"
                fullWidth
                control={control}
              />
            </Box>

            <FormTextField
              name="budget"
              label="예산"
              type="number"
              placeholder="0"
              helperText="원 단위로 입력해주세요 (선택사항)"
              control={control}
            />
          </Stack>
        </CardContent>
      </Card>

      {/* Tags and Settings */}
      <Card variant="outlined">
        <CardHeader title="태그 및 설정" />
        <CardContent>
          <Stack spacing={2}>
            <FormAutocomplete
              name="tags"
              label="태그"
              options={COMMON_TAGS}
              multiple
              freeSolo
              placeholder="프로젝트 태그를 선택하거나 추가해주세요"
              helperText="엔터키로 새로운 태그를 추가할 수 있습니다"
              control={control}
            />

            <Box>
              <FormTextField
                name="isPublic"
                label="공개 프로젝트"
                type="checkbox"
                helperText="체크하면 다른 사용자가 프로젝트를 볼 수 있습니다"
                control={control}
              />
            </Box>
          </Stack>
        </CardContent>
      </Card>

      {/* Form Status */}
      {hasUnsavedChanges && (
        <Box>
          <Typography variant="body2" color="warning.main">
            ⚠️ 저장되지 않은 변경사항이 있습니다
          </Typography>
        </Box>
      )}
    </Stack>
  )
}

/**
 * Project creation form with auto-save and validation
 */
export function ProjectCreateForm({
  onSubmit,
  onCancel,
  initialData = {},
  loading = false,
}: ProjectCreateFormProps) {
  const { showSuccess } = useToastHelpers()

  const defaultValues: Partial<ProjectCreateFormData> = {
    name: '',
    type: 'drama',
    description: '',
    genre: '',
    targetAudience: 'all',
    budget: undefined,
    startDate: undefined,
    endDate: undefined,
    tags: [],
    isPublic: false,
    collaborators: [],
    ...initialData,
  }

  const handleSubmit = async (data: ProjectCreateFormData) => {
    await onSubmit(data)
    showSuccess('프로젝트가 성공적으로 생성되었습니다!')
  }

  return (
    <FormProvider
      schema={ProjectCreateSchema}
      defaultValues={defaultValues}
      onSubmit={handleSubmit}
      options={{
        autoSave: true,
        autoSaveKey: 'project-create-form',
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
              새 프로젝트 만들기
            </Typography>
            <Typography variant="body1" color="textSecondary">
              스크립트 생성을 위한 새로운 프로젝트를 설정해주세요.
            </Typography>
          </Box>

          <Divider />

          {/* Form Content */}
          <ProjectCreateFormContent />

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
            {isSubmitting ? '생성 중...' : '프로젝트 생성'}
          </Button>
        </Stack>
      </CardContent>
    </Card>
  )
}
