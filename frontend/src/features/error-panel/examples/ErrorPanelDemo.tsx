/**
 * Demo component to test ErrorPanel implementation
 * This can be used for manual testing and proof of concept
 */

import { useState } from 'react'
import {
  Box,
  Button,
  Stack,
  Typography,
  Paper,
  FormControlLabel,
  Checkbox,
} from '@mui/material'

import { StandardErrorPanel } from '../components/StandardErrorPanel'
import { LoadingWithTimeout } from '../components/LoadingWithTimeout'
import { adaptError } from '../adapters/errorAdapter'
import type { StandardErrorFormat } from '../types/standardError'

export function ErrorPanelDemo() {
  const [currentError, setCurrentError] = useState<StandardErrorFormat | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [language, setLanguage] = useState<'en' | 'ko'>('ko')
  const [enableOfflineSimulation, setEnableOfflineSimulation] = useState(false)

  // Simulate offline mode
  const simulateOffline = () => {
    // Override navigator.onLine temporarily
    Object.defineProperty(navigator, 'onLine', {
      writable: true,
      value: !enableOfflineSimulation,
    })
  }

  const createTestError = (type: string): StandardErrorFormat => {
    // Simulate offline if enabled
    if (enableOfflineSimulation) {
      simulateOffline()
    }

    const testErrors: Record<string, any> = {
      network: new Error('Network request failed'),
      server_503: {
        response: { status: 503, data: { message: 'Service Unavailable' } },
        isAxiosError: true,
        config: { url: '/api/v1/projects', method: 'GET' },
      },
      server_500: {
        response: { 
          status: 500, 
          data: { message: 'Internal Server Error', error: { code: 'INTERNAL_ERROR' } } 
        },
        isAxiosError: true,
        config: { url: '/api/v1/generations', method: 'POST' },
      },
      validation: {
        response: { status: 400, data: { message: 'Invalid input parameters' } },
        isAxiosError: true,
        config: { url: '/api/v1/projects', method: 'POST' },
      },
      authorization: {
        response: { status: 401, data: { message: 'Unauthorized' } },
        isAxiosError: true,
        config: { url: '/api/v1/user/profile', method: 'GET' },
      },
      rate_limit: {
        response: { status: 429, data: { message: 'Too Many Requests' } },
        isAxiosError: true,
        config: { url: '/api/v1/generations', method: 'POST' },
      },
      timeout: {
        code: 'ECONNABORTED',
        message: 'timeout of 30000ms exceeded',
        isAxiosError: true,
        config: { url: '/api/v1/projects', method: 'GET' },
      },
    }

    return adaptError(testErrors[type] || new Error('Unknown error'), {
      endpoint: testErrors[type]?.config?.url,
      method: testErrors[type]?.config?.method,
      requestId: `req_${Math.random().toString(36).substring(7)}`,
      traceId: `trace_${Math.random().toString(36).substring(7)}`,
    })
  }

  const handleRetry = async () => {
    console.log('Retry button clicked')
    // Simulate retry delay
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    // Random success/failure for testing
    if (Math.random() > 0.3) {
      setCurrentError(null)
      console.log('Retry succeeded')
    } else {
      console.log('Retry failed')
      throw new Error('Retry failed')
    }
  }

  const handleDismiss = () => {
    setCurrentError(null)
  }

  const simulateLoading = (duration = 8000) => {
    setIsLoading(true)
    setTimeout(() => {
      setIsLoading(false)
    }, duration)
  }

  return (
    <Box sx={{ p: 3, maxWidth: 800, mx: 'auto' }}>
      <Typography variant="h4" gutterBottom>
        ErrorPanel Demo
      </Typography>
      
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Controls
        </Typography>
        
        <Stack spacing={2}>
          <FormControlLabel
            control={
              <Checkbox
                checked={language === 'en'}
                onChange={(e) => setLanguage(e.target.checked ? 'en' : 'ko')}
              />
            }
            label="English (unchecked = Korean)"
          />
          
          <FormControlLabel
            control={
              <Checkbox
                checked={enableOfflineSimulation}
                onChange={(e) => setEnableOfflineSimulation(e.target.checked)}
              />
            }
            label="Simulate offline mode"
          />
          
          <Stack direction="row" spacing={1} flexWrap="wrap">
            <Button 
              variant="outlined" 
              onClick={() => setCurrentError(createTestError('network'))}
            >
              Network Error
            </Button>
            <Button 
              variant="outlined" 
              onClick={() => setCurrentError(createTestError('server_503'))}
            >
              503 Error
            </Button>
            <Button 
              variant="outlined" 
              onClick={() => setCurrentError(createTestError('server_500'))}
            >
              500 Error
            </Button>
            <Button 
              variant="outlined" 
              onClick={() => setCurrentError(createTestError('validation'))}
            >
              400 Error
            </Button>
            <Button 
              variant="outlined" 
              onClick={() => setCurrentError(createTestError('authorization'))}
            >
              401 Error
            </Button>
            <Button 
              variant="outlined" 
              onClick={() => setCurrentError(createTestError('rate_limit'))}
            >
              429 Error
            </Button>
            <Button 
              variant="outlined" 
              onClick={() => setCurrentError(createTestError('timeout'))}
            >
              Timeout
            </Button>
          </Stack>
          
          <Stack direction="row" spacing={1}>
            <Button 
              variant="contained" 
              onClick={() => simulateLoading(3000)}
              disabled={isLoading}
            >
              3s Loading Test
            </Button>
            <Button 
              variant="contained" 
              onClick={() => simulateLoading(10000)}
              disabled={isLoading}
            >
              10s Loading Test
            </Button>
            <Button 
              variant="outlined" 
              color="error"
              onClick={() => setCurrentError(null)}
            >
              Clear Error
            </Button>
          </Stack>
        </Stack>
      </Paper>

      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Error Panel Display
        </Typography>
        
        <LoadingWithTimeout
          isLoading={isLoading}
          onRetry={() => simulateLoading(3000)}
          language={language}
          skeletonRows={3}
        >
          {currentError ? (
            <StandardErrorPanel
              error={currentError}
              onRetry={handleRetry}
              onDismiss={handleDismiss}
              language={language}
            />
          ) : (
            <Box sx={{ p: 4, textAlign: 'center', color: 'text.secondary' }}>
              <Typography variant="body1">
                {language === 'en' 
                  ? 'No error to display. Click a button above to test different error scenarios.'
                  : '표시할 오류가 없습니다. 위의 버튼을 클릭하여 다양한 오류 시나리오를 테스트하세요.'
                }
              </Typography>
            </Box>
          )}
        </LoadingWithTimeout>
      </Paper>

      {/* Instructions */}
      <Paper sx={{ p: 3, mt: 3, bgcolor: 'info.light', color: 'info.contrastText' }}>
        <Typography variant="h6" gutterBottom>
          Testing Instructions
        </Typography>
        <Typography variant="body2" component="div">
          <ul>
            <li><strong>Copy Details:</strong> Click the copy button and paste to see error details format</li>
            <li><strong>Retry Logic:</strong> Try retry buttons to test exponential backoff</li>
            <li><strong>Keyboard:</strong> Focus error panel and press Enter to retry, Cmd/Ctrl+C to copy</li>
            <li><strong>Loading:</strong> Test loading timeouts to see skeleton → timeout warning progression</li>
            <li><strong>Offline:</strong> Enable offline simulation to test network detection</li>
            <li><strong>i18n:</strong> Toggle English/Korean to test localization</li>
          </ul>
        </Typography>
      </Paper>
    </Box>
  )
}

export default ErrorPanelDemo