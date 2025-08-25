import { Box, Typography, Paper } from '@mui/material'
import { useParams } from 'react-router-dom'

const EpisodeDetailPage = () => {
  const { projectId, episodeId } = useParams()

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Episode Details
      </Typography>
      <Paper sx={{ p: 3 }}>
        <Typography>Project ID: {projectId}</Typography>
        <Typography>Episode ID: {episodeId}</Typography>
        <Typography variant="body2" color="text.secondary" mt={2}>
          Episode detail view coming soon...
        </Typography>
      </Paper>
    </Box>
  )
}

export default EpisodeDetailPage
