import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { ThemeProvider } from '@mui/material/styles'

import ProjectListPage from './index'
import { theme } from '@/shared/ui/theme'

// Mock the API
vi.mock('@/shared/api/client', () => ({
  projectApi: {
    get: vi.fn().mockResolvedValue({
      data: {
        data: [
          {
            id: '1',
            name: 'Test Project',
            type: 'drama',
            status: 'active',
            description: 'Test description',
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          },
        ],
      },
    }),
  },
}))

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  })

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <BrowserRouter>{children}</BrowserRouter>
      </ThemeProvider>
    </QueryClientProvider>
  )
}

describe('ProjectListPage', () => {
  it('renders project list title', async () => {
    render(<ProjectListPage />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText('Projects')).toBeInTheDocument()
    })
  })

  it('renders search input', async () => {
    render(<ProjectListPage />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(
        screen.getByPlaceholderText('Search projects...'),
      ).toBeInTheDocument()
    })
  })

  it('renders new project button', async () => {
    render(<ProjectListPage />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText('New Project')).toBeInTheDocument()
    })
  })
})
