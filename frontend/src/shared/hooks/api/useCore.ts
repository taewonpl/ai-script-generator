import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { UseQueryOptions } from '@tanstack/react-query'
import { coreService } from '@/shared/api/services/core'
import type {
  UserProfile,
  UserPreferences,
  SystemStatus,
  UsageStats,
} from '@/shared/types/api'

// Query Keys
export const coreKeys = {
  all: ['core'] as const,
  user: () => [...coreKeys.all, 'user'] as const,
  userProfile: () => [...coreKeys.user(), 'profile'] as const,
  systemStatus: () => [...coreKeys.all, 'system', 'status'] as const,
  systemHealth: () => [...coreKeys.all, 'system', 'health'] as const,
  analytics: () => [...coreKeys.all, 'analytics'] as const,
  usageStats: (period?: string) =>
    [...coreKeys.analytics(), 'usage', { period }] as const,
  userStats: () => [...coreKeys.analytics(), 'user'] as const,
  settings: () => [...coreKeys.all, 'settings'] as const,
  notifications: () => [...coreKeys.all, 'notifications'] as const,
  notificationsList: (page: number, limit: number) =>
    [...coreKeys.notifications(), 'list', { page, limit }] as const,
  backups: () => [...coreKeys.all, 'backups'] as const,
}

// Current User Hook
export function useCurrentUser(
  options?: Omit<UseQueryOptions<UserProfile>, 'queryKey' | 'queryFn'>,
) {
  return useQuery({
    queryKey: coreKeys.userProfile(),
    queryFn: () => coreService.getCurrentUser(),
    staleTime: 1000 * 60 * 10, // 10 minutes
    gcTime: 1000 * 60 * 60, // 1 hour
    retry: (failureCount, error: any) => {
      // Don't retry on 401/403 errors (auth issues)
      if (error?.status === 401 || error?.status === 403) {
        return false
      }
      return failureCount < 3
    },
    ...options,
  })
}

// System Status Hook
export function useSystemStatus(
  options?: Omit<UseQueryOptions<SystemStatus>, 'queryKey' | 'queryFn'>,
) {
  return useQuery({
    queryKey: coreKeys.systemStatus(),
    queryFn: () => coreService.getSystemStatus(),
    staleTime: 1000 * 10, // 10 seconds
    gcTime: 1000 * 60 * 5, // 5 minutes
    refetchInterval: 10000, // Refresh every 10 seconds
    ...options,
  })
}

// System Health Hook
export function useSystemHealth(
  options?: Omit<
    UseQueryOptions<{ status: 'healthy' | 'unhealthy' }>,
    'queryKey' | 'queryFn'
  >,
) {
  return useQuery({
    queryKey: coreKeys.systemHealth(),
    queryFn: () => coreService.getSystemHealth(),
    staleTime: 1000 * 30, // 30 seconds
    gcTime: 1000 * 60 * 5, // 5 minutes
    refetchInterval: 30000, // Refresh every 30 seconds
    ...options,
  })
}

// Usage Stats Hook
export function useUsageStats(
  period: 'day' | 'week' | 'month' | 'year' = 'week',
  options?: Omit<UseQueryOptions<UsageStats>, 'queryKey' | 'queryFn'>,
) {
  return useQuery({
    queryKey: coreKeys.usageStats(period),
    queryFn: () => coreService.getUsageStats(period),
    staleTime: 1000 * 60 * 5, // 5 minutes
    gcTime: 1000 * 60 * 30, // 30 minutes
    ...options,
  })
}

// User Stats Hook
interface UserStats {
  total_projects: number
  total_scripts: number
  total_generations: number
  usage_hours: number
  join_date: string
}

export function useUserStats(
  options?: Omit<UseQueryOptions<UserStats>, 'queryKey' | 'queryFn'>,
) {
  return useQuery({
    queryKey: coreKeys.userStats(),
    queryFn: () => coreService.getUserStats(),
    staleTime: 1000 * 60 * 5, // 5 minutes
    gcTime: 1000 * 60 * 30, // 30 minutes
    ...options,
  })
}

