import { useState, useEffect } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  RadioGroup,
  FormControlLabel,
  Radio,
  Stack,
  Chip,
  Divider,
  Alert,
  Button,
  IconButton,
} from '@mui/material'
import {
  Movie as ProjectIcon,
  PlayArrow as EpisodeIcon,
  Add as AddIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material'

import type { ProjectOption, EpisodeOption, GenerationConfig } from '../types'

interface SelectionStepProps {
  projects: ProjectOption[]
  episodes: EpisodeOption[]
  config: Partial<GenerationConfig>
  onConfigChange: (updates: Partial<GenerationConfig>) => void
  onLoadProjects: () => void
  onLoadEpisodes: (projectId: string) => void
  onCreateProject: () => void
  onCreateEpisode: () => void
  loading?: boolean
}

/**
 * Step 1: Project and Episode Selection
 */
export function SelectionStep({
  projects,
  episodes,
  config,
  onConfigChange,
  onLoadProjects,
  onLoadEpisodes,
  onCreateProject,
  onCreateEpisode,
  loading = false,
}: SelectionStepProps) {
  const [selectedProject, setSelectedProject] = useState<ProjectOption | null>(
    projects.find(p => p.id === config.projectId) || null,
  )

  // Load episodes when project changes
  useEffect(() => {
    if (selectedProject) {
      onLoadEpisodes(selectedProject.id)
    }
  }, [selectedProject, onLoadEpisodes])

  const handleProjectChange = (projectId: string) => {
    const project = projects.find(p => p.id === projectId)
    setSelectedProject(project || null)
    onConfigChange({
      projectId,
      // episodeId omitted to reset episode selection
    })
  }

  const handleEpisodeChange = (episodeId: string) => {
    onConfigChange({ episodeId })
  }

  const selectedProjectData = projects.find(p => p.id === config.projectId)
  const selectedEpisodeData = episodes.find(e => e.id === config.episodeId)

  return (
    <Stack spacing={3}>
      {/* Header */}
      <Box>
        <Typography variant="h5" gutterBottom>
          프로젝트 및 에피소드 선택
        </Typography>
        <Typography variant="body1" color="textSecondary">
          스크립트를 생성할 프로젝트와 에피소드를 선택해주세요.
        </Typography>
      </Box>

      {/* Project Selection */}
      <Card>
        <CardContent>
          <Box
            display="flex"
            alignItems="center"
            justifyContent="space-between"
            mb={2}
          >
            <Typography variant="h6" display="flex" alignItems="center" gap={1}>
              <ProjectIcon color="primary" />
              프로젝트 선택
            </Typography>

            <Stack direction="row" spacing={1}>
              <IconButton
                onClick={onLoadProjects}
                disabled={loading}
                size="small"
              >
                <RefreshIcon />
              </IconButton>
              <Button
                startIcon={<AddIcon />}
                onClick={onCreateProject}
                size="small"
                variant="outlined"
              >
                새 프로젝트
              </Button>
            </Stack>
          </Box>

          {projects.length === 0 ? (
            <Alert severity="info">
              사용 가능한 프로젝트가 없습니다. 새 프로젝트를 생성해주세요.
            </Alert>
          ) : (
            <RadioGroup
              value={config.projectId || ''}
              onChange={e => handleProjectChange(e.target.value)}
            >
              <Stack spacing={1}>
                {projects.map(project => (
                  <Card
                    key={project.id}
                    variant="outlined"
                    sx={{
                      cursor: 'pointer',
                      '&:hover': { bgcolor: 'action.hover' },
                      bgcolor:
                        config.projectId === project.id
                          ? 'action.selected'
                          : 'background.paper',
                    }}
                    onClick={() => handleProjectChange(project.id)}
                  >
                    <CardContent sx={{ py: 2 }}>
                      <FormControlLabel
                        value={project.id}
                        control={<Radio />}
                        label={
                          <Box flex={1}>
                            <Typography variant="subtitle1" fontWeight="medium">
                              {project.name}
                            </Typography>
                            <Stack direction="row" spacing={1} mt={1}>
                              <Chip label={project.type} size="small" />
                              {project.episodeCount && (
                                <Chip
                                  label={`${project.episodeCount}개 에피소드`}
                                  size="small"
                                  variant="outlined"
                                />
                              )}
                            </Stack>
                            {project.description && (
                              <Typography
                                variant="body2"
                                color="textSecondary"
                                mt={1}
                              >
                                {project.description}
                              </Typography>
                            )}
                          </Box>
                        }
                        sx={{ width: '100%', m: 0 }}
                      />
                    </CardContent>
                  </Card>
                ))}
              </Stack>
            </RadioGroup>
          )}
        </CardContent>
      </Card>

      {/* Episode Selection */}
      {config.projectId && (
        <Card>
          <CardContent>
            <Box
              display="flex"
              alignItems="center"
              justifyContent="space-between"
              mb={2}
            >
              <Typography
                variant="h6"
                display="flex"
                alignItems="center"
                gap={1}
              >
                <EpisodeIcon color="primary" />
                에피소드 선택
              </Typography>

              <Button
                startIcon={<AddIcon />}
                onClick={onCreateEpisode}
                size="small"
                variant="outlined"
                disabled={!config.projectId}
              >
                새 에피소드
              </Button>
            </Box>

            {episodes.length === 0 ? (
              <Alert severity="info">
                선택한 프로젝트에 에피소드가 없습니다. 새 에피소드를
                생성해주세요.
              </Alert>
            ) : (
              <RadioGroup
                value={config.episodeId || 'new'}
                onChange={e => {
                  const value = e.target.value
                  handleEpisodeChange(value === 'new' ? '' : value)
                }}
              >
                <Stack spacing={1}>
                  {/* Option for new episode */}
                  <Card
                    variant="outlined"
                    sx={{
                      cursor: 'pointer',
                      '&:hover': { bgcolor: 'action.hover' },
                      bgcolor: !config.episodeId
                        ? 'action.selected'
                        : 'background.paper',
                      borderStyle: 'dashed',
                    }}
                    onClick={() => handleEpisodeChange('')}
                  >
                    <CardContent sx={{ py: 2 }}>
                      <FormControlLabel
                        value="new"
                        control={<Radio />}
                        label={
                          <Box>
                            <Typography
                              variant="subtitle1"
                              fontWeight="medium"
                              color="primary"
                            >
                              새 에피소드 생성
                            </Typography>
                            <Typography variant="body2" color="textSecondary">
                              AI가 프로젝트 설정에 맞는 새로운 에피소드를
                              생성합니다
                            </Typography>
                          </Box>
                        }
                        sx={{ width: '100%', m: 0 }}
                      />
                    </CardContent>
                  </Card>

                  <Divider sx={{ my: 1 }}>또는 기존 에피소드</Divider>

                  {/* Existing episodes */}
                  {episodes.map(episode => (
                    <Card
                      key={episode.id}
                      variant="outlined"
                      sx={{
                        cursor: 'pointer',
                        '&:hover': { bgcolor: 'action.hover' },
                        bgcolor:
                          config.episodeId === episode.id
                            ? 'action.selected'
                            : 'background.paper',
                      }}
                      onClick={() => handleEpisodeChange(episode.id)}
                    >
                      <CardContent sx={{ py: 2 }}>
                        <FormControlLabel
                          value={episode.id}
                          control={<Radio />}
                          label={
                            <Box flex={1}>
                              <Typography
                                variant="subtitle1"
                                fontWeight="medium"
                              >
                                {episode.title}
                              </Typography>
                              <Stack direction="row" spacing={1} mt={1}>
                                <Chip
                                  label={`에피소드 ${episode.number}`}
                                  size="small"
                                />
                                {episode.seasonNumber && (
                                  <Chip
                                    label={`시즌 ${episode.seasonNumber}`}
                                    size="small"
                                    variant="outlined"
                                  />
                                )}
                                {episode.duration && (
                                  <Chip
                                    label={`${episode.duration}분`}
                                    size="small"
                                    variant="outlined"
                                  />
                                )}
                                {episode.status && (
                                  <Chip
                                    label={episode.status}
                                    size="small"
                                    color={
                                      episode.status === 'completed'
                                        ? 'success'
                                        : 'default'
                                    }
                                  />
                                )}
                              </Stack>
                              {episode.description && (
                                <Typography
                                  variant="body2"
                                  color="textSecondary"
                                  mt={1}
                                >
                                  {episode.description}
                                </Typography>
                              )}
                            </Box>
                          }
                          sx={{ width: '100%', m: 0 }}
                        />
                      </CardContent>
                    </Card>
                  ))}
                </Stack>
              </RadioGroup>
            )}
          </CardContent>
        </Card>
      )}

      {/* Selection Summary */}
      {(selectedProjectData || selectedEpisodeData) && (
        <Alert severity="success">
          <Typography variant="subtitle2" gutterBottom>
            선택된 항목:
          </Typography>
          <Stack spacing={1}>
            {selectedProjectData && (
              <Typography variant="body2">
                📁 프로젝트: {selectedProjectData.name} (
                {selectedProjectData.type})
              </Typography>
            )}
            {selectedEpisodeData && (
              <Typography variant="body2">
                🎬 에피소드: {selectedEpisodeData.title} (에피소드{' '}
                {selectedEpisodeData.number})
              </Typography>
            )}
            {config.projectId && !config.episodeId && (
              <Typography variant="body2" color="primary">
                🎭 새 에피소드를 생성합니다
              </Typography>
            )}
          </Stack>
        </Alert>
      )}
    </Stack>
  )
}
