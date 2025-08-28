import { useState, useCallback } from 'react'
import { Box, Typography, Paper, Stack, Divider } from '@mui/material'
import { useParams } from 'react-router-dom'

import { CommitButton } from '@/features/episode/components/CommitButton'
import { CommitStatusBar } from '@/features/episode/components/CommitStatusBar'
// import { useToastHelpers } from '@/shared/ui/components/toast' // Reserved for future use

const EpisodeDetailPage = () => {
  const { projectId, episodeId } = useParams()
  // const { showSuccess } = useToastHelpers() // Reserved for future use
  
  // Mock states for demonstration (in real implementation, these would come from episode editor state)
  const [isGenerating] = useState(false) // SSE generation in progress
  const [hasUnsavedChanges] = useState(false) // Unsaved changes in editor

  const handleCommitSuccess = useCallback(
    (commitId: string, timestamp: string) => {
      console.log('Commit successful:', { commitId, timestamp })
      // In real implementation, this would update the episode editor state
    },
    []
  )

  const handleCommitError = useCallback((error: any) => {
    console.error('Commit failed:', error)
  }, [])

  if (!projectId || !episodeId) {
    return (
      <Box>
        <Typography color="error">Missing project or episode ID</Typography>
      </Box>
    )
  }

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Episode Editor
      </Typography>
      
      <Stack spacing={3}>
        {/* Episode Info */}
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Episode Information
          </Typography>
          <Typography>Project ID: {projectId}</Typography>
          <Typography>Episode ID: {episodeId}</Typography>
        </Paper>

        {/* Commit System Demo */}
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Episode Commit System
          </Typography>
          
          <Stack spacing={2}>
            {/* Commit Status Bar */}
            <CommitStatusBar 
              episodeId={episodeId}
              language="kr"
            />
            
            <Divider />
            
            {/* Commit Button */}
            <Box display="flex" justifyContent="flex-end">
              <CommitButton
                projectId={projectId}
                episodeId={episodeId}
                isGenerating={isGenerating}
                hasUnsavedChanges={hasUnsavedChanges}
                onCommitSuccess={handleCommitSuccess}
                onCommitError={handleCommitError}
                language="kr"
              />
            </Box>
            
            {/* Demo Controls */}
            <Typography variant="caption" color="text.secondary">
              키보드 단축키: Cmd/Ctrl + Enter로 확정
            </Typography>
          </Stack>
        </Paper>
      </Stack>
    </Box>
  )
}

export default EpisodeDetailPage
