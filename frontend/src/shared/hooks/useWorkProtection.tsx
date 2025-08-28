/**
 * Work protection hook for preventing navigation during critical operations
 * Shows confirmation dialog and provides background task continuation options
 */

import { useEffect, useCallback, useState, createContext, useContext } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Alert,
  Stack,
  Box,
  Link,
} from '@mui/material'
import {
  Warning as WarningIcon,
  PlayArrow as ContinueIcon,
  Link as LinkIcon,
} from '@mui/icons-material'

import { useToastHelpers } from '@/shared/ui/components/toast'

interface ActiveWork {
  id: string
  type: 'generation' | 'commit' | 'save' | 'upload'
  description: string
  canContinueInBackground: boolean
  reconnectPath?: string
  scopeId?: string
}

interface WorkProtectionContextType {
  registerWork: (work: ActiveWork) => void
  unregisterWork: (workId: string) => void
  isWorkActive: (type?: string) => boolean
  getActiveWork: () => ActiveWork[]
}

const WorkProtectionContext = createContext<WorkProtectionContextType | null>(null)

export function useWorkProtection() {
  const context = useContext(WorkProtectionContext)
  if (!context) {
    throw new Error('useWorkProtection must be used within a WorkProtectionProvider')
  }
  return context
}

/**
 * Provider component for work protection
 */
