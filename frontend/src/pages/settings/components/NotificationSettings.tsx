import { useState, Fragment } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  FormControlLabel,
  Switch,
  Button,
  Stack,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Divider,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Alert,
  Chip,
} from '@mui/material'
import {
  Email as EmailIcon,
  Phone as PhoneIcon,
  Computer as DesktopIcon,
  Save as SaveIcon,
  BugReport as TestIcon,
} from '@mui/icons-material'
import { useForm, Controller } from 'react-hook-form'

import { useToastHelpers } from '@/shared/ui/components/toast'

interface NotificationSettings {
  // Email notifications
  emailEnabled: boolean
  emailScriptComplete: boolean
  emailProjectUpdate: boolean
  emailSystemAlert: boolean
  emailWeeklyReport: boolean
  emailFrequency: 'immediate' | 'daily' | 'weekly'

  // Push notifications
  pushEnabled: boolean
  pushScriptComplete: boolean
  pushProjectUpdate: boolean
  pushSystemAlert: boolean

  // In-app notifications
  inAppEnabled: boolean
  inAppScriptComplete: boolean
  inAppProjectUpdate: boolean
  inAppSystemAlert: boolean

  // Notification schedule
  quietHoursEnabled: boolean
  quietHoursStart: string
  quietHoursEnd: string

  // Contact preferences
  primaryEmail: string
  phoneNumber: string
  phoneNotificationsEnabled: boolean
}

const NOTIFICATION_TYPES = [
  {
    key: 'scriptComplete',
    title: '스크립트 생성 완료',
    description: 'AI 스크립트 생성이 완료되었을 때',
  },
  {
    key: 'projectUpdate',
    title: '프로젝트 업데이트',
    description: '프로젝트에 새로운 활동이 있을 때',
  },
  {
    key: 'systemAlert',
    title: '시스템 알림',
    description: '중요한 시스템 공지사항이 있을 때',
  },
]

