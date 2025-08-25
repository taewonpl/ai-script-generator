/**
 * Zod validation schemas for forms
 */

import { z } from 'zod'

// Common validation patterns
export const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
export const PHONE_REGEX = /^[0-9-+\s()]+$/
export const URL_REGEX = /^https?:\/\/.+/

// Common field validators
export const requiredString = (message = '필수 입력 항목입니다') =>
  z.string().min(1, message)

export const optionalString = z.string().optional()

export const email = (message = '유효한 이메일 주소를 입력해주세요') =>
  z.string().regex(EMAIL_REGEX, message)

export const phone = (message = '유효한 전화번호를 입력해주세요') =>
  z.string().regex(PHONE_REGEX, message)

export const url = (message = '유효한 URL을 입력해주세요') =>
  z.string().regex(URL_REGEX, message)

// Project validation schemas
export const ProjectCreateSchema = z
  .object({
    name: requiredString('프로젝트 이름을 입력해주세요')
      .min(2, '프로젝트 이름은 최소 2자 이상이어야 합니다')
      .max(100, '프로젝트 이름은 최대 100자까지 입력할 수 있습니다'),

    type: z.enum(
      [
        'drama',
        'comedy',
        'action',
        'romance',
        'thriller',
        'documentary',
        'animation',
      ] as const,
      {
        message: '프로젝트 타입을 선택해주세요',
      },
    ),

    description: optionalString.refine(val => !val || val.length <= 1000, {
      message: '설명은 최대 1000자까지 입력할 수 있습니다',
    }),

    genre: optionalString,

    targetAudience: z
      .enum(['all', 'kids', 'teens', 'adults'] as const, {
        message: '대상 연령을 선택해주세요',
      })
      .optional(),

    budget: z.number().min(0, '예산은 0 이상이어야 합니다').optional(),

    startDate: z.date().optional(),

    endDate: z.date().optional(),

    tags: z.array(z.string()).optional(),

    isPublic: z.boolean().default(false),

    collaborators: z.array(z.string()).optional(),
  })
  .refine(
    data => !data.startDate || !data.endDate || data.startDate <= data.endDate,
    {
      message: '종료 날짜는 시작 날짜보다 늦어야 합니다',
      path: ['endDate'],
    },
  )

export const ProjectEditSchema = ProjectCreateSchema.extend({
  id: requiredString('프로젝트 ID가 필요합니다'),

  status: z
    .enum(
      ['planning', 'in_progress', 'completed', 'on_hold', 'cancelled'] as const,
      {
        message: '프로젝트 상태를 선택해주세요',
      },
    )
    .optional(),

  progressPercentage: z
    .number()
    .min(0, '진행률은 0% 이상이어야 합니다')
    .max(100, '진행률은 100% 이하여야 합니다')
    .optional(),
})

// Episode validation schemas
export const EpisodeCreateSchema = z.object({
  projectId: requiredString('프로젝트 ID가 필요합니다'),

  title: requiredString('에피소드 제목을 입력해주세요')
    .min(2, '에피소드 제목은 최소 2자 이상이어야 합니다')
    .max(200, '에피소드 제목은 최대 200자까지 입력할 수 있습니다'),

  // number 필드는 서버에서 자동 할당되므로 제거

  seasonNumber: z
    .number()
    .int('시즌 번호는 정수여야 합니다')
    .min(1, '시즌 번호는 1 이상이어야 합니다')
    .optional(),

  description: optionalString.refine(val => !val || val.length <= 2000, {
    message: '설명은 최대 2000자까지 입력할 수 있습니다',
  }),

  duration: z
    .number()
    .min(1, '런타임은 1분 이상이어야 합니다')
    .max(600, '런타임은 600분(10시간) 이하여야 합니다')
    .optional(),

  airDate: z.date().optional(),

  writer: optionalString,
  director: optionalString,

  characters: z.array(z.string()).optional(),

  locations: z.array(z.string()).optional(),

  mood: z
    .enum(
      [
        'light',
        'serious',
        'dramatic',
        'comedic',
        'suspenseful',
        'romantic',
      ] as const,
      {
        message: '에피소드 무드를 선택해주세요',
      },
    )
    .optional(),

  themes: z.array(z.string()).optional(),

  notes: optionalString.refine(val => !val || val.length <= 1000, {
    message: '노트는 최대 1000자까지 입력할 수 있습니다',
  }),
})

export const EpisodeEditSchema = EpisodeCreateSchema.extend({
  id: requiredString('에피소드 ID가 필요합니다'),

  status: z
    .enum(
      [
        'draft',
        'outline',
        'first_draft',
        'revision',
        'final',
        'approved',
      ] as const,
      {
        message: '에피소드 상태를 선택해주세요',
      },
    )
    .optional(),

  version: z.number().int().min(1).optional(),

  lastModified: z.date().optional(),
})

// User/Profile schemas
export const UserProfileSchema = z.object({
  name: requiredString('이름을 입력해주세요')
    .min(2, '이름은 최소 2자 이상이어야 합니다')
    .max(50, '이름은 최대 50자까지 입력할 수 있습니다'),

  email: email(),

  phone: phone().optional(),

  bio: optionalString.refine(val => !val || val.length <= 500, {
    message: '소개는 최대 500자까지 입력할 수 있습니다',
  }),

  website: url().optional().or(z.literal('')),

  location: optionalString,

  timezone: optionalString,

  avatar: optionalString,

  preferences: z
    .object({
      language: z.enum(['ko', 'en', 'ja', 'zh']).optional(),
      theme: z.enum(['light', 'dark', 'auto']).optional(),
      notifications: z
        .object({
          email: z.boolean().optional(),
          push: z.boolean().optional(),
          mentions: z.boolean().optional(),
        })
        .optional(),
    })
    .optional(),
})

// Export form data types
export type ProjectCreateFormData = z.infer<typeof ProjectCreateSchema>
export type ProjectEditFormData = z.infer<typeof ProjectEditSchema>
export type EpisodeCreateFormData = z.infer<typeof EpisodeCreateSchema>
export type EpisodeEditFormData = z.infer<typeof EpisodeEditSchema>
export type UserProfileFormData = z.infer<typeof UserProfileSchema>