export function WorkProtectionProvider({ children }: { children: React.ReactNode }) {
  const [activeWork, setActiveWork] = useState<Map<string, ActiveWork>>(new Map())
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false)
  const [pendingNavigation, setPendingNavigation] = useState<string | null>(null)
  const [backgroundWork, setBackgroundWork] = useState<ActiveWork[]>([])
  
  const location = useLocation()
  const navigate = useNavigate()
  const { showSuccess, showInfo } = useToastHelpers()

  const registerWork = useCallback((work: ActiveWork) => {
    setActiveWork(prev => new Map(prev.set(work.id, work)))
    console.log(`🛡️ Work protection registered: ${work.id} (${work.type})`)
  }, [])

  const unregisterWork = useCallback((workId: string) => {
    setActiveWork(prev => {
      const next = new Map(prev)
      const removed = next.delete(workId)
      if (removed) {
        console.log(`🛡️ Work protection unregistered: ${workId}`)
      }
      return next
    })
    
    // Remove from background work as well
    setBackgroundWork(prev => prev.filter(w => w.id !== workId))
  }, [])

  const isWorkActive = useCallback((type?: string) => {
    if (!type) return activeWork.size > 0
    
    for (const work of activeWork.values()) {
      if (work.type === type) return true
    }
    return false
  }, [activeWork])

  const getActiveWork = useCallback(() => {
    return Array.from(activeWork.values())
  }, [activeWork])

  // Handle navigation protection
  useEffect(() => {
    if (activeWork.size === 0) return

    const handleBeforeUnload = (event: BeforeUnloadEvent) => {
      // Browser-level protection for page reload/close
      const message = '진행 중인 작업이 있습니다. 페이지를 떠나시겠습니까?'
      event.preventDefault()
      event.returnValue = message
      return message
    }

    const handlePopState = (event: PopStateEvent) => {
      // Handle browser back/forward buttons
      event.preventDefault()
      const currentWork = Array.from(activeWork.values())
      
      if (currentWork.some(w => w.canContinueInBackground)) {
        // Show continuation dialog
        setPendingNavigation(window.location.pathname)
        setConfirmDialogOpen(true)
      }
    }

    window.addEventListener('beforeunload', handleBeforeUnload)
    window.addEventListener('popstate', handlePopState)

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload)
      window.removeEventListener('popstate', handlePopState)
    }
  }, [activeWork])

  // Handle route changes within the app
  useEffect(() => {
    if (activeWork.size === 0) return

    // This effect runs when location changes
    const currentWork = Array.from(activeWork.values())
    const backgroundCapableWork = currentWork.filter(w => w.canContinueInBackground)
    
    if (backgroundCapableWork.length > 0) {
      console.log(`🛡️ Route change with active work: ${backgroundCapableWork.length} can continue in background`)
      
      // Move to background and show notification
      setBackgroundWork(prev => [...prev, ...backgroundCapableWork])
      
      backgroundCapableWork.forEach(work => {
        showInfo(
          `${work.description} continues in background`,
          {
            action: work.reconnectPath ? (
              <Button
                size="small"
                startIcon={<LinkIcon />}
                onClick={() => navigate(work.reconnectPath!)}
                sx={{ ml: 1 }}
              >
                Reconnect
              </Button>
            ) : undefined,
          }
        )
      })
    }
  }, [location.pathname])

  const handleConfirmNavigation = useCallback(() => {
    const currentWork = Array.from(activeWork.values())
    const backgroundCapableWork = currentWork.filter(w => w.canContinueInBackground)
    
    // Move work to background
    setBackgroundWork(prev => [...prev, ...backgroundCapableWork])
    
    // Show continuation notifications
    backgroundCapableWork.forEach(work => {
      showSuccess(
        `${work.description} continues in background`,
        {
          action: work.reconnectPath ? (
            <Link
              component="button"
              onClick={() => navigate(work.reconnectPath!)}
              sx={{ ml: 1, textDecoration: 'underline', cursor: 'pointer' }}
            >
              Reconnect
            </Link>
          ) : undefined,
        }
      )
    })

    setConfirmDialogOpen(false)
    setPendingNavigation(null)
    
    if (pendingNavigation) {
      navigate(pendingNavigation)
    }
  }, [activeWork, pendingNavigation, navigate, showSuccess])

  const handleCancelNavigation = useCallback(() => {
    setConfirmDialogOpen(false)
    setPendingNavigation(null)
    
    // Stay on current page
    window.history.pushState(null, '', location.pathname)
  }, [location.pathname])

  const contextValue: WorkProtectionContextType = {
    registerWork,
    unregisterWork,
    isWorkActive,
    getActiveWork,
  }

  return (
    <WorkProtectionContext.Provider value={contextValue}>
      {children}
      
      {/* Work Protection Dialog */}
      <Dialog
        open={confirmDialogOpen}
        onClose={handleCancelNavigation}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <WarningIcon color="warning" />
          <Typography variant="h6" component="span">
            진행 중인 작업 확인
          </Typography>
        </DialogTitle>
        
        <DialogContent>
          <Stack spacing={2}>
            <Alert severity="warning">
              <Typography variant="body2">
                현재 진행 중인 작업이 있습니다. 페이지를 떠나면 작업이 백그라운드에서 계속됩니다.
              </Typography>
            </Alert>

            <Box>
              <Typography variant="subtitle2" gutterBottom>
                진행 중인 작업:
              </Typography>
              {Array.from(activeWork.values()).map(work => (
                <Box key={work.id} sx={{ pl: 2, py: 0.5 }}>
                  <Typography variant="body2">
                    • {work.description}
                    {work.canContinueInBackground && (
                      <Typography component="span" variant="caption" color="success.main" sx={{ ml: 1 }}>
                        (백그라운드 계속 진행 가능)
                      </Typography>
                    )}
                  </Typography>
                </Box>
              ))}
            </Box>
          </Stack>
        </DialogContent>

        <DialogActions>
          <Button onClick={handleCancelNavigation}>
            머물기
          </Button>
          <Button
            onClick={handleConfirmNavigation}
            variant="contained"
            startIcon={<ContinueIcon />}
          >
            백그라운드에서 계속하고 이동
          </Button>
        </DialogActions>
      </Dialog>

      {/* Background Work Notification */}
      {backgroundWork.length > 0 && (
        <Box
          sx={{
            position: 'fixed',
            bottom: 16,
            right: 16,
            zIndex: 1400,
            maxWidth: 400,
          }}
        >
          <Alert
            severity="info"
            onClose={() => setBackgroundWork([])}
            sx={{ mb: 1 }}
          >
            <Typography variant="body2">
              {backgroundWork.length}개 작업이 백그라운드에서 진행 중입니다
            </Typography>
            <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
              {backgroundWork.map(work => (
                work.reconnectPath && (
                  <Button
                    key={work.id}
                    size="small"
                    onClick={() => navigate(work.reconnectPath!)}
                  >
                    {work.description} 확인
                  </Button>
                )
              ))}
            </Stack>
          </Alert>
        </Box>
      )}
    </WorkProtectionContext.Provider>
  )
}

/**
 * Hook for registering specific work types with protection
 */
export function useWorkProtectionFor(
  workType: ActiveWork['type'],
  isActive: boolean,
  options: Partial<Pick<ActiveWork, 'description' | 'canContinueInBackground' | 'reconnectPath' | 'scopeId'>> = {}
) {
  const { registerWork, unregisterWork } = useWorkProtection()
  const workId = `${workType}-${Date.now()}`

  useEffect(() => {
    if (isActive) {
      const work: ActiveWork = {
        id: workId,
        type: workType,
        description: options.description || `${workType} in progress`,
        canContinueInBackground: options.canContinueInBackground ?? false,
        reconnectPath: options.reconnectPath,
        scopeId: options.scopeId,
      }
      
      registerWork(work)
      
      return () => {
        unregisterWork(workId)
      }
    }
  }, [isActive, workType, registerWork, unregisterWork, workId, options])

  return { workId }
}

/**
 * Higher-order component for automatic work protection
 */
export function withWorkProtection<P extends object>(
  Component: React.ComponentType<P>,
  workOptions: Partial<ActiveWork>
) {
  return function ProtectedComponent(props: P) {
    return (
      <WorkProtectionProvider>
        <Component {...props} />
      </WorkProtectionProvider>
    )
  }
}