/**
 * Commit Status Bar for Episode Editor
 * Shows last committed timestamp and commit count
 */

import { Box, Typography, Chip, Skeleton } from '@mui/material'
import {
  CheckCircle as CommittedIcon,
  Schedule as PendingIcon,
} from '@mui/icons-material'

import { useCommitStatus, formatCommitTimestamp } from '../hooks/useCommitStatus'

export interface CommitStatusBarProps {
  episodeId: string
  /** Language for display text */
  language?: 'kr' | 'en'
  /** Show in compact mode */
  compact?: boolean
}

/**
 * Status bar showing commit information for an episode
 */
export function CommitStatusBar({
  episodeId,
  language = 'kr',
  compact = false,
}: CommitStatusBarProps) {
  const { lastCommittedAt, commitCount, hasCommits, isLoading } = useCommitStatus(episodeId)

  if (isLoading) {
    return (
      <Box display="flex" alignItems="center" gap={1}>
        <Skeleton variant="rectangular" width={120} height={24} />
        <Skeleton variant="circular" width={60} height={24} />
      </Box>
    )
  }

  const statusText = hasCommits
    ? language === 'kr'
      ? `마지막 확정 · ${formatCommitTimestamp(lastCommittedAt, language)}`
      : `Last committed · ${formatCommitTimestamp(lastCommittedAt, language)}`
    : language === 'kr'
    ? '아직 확정되지 않음'
    : 'Not committed yet'

  const countText = language === 'kr' ? `${commitCount}회` : `${commitCount} times`

  return (
    <Box
      display="flex"
      alignItems="center"
      gap={1}
      sx={{
        py: compact ? 0.5 : 1,
        px: compact ? 1 : 2,
        backgroundColor: hasCommits ? 'success.light' : 'grey.100',
        borderRadius: 1,
        border: hasCommits ? '1px solid' : '1px dashed',
        borderColor: hasCommits ? 'success.main' : 'grey.400',
      }}
    >
      {/* Status Icon */}
      {hasCommits ? (
        <CommittedIcon
          color="success"
          sx={{ fontSize: compact ? 16 : 20 }}
        />
      ) : (
        <PendingIcon
          color="action"
          sx={{ fontSize: compact ? 16 : 20 }}
        />
      )}

      {/* Status Text */}
      <Typography
        variant={compact ? 'body2' : 'body1'}
        color={hasCommits ? 'success.main' : 'text.secondary'}
        sx={{ fontWeight: hasCommits ? 500 : 400 }}
      >
        {statusText}
      </Typography>

      {/* Commit Count Chip */}
      {hasCommits && (
        <Chip
          label={countText}
          size="small"
          variant="outlined"
          color="success"
          sx={{
            fontSize: compact ? 11 : 12,
            height: compact ? 20 : 24,
          }}
        />
      )}
    </Box>
  )
}

export default CommitStatusBar