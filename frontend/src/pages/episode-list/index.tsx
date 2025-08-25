import { Box, Typography, Paper } from '@mui/material'
import { useParams } from 'react-router-dom'

const EpisodeListPage = () => {
  const { projectId } = useParams()

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Episodes
      </Typography>
      <Paper sx={{ p: 3 }}>
        <Typography>Project ID: {projectId}</Typography>
        <Typography variant="body2" color="text.secondary" mt={2}>
          Episode list view coming soon...
        </Typography>
      </Paper>
    </Box>
  )
}

export default EpisodeListPage