// Settings Hook
export function useSettings(
  options?: Omit<
    UseQueryOptions<Record<string, unknown>>,
    'queryKey' | 'queryFn'
  >,
) {
  return useQuery({
    queryKey: coreKeys.settings(),
    queryFn: () => coreService.getSettings(),
    staleTime: 1000 * 60 * 10, // 10 minutes
    gcTime: 1000 * 60 * 60, // 1 hour
    ...options,
  })
}

// Notifications Hook
interface NotificationResponse {
  notifications: Array<{
    id: string
    title: string
    message: string
    type: 'info' | 'warning' | 'error' | 'success'
    read: boolean
    created_at: string
  }>
  total: number
  unread_count: number
}

export function useNotifications(
  page = 1,
  limit = 20,
  options?: Omit<UseQueryOptions<NotificationResponse>, 'queryKey' | 'queryFn'>,
) {
  return useQuery({
    queryKey: coreKeys.notificationsList(page, limit),
    queryFn: () => coreService.getNotifications(page, limit),
    staleTime: 1000 * 30, // 30 seconds
    gcTime: 1000 * 60 * 10, // 10 minutes
    ...options,
  })
}

// Backups Hook
interface BackupInfo {
  id: string
  created_at: string
  size: number
  status: 'completed' | 'failed'
}

export function useBackups(
  options?: Omit<UseQueryOptions<BackupInfo[]>, 'queryKey' | 'queryFn'>,
) {
  return useQuery({
    queryKey: coreKeys.backups(),
    queryFn: () => coreService.getBackups(),
    staleTime: 1000 * 60 * 5, // 5 minutes
    gcTime: 1000 * 60 * 30, // 30 minutes
    ...options,
  })
}

// Authentication Mutations
export function useLogin() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      coreService.login(email, password),
    onSuccess: response => {
      // Store token
      localStorage.setItem('authToken', response.token)

      // Cache user data
      queryClient.setQueryData(coreKeys.userProfile(), response.user)

      // Invalidate all queries to refresh with authenticated state
      queryClient.invalidateQueries()
    },
  })
}

export function useRegister() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: { email: string; password: string; name: string }) =>
      coreService.register(data),
    onSuccess: response => {
      // Store token
      localStorage.setItem('authToken', response.token)

      // Cache user data
      queryClient.setQueryData(coreKeys.userProfile(), response.user)

      // Invalidate all queries
      queryClient.invalidateQueries()
    },
  })
}

export function useLogout() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => coreService.logout(),
    onSuccess: () => {
      // Clear token
      localStorage.removeItem('authToken')

      // Clear all cached data
      queryClient.clear()
    },
    onError: () => {
      // Even if logout API fails, clear local data
      localStorage.removeItem('authToken')
      queryClient.clear()
    },
  })
}

export function useChangePassword() {
  return useMutation({
    mutationFn: ({
      currentPassword,
      newPassword,
    }: {
      currentPassword: string
      newPassword: string
    }) => coreService.changePassword(currentPassword, newPassword),
  })
}

// Profile Management Mutations
export function useUpdateUserProfile() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: Partial<UserProfile>) =>
      coreService.updateUserProfile(data),
    onMutate: async newProfileData => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: coreKeys.userProfile() })

      // Snapshot previous value
      const previousProfile = queryClient.getQueryData(coreKeys.userProfile())

      // Optimistically update
      queryClient.setQueryData(coreKeys.userProfile(), (old: any) => {
        if (!old) return old
        return { ...old, ...newProfileData }
      })

      return { previousProfile }
    },
    onError: (_, __, context) => {
      // Rollback on error
      if (context?.previousProfile) {
        queryClient.setQueryData(
          coreKeys.userProfile(),
          context.previousProfile,
        )
      }
    },
    onSettled: () => {
      // Always refetch after mutation
      queryClient.invalidateQueries({ queryKey: coreKeys.userProfile() })
    },
  })
}

