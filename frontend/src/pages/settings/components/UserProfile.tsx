import { useState } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Avatar,
  Stack,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Switch,
  Divider,
  Alert,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
} from '@mui/material'
import {
  Edit as EditIcon,
  PhotoCamera as CameraIcon,
  Save as SaveIcon,
  Cancel as CancelIcon,
  Security as SecurityIcon,
  ExitToApp as LogoutIcon,
} from '@mui/icons-material'
import { useForm, Controller } from 'react-hook-form'

import { useToastHelpers } from '@/shared/ui/components/toast'

interface UserProfileData {
  name: string
  email: string
  bio: string
  avatar?: string
  language: string
  timezone: string
  emailNotifications: boolean
  profileVisibility: boolean
}

export function UserProfile() {
  const { showSuccess, showError } = useToastHelpers()
  const [isEditing, setIsEditing] = useState(false)
  const [showPasswordDialog, setShowPasswordDialog] = useState(false)

  // Mock user data - replace with actual API call
  const [userData] = useState<UserProfileData>({
    name: '김작가',
    email: 'writer@example.com',
    bio: 'AI를 활용한 창작 작업에 관심이 많은 시나리오 작가입니다.',
    language: 'ko',
    timezone: 'Asia/Seoul',
    emailNotifications: true,
    profileVisibility: true,
  })

  const {
    control,
    handleSubmit,
    reset,
    formState: { isDirty },
  } = useForm<UserProfileData>({
    defaultValues: userData,
  })

  const handleSave = async (data: UserProfileData) => {
    try {
      // TODO: Implement API call to save profile
      console.log('Save profile:', data)
      showSuccess('프로필이 업데이트되었습니다.')
      setIsEditing(false)
    } catch {
      showError('프로필 업데이트에 실패했습니다.')
    }
  }

  const handleCancel = () => {
    reset(userData)
    setIsEditing(false)
  }

  const handleAvatarUpload = () => {
    // TODO: Implement avatar upload
    console.log('Upload avatar')
    showSuccess('프로필 이미지가 업데이트되었습니다.')
  }

  const handlePasswordChange = () => {
    setShowPasswordDialog(false)
    showSuccess('비밀번호가 변경되었습니다.')
  }

  const handleLogout = () => {
    // TODO: Implement logout
    console.log('Logout')
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
        {/* Profile Information */}
        <Box sx={{ flex: { xs: '1 1 100%', md: '1 1 calc(66.667% - 16px)' } }}>
          <Card>
            <CardContent>
              <Box
                display="flex"
                justifyContent="space-between"
                alignItems="center"
                mb={3}
              >
                <Typography variant="h6">프로필 정보</Typography>
                {!isEditing ? (
                  <Button
                    startIcon={<EditIcon />}
                    onClick={() => setIsEditing(true)}
                  >
                    편집
                  </Button>
                ) : (
                  <Stack direction="row" spacing={1}>
                    <Button
                      variant="contained"
                      startIcon={<SaveIcon />}
                      onClick={handleSubmit(handleSave)}
                      disabled={!isDirty}
                    >
                      저장
                    </Button>
                    <Button startIcon={<CancelIcon />} onClick={handleCancel}>
                      취소
                    </Button>
                  </Stack>
                )}
              </Box>

              <form onSubmit={handleSubmit(handleSave)}>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
                  <Box sx={{ flex: '1 1 100%' }}>
                    <Controller
                      name="name"
                      control={control}
                      render={({ field }) => (
                        <TextField
                          {...field}
                          label="이름"
                          fullWidth
                          disabled={!isEditing}
                          variant={isEditing ? 'outlined' : 'standard'}
                        />
                      )}
                    />
                  </Box>

                  <Box sx={{ flex: '1 1 100%' }}>
                    <Controller
                      name="email"
                      control={control}
                      render={({ field }) => (
                        <TextField
                          {...field}
                          label="이메일"
                          type="email"
                          fullWidth
                          disabled={!isEditing}
                          variant={isEditing ? 'outlined' : 'standard'}
                        />
                      )}
                    />
                  </Box>

                  <Box sx={{ flex: '1 1 100%' }}>
                    <Controller
                      name="bio"
                      control={control}
                      render={({ field }) => (
                        <TextField
                          {...field}
                          label="소개"
                          multiline
                          rows={3}
                          fullWidth
                          disabled={!isEditing}
                          variant={isEditing ? 'outlined' : 'standard'}
                        />
                      )}
                    />
                  </Box>

                  <Box
                    sx={{
                      flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 12px)' },
                    }}
                  >
                    <Controller
                      name="language"
                      control={control}
                      render={({ field }) => (
                        <TextField
                          {...field}
                          label="언어"
                          select
                          fullWidth
                          disabled={!isEditing}
                          variant={isEditing ? 'outlined' : 'standard'}
                          SelectProps={{
                            native: true,
                          }}
                        >
                          <option value="ko">한국어</option>
                          <option value="en">English</option>
                          <option value="ja">日本語</option>
                        </TextField>
                      )}
                    />
                  </Box>

                  <Box
                    sx={{
                      flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 12px)' },
                    }}
                  >
                    <Controller
                      name="timezone"
                      control={control}
                      render={({ field }) => (
                        <TextField
                          {...field}
                          label="시간대"
                          select
                          fullWidth
                          disabled={!isEditing}
                          variant={isEditing ? 'outlined' : 'standard'}
                          SelectProps={{
                            native: true,
                          }}
                        >
                          <option value="Asia/Seoul">Asia/Seoul</option>
                          <option value="UTC">UTC</option>
                          <option value="America/New_York">
                            America/New_York
                          </option>
                        </TextField>
                      )}
                    />
                  </Box>
                </Box>
              </form>
            </CardContent>
          </Card>
        </Box>

        {/* Profile Picture & Quick Settings */}
        <Box sx={{ flex: { xs: '1 1 100%', md: '1 1 calc(33.333% - 16px)' } }}>
          <Stack spacing={3}>
            {/* Avatar */}
            <Card>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h6" gutterBottom>
                  프로필 사진
                </Typography>
                <Box position="relative" display="inline-block" mb={2}>
                  <Avatar
                    sx={{ width: 120, height: 120, mx: 'auto' }}
                    src={userData.avatar}
                  >
                    {userData.name.charAt(0)}
                  </Avatar>
                  <IconButton
                    sx={{
                      position: 'absolute',
                      bottom: 0,
                      right: 0,
                      bgcolor: 'primary.main',
                      '&:hover': { bgcolor: 'primary.dark' },
                    }}
                    size="small"
                    onClick={handleAvatarUpload}
                  >
                    <CameraIcon sx={{ color: 'white', fontSize: 20 }} />
                  </IconButton>
                </Box>
                <Typography variant="body2" color="textSecondary">
                  클릭하여 프로필 사진 변경
                </Typography>
              </CardContent>
            </Card>

            {/* Privacy Settings */}
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  개인정보 설정
                </Typography>
                <List dense>
                  <ListItem>
                    <ListItemText
                      primary="이메일 알림"
                      secondary="새로운 기능 및 업데이트 알림 받기"
                    />
                    <ListItemSecondaryAction>
                      <Controller
                        name="emailNotifications"
                        control={control}
                        render={({ field }) => (
                          <Switch {...field} checked={field.value} />
                        )}
                      />
                    </ListItemSecondaryAction>
                  </ListItem>
                  <ListItem>
                    <ListItemText
                      primary="프로필 공개"
                      secondary="다른 사용자가 프로필을 볼 수 있도록 허용"
                    />
                    <ListItemSecondaryAction>
                      <Controller
                        name="profileVisibility"
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
          </Stack>
        </Box>

        {/* Account Security */}
        <Box sx={{ flex: '1 1 100%' }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                계정 보안
              </Typography>
              <List>
                <ListItem>
                  <ListItemText
                    primary="비밀번호 변경"
                    secondary="정기적으로 비밀번호를 변경하여 보안을 강화하세요"
                  />
                  <ListItemSecondaryAction>
                    <Button
                      startIcon={<SecurityIcon />}
                      onClick={() => setShowPasswordDialog(true)}
                    >
                      변경
                    </Button>
                  </ListItemSecondaryAction>
                </ListItem>
                <Divider />
                <ListItem>
                  <ListItemText
                    primary="계정 로그아웃"
                    secondary="모든 기기에서 로그아웃합니다"
                  />
                  <ListItemSecondaryAction>
                    <Button
                      startIcon={<LogoutIcon />}
                      color="error"
                      onClick={handleLogout}
                    >
                      로그아웃
                    </Button>
                  </ListItemSecondaryAction>
                </ListItem>
              </List>
            </CardContent>
          </Card>
        </Box>
      </Box>

      {/* Password Change Dialog */}
      <Dialog
        open={showPasswordDialog}
        onClose={() => setShowPasswordDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>비밀번호 변경</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              label="현재 비밀번호"
              type="password"
              fullWidth
              autoFocus
            />
            <TextField label="새 비밀번호" type="password" fullWidth />
            <TextField label="새 비밀번호 확인" type="password" fullWidth />
            <Alert severity="info">
              비밀번호는 8자 이상이어야 하며, 영문자, 숫자, 특수문자를 포함해야
              합니다.
            </Alert>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowPasswordDialog(false)}>취소</Button>
          <Button onClick={handlePasswordChange} variant="contained">
            변경
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
