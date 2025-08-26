import { useState } from 'react'
import {
  Box,
  Button,
  Card,
  CardContent,
  CardHeader,
  Stack,
  Typography,
  Divider,
  LinearProgress,
  Alert,
} from '@mui/material'
import {
  Save as SaveIcon,
  Cancel as CancelIcon,
  Delete as DeleteIcon,
  Archive as ArchiveIcon,
  Restore as RestoreIcon,
} from '@mui/icons-material'

import { FormProvider, useFormContext } from '@/shared/ui/forms/FormProvider'
import { FormTextField, FormTextArea } from '@/shared/ui/forms/FormTextField'
import { FormSelect } from '@/shared/ui/forms/FormSelect'
import { FormDatePicker } from '@/shared/ui/forms/FormDatePicker'
import { FormAutocomplete } from '@/shared/ui/forms/FormAutocomplete'
import {
  ProjectEditSchema,
  type ProjectEditFormData,
} from '../../../shared/lib/validation/schemas'
import { useToastHelpers } from '@/shared/ui/components/toast'

interface ProjectEditFormProps {
  projectId: string
  initialData: ProjectEditFormData
  onSubmit: (data: ProjectEditFormData) => Promise<void>
  onDelete?: (projectId: string) => Promise<void>
  onArchive?: (projectId: string) => Promise<void>
  onRestore?: (projectId: string) => Promise<void>
  onCancel?: () => void
  loading?: boolean
  canDelete?: boolean
  canArchive?: boolean
}

// Project status options
const PROJECT_STATUS_OPTIONS = [
  { value: 'planning', label: '기획 중' },
  { value: 'in_progress', label: '진행 중' },
  { value: 'completed', label: '완료' },
  { value: 'on_hold', label: '보류' },
  { value: 'cancelled', label: '취소' },
]

// Same options as create form
const PROJECT_TYPE_OPTIONS = [
  { value: 'drama', label: '드라마' },
  { value: 'comedy', label: '코미디' },
  { value: 'action', label: '액션' },
  { value: 'romance', label: '로맨스' },
  { value: 'thriller', label: '스릴러' },
  { value: 'documentary', label: '다큐멘터리' },
  { value: 'animation', label: '애니메이션' },
]

const TARGET_AUDIENCE_OPTIONS = [
  { value: 'all', label: '전체 관람가' },
  { value: 'kids', label: '어린이' },
  { value: 'teens', label: '청소년' },
  { value: 'adults', label: '성인' },
]

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

/**
 * Project progress indicator
 */
function ProjectProgress() {
  const { form } = useFormContext<ProjectEditFormData>()
  const progressPercentage = form.watch('progressPercentage') || 0
  const status = form.watch('status')

  const getProgressColor = () => {
    if (status === 'completed') return 'success'
    if (status === 'on_hold' || status === 'cancelled') return 'warning'
    if (progressPercentage > 75) return 'success'
    if (progressPercentage > 50) return 'info'
    if (progressPercentage > 25) return 'warning'
    return 'error'
  }

  return (
    <Box>
      <Typography variant="body2" color="textSecondary" gutterBottom>
        프로젝트 진행률: {progressPercentage}%
      </Typography>
      <LinearProgress
        variant="determinate"
        value={progressPercentage}
        color={getProgressColor() as any}
        sx={{ height: 8, borderRadius: 4 }}
      />
    </Box>
  )
}

/**
 * Project edit form content
 */
function ProjectEditFormContent({
  initialData,
}: {
  initialData: ProjectEditFormData
}) {
  const { form, control } = useFormContext<ProjectEditFormData>()
  const status = form.watch('status')

  const isCompleted = status === 'completed'
  const isCancelled = status === 'cancelled'

  return (
    <Stack spacing={3}>
      {/* Project Status */}
      <Card variant="outlined">
        <CardHeader title="프로젝트 상태" />
        <CardContent>
          <Stack spacing={2}>
            <FormSelect
              name="status"
              label="상태"
              options={PROJECT_STATUS_OPTIONS}
              control={control}
              required
            />

            <FormTextField
              name="progressPercentage"
              label="진행률 (%)"
              type="text"
              inputMode="numeric"
              helperText="0-100 사이의 숫자를 입력해주세요"
              control={control}
              disabled={isCompleted || isCancelled}
            />

            <ProjectProgress />
          </Stack>
        </CardContent>
      </Card>

      {/* Basic Information */}
      <Card variant="outlined">
        <CardHeader title="기본 정보" />
        <CardContent>
          <Stack spacing={2}>
            <FormTextField
              name="name"
              label="프로젝트 이름"
              control={control}
              required
            />

            <Box display="flex" gap={2}>
              <FormSelect
                name="type"
                label="프로젝트 타입"
                options={PROJECT_TYPE_OPTIONS}
                control={control}
                required
                fullWidth
              />

              <FormSelect
                name="targetAudience"
                label="대상 연령"
                options={TARGET_AUDIENCE_OPTIONS}
                control={control}
                emptyOption
                fullWidth
              />
            </Box>

            <FormAutocomplete
              name="genre"
              label="장르"
              options={GENRE_SUGGESTIONS}
              control={control}
              freeSolo
            />

            <FormTextArea
              name="description"
              label="프로젝트 설명"
              control={control}
              rows={4}
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
                label="시작일"
                control={control}
                fullWidth
              />

              <FormDatePicker
                name="endDate"
                label="완료 예정일"
                control={control}
                fullWidth
              />
            </Box>

            <FormTextField
              name="budget"
              label="예산"
              type="text"
              inputMode="numeric"
              helperText="원 단위"
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
              options={[]}
              control={control}
              multiple
              freeSolo
            />

            <FormTextField
              name="isPublic"
              label="공개 프로젝트"
              type="checkbox"
              control={control}
            />
          </Stack>
        </CardContent>
      </Card>

      {/* Project Metadata */}
      <Card variant="outlined">
        <CardHeader title="프로젝트 정보" />
        <CardContent>
          <Stack spacing={1}>
            <Typography variant="body2" color="textSecondary">
              프로젝트 ID: {initialData.id}
            </Typography>
            <Typography variant="body2" color="textSecondary">
              생성일: {new Date().toLocaleDateString()}
            </Typography>
            <Typography variant="body2" color="textSecondary">
              마지막 수정: {new Date().toLocaleDateString()}
            </Typography>
          </Stack>
        </CardContent>
      </Card>

      {/* Warnings for status changes */}
      {status === 'cancelled' && (
        <Alert severity="warning">
          취소된 프로젝트입니다. 일부 기능이 제한될 수 있습니다.
        </Alert>
      )}

      {status === 'completed' && (
        <Alert severity="success">
          완료된 프로젝트입니다. 프로젝트 설정 변경 시 상태가 변경될 수
          있습니다.
        </Alert>
      )}
    </Stack>
  )
}

/**
 * Project edit form with enhanced features
 */
export function ProjectEditForm({
  projectId,
  initialData,
  onSubmit,
  onDelete,
  onArchive,
  onRestore,
  onCancel,
  loading = false,
  canDelete = false,
  canArchive = false,
}: ProjectEditFormProps) {
  const { showSuccess, showWarning } = useToastHelpers()

  const handleSubmit = async (data: ProjectEditFormData) => {
    await onSubmit(data)
    showSuccess('프로젝트가 성공적으로 수정되었습니다!')
  }

  const handleDelete = async () => {
    if (!onDelete) return

    await onDelete(projectId)
    showWarning('프로젝트가 삭제되었습니다.')
  }

  const handleArchive = async () => {
    if (!onArchive) return

    await onArchive(projectId)
    showSuccess('프로젝트가 아카이브되었습니다.')
  }

  return (
    <FormProvider
      schema={ProjectEditSchema}
      defaultValues={initialData}
      onSubmit={handleSubmit}
      options={{
        autoSave: true,
        autoSaveKey: `project-edit-form-${projectId}`,
        autoSaveDelay: 2000,
        confirmOnLeave: true,
        resetOnSuccess: false,
      }}
      config={{
        showErrorToasts: true,
        validateOnChange: true,
      }}
    >
      <Box maxWidth="800px" mx="auto" p={3}>
        <Stack spacing={3}>
          {/* Header */}
          <Box>
            <Typography variant="h4" component="h1" gutterBottom>
              프로젝트 수정
            </Typography>
            <Typography variant="body1" color="textSecondary">
              {initialData.name} 프로젝트를 수정합니다.
            </Typography>
          </Box>

          <Divider />

          {/* Form Content */}
          <ProjectEditFormContent initialData={initialData} />

          {/* Form Actions */}
          <FormActions
            {...(onCancel && { onCancel })}
            {...(canDelete && { onDelete: handleDelete })}
            {...(canArchive && { onArchive: handleArchive })}
            {...(onRestore && { onRestore: () => onRestore(projectId) })}
            loading={loading}
          />
        </Stack>
      </Box>
    </FormProvider>
  )
}

/**
 * Enhanced form action buttons
 */
function FormActions({
  onCancel,
  onDelete,
  onArchive,
  onRestore,
  loading,
}: {
  onCancel?: () => void
  onDelete?: () => Promise<void>
  onArchive?: () => Promise<void>
  onRestore?: () => Promise<void>
  loading: boolean
}) {
  const { submitForm, isSubmitting, isDirty } = useFormContext()
  const [deleteConfirm, setDeleteConfirm] = useState(false)

  return (
    <Card variant="outlined">
      <CardContent>
        <Stack spacing={2}>
          {/* Primary Actions */}
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
              {isSubmitting ? '저장 중...' : '변경사항 저장'}
            </Button>
          </Stack>

          {/* Secondary Actions */}
          {(onDelete || onArchive || onRestore) && (
            <>
              <Divider />
              <Stack direction="row" spacing={1} justifyContent="flex-start">
                {onRestore && (
                  <Button
                    variant="outlined"
                    startIcon={<RestoreIcon />}
                    onClick={onRestore}
                    disabled={isSubmitting || loading}
                    color="info"
                    size="small"
                  >
                    복원
                  </Button>
                )}

                {onArchive && (
                  <Button
                    variant="outlined"
                    startIcon={<ArchiveIcon />}
                    onClick={onArchive}
                    disabled={isSubmitting || loading}
                    color="warning"
                    size="small"
                  >
                    아카이브
                  </Button>
                )}

                {onDelete && (
                  <Button
                    variant="outlined"
                    startIcon={<DeleteIcon />}
                    onClick={() => setDeleteConfirm(true)}
                    disabled={isSubmitting || loading}
                    color="error"
                    size="small"
                  >
                    삭제
                  </Button>
                )}
              </Stack>
            </>
          )}

          {/* Delete Confirmation */}
          {deleteConfirm && (
            <Alert
              severity="error"
              action={
                <Stack direction="row" spacing={1}>
                  <Button size="small" onClick={() => setDeleteConfirm(false)}>
                    취소
                  </Button>
                  <Button
                    size="small"
                    color="error"
                    variant="contained"
                    onClick={() => {
                      onDelete?.()
                      setDeleteConfirm(false)
                    }}
                  >
                    삭제 확인
                  </Button>
                </Stack>
              }
            >
              정말로 이 프로젝트를 삭제하시겠습니까? 이 작업은 되돌릴 수
              없습니다.
            </Alert>
          )}
        </Stack>
      </CardContent>
    </Card>
  )
}
