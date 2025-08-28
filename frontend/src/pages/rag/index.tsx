/**
 * RAG Management Page
 * Demonstrates the complete RAG document pipeline with upload and monitoring
 */

import { useState, useCallback } from 'react'
import {
  Box,
  Typography,
  Tabs,
  Tab,
  Paper,
  Container,
  Alert,
  Stack,
  Breadcrumbs,
  Link,
} from '@mui/material'
import {
  CloudUpload as UploadIcon,
  Dashboard as DashboardIcon,
  Home as HomeIcon,
} from '@mui/icons-material'
import { Link as RouterLink } from 'react-router-dom'

import { RAGDropzone, RAGStatusDashboard } from '@/features/rag'

interface TabPanelProps {
  children?: React.ReactNode
  index: number
  value: number
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`rag-tabpanel-${index}`}
      aria-labelledby={`rag-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ py: 3 }}>
          {children}
        </Box>
      )}
    </div>
  )
}

function a11yProps(index: number) {
  return {
    id: `rag-tab-${index}`,
    'aria-controls': `rag-tabpanel-${index}`,
  }
}

/**
 * Main RAG management page
 */
export default function RAGPage() {
  const [activeTab, setActiveTab] = useState(0)
  const [uploadSuccess, setUploadSuccess] = useState<string[]>([])

  const handleTabChange = useCallback((_event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue)
  }, [])

  const handleUploadSuccess = useCallback((documentIds: string[]) => {
    setUploadSuccess(documentIds)
    // Switch to status tab to see the uploaded documents
    setActiveTab(1)
  }, [])

  const handleDocumentDeleted = useCallback((documentId: string) => {
    setUploadSuccess(prev => prev.filter(id => id !== documentId))
  }, [])

  // For demo purposes, using a fixed project ID
  const projectId = 'demo-project'

  return (
    <Container maxWidth="xl">
      <Box sx={{ py: 3 }}>
        {/* Breadcrumbs */}
        <Breadcrumbs aria-label="breadcrumb" sx={{ mb: 2 }}>
          <Link 
            underline="hover" 
            color="inherit" 
            component={RouterLink}
            to="/"
            sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}
          >
            <HomeIcon fontSize="inherit" />
            홈
          </Link>
          <Typography color="text.primary" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <DashboardIcon fontSize="inherit" />
            RAG 관리
          </Typography>
        </Breadcrumbs>

        {/* Page Header */}
        <Stack spacing={1} sx={{ mb: 4 }}>
          <Typography variant="h3" component="h1">
            RAG 문서 관리
          </Typography>
          <Typography variant="body1" color="text.secondary">
            AI 대본 생성을 위한 참조 문서를 업로드하고 관리하세요. 
            PDF, DOCX, TXT, MD 파일을 지원하며, 자동으로 텍스트를 추출하여 임베딩으로 변환합니다.
          </Typography>
        </Stack>

        {/* Success Alert */}
        {uploadSuccess.length > 0 && (
          <Alert severity="success" sx={{ mb: 3 }} onClose={() => setUploadSuccess([])}>
            <Typography variant="body2">
              {uploadSuccess.length}개의 문서가 성공적으로 업로드되어 처리 중입니다.
            </Typography>
          </Alert>
        )}

        {/* Main Content */}
        <Paper sx={{ width: '100%' }}>
          {/* Tabs */}
          <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
            <Tabs 
              value={activeTab} 
              onChange={handleTabChange}
              aria-label="RAG management tabs"
              sx={{ px: 2 }}
            >
              <Tab 
                icon={<UploadIcon />}
                label="문서 업로드"
                iconPosition="start"
                {...a11yProps(0)} 
              />
              <Tab 
                icon={<DashboardIcon />}
                label="상태 모니터링"
                iconPosition="start"
                {...a11yProps(1)} 
              />
            </Tabs>
          </Box>

          {/* Upload Tab */}
          <TabPanel value={activeTab} index={0}>
            <Box sx={{ px: 3, pb: 3 }}>
              <Stack spacing={3}>
                <Box>
                  <Typography variant="h5" component="h2" sx={{ mb: 1 }}>
                    문서 업로드
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    스토리 바이블, 캐릭터 설정, 세계관 문서 등 AI 대본 생성에 참조될 문서를 업로드하세요.
                  </Typography>
                </Box>

                <RAGDropzone
                  projectId={projectId}
                  language="kr"
                  maxFileSizeMB={50}
                  maxFiles={20}
                  onSuccess={handleUploadSuccess}
                  onError={(error) => {
                    console.error('Upload error:', error)
                  }}
                />

                <Alert severity="info">
                  <Typography variant="body2">
                    <strong>지원 파일 형식:</strong>
                    <br />
                    • PDF (.pdf) - 텍스트 추출 또는 OCR 처리
                    <br />
                    • Word 문서 (.docx, .doc) - 텍스트 직접 추출
                    <br />
                    • 텍스트 파일 (.txt) - UTF-8, CP949, EUC-KR 인코딩 지원
                    <br />
                    • 마크다운 (.md) - 구조화된 텍스트 처리
                    <br />
                    <br />
                    <strong>처리 과정:</strong> 업로드 → 텍스트 추출 → 청킹 → 임베딩 생성 → ChromaDB 저장
                  </Typography>
                </Alert>
              </Stack>
            </Box>
          </TabPanel>

          {/* Status Tab */}
          <TabPanel value={activeTab} index={1}>
            <Box sx={{ px: 3, pb: 3 }}>
              <Stack spacing={3}>
                <Box>
                  <Typography variant="h5" component="h2" sx={{ mb: 1 }}>
                    처리 상태 모니터링
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    업로드된 문서들의 처리 상태를 실시간으로 확인하고 관리하세요.
                  </Typography>
                </Box>

                <RAGStatusDashboard
                  projectId={projectId}
                  language="kr"
                  autoRefresh={true}
                  onDocumentDeleted={handleDocumentDeleted}
                />
              </Stack>
            </Box>
          </TabPanel>
        </Paper>
      </Box>
    </Container>
  )
}