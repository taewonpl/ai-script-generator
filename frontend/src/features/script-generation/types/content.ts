/**
 * Content type definitions and helper functions for script generation
 * Handles both string and object content types from backend SSE
 */

/**
 * Preview content can be either a string or an object with markdown field
 * Supports both legacy string format and new structured format from Episode.script
 */
export type PreviewContent =
  | string
  | { markdown: string; tokens?: number }
  | null
  | undefined

/**
 * Converts preview content to markdown text string
 * Handles both string and object formats safely
 *
 * @param content - Preview content in either format
 * @returns Markdown text string
 */
export function toMarkdownText(content: PreviewContent): string {
  if (typeof content === 'string') {
    return content
  }

  if (content && typeof content === 'object' && 'markdown' in content) {
    return content.markdown
  }

  return ''
}

/**
 * Checks if content is in object format with markdown field
 *
 * @param content - Content to check
 * @returns True if content is object with markdown field
 */
export function isMarkdownObject(
  content: PreviewContent,
): content is { markdown: string; tokens?: number } {
  return (
    typeof content === 'object' && content !== null && 'markdown' in content
  )
}

/**
 * Safely extracts markdown text from any content format
 * Provides fallback for null/undefined values
 *
 * @param content - Content to extract from (can be null/undefined)
 * @param fallback - Fallback text if content is empty
 * @returns Extracted markdown text or fallback
 */
export function extractMarkdown(
  content: PreviewContent,
  fallback = '',
): string {
  if (!content) {
    return fallback
  }

  return toMarkdownText(content)
}
