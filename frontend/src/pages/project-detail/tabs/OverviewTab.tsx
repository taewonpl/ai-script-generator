import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Alert,
  Stack,
  Divider,
  LinearProgress,
  Avatar,
} from '@mui/material'
import StatsIcon from '@mui/icons-material/TrendingUp'
import TrendingIcon from '@mui/icons-material/TrendingUp'
import InfoIcon from '@mui/icons-material/Info'
import CompletedIcon from '@mui/icons-material/CheckCircle'
import PendingIcon from '@mui/icons-material/Schedule'

interface OverviewTabProps {
  projectId: string
}

export function OverviewTab({ projectId: _projectId }: OverviewTabProps) {
  // Mock 데이터 - 실제로는 API에서 가져올 데이터
  const projectStats = {
    totalEpisodes: 12,
    completedEpisodes: 8,
    totalScripts: 45,
    progress: 67,
    status: 'active' as const,
    createdAt: '2024-01-15',
    lastUpdated: '2024-03-20',
  }

  const currentSystemPrompt = {
    version: '1.2.0',
    content: `당신은 전문적인 드라마 작가입니다. 다음 조건에 맞춰 고품질 스크립트를 작성해주세요:

1. 자연스럽고 현실적인 대화
2. 등장인물의 성격과 배경에 맞는 말투
3. 적절한 감정 표현과 갈등 구조
4. 시청자의 몰입을 높이는 전개

항상 최신 버전의 시스템 프롬프트를 사용하여 일관된 품질을 유지합니다.`,
    updatedAt: '2024-03-15',
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'success'
      case 'paused':
        return 'warning'
      case 'completed':
        return 'primary'
      default:
        return 'default'
    }
  }

  return (
    <Box>
      {/* 프로젝트 상태 개요 */}
      <Box display="flex" flexWrap="wrap" gap={3} sx={{ mb: 4 }}>
        <Box flex="1 1 250px" minWidth="250px">
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <Avatar sx={{ bgcolor: 'primary.main', mr: 2 }}>
                  <StatsIcon />
                </Avatar>
                <Box>
                  <Typography variant="h4" color="primary">
                    {projectStats.totalEpisodes}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    총 에피소드
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Box>

        <Box flex="1 1 250px" minWidth="250px">
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <Avatar sx={{ bgcolor: 'success.main', mr: 2 }}>
                  <CompletedIcon />
                </Avatar>
                <Box>
                  <Typography variant="h4" color="success.main">
                    {projectStats.completedEpisodes}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    완료된 에피소드
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Box>

        <Box flex="1 1 250px" minWidth="250px">
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <Avatar sx={{ bgcolor: 'info.main', mr: 2 }}>
                  <PendingIcon />
                </Avatar>
                <Box>
                  <Typography variant="h4" color="info.main">
                    {projectStats.totalScripts}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    생성된 스크립트
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Box>

        <Box flex="1 1 250px" minWidth="250px">
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <Avatar sx={{ bgcolor: 'warning.main', mr: 2 }}>
                  <TrendingIcon />
                </Avatar>
                <Box>
                  <Typography variant="h4" color="warning.main">
                    {projectStats.progress}%
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    진행률
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Box>
      </Box>

      <Box display="flex" flexWrap="wrap" gap={3}>
        {/* 프로젝트 정보 */}
        <Box flex="1 1 400px" minWidth="400px">
          <Card>
            <CardContent>
              <Typography
                variant="h6"
                gutterBottom
                sx={{ display: 'flex', alignItems: 'center', gap: 1 }}
              >
                <InfoIcon color="primary" />
                프로젝트 정보
              </Typography>

              <Stack spacing={2}>
                <Box>
                  <Typography variant="subtitle2" color="text.secondary">
                    상태
                  </Typography>
                  <Chip
                    label={
                      projectStats.status === 'active'
                        ? '진행중'
                        : projectStats.status
                    }
                    color={
                      getStatusColor(projectStats.status) as
                        | 'success'
                        | 'warning'
                        | 'primary'
                        | 'default'
                    }
                    size="small"
                  />
                </Box>

                <Divider />

                <Box>
                  <Typography
                    variant="subtitle2"
                    color="text.secondary"
                    gutterBottom
                  >
                    전체 진행률
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <LinearProgress
                      variant="determinate"
                      value={projectStats.progress}
                      sx={{ flexGrow: 1, height: 8, borderRadius: 4 }}
                    />
                    <Typography
                      variant="body2"
                      color="primary"
                      fontWeight="bold"
                    >
                      {projectStats.progress}%
                    </Typography>
                  </Box>
                </Box>

                <Divider />

                <Box>
                  <Typography variant="subtitle2" color="text.secondary">
                    생성일
                  </Typography>
                  <Typography variant="body2">
                    {new Date(projectStats.createdAt).toLocaleDateString(
                      'ko-KR',
                    )}
                  </Typography>
                </Box>

                <Box>
                  <Typography variant="subtitle2" color="text.secondary">
                    마지막 업데이트
                  </Typography>
                  <Typography variant="body2">
                    {new Date(projectStats.lastUpdated).toLocaleDateString(
                      'ko-KR',
                    )}
                  </Typography>
                </Box>
              </Stack>
            </CardContent>
          </Card>
        </Box>

        {/* 현재 시스템 프롬프트 */}
        <Box flex="1 1 400px" minWidth="400px">
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                현재 시스템 프롬프트
              </Typography>

              <Alert severity="info" sx={{ mb: 2 }}>
                <Typography variant="body2">
                  <strong>최신 버전 사용 중:</strong> v
                  {currentSystemPrompt.version}
                </Typography>
              </Alert>

              <Box
                sx={{
                  bgcolor: 'grey.50',
                  p: 2,
                  borderRadius: 1,
                  maxHeight: 200,
                  overflow: 'auto',
                  border: '1px solid',
                  borderColor: 'grey.200',
                }}
              >
                <Typography
                  variant="body2"
                  component="pre"
                  sx={{
                    fontFamily: 'monospace',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                    margin: 0,
                  }}
                >
                  {currentSystemPrompt.content}
                </Typography>
              </Box>

              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ mt: 1, display: 'block' }}
              >
                마지막 업데이트:{' '}
                {new Date(currentSystemPrompt.updatedAt).toLocaleDateString(
                  'ko-KR',
                )}
              </Typography>

              <Alert severity="success" sx={{ mt: 2 }}>
                <Typography variant="body2">
                  모든 스크립트 생성에서 <strong>항상 최신 버전</strong>의
                  시스템 프롬프트가 사용됩니다.
                </Typography>
              </Alert>
            </CardContent>
          </Card>
        </Box>
      </Box>
    </Box>
  )
}
