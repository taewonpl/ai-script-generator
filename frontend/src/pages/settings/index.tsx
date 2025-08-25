import { useState } from 'react'
import type { ReactNode, SyntheticEvent } from 'react'
import { Box, Container, Typography, Tabs, Tab, Paper } from '@mui/material'
import {
  Person as ProfileIcon,
  AutoAwesome as AIIcon,
  Notifications as NotificationIcon,
  ImportExport as DataIcon,
} from '@mui/icons-material'

import { UserProfile } from './components/UserProfile'
import { AIModelSettings } from './components/AIModelSettings'
import { NotificationSettings } from './components/NotificationSettings'
import { DataManagement } from './components/DataManagement'

interface TabPanelProps {
  children?: ReactNode
  index: number
  value: number
}

function TabPanel({ children, value, index, ...other }: TabPanelProps) {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`settings-tabpanel-${index}`}
      aria-labelledby={`settings-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  )
}

export default function SettingsPage() {
  const [currentTab, setCurrentTab] = useState(0)

  const handleTabChange = (_: SyntheticEvent, newValue: number) => {
    setCurrentTab(newValue)
  }

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      {/* Header */}
      <Box mb={4}>
        <Typography variant="h4" component="h1" gutterBottom>
          설정
        </Typography>
        <Typography variant="body1" color="textSecondary">
          계정, AI 모델, 알림 및 데이터 설정을 관리하세요
        </Typography>
      </Box>

      {/* Settings Tabs */}
      <Paper elevation={1}>
        <Tabs
          value={currentTab}
          onChange={handleTabChange}
          indicatorColor="primary"
          textColor="primary"
          variant="scrollable"
          scrollButtons="auto"
        >
          <Tab
            icon={<ProfileIcon />}
            label="프로필"
            iconPosition="start"
            sx={{ minHeight: 64 }}
          />
          <Tab
            icon={<AIIcon />}
            label="AI 설정"
            iconPosition="start"
            sx={{ minHeight: 64 }}
          />
          <Tab
            icon={<NotificationIcon />}
            label="알림"
            iconPosition="start"
            sx={{ minHeight: 64 }}
          />
          <Tab
            icon={<DataIcon />}
            label="데이터"
            iconPosition="start"
            sx={{ minHeight: 64 }}
          />
        </Tabs>

        {/* Tab Content */}
        <TabPanel value={currentTab} index={0}>
          <UserProfile />
        </TabPanel>

        <TabPanel value={currentTab} index={1}>
          <AIModelSettings />
        </TabPanel>

        <TabPanel value={currentTab} index={2}>
          <NotificationSettings />
        </TabPanel>

        <TabPanel value={currentTab} index={3}>
          <DataManagement />
        </TabPanel>
      </Paper>
    </Container>
  )
}