export function useUpdateUserPreferences() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (preferences: Partial<UserPreferences>) =>
      coreService.updateUserPreferences(preferences),
    onSuccess: updatedProfile => {
      // Update user profile cache
      queryClient.setQueryData(coreKeys.userProfile(), updatedProfile)
    },
  })
}

export function useUploadAvatar() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      file,
      onProgress,
    }: {
      file: File
      onProgress?: (progress: number) => void
    }) => coreService.uploadAvatar(file, onProgress),
    onSuccess: response => {
      // Update user profile with new avatar URL
      queryClient.setQueryData(coreKeys.userProfile(), (old: any) => {
        if (!old) return old
        return { ...old, avatar: response.avatar_url }
      })
    },
  })
}

// Settings Mutations
export function useUpdateSettings() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (settings: Record<string, any>) =>
      coreService.updateSettings(settings),
    onSuccess: updatedSettings => {
      // Update settings cache
      queryClient.setQueryData(coreKeys.settings(), updatedSettings)
    },
  })
}

// Notifications Mutations
export function useMarkNotificationRead() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (notificationId: string) =>
      coreService.markNotificationRead(notificationId),
    onSuccess: (_, notificationId) => {
      // Update notifications cache
      queryClient.setQueriesData(
        { queryKey: coreKeys.notifications() },
        (old: any) => {
          if (!old) return old
          return {
            ...old,
            notifications: old.notifications.map((notif: any) =>
              notif.id === notificationId ? { ...notif, read: true } : notif,
            ),
            unread_count: Math.max(0, old.unread_count - 1),
          }
        },
      )
    },
  })
}

export function useMarkAllNotificationsRead() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => coreService.markAllNotificationsRead(),
    onSuccess: () => {
      // Update all notifications as read
      queryClient.setQueriesData(
        { queryKey: coreKeys.notifications() },
        (old: any) => {
          if (!old) return old
          return {
            ...old,
            notifications: old.notifications.map((notif: any) => ({
              ...notif,
              read: true,
            })),
            unread_count: 0,
          }
        },
      )
    },
  })
}

export function useDeleteNotification() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (notificationId: string) =>
      coreService.deleteNotification(notificationId),
    onSuccess: (_, notificationId) => {
      // Remove notification from cache
      queryClient.setQueriesData(
        { queryKey: coreKeys.notifications() },
        (old: any) => {
          if (!old) return old
          return {
            ...old,
            notifications: old.notifications.filter(
              (notif: any) => notif.id !== notificationId,
            ),
            total: old.total - 1,
          }
        },
      )
    },
  })
}

// Data Management Mutations
export function useExportUserData() {
  return useMutation({
    mutationFn: (format: 'json' | 'csv' = 'json') =>
      coreService.exportUserData(format),
  })
}

export function useImportUserData() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      file,
      onProgress,
    }: {
      file: File
      onProgress?: (progress: number) => void
    }) => coreService.importUserData(file, onProgress),
    onSuccess: () => {
      // Invalidate all data after import
      queryClient.invalidateQueries()
    },
  })
}

export function useCreateBackup() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => coreService.createBackup(),
    onSuccess: () => {
      // Invalidate backups list
      queryClient.invalidateQueries({ queryKey: coreKeys.backups() })
    },
  })
}

export function useRestoreBackup() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (backupId: string) => coreService.restoreBackup(backupId),
    onSuccess: () => {
      // Invalidate all data after restore
      queryClient.invalidateQueries()
    },
  })
}

export function useDeleteUser() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => coreService.deleteUser(),
    onSuccess: () => {
      // Clear all data and redirect to login
      localStorage.removeItem('authToken')
      queryClient.clear()
      window.location.href = '/login'
    },
  })
}
