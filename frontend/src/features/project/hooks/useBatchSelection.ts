import { useState, useCallback, useMemo, useEffect } from 'react'

/**
 * Hook for managing batch selection of items
 */
export function useBatchSelection<T extends { id: string }>(items: T[] = []) {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())

  // Check if item is selected
  const isSelected = useCallback(
    (id: string) => {
      return selectedIds.has(id)
    },
    [selectedIds],
  )

  // Toggle single item selection
  const toggleSelection = useCallback((id: string) => {
    setSelectedIds(prev => {
      const newSet = new Set(prev)
      if (newSet.has(id)) {
        newSet.delete(id)
      } else {
        newSet.add(id)
      }
      return newSet
    })
  }, [])

  // Select all items
  const selectAll = useCallback(() => {
    setSelectedIds(new Set(items.map(item => item.id)))
  }, [items])

  // Clear all selections
  const clearSelection = useCallback(() => {
    setSelectedIds(new Set())
  }, [])

  // Toggle select all
  const toggleSelectAll = useCallback(() => {
    if (selectedIds.size === items.length && items.length > 0) {
      clearSelection()
    } else {
      selectAll()
    }
  }, [selectedIds.size, items.length, selectAll, clearSelection])

  // Select range of items
  const selectRange = useCallback(
    (fromId: string, toId: string) => {
      const fromIndex = items.findIndex(item => item.id === fromId)
      const toIndex = items.findIndex(item => item.id === toId)

      if (fromIndex === -1 || toIndex === -1) return

      const startIndex = Math.min(fromIndex, toIndex)
      const endIndex = Math.max(fromIndex, toIndex)

      const rangeIds = items
        .slice(startIndex, endIndex + 1)
        .map(item => item.id)

      setSelectedIds(prev => new Set([...prev, ...rangeIds]))
    },
    [items],
  )

  // Get selected items
  const selectedItems = useMemo(() => {
    return items.filter(item => selectedIds.has(item.id))
  }, [items, selectedIds])

  // Selection statistics
  const selectionStats = useMemo(
    () => ({
      selectedCount: selectedIds.size,
      totalCount: items.length,
      allSelected: selectedIds.size === items.length && items.length > 0,
      noneSelected: selectedIds.size === 0,
      partiallySelected:
        selectedIds.size > 0 && selectedIds.size < items.length,
    }),
    [selectedIds.size, items.length],
  )

  // Reset selection when items change significantly
  useEffect(() => {
    const currentItemIds = new Set(items.map(item => item.id))
    const selectedIdsList = Array.from(selectedIds)
    const validSelectedIds = selectedIdsList.filter(id =>
      currentItemIds.has(id),
    )

    if (validSelectedIds.length !== selectedIds.size) {
      setSelectedIds(new Set(validSelectedIds))
    }
  }, [items, selectedIds])

  return {
    selectedIds: Array.from(selectedIds),
    selectedItems,
    isSelected,
    toggleSelection,
    selectAll,
    clearSelection,
    toggleSelectAll,
    selectRange,
    selectionStats,
  }
}
