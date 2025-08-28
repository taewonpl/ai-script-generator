/**
 * Memory Controls Component for Episode Editor
 * Provides memory ON/OFF toggle, settings, and status display
 */

import { useState, useCallback, useEffect } from 'react'
import {
  Box,
  Switch,
  FormControlLabel,
  Chip,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Typography,
  Alert,
  Collapse,
  Divider,
  Slider,
  FormGroup,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
} from '@mui/material'
import {
  Memory as MemoryIcon,
  Settings as SettingsIcon,
  Clear as ClearIcon,
  Info as InfoIcon,
  ExpandMore as ExpandIcon,
  ExpandLess as CollapseIcon,
  Compress as CompressIcon,
} from '@mui/icons-material'

import { useToastHelpers } from '@/shared/ui/components/toast'

export interface MemoryState {
  enabled: boolean
  historyDepth: number
  turnsCount: number
  entityRenames: number
  entityFacts: number
  styleFlags: number
  memoryVersion: number
  tokensUsed: number
  compressionRecommended: boolean
  lastCompressed?: string
}

export interface MemoryControlsProps {
  memoryState: MemoryState
  onMemoryToggle: (enabled: boolean) => Promise<void>
  onHistoryDepthChange: (depth: number) => Promise<void>
  onClearMemory: (options: { clearHistory: boolean; clearEntityMemory: boolean }) => Promise<void>
  onCompressMemory: () => Promise<void>
  loading?: boolean
  className?: string
}

/**
 * Memory Controls Component
 */
