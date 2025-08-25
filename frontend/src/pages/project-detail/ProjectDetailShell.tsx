import { useMemo, useEffect } from 'react'
import {
  Box,
  Container,
  Tab,
  Tabs,
  Typography,
  Paper,
  Drawer,
  IconButton,
  Alert,
} from '@mui/material'
import CloseIcon from '@mui/icons-material/Close'
import GenerateIcon from '@mui/icons-material/AutoAwesome'
import { useSearchParams } from 'react-router-dom'

import { OverviewTab } from './tabs/OverviewTab'
import { PromptTab } from './tabs/PromptTab'
import { EpisodesTab } from './tabs/EpisodesTab'

type TabValue = 'overview' | 'prompt' | 'episodes'

const TABS = [
  { value: 'overview', label: '개요', icon: '📊' },
  { value: 'prompt', label: '시스템 프롬프트', icon: '⚙️' },
  { value: 'episodes', label: '에피소드', icon: '📝' },
] as const

interface ProjectDetailShellProps {
  projectId: string
}

export function ProjectDetailShell({ projectId }: ProjectDetailShellProps) {
  const [searchParams, setSearchParams] = useSearchParams()

  // URL 상태 동기화
  const currentTab = useMemo(() => {
    const tab = searchParams.get('tab') as TabValue
    return TABS.find(t => t.value === tab)?.value || 'overview'
  }, [searchParams])

  const isGenerateDrawerOpen = useMemo(() => {
    return searchParams.get('gen') === 'new'
  }, [searchParams])

  // 탭 변경
  const handleTabChange = (_event: React.SyntheticEvent, newTab: TabValue) => {
    const newParams = new URLSearchParams(searchParams)
    newParams.set('tab', newTab)
    setSearchParams(newParams)
  }

  // Generate Drawer 열기/닫기
  const handleOpenGenerateDrawer = () => {
    const newParams = new URLSearchParams(searchParams)
    newParams.set('gen', 'new')
    setSearchParams(newParams)
  }

  const handleCloseGenerateDrawer = () => {
    const newParams = new URLSearchParams(searchParams)
    newParams.delete('gen')
    setSearchParams(newParams)
  }

  // 키보드 네비게이션
  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
      const currentIndex = TABS.findIndex(tab => tab.value === currentTab)
      let newIndex = currentIndex

      if (event.key === 'ArrowLeft') {
        newIndex = currentIndex > 0 ? currentIndex - 1 : TABS.length - 1
      } else {
        newIndex = currentIndex < TABS.length - 1 ? currentIndex + 1 : 0
      }

      const newTab = TABS[newIndex]
      if (newTab) {
        handleTabChange(event, newTab.value)
      }
    }

    // ESC 키로 Drawer 닫기
    if (event.key === 'Escape' && isGenerateDrawerOpen) {
      handleCloseGenerateDrawer()
    }
  }

  // 브라우저 히스토리 지원 (뒤로가기로 Drawer 닫기)
  useEffect(() => {
    const handlePopState = () => {
      // 현재 URL에 gen=new가 없으면 Drawer가 닫힌 상태
      const currentParams = new URLSearchParams(window.location.search)
      if (currentParams.get('gen') !== 'new' && isGenerateDrawerOpen) {
        // 상태 동기화를 위해 searchParams 업데이트
        setSearchParams(currentParams)
      }
    }

    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [isGenerateDrawerOpen, setSearchParams])

  // 탭 컨텐츠 렌더링
  const renderTabContent = () => {
    switch (currentTab) {
      case 'overview':
        return <OverviewTab projectId={projectId} />
      case 'prompt':
        return <PromptTab projectId={projectId} />
      case 'episodes':
        return (
          <EpisodesTab
            projectId={projectId}
            onGenerateClick={handleOpenGenerateDrawer}
          />
        )
      default:
        return <OverviewTab projectId={projectId} />
    }
  }

  return (
    <Container maxWidth="xl" onKeyDown={handleKeyDown} tabIndex={-1}>
      <Box sx={{ py: 3 }}>
        {/* 프로젝트 헤더 */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="h4" component="h1" gutterBottom>
            프로젝트 상세
          </Typography>
          <Typography variant="body1" color="text.secondary">
            프로젝트 ID: {projectId}
          </Typography>
        </Box>

        {/* 탭 네비게이션 */}
        <Paper sx={{ mb: 3 }}>
          <Tabs
            value={currentTab}
            onChange={handleTabChange}
            onKeyDown={handleKeyDown}
            sx={{ borderBottom: 1, borderColor: 'divider' }}
            role="tablist"
            aria-label="프로젝트 상세 탭"
          >
            {TABS.map(tab => (
              <Tab
                key={tab.value}
                label={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <span role="img" aria-hidden="true">
                      {tab.icon}
                    </span>
                    {tab.label}
                  </Box>
                }
                value={tab.value}
                id={`tab-${tab.value}`}
                aria-controls={`tabpanel-${tab.value}`}
                role="tab"
                aria-selected={currentTab === tab.value}
              />
            ))}
          </Tabs>
        </Paper>

        {/* 탭 컨텐츠 */}
        <Box
          id={`tabpanel-${currentTab}`}
          role="tabpanel"
          aria-labelledby={`tab-${currentTab}`}
          tabIndex={0}
        >
          {renderTabContent()}
        </Box>

        {/* Generate Script Drawer */}
        <Drawer
          anchor="right"
          open={isGenerateDrawerOpen}
          onClose={handleCloseGenerateDrawer}
          sx={{
            '& .MuiDrawer-paper': {
              width: { xs: '100%', sm: 480 },
              maxWidth: '100vw',
            },
          }}
          role="dialog"
          aria-labelledby="generate-drawer-title"
          aria-modal="true"
        >
          <Box sx={{ p: 3 }}>
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                mb: 3,
              }}
            >
              <Typography variant="h6" id="generate-drawer-title">
                <GenerateIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                스크립트 생성
              </Typography>
              <IconButton
                onClick={handleCloseGenerateDrawer}
                aria-label="생성 창 닫기"
                size="small"
              >
                <CloseIcon />
              </IconButton>
            </Box>

            <Alert severity="info" sx={{ mb: 2 }}>
              스크립트 생성 기능은 준비 중입니다.
            </Alert>

            <Typography variant="body2" color="text.secondary">
              프로젝트: {projectId}
            </Typography>
          </Box>
        </Drawer>
      </Box>
    </Container>
  )
}
