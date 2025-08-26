import { useState } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Stack,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  LinearProgress,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemSecondaryAction,
  Divider,
  FormControlLabel,
  Switch,
  TextField,
  Paper,
  Chip,
} from '@mui/material'
import {
  CloudDownload as ExportIcon,
  CloudUpload as ImportIcon,
  DeleteForever as DeleteIcon,
  Security as PrivacyIcon,
  Storage as StorageIcon,
  Backup as BackupIcon,
  Restore as RestoreIcon,
  Warning as WarningIcon,
  CheckCircle as SuccessIcon,
} from '@mui/icons-material'

import { useToastHelpers } from '@/shared/ui/components/toast'

interface DataStats {
  totalProjects: number
  totalScripts: number
  totalStorage: string
  lastBackup: string
  dataRetention: number
}

interface ExportOptions {
  includeProjects: boolean
  includeScripts: boolean
  includeSettings: boolean
  format: 'json' | 'csv' | 'pdf'
  dateRange: 'all' | 'last_month' | 'last_year'
}

export function DataManagement() {
  const { showSuccess, showError, showWarning } = useToastHelpers()

  const [showExportDialog, setShowExportDialog] = useState(false)
  const [showImportDialog, setShowImportDialog] = useState(false)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [exportProgress, setExportProgress] = useState(0)
  const [isExporting, setIsExporting] = useState(false)
  const [importFile, setImportFile] = useState<File | null>(null)

  // Mock data stats - replace with actual API call
  const [dataStats] = useState<DataStats>({
    totalProjects: 15,
    totalScripts: 127,
    totalStorage: '245 MB',
    lastBackup: '2024-01-20',
    dataRetention: 365,
  })

  const [exportOptions, setExportOptions] = useState<ExportOptions>({
    includeProjects: true,
    includeScripts: true,
    includeSettings: false,
    format: 'json',
    dateRange: 'all',
  })

  const handleExport = async () => {
    setIsExporting(true)
    setExportProgress(0)

    try {
      // Simulate export progress
      const progressInterval = setInterval(() => {
        setExportProgress(prev => {
          if (prev >= 100) {
            clearInterval(progressInterval)
            setIsExporting(false)
            setShowExportDialog(false)
            showSuccess('데이터 내보내기가 완료되었습니다.')
            return 100
          }
          return prev + 10
        })
      }, 200)

      // TODO: Implement actual export API call
      console.log('Export data with options:', exportOptions)
    } catch {
      setIsExporting(false)
      showError('데이터 내보내기에 실패했습니다.')
    }
  }

  const handleImport = async () => {
    if (!importFile) {
      showWarning('파일을 선택해주세요.')
      return
    }

    try {
      // TODO: Implement actual import API call
      console.log('Import file:', importFile.name)
      showSuccess('데이터 가져오기가 완료되었습니다.')
      setShowImportDialog(false)
      setImportFile(null)
    } catch {
      showError('데이터 가져오기에 실패했습니다.')
    }
  }

  const handleBackup = async () => {
    try {
      // TODO: Implement backup API call
      console.log('Create backup')
      showSuccess('백업이 생성되었습니다.')
    } catch {
      showError('백업 생성에 실패했습니다.')
    }
  }

  const handleDeleteAllData = async () => {
    try {
      // TODO: Implement delete all data API call
      console.log('Delete all user data')
      showSuccess('모든 데이터가 삭제되었습니다.')
      setShowDeleteDialog(false)
    } catch {
      showError('데이터 삭제에 실패했습니다.')
    }
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
        {/* Data Overview */}
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
                <StorageIcon color="primary" />
                데이터 현황
              </Typography>

              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
                <Box
                  sx={{
                    flex: {
                      xs: '1 1 calc(50% - 12px)',
                      sm: '1 1 calc(25% - 18px)',
                    },
                  }}
                >
                  <Paper variant="outlined" sx={{ p: 2, textAlign: 'center' }}>
                    <Typography variant="h4" color="primary">
                      {dataStats.totalProjects}
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      총 프로젝트
                    </Typography>
                  </Paper>
                </Box>
                <Box
                  sx={{
                    flex: {
                      xs: '1 1 calc(50% - 12px)',
                      sm: '1 1 calc(25% - 18px)',
                    },
                  }}
                >
                  <Paper variant="outlined" sx={{ p: 2, textAlign: 'center' }}>
                    <Typography variant="h4" color="success.main">
                      {dataStats.totalScripts}
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      생성된 스크립트
                    </Typography>
                  </Paper>
                </Box>
                <Box
                  sx={{
                    flex: {
                      xs: '1 1 calc(50% - 12px)',
                      sm: '1 1 calc(25% - 18px)',
                    },
                  }}
                >
                  <Paper variant="outlined" sx={{ p: 2, textAlign: 'center' }}>
                    <Typography variant="h4" color="info.main">
                      {dataStats.totalStorage}
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      사용 중인 용량
                    </Typography>
                  </Paper>
                </Box>
                <Box
                  sx={{
                    flex: {
                      xs: '1 1 calc(50% - 12px)',
                      sm: '1 1 calc(25% - 18px)',
                    },
                  }}
                >
                  <Paper variant="outlined" sx={{ p: 2, textAlign: 'center' }}>
                    <Typography variant="h4" color="warning.main">
                      {dataStats.dataRetention}일
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      데이터 보관 기간
                    </Typography>
                  </Paper>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Box>

        {/* Export & Import */}
        <Box sx={{ flex: { xs: '1 1 100%', md: '1 1 calc(50% - 8px)' } }}>
          <Card>
            <CardContent>
              <Typography
                variant="h6"
                gutterBottom
                display="flex"
                alignItems="center"
                gap={1}
              >
                <ExportIcon color="primary" />
                데이터 내보내기/가져오기
              </Typography>

              <Stack spacing={2}>
                <Button
                  variant="contained"
                  fullWidth
                  startIcon={<ExportIcon />}
                  onClick={() => setShowExportDialog(true)}
                >
                  데이터 내보내기
                </Button>

                <Button
                  variant="outlined"
                  fullWidth
                  startIcon={<ImportIcon />}
                  onClick={() => setShowImportDialog(true)}
                >
                  데이터 가져오기
                </Button>

                <Alert severity="info" sx={{ mt: 2 }}>
                  내보낸 데이터는 다른 계정에서 가져올 수 있으며, JSON, CSV, PDF
                  형식을 지원합니다.
                </Alert>
              </Stack>
            </CardContent>
          </Card>
        </Box>

        {/* Backup & Restore */}
        <Box sx={{ flex: { xs: '1 1 100%', md: '1 1 calc(50% - 8px)' } }}>
          <Card>
            <CardContent>
              <Typography
                variant="h6"
                gutterBottom
                display="flex"
                alignItems="center"
                gap={1}
              >
                <BackupIcon color="primary" />
                백업 및 복원
              </Typography>

              <Stack spacing={2}>
                <Box>
                  <Typography
                    variant="body2"
                    color="textSecondary"
                    gutterBottom
                  >
                    마지막 백업: {dataStats.lastBackup}
                  </Typography>
                  <Button
                    variant="contained"
                    fullWidth
                    startIcon={<BackupIcon />}
                    onClick={handleBackup}
                  >
                    지금 백업
                  </Button>
                </Box>

                <Button
                  variant="outlined"
                  fullWidth
                  startIcon={<RestoreIcon />}
                  onClick={() =>
                    showWarning(
                      '복원 기능은 고객센터를 통해 요청하실 수 있습니다.',
                    )
                  }
                >
                  백업에서 복원
                </Button>

                <Alert severity="warning">
                  백업은 자동으로 생성되며, 최근 30개의 백업이 보관됩니다.
                </Alert>
              </Stack>
            </CardContent>
          </Card>
        </Box>

        {/* Privacy & Data Retention */}
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
                <PrivacyIcon color="primary" />
                개인정보 및 데이터 보관
              </Typography>

              <List>
                <ListItem>
                  <ListItemIcon>
                    <SuccessIcon color="success" />
                  </ListItemIcon>
                  <ListItemText
                    primary="데이터 암호화"
                    secondary="모든 데이터는 AES-256 방식으로 암호화되어 저장됩니다"
                  />
                  <ListItemSecondaryAction>
                    <Chip label="활성화" color="success" size="small" />
                  </ListItemSecondaryAction>
                </ListItem>
                <Divider />
                <ListItem>
                  <ListItemIcon>
                    <SuccessIcon color="success" />
                  </ListItemIcon>
                  <ListItemText
                    primary="자동 백업"
                    secondary="매일 자동으로 데이터가 백업됩니다"
                  />
                  <ListItemSecondaryAction>
                    <Chip label="활성화" color="success" size="small" />
                  </ListItemSecondaryAction>
                </ListItem>
                <Divider />
                <ListItem>
                  <ListItemIcon>
                    <StorageIcon color="info" />
                  </ListItemIcon>
                  <ListItemText
                    primary="데이터 보관 기간"
                    secondary={`삭제된 데이터는 ${dataStats.dataRetention}일 동안 복구 가능합니다`}
                  />
                  <ListItemSecondaryAction>
                    <Chip
                      label={`${dataStats.dataRetention}일`}
                      color="info"
                      size="small"
                    />
                  </ListItemSecondaryAction>
                </ListItem>
              </List>
            </CardContent>
          </Card>
        </Box>

        {/* Danger Zone */}
        <Box sx={{ flex: '1 1 100%' }}>
          <Card>
            <CardContent>
              <Typography
                variant="h6"
                gutterBottom
                color="error"
                display="flex"
                alignItems="center"
                gap={1}
              >
                <WarningIcon />
                위험 구역
              </Typography>

              <Alert severity="error" sx={{ mb: 2 }}>
                아래 작업들은 되돌릴 수 없습니다. 신중하게 진행하세요.
              </Alert>

              <Stack spacing={2}>
                <Box>
                  <Typography variant="subtitle2" gutterBottom>
                    모든 데이터 삭제
                  </Typography>
                  <Typography variant="body2" color="textSecondary" mb={2}>
                    계정과 관련된 모든 프로젝트, 스크립트, 설정이 영구적으로
                    삭제됩니다.
                  </Typography>
                  <Button
                    variant="outlined"
                    color="error"
                    startIcon={<DeleteIcon />}
                    onClick={() => setShowDeleteDialog(true)}
                  >
                    모든 데이터 삭제
                  </Button>
                </Box>
              </Stack>
            </CardContent>
          </Card>
        </Box>
      </Box>

      {/* Export Dialog */}
      <Dialog
        open={showExportDialog}
        onClose={() => setShowExportDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>데이터 내보내기</DialogTitle>
        <DialogContent>
          <Stack spacing={3} sx={{ mt: 1 }}>
            <Box>
              <Typography variant="subtitle2" gutterBottom>
                내보낼 데이터 선택
              </Typography>
              <FormControlLabel
                control={
                  <Switch
                    checked={exportOptions.includeProjects}
                    onChange={e =>
                      setExportOptions(prev => ({
                        ...prev,
                        includeProjects: e.target.checked,
                      }))
                    }
                  />
                }
                label="프로젝트 데이터"
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={exportOptions.includeScripts}
                    onChange={e =>
                      setExportOptions(prev => ({
                        ...prev,
                        includeScripts: e.target.checked,
                      }))
                    }
                  />
                }
                label="스크립트 데이터"
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={exportOptions.includeSettings}
                    onChange={e =>
                      setExportOptions(prev => ({
                        ...prev,
                        includeSettings: e.target.checked,
                      }))
                    }
                  />
                }
                label="설정 데이터"
              />
            </Box>

            <TextField
              select
              label="파일 형식"
              value={exportOptions.format}
              onChange={e =>
                setExportOptions(prev => ({
                  ...prev,
                  format: e.target.value as 'json' | 'csv' | 'pdf',
                }))
              }
              fullWidth
              SelectProps={{ native: true }}
            >
              <option value="json">JSON</option>
              <option value="csv">CSV</option>
              <option value="pdf">PDF</option>
            </TextField>

            <TextField
              select
              label="기간"
              value={exportOptions.dateRange}
              onChange={e =>
                setExportOptions(prev => ({
                  ...prev,
                  dateRange: e.target.value as
                    | 'all'
                    | 'last_month'
                    | 'last_year',
                }))
              }
              fullWidth
              SelectProps={{ native: true }}
            >
              <option value="all">전체 기간</option>
              <option value="last_month">최근 1개월</option>
              <option value="last_year">최근 1년</option>
            </TextField>

            {isExporting && (
              <Box>
                <Typography variant="body2" gutterBottom>
                  내보내기 진행 중... {exportProgress}%
                </Typography>
                <LinearProgress variant="determinate" value={exportProgress} />
              </Box>
            )}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => setShowExportDialog(false)}
            disabled={isExporting}
          >
            취소
          </Button>
          <Button
            onClick={handleExport}
            variant="contained"
            disabled={isExporting}
          >
            내보내기
          </Button>
        </DialogActions>
      </Dialog>

      {/* Import Dialog */}
      <Dialog
        open={showImportDialog}
        onClose={() => setShowImportDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>데이터 가져오기</DialogTitle>
        <DialogContent>
          <Stack spacing={3} sx={{ mt: 1 }}>
            <Alert severity="warning">
              가져오기를 진행하면 기존 데이터가 덮어쓰여질 수 있습니다.
            </Alert>

            <Button variant="outlined" component="label" fullWidth>
              파일 선택
              <input
                type="file"
                hidden
                accept=".json,.csv"
                onChange={e => setImportFile(e.target.files?.[0] || null)}
              />
            </Button>

            {importFile && (
              <Typography variant="body2" color="textSecondary">
                선택된 파일: {importFile.name}
              </Typography>
            )}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowImportDialog(false)}>취소</Button>
          <Button
            onClick={handleImport}
            variant="contained"
            disabled={!importFile}
          >
            가져오기
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={showDeleteDialog}
        onClose={() => setShowDeleteDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle color="error.main">모든 데이터 삭제</DialogTitle>
        <DialogContent>
          <Stack spacing={2}>
            <Alert severity="error">이 작업은 되돌릴 수 없습니다!</Alert>
            <Typography>정말로 모든 데이터를 삭제하시겠습니까?</Typography>
            <Typography variant="body2" color="textSecondary">
              삭제될 데이터:
            </Typography>
            <List dense>
              <ListItem>
                <ListItemText
                  primary={`${dataStats.totalProjects}개의 프로젝트`}
                />
              </ListItem>
              <ListItem>
                <ListItemText
                  primary={`${dataStats.totalScripts}개의 스크립트`}
                />
              </ListItem>
              <ListItem>
                <ListItemText primary="모든 설정 정보" />
              </ListItem>
              <ListItem>
                <ListItemText primary="백업 파일" />
              </ListItem>
            </List>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowDeleteDialog(false)}>취소</Button>
          <Button
            onClick={handleDeleteAllData}
            color="error"
            variant="contained"
          >
            영구 삭제
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