export function NotificationSettings() {
  const { showSuccess, showError } = useToastHelpers()

  // Mock current settings - replace with actual API call
  const [currentSettings] = useState<NotificationSettings>({
    emailEnabled: true,
    emailScriptComplete: true,
    emailProjectUpdate: true,
    emailSystemAlert: true,
    emailWeeklyReport: false,
    emailFrequency: 'immediate',

    pushEnabled: true,
    pushScriptComplete: true,
    pushProjectUpdate: false,
    pushSystemAlert: true,

    inAppEnabled: true,
    inAppScriptComplete: true,
    inAppProjectUpdate: true,
    inAppSystemAlert: true,

    quietHoursEnabled: true,
    quietHoursStart: '22:00',
    quietHoursEnd: '08:00',

    primaryEmail: 'writer@example.com',
    phoneNumber: '',
    phoneNotificationsEnabled: false,
  })

  const {
    control,
    handleSubmit,
    watch,
    formState: { isDirty },
  } = useForm<NotificationSettings>({
    defaultValues: currentSettings,
  })

  const emailEnabled = watch('emailEnabled')
  const pushEnabled = watch('pushEnabled')
  const inAppEnabled = watch('inAppEnabled')
  const quietHoursEnabled = watch('quietHoursEnabled')

  const handleSave = async (data: NotificationSettings) => {
    try {
      // TODO: Implement API call to save notification settings
      console.log('Save notification settings:', data)
      showSuccess('알림 설정이 저장되었습니다.')
    } catch (error) {
      showError('알림 설정 저장에 실패했습니다.')
    }
  }

  const handleTestNotification = (type: string) => {
    showSuccess(`${type} 테스트 알림이 발송되었습니다.`)
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
        {/* Contact Information */}
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
                <EmailIcon color="primary" />
                연락처 정보
              </Typography>

              <Stack spacing={3}>
                <Controller
                  name="primaryEmail"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="기본 이메일"
                      type="email"
                      fullWidth
                      helperText="알림을 받을 기본 이메일 주소입니다"
                    />
                  )}
                />

                <Controller
                  name="phoneNumber"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="전화번호 (선택사항)"
                      fullWidth
                      helperText="긴급 알림용 전화번호입니다"
                    />
                  )}
                />

                <FormControlLabel
                  control={
                    <Controller
                      name="phoneNotificationsEnabled"
                      control={control}
                      render={({ field }) => (
                        <Switch {...field} checked={field.value} />
                      )}
                    />
                  }
                  label="SMS 알림 활성화"
                />
              </Stack>
            </CardContent>
          </Card>
        </Box>

        {/* Quiet Hours */}
        <Box sx={{ flex: { xs: '1 1 100%', md: '1 1 calc(50% - 8px)' } }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                방해 금지 시간
              </Typography>

              <Stack spacing={3}>
                <FormControlLabel
                  control={
                    <Controller
                      name="quietHoursEnabled"
                      control={control}
                      render={({ field }) => (
                        <Switch {...field} checked={field.value} />
                      )}
                    />
                  }
                  label="방해 금지 시간 활성화"
                />

                {quietHoursEnabled && (
                  <>
                    <Controller
                      name="quietHoursStart"
                      control={control}
                      render={({ field }) => (
                        <TextField
                          {...field}
                          label="시작 시간"
                          type="time"
                          fullWidth
                          InputLabelProps={{ shrink: true }}
                        />
                      )}
                    />

                    <Controller
                      name="quietHoursEnd"
                      control={control}
                      render={({ field }) => (
                        <TextField
                          {...field}
                          label="종료 시간"
                          type="time"
                          fullWidth
                          InputLabelProps={{ shrink: true }}
                        />
                      )}
                    />

                    <Alert severity="info">
                      이 시간 동안에는 긴급 알림을 제외한 모든 알림이
                      음소거됩니다.
                    </Alert>
                  </>
                )}
              </Stack>
            </CardContent>
          </Card>
        </Box>

        {/* Email Notifications */}
        <Box sx={{ flex: '1 1 100%' }}>
          <Card>
            <CardContent>
              <Box
                display="flex"
                justifyContent="space-between"
                alignItems="center"
                mb={2}
              >
                <Typography
                  variant="h6"
                  display="flex"
                  alignItems="center"
                  gap={1}
                >
                  <EmailIcon color="primary" />
                  이메일 알림
                </Typography>
                <Button
                  size="small"
                  startIcon={<TestIcon />}
                  onClick={() => handleTestNotification('이메일')}
                  disabled={!emailEnabled}
                >
                  테스트 발송
                </Button>
              </Box>

              <Stack spacing={2}>
                <FormControlLabel
                  control={
                    <Controller
                      name="emailEnabled"
                      control={control}
                      render={({ field }) => (
                        <Switch {...field} checked={field.value} />
                      )}
                    />
                  }
                  label="이메일 알림 활성화"
                />

                {emailEnabled && (
                  <>
                    <List>
                      {NOTIFICATION_TYPES.map(type => (
                        <Fragment key={type.key}>
                          <ListItem>
                            <ListItemText
                              primary={type.title}
                              secondary={type.description}
                            />
                            <ListItemSecondaryAction>
                              <Controller
                                name={
                                  `email${type.key.charAt(0).toUpperCase() + type.key.slice(1)}` as keyof NotificationSettings
                                }
                                control={control}
                                render={({ field }) => (
                                  <Switch
                                    {...field}
                                    checked={field.value as boolean}
                                  />
                                )}
                              />
                            </ListItemSecondaryAction>
                          </ListItem>
                          <Divider />
                        </Fragment>
                      ))}
                      <ListItem>
                        <ListItemText
                          primary="주간 리포트"
                          secondary="프로젝트 진행 상황 및 통계 요약 리포트"
                        />
                        <ListItemSecondaryAction>
                          <Controller
                            name="emailWeeklyReport"
                            control={control}
                            render={({ field }) => (
                              <Switch {...field} checked={field.value} />
                            )}
                          />
                        </ListItemSecondaryAction>
                      </ListItem>
                    </List>

                    <Box mt={2}>
                      <Controller
                        name="emailFrequency"
                        control={control}
                        render={({ field }) => (
                          <FormControl fullWidth>
                            <InputLabel>알림 빈도</InputLabel>
                            <Select {...field} label="알림 빈도">
                              <MenuItem value="immediate">즉시 알림</MenuItem>
                              <MenuItem value="daily">일일 요약</MenuItem>
                              <MenuItem value="weekly">주간 요약</MenuItem>
                            </Select>
                          </FormControl>
                        )}
                      />
                    </Box>
                  </>
                )}
              </Stack>
            </CardContent>
          </Card>
        </Box>

        {/* Push Notifications */}
        <Box sx={{ flex: { xs: '1 1 100%', md: '1 1 calc(50% - 8px)' } }}>
          <Card>
            <CardContent>
              <Box
                display="flex"
                justifyContent="space-between"
                alignItems="center"
                mb={2}
              >
                <Typography
                  variant="h6"
                  display="flex"
                  alignItems="center"
                  gap={1}
                >
                  <PhoneIcon color="primary" />
                  푸시 알림
                </Typography>
                <Button
                  size="small"
                  startIcon={<TestIcon />}
                  onClick={() => handleTestNotification('푸시')}
                  disabled={!pushEnabled}
                >
                  테스트 발송
                </Button>
              </Box>

              <Stack spacing={2}>
                <FormControlLabel
                  control={
                    <Controller
                      name="pushEnabled"
                      control={control}
                      render={({ field }) => (
                        <Switch {...field} checked={field.value} />
                      )}
                    />
                  }
                  label="푸시 알림 활성화"
                />

                {pushEnabled && (
                  <List dense>
                    {NOTIFICATION_TYPES.map(type => (
                      <ListItem key={type.key}>
                        <ListItemText
                          primary={type.title}
                          secondary={type.description}
                        />
                        <ListItemSecondaryAction>
                          <Controller
                            name={
                              `push${type.key.charAt(0).toUpperCase() + type.key.slice(1)}` as keyof NotificationSettings
                            }
                            control={control}
                            render={({ field }) => (
                              <Switch
                                {...field}
                                checked={field.value as boolean}
                                size="small"
                              />
                            )}
                          />
                        </ListItemSecondaryAction>
                      </ListItem>
                    ))}
                  </List>
                )}
              </Stack>
            </CardContent>
          </Card>
        </Box>

        {/* In-App Notifications */}
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
                <DesktopIcon color="primary" />
                인앱 알림
              </Typography>

              <Stack spacing={2}>
                <FormControlLabel
                  control={
                    <Controller
                      name="inAppEnabled"
                      control={control}
                      render={({ field }) => (
                        <Switch {...field} checked={field.value} />
                      )}
                    />
                  }
                  label="인앱 알림 활성화"
                />

                {inAppEnabled && (
                  <List dense>
                    {NOTIFICATION_TYPES.map(type => (
                      <ListItem key={type.key}>
                        <ListItemText
                          primary={type.title}
                          secondary={type.description}
                        />
                        <ListItemSecondaryAction>
                          <Controller
                            name={
                              `inApp${type.key.charAt(0).toUpperCase() + type.key.slice(1)}` as keyof NotificationSettings
                            }
                            control={control}
                            render={({ field }) => (
                              <Switch
                                {...field}
                                checked={field.value as boolean}
                                size="small"
                              />
                            )}
                          />
                        </ListItemSecondaryAction>
                      </ListItem>
                    ))}
                  </List>
                )}
              </Stack>
            </CardContent>
          </Card>
        </Box>

        {/* Notification Summary */}
        <Box sx={{ flex: '1 1 100%' }}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" gutterBottom>
                알림 설정 요약
              </Typography>

              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                <Chip
                  label={`이메일: ${emailEnabled ? '활성화' : '비활성화'}`}
                  color={emailEnabled ? 'success' : 'default'}
                  size="small"
                />
                <Chip
                  label={`푸시: ${pushEnabled ? '활성화' : '비활성화'}`}
                  color={pushEnabled ? 'success' : 'default'}
                  size="small"
                />
                <Chip
                  label={`인앱: ${inAppEnabled ? '활성화' : '비활성화'}`}
                  color={inAppEnabled ? 'success' : 'default'}
                  size="small"
                />
                <Chip
                  label={`방해금지: ${quietHoursEnabled ? '활성화' : '비활성화'}`}
                  color={quietHoursEnabled ? 'warning' : 'default'}
                  size="small"
                />
              </Stack>
            </CardContent>
          </Card>
        </Box>

        {/* Save Button */}
        <Box sx={{ flex: '1 1 100%' }}>
          <Box display="flex" justifyContent="flex-end">
            <Button
              variant="contained"
              size="large"
              startIcon={<SaveIcon />}
              onClick={handleSubmit(handleSave)}
              disabled={!isDirty}
            >
              설정 저장
            </Button>
          </Box>
        </Box>
      </Box>
    </Box>
  )
}
