import { Routes, Route, Navigate } from 'react-router-dom'
import { Suspense, lazy } from 'react'
import { CircularProgress, Box } from '@mui/material'

import { AppLayout } from '@/shared/ui/layouts/AppLayout'

// Lazy load pages
const DashboardPage = lazy(() => import('@/pages/dashboard'))
const ProjectDetailPage = lazy(() => import('@/pages/project-detail'))
const NotFoundPage = lazy(() => import('@/pages/not-found'))

// Loading component
const PageLoader = () => (
  <Box
    display="flex"
    justifyContent="center"
    alignItems="center"
    minHeight="50vh"
  >
    <CircularProgress />
  </Box>
)

export const AppRouter = () => {
  return (
    <AppLayout>
      <Suspense fallback={<PageLoader />}>
        <Routes>
          <Route path="/" element={<Navigate to="/projects" replace />} />
          <Route path="/dashboard" element={<Navigate to="/projects" replace />} />
          <Route path="/projects" element={<DashboardPage />} />
          <Route path="/projects/:projectId" element={<ProjectDetailPage />} />
          <Route path="/404" element={<NotFoundPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </Suspense>
    </AppLayout>
  )
}