export function MemoryControls({
  memoryState,
  onMemoryToggle,
  onHistoryDepthChange,
  onClearMemory,
  onCompressMemory,
  loading = false,
  className,
}: MemoryControlsProps) {
  const { showSuccess, showError } = useToastHelpers()
  
  // Dialog states
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [clearDialogOpen, setClearDialogOpen] = useState(false)
  const [detailsExpanded, setDetailsExpanded] = useState(false)
  
  // Local state for settings
  const [historyDepth, setHistoryDepth] = useState(memoryState.historyDepth)
  
  // Sync local state with props
  useEffect(() => {
    setHistoryDepth(memoryState.historyDepth)
  }, [memoryState.historyDepth])
  
  const handleMemoryToggle = useCallback(async (event: React.ChangeEvent<HTMLInputElement>) => {
    try {
      await onMemoryToggle(event.target.checked)
      showSuccess(
        event.target.checked 
          ? '메모리가 활성화되었습니다.' 
          : '메모리가 비활성화되었습니다.'
      )
    } catch (error) {
      showError('메모리 설정 변경에 실패했습니다.')
    }
  }, [onMemoryToggle, showSuccess, showError])
  
  const handleHistoryDepthSave = useCallback(async () => {
    if (historyDepth !== memoryState.historyDepth) {
      try {
        await onHistoryDepthChange(historyDepth)
        showSuccess('히스토리 설정이 저장되었습니다.')
      } catch (error) {
        showError('히스토리 설정 저장에 실패했습니다.')
        setHistoryDepth(memoryState.historyDepth) // Revert
      }
    }
    setSettingsOpen(false)
  }, [historyDepth, memoryState.historyDepth, onHistoryDepthChange, showSuccess, showError])
  
  const handleClearMemory = useCallback(async (clearHistory: boolean, clearEntityMemory: boolean) => {
    try {
      await onClearMemory({ clearHistory, clearEntityMemory })
      setClearDialogOpen(false)
      showSuccess('메모리가 삭제되었습니다. 60초 내에 되돌릴 수 있습니다.')
    } catch (error) {
      showError('메모리 삭제에 실패했습니다.')
    }
  }, [onClearMemory, showSuccess, showError])
  
  const handleCompressMemory = useCallback(async () => {
    try {
      await onCompressMemory()
      showSuccess('메모리가 압축되었습니다.')
    } catch (error) {
      showError('메모리 압축에 실패했습니다.')
    }
  }, [onCompressMemory, showSuccess, showError])
  
  // Generate status text
  const getStatusText = () => {
    if (!memoryState.enabled) return 'Memory OFF'
    
    const parts = []
    if (memoryState.turnsCount > 0) {
      parts.push(`${memoryState.turnsCount} turns`)
    }
    if (memoryState.entityRenames > 0) {
      parts.push(`${memoryState.entityRenames} rename${memoryState.entityRenames > 1 ? 's' : ''}`)
    }
    
    return parts.length > 0 ? `Context: ${parts.join(' · ')}` : 'Context: Empty'
  }
  
  return (
    <Box className={className}>
      {/* Main Controls */}
      <Box display="flex" alignItems="center" gap={1}>
        {/* Memory Toggle with Tooltip */}
        <Tooltip 
          title="최근 맥락을 유지해 일관성을 높입니다. 토큰 사용량이 증가할 수 있습니다."
          placement="top"
        >
          <FormControlLabel
            control={
              <Switch
                checked={memoryState.enabled}
                onChange={handleMemoryToggle}
                disabled={loading}
                color="primary"
              />
            }
            label={
              <Box display="flex" alignItems="center" gap={0.5}>
                <MemoryIcon fontSize="small" />
                <Typography variant="body2">Memory</Typography>
              </Box>
            }
          />
        </Tooltip>
        
        {/* Status Chip */}
        {memoryState.enabled && (
          <Chip
            label={getStatusText()}
            size="small"
            variant="outlined"
            icon={<InfoIcon />}
            onClick={() => setDetailsExpanded(!detailsExpanded)}
            sx={{ cursor: 'pointer' }}
          />
        )}
        
        {/* Settings Button */}
        {memoryState.enabled && (
          <Tooltip title="메모리 설정">
            <IconButton
              size="small"
              onClick={() => setSettingsOpen(true)}
              disabled={loading}
            >
              <SettingsIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        )}
        
        {/* Compress Button */}
        {memoryState.enabled && memoryState.compressionRecommended && (
          <Tooltip title="메모리 압축으로 토큰 절약">
            <IconButton
              size="small"
              onClick={handleCompressMemory}
              disabled={loading}
              color="warning"
            >
              <CompressIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        )}
      </Box>
      
      {/* Expanded Details */}
      <Collapse in={detailsExpanded && memoryState.enabled}>
        <Box mt={1} p={1} bgcolor="action.hover" borderRadius={1}>
          <Typography variant="caption" color="text.secondary" gutterBottom>
            메모리 상세 정보
          </Typography>
          
          <Box display="flex" gap={2} flexWrap="wrap">
            <Typography variant="body2">
              대화 턴: {memoryState.turnsCount}
            </Typography>
            <Typography variant="body2">
              이름 변경: {memoryState.entityRenames}
            </Typography>
            <Typography variant="body2">
              저장된 정보: {memoryState.entityFacts}
            </Typography>
            <Typography variant="body2">
              스타일 설정: {memoryState.styleFlags}
            </Typography>
          </Box>
          
          {memoryState.tokensUsed > 0 && (
            <Typography variant="caption" color="text.secondary" display="block" mt={0.5}>
              토큰 사용량: ~{memoryState.tokensUsed}
            </Typography>
          )}
          
          {memoryState.compressionRecommended && (
            <Alert severity="info" sx={{ mt: 1 }}>
              메모리 압축을 권장합니다. 토큰 사용량을 줄일 수 있습니다.
            </Alert>
          )}
        </Box>
      </Collapse>
      
      {/* Settings Dialog */}
      <Dialog open={settingsOpen} onClose={() => setSettingsOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>메모리 설정</DialogTitle>
        <DialogContent>
          <Box py={2}>
            <Typography gutterBottom>
              히스토리 깊이: {historyDepth}턴
            </Typography>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              최근 몇 개의 대화를 기억할지 설정합니다.
            </Typography>
            
            <Slider
              value={historyDepth}
              onChange={(_, value) => setHistoryDepth(value as number)}
              min={1}
              max={10}
              marks={[
                { value: 1, label: '1' },
                { value: 5, label: '5' },
                { value: 10, label: '10' },
              ]}
              step={1}
              sx={{ mt: 2, mb: 3 }}
            />
            
            <Divider sx={{ my: 2 }} />
            
            <Typography variant="subtitle2" gutterBottom>
              현재 메모리 상태
            </Typography>
            
            <List dense>
              <ListItem>
                <ListItemText 
                  primary="버전" 
                  secondary={`v${memoryState.memoryVersion}`}
                />
              </ListItem>
              <ListItem>
                <ListItemText 
                  primary="대화 턴" 
                  secondary={`${memoryState.turnsCount}개`}
                />
              </ListItem>
              <ListItem>
                <ListItemText 
                  primary="엔터티 정보" 
                  secondary={`이름 변경 ${memoryState.entityRenames}개, 저장된 정보 ${memoryState.entityFacts}개`}
                />
              </ListItem>
            </List>
            
            <Box mt={2}>
              <Button
                variant="outlined"
                color="error"
                startIcon={<ClearIcon />}
                onClick={() => {
                  setSettingsOpen(false)
                  setClearDialogOpen(true)
                }}
                size="small"
              >
                메모리 삭제
              </Button>
            </Box>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSettingsOpen(false)}>취소</Button>
          <Button onClick={handleHistoryDepthSave} variant="contained">저장</Button>
        </DialogActions>
      </Dialog>
      
      {/* Clear Memory Dialog */}
      <Dialog open={clearDialogOpen} onClose={() => setClearDialogOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>메모리 삭제 확인</DialogTitle>
        <DialogContent>
          <Typography gutterBottom>
            이 에피소드의 기억된 맥락을 삭제할까요? 60초 후 되돌릴 수 없습니다.
          </Typography>
          
          <FormGroup sx={{ mt: 2 }}>
            <FormControlLabel
              control={<Switch defaultChecked />}
              label="대화 히스토리 삭제"
            />
            <FormControlLabel
              control={<Switch defaultChecked />}
              label="엔터티 메모리 삭제 (이름 변경, 설정 등)"
            />
          </FormGroup>
          
          <Alert severity="warning" sx={{ mt: 2 }}>
            삭제된 메모리는 60초 후 복구할 수 없습니다.
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setClearDialogOpen(false)}>취소</Button>
          <Button
            onClick={() => handleClearMemory(true, true)}
            color="error"
            variant="contained"
          >
            삭제
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default MemoryControls