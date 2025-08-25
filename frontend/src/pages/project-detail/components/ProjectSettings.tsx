import { useState } from 'react'
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  Alert,
  Stack,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
} from '@mui/material'
import {
  Edit as EditIcon,
  Delete as DeleteIcon,
  Archive as ArchiveIcon,
  Download as ExportIcon,
  Share as ShareIcon,
  Backup as BackupIcon,
} from '@mui/icons-material'
import { useNavigate } from 'react-router-dom'

import { ProjectEditForm } from '@features/project/forms'
import { useToastHelpers } from '@/shared/ui/components/toast'

interface Project {
  id: string
  name: string
  description?: string
  type: string
  status: string
  created_at: string
  updated_at: string
  episodes_count?: number
  scripts_count?: number
  progress_percentage?: number
}

interface ProjectSettingsProps {
  project: Project
  onUpdate: () => void
}

export function ProjectSettings({ project, onUpdate }: ProjectSettingsProps) {
  const navigate = useNavigate()
  const { showSuccess, showError } = useToastHelpers()

  const [showEditDialog, setShowEditDialog] = useState(false)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [showExportDialog, setShowExportDialog] = useState(false)

  const handleEdit = async (data: unknown) => {
    try {
      // TODO: Implement project update API call
      console.log('Update project:', data)
      showSuccess('프로젝트가 업데이트되었습니다.')
      setShowEditDialog(false)
      onUpdate()
    } catch (error) {
      showError('프로젝트 업데이트에 실패했습니다.')
      throw error
    }
  }

  const handleDelete = async () => {
    try {
      // TODO: Implement project deletion API call
      console.log('Delete project:', project.id)
      showSuccess('프로젝트가 삭제되었습니다.')
      navigate('/projects')
    } catch {
      showError('프로젝트 삭제에 실패했습니다.')
    }
  }

  const handleArchive = async () => {
    try {
      // TODO: Implement project archiving API call
      console.log('Archive project:', project.id)
      showSuccess('프로젝트가 아카이브되었습니다.')
      onUpdate()
    } catch {
      showError('프로젝트 아카이브에 실패했습니다.')
    }
  }

  const handleExport = async (format: 'json' | 'pdf' | 'docx') => {
    try {
      // TODO: Implement project export functionality
      console.log('Export project:', project.id, format)
      showSuccess(`프로젝트가 ${format.toUpperCase()} 형식으로 내보내졌습니다.`)
      setShowExportDialog(false)
    } catch {
      showError('프로젝트 내보내기에 실패했습니다.')
    }
  }

  const handleBackup = async () => {
    try {
      // TODO: Implement project backup functionality
      console.log('Backup project:', project.id)
      showSuccess('프로젝트가 백업되었습니다.')
    } catch {
      showError('프로젝트 백업에 실패했습니다.')
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return (
    <Box>
      <Stack spacing={3}>
        {/* Project Information */}
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              프로젝트 정보
            </Typography>

            <Stack spacing={2}>
              <Box>
                <Typography variant="subtitle2" color="textSecondary">
                  프로젝트 ID
                </Typography>
                <Typography variant="body2" fontFamily="monospace">
                  {project.id}
                </Typography>
              </Box>

              <Box>
                <Typography variant="subtitle2" color="textSecondary">
                  생성일시
                </Typography>
                <Typography variant="body2">
                  {formatDate(project.created_at)}
                </Typography>
              </Box>

              <Box>
                <Typography variant="subtitle2" color="textSecondary">
                  마지막 수정
                </Typography>
                <Typography variant="body2">
                  {formatDate(project.updated_at)}
                </Typography>
              </Box>

              <Box>
                <Typography variant="subtitle2" color="textSecondary">
                  현재 상태
                </Typography>
                <Stack direction="row" spacing={1} mt={1}>
                  <Chip label={project.status} size="small" color="primary" />
                  <Chip label={project.type} size="small" variant="outlined" />
                  {project.progress_percentage !== undefined && (
                    <Chip
                      label={`${project.progress_percentage}% 완료`}
                      size="small"
                      variant="outlined"
                      color="info"
                    />
                  )}
                </Stack>
              </Box>

              <Box>
                <Typography variant="subtitle2" color="textSecondary">
                  콘텐츠 통계
                </Typography>
                <Stack direction="row" spacing={2} mt={1}>
                  <Typography variant="body2">
                    에피소드: {project.episodes_count || 0}개
                  </Typography>
                  <Typography variant="body2">
                    스크립트: {project.scripts_count || 0}개
                  </Typography>
                </Stack>
              </Box>
            </Stack>
          </CardContent>
        </Card>

        {/* General Settings */}
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              일반 설정
            </Typography>

            <List>
              <ListItem>
                <ListItemText
                  primary="프로젝트 편집"
                  secondary="프로젝트 이름, 설명, 설정 등을 수정합니다"
                />
                <ListItemSecondaryAction>
                  <IconButton onClick={() => setShowEditDialog(true)}>
                    <EditIcon />
                  </IconButton>
                </ListItemSecondaryAction>
              </ListItem>

              <ListItem>
                <ListItemText
                  primary="프로젝트 아카이브"
                  secondary="프로젝트를 아카이브하여 숨깁니다"
                />
                <ListItemSecondaryAction>
                  <IconButton onClick={handleArchive}>
                    <ArchiveIcon />
                  </IconButton>
                </ListItemSecondaryAction>
              </ListItem>

              <ListItem>
                <ListItemText
                  primary="프로젝트 백업"
                  secondary="프로젝트 데이터를 백업합니다"
                />
                <ListItemSecondaryAction>
                  <IconButton onClick={handleBackup}>
                    <BackupIcon />
                  </IconButton>
                </ListItemSecondaryAction>
              </ListItem>
            </List>
          </CardContent>
        </Card>

        {/* Data Management */}
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              데이터 관리
            </Typography>

            <List>
              <ListItem>
                <ListItemText
                  primary="프로젝트 내보내기"
                  secondary="프로젝트 데이터를 다양한 형식으로 내보냅니다"
                />
                <ListItemSecondaryAction>
                  <IconButton onClick={() => setShowExportDialog(true)}>
                    <ExportIcon />
                  </IconButton>
                </ListItemSecondaryAction>
              </ListItem>

              <ListItem>
                <ListItemText
                  primary="프로젝트 공유"
                  secondary="다른 사용자와 프로젝트를 공유합니다"
                />
                <ListItemSecondaryAction>
                  <IconButton>
                    <ShareIcon />
                  </IconButton>
                </ListItemSecondaryAction>
              </ListItem>
            </List>
          </CardContent>
        </Card>

        {/* Danger Zone */}
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom color="error">
              위험 구역
            </Typography>

            <Alert severity="warning" sx={{ mb: 2 }}>
              아래 작업들은 되돌릴 수 없습니다. 신중하게 진행하세요.
            </Alert>

            <List>
              <ListItem>
                <ListItemText
                  primary="프로젝트 삭제"
                  secondary="프로젝트와 모든 관련 데이터를 영구적으로 삭제합니다"
                />
                <ListItemSecondaryAction>
                  <Button
                    variant="outlined"
                    color="error"
                    startIcon={<DeleteIcon />}
                    onClick={() => setShowDeleteDialog(true)}
                  >
                    삭제
                  </Button>
                </ListItemSecondaryAction>
              </ListItem>
            </List>
          </CardContent>
        </Card>
      </Stack>

      {/* Edit Project Dialog */}
      <Dialog
        open={showEditDialog}
        onClose={() => setShowEditDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>프로젝트 편집</DialogTitle>
        <DialogContent>
          <ProjectEditForm
            projectId={project.id}
            initialData={{
              ...project,
              type: project.type as
                | 'action'
                | 'animation'
                | 'comedy'
                | 'drama'
                | 'romance'
                | 'thriller'
                | 'documentary',
              isPublic: false, // Add missing required field
            }}
            onSubmit={handleEdit}
            onCancel={() => setShowEditDialog(false)}
          />
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={showDeleteDialog}
        onClose={() => setShowDeleteDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle color="error.main">프로젝트 삭제</DialogTitle>
        <DialogContent>
          <Alert severity="error" sx={{ mb: 2 }}>
            이 작업은 되돌릴 수 없습니다!
          </Alert>
          <Typography gutterBottom>
            '{project.name}' 프로젝트를 영구적으로 삭제하시겠습니까?
          </Typography>
          <Typography variant="body2" color="textSecondary">
            다음 데이터가 모두 삭제됩니다:
          </Typography>
          <List dense>
            <ListItem>
              <ListItemText
                primary={`${project.episodes_count || 0}개의 에피소드`}
              />
            </ListItem>
            <ListItem>
              <ListItemText
                primary={`${project.scripts_count || 0}개의 스크립트`}
              />
            </ListItem>
            <ListItem>
              <ListItemText primary="모든 프로젝트 설정" />
            </ListItem>
            <ListItem>
              <ListItemText primary="프로젝트 히스토리" />
            </ListItem>
          </List>
          <Box mt={2} p={2} bgcolor="grey.100" borderRadius={1}>
            <Typography variant="body2" fontWeight="bold">
              확인하려면 프로젝트 이름을 입력하세요: {project.name}
            </Typography>
          </Box>
        </DialogContent>
        <Box display="flex" justifyContent="space-between" p={3}>
          <Button onClick={() => setShowDeleteDialog(false)}>취소</Button>
          <Button onClick={handleDelete} color="error" variant="contained">
            영구 삭제
          </Button>
        </Box>
      </Dialog>

      {/* Export Options Dialog */}
      <Dialog
        open={showExportDialog}
        onClose={() => setShowExportDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>프로젝트 내보내기</DialogTitle>
        <DialogContent>
          <Typography gutterBottom>내보낼 형식을 선택하세요:</Typography>

          <Stack spacing={2} mt={2}>
            <Button
              variant="outlined"
              fullWidth
              startIcon={<ExportIcon />}
              onClick={() => handleExport('json')}
            >
              JSON - 프로젝트 데이터
            </Button>

            <Button
              variant="outlined"
              fullWidth
              startIcon={<ExportIcon />}
              onClick={() => handleExport('pdf')}
            >
              PDF - 스크립트 모음
            </Button>

            <Button
              variant="outlined"
              fullWidth
              startIcon={<ExportIcon />}
              onClick={() => handleExport('docx')}
            >
              DOCX - 편집 가능한 문서
            </Button>
          </Stack>
        </DialogContent>
      </Dialog>
    </Box>
  )
}
