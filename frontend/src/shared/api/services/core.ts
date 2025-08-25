import { APIClient, SERVICE_URLS } from '../base'
import type {
  User,
  UserProfile,
  UserPreferences,
  SystemStatus,
  UsageStats,
} from '@/shared/types/api'

class CoreService extends APIClient {
  constructor() {
    super(SERVICE_URLS.CORE, 'core')
  }

  // User Management
  async getCurrentUser() {
    return this.get<UserProfile>('/api/v1/users/me')
  }

  async updateUserProfile(data: Partial<UserProfile>) {
    return this.put<UserProfile>('/api/v1/users/me', data)
  }

  async updateUserPreferences(preferences: Partial<UserPreferences>) {
    return this.patch<UserProfile>('/api/v1/users/me/preferences', preferences)
  }

  async uploadAvatar(file: File, onProgress?: (progress: number) => void) {
    return this.uploadFile<{ avatar_url: string }>(
      '/api/v1/users/me/avatar',
      file,
      onProgress,
    )
  }

  async deleteUser() {
    return this.delete<void>('/api/v1/users/me')
  }

  // Authentication
  async login(email: string, password: string) {
    return this.post<{ token: string; user: User }>('/api/v1/auth/login', {
      email,
      password,
    })
  }

  async register(data: { email: string; password: string; name: string }) {
    return this.post<{ token: string; user: User }>(
      '/api/v1/auth/register',
      data,
    )
  }

  async refreshToken() {
    return this.post<{ token: string }>('/api/v1/auth/refresh')
  }

  async logout() {
    return this.post<void>('/api/v1/auth/logout')
  }

  async forgotPassword(email: string) {
    return this.post<void>('/api/v1/auth/forgot-password', { email })
  }

  async resetPassword(token: string, password: string) {
    return this.post<void>('/api/v1/auth/reset-password', { token, password })
  }

  async changePassword(currentPassword: string, newPassword: string) {
    return this.post<void>('/api/v1/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    })
  }

  // System Status
  async getSystemStatus() {
    return this.get<SystemStatus>('/api/v1/system/status')
  }

  async getSystemHealth() {
    return this.get<{ status: 'healthy' | 'unhealthy' }>(
      '/api/v1/system/health',
    )
  }

  // Analytics
  async getUsageStats(period: 'day' | 'week' | 'month' | 'year' = 'week') {
    return this.get<UsageStats>(`/api/v1/analytics/usage?period=${period}`)
  }

  async getUserStats() {
    return this.get<{
      total_projects: number
      total_scripts: number
      total_generations: number
      usage_hours: number
      join_date: string
    }>('/api/v1/analytics/user')
  }

  // Data Management
  async exportUserData(format: 'json' | 'csv' = 'json') {
    const response = await this.get<{ download_url: string }>(
      `/api/v1/data/export?format=${format}`,
    )
    return response
  }

  async importUserData(file: File, onProgress?: (progress: number) => void) {
    return this.uploadFile<{ imported_count: number }>(
      '/api/v1/data/import',
      file,
      onProgress,
    )
  }

  async createBackup() {
    return this.post<{ backup_id: string; created_at: string }>(
      '/api/v1/data/backup',
    )
  }

  async getBackups() {
    return this.get<
      Array<{
        id: string
        created_at: string
        size: number
        status: 'completed' | 'failed'
      }>
    >('/api/v1/data/backups')
  }

  async restoreBackup(backupId: string) {
    return this.post<void>(`/api/v1/data/backups/${backupId}/restore`)
  }

  // Settings
  async getSettings() {
    return this.get<Record<string, any>>('/api/v1/settings')
  }

  async updateSettings(settings: Record<string, any>) {
    return this.put<Record<string, any>>('/api/v1/settings', settings)
  }

  // Notifications
  async getNotifications(page = 1, limit = 20) {
    return this.get<{
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
    }>(`/api/v1/notifications?page=${page}&limit=${limit}`)
  }

  async markNotificationRead(notificationId: string) {
    return this.patch<void>(`/api/v1/notifications/${notificationId}/read`)
  }

  async markAllNotificationsRead() {
    return this.post<void>('/api/v1/notifications/read-all')
  }

  async deleteNotification(notificationId: string) {
    return this.delete<void>(`/api/v1/notifications/${notificationId}`)
  }

  // WebSocket connections
  createNotificationSocket() {
    return this.createWebSocket('/ws/notifications')
  }

  createSystemSocket() {
    return this.createWebSocket('/ws/system')
  }
}

export const coreService = new CoreService()
