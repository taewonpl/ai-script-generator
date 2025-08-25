import { z } from 'zod'

// Common validation schemas
export const projectCreateSchema = z.object({
  name: z
    .string()
    .min(1, 'Project name is required')
    .max(100, 'Project name is too long'),
  type: z.enum(['drama', 'comedy', 'documentary', 'other']),
  description: z.string().max(500, 'Description is too long').optional(),
})

export const episodeCreateSchema = z.object({
  title: z
    .string()
    .min(1, 'Episode title is required')
    .max(100, 'Episode title is too long'),
  description: z.string().max(500, 'Description is too long').optional(),
  order: z.number().int().positive().optional(),
})

export const generationRequestSchema = z.object({
  project_id: z.string().min(1, 'Project ID is required'),
  episode_id: z.string().optional(),
  prompt: z
    .string()
    .min(10, 'Prompt must be at least 10 characters')
    .max(2000, 'Prompt is too long'),
  model: z.enum(['gpt-4', 'claude-3']).optional(),
  max_tokens: z.number().int().min(100).max(4000).optional(),
  temperature: z.number().min(0).max(2).optional(),
})

// Type exports
export type ProjectCreateFormData = z.infer<typeof projectCreateSchema>
export type EpisodeCreateFormData = z.infer<typeof episodeCreateSchema>
export type GenerationRequestFormData = z.infer<typeof generationRequestSchema>

/**
 * Validate email format
 */
export const isValidEmail = (email: string): boolean => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRegex.test(email)
}

/**
 * Validate URL format
 */
export const isValidUrl = (url: string): boolean => {
  try {
    new URL(url)
    return true
  } catch {
    return false
  }
}
