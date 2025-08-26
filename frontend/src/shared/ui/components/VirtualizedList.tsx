import React, { memo, useMemo, useCallback } from 'react'
import { FixedSizeList as List, VariableSizeList } from 'react-window'
// @ts-expect-error - react-window-infinite-loader types not available
import InfiniteLoader from 'react-window-infinite-loader'
import { Box, CircularProgress, Typography } from '@mui/material'

interface VirtualizedListProps<T> {
  items: T[]
  renderItem: (
    item: T,
    index: number,
    style: React.CSSProperties,
  ) => React.ReactNode
  itemHeight?: number
  getItemSize?: (index: number) => number
  height: number
  width?: string | number
  hasNextPage?: boolean
  isNextPageLoading?: boolean
  loadNextPage?: () => Promise<void>
  overscanCount?: number
  className?: string
  onScroll?: (props: {
    scrollTop: number
    scrollHeight: number
    clientHeight: number
  }) => void
}

export const VirtualizedList = memo(function VirtualizedList<T>({
  items,
  renderItem,
  itemHeight = 100,
  getItemSize,
  height,
  width = '100%',
  hasNextPage = false,
  isNextPageLoading: _isNextPageLoading = false,
  loadNextPage,
  overscanCount = 5,
  className,
  onScroll,
}: VirtualizedListProps<T>) {
  // If we have infinite loading, add a loading item
  const itemCount = hasNextPage ? items.length + 1 : items.length

  const isItemLoaded = useCallback(
    (index: number) => {
      return !!items[index]
    },
    [items],
  )

  const Item = useCallback(
    ({ index, style }: { index: number; style: React.CSSProperties }) => {
      let content: React.ReactNode

      if (index >= items.length) {
        // Loading item
        content = (
          <Box
            display="flex"
            alignItems="center"
            justifyContent="center"
            height="100%"
            style={style}
          >
            <CircularProgress size={24} />
            <Typography variant="body2" sx={{ ml: 2 }}>
              로딩 중...
            </Typography>
          </Box>
        )
      } else {
        content = renderItem(items[index], index, style)
      }

      return <div style={style}>{content}</div>
    },
    [items, renderItem],
  )

  const memoizedList = useMemo(() => {
    if (hasNextPage && loadNextPage) {
      return (
        <InfiniteLoader
          isItemLoaded={isItemLoaded}
          itemCount={itemCount}
          loadMoreItems={loadNextPage}
        >
          {({ onItemsRendered, ref }: any) => {
            if (getItemSize) {
              return (
                <VariableSizeList
                  ref={ref}
                  height={height}
                  width={width}
                  itemCount={itemCount}
                  itemSize={getItemSize}
                  onItemsRendered={onItemsRendered}
                  overscanCount={overscanCount}
                  className={className}
                  onScroll={onScroll as any}
                >
                  {Item}
                </VariableSizeList>
              )
            } else {
              return (
                <List
                  ref={ref}
                  height={height}
                  width={width}
                  itemCount={itemCount}
                  itemSize={itemHeight}
                  onItemsRendered={onItemsRendered}
                  overscanCount={overscanCount}
                  className={className}
                  onScroll={onScroll as any}
                >
                  {Item}
                </List>
              )
            }
          }}
        </InfiniteLoader>
      )
    } else {
      if (getItemSize) {
        return (
          <VariableSizeList
            height={height}
            width={width}
            itemCount={itemCount}
            itemSize={getItemSize}
            overscanCount={overscanCount}
            className={className}
            onScroll={onScroll as any /* react-window scroll props mismatch */}
          >
            {Item}
          </VariableSizeList>
        )
      } else {
        return (
          <List
            height={height}
            width={width}
            itemCount={itemCount}
            itemSize={itemHeight}
            overscanCount={overscanCount}
            className={className}
            onScroll={onScroll as any /* react-window scroll props mismatch */}
          >
            {Item}
          </List>
        )
      }
    }
  }, [
    hasNextPage,
    loadNextPage,
    isItemLoaded,
    itemCount,
    getItemSize,
    height,
    width,
    itemHeight,
    overscanCount,
    className,
    onScroll,
    Item,
  ])

  return (
    <Box width={width} height={height}>
      {memoizedList}
    </Box>
  )
})

VirtualizedList.displayName = 'VirtualizedList'

// Specialized components
interface VirtualizedProjectListProps<T = unknown> {
  projects: T[]
  renderProject: (
    project: T,
    index: number,
    style: React.CSSProperties,
  ) => React.ReactNode
  height: number
  hasNextPage?: boolean
  isNextPageLoading?: boolean
  loadNextPage?: () => Promise<void>
}

export const VirtualizedProjectList = memo(function VirtualizedProjectList<
  T = unknown,
>({
  projects,
  renderProject,
  height,
  hasNextPage,
  isNextPageLoading,
  loadNextPage,
}: VirtualizedProjectListProps<T>) {
  return (
    <VirtualizedList
      items={projects}
      renderItem={renderProject as any}
      itemHeight={180} // Estimated height for project cards
      height={height}
      hasNextPage={hasNextPage}
      isNextPageLoading={isNextPageLoading}
      loadNextPage={loadNextPage}
      overscanCount={3}
    />
  )
})

interface VirtualizedEpisodeListProps<T = unknown> {
  episodes: T[]
  renderEpisode: (
    episode: T,
    index: number,
    style: React.CSSProperties,
  ) => React.ReactNode
  height: number
  hasNextPage?: boolean
  isNextPageLoading?: boolean
  loadNextPage?: () => Promise<void>
}

export const VirtualizedEpisodeList = memo(function VirtualizedEpisodeList<
  T = unknown,
>({
  episodes,
  renderEpisode,
  height,
  hasNextPage,
  isNextPageLoading,
  loadNextPage,
}: VirtualizedEpisodeListProps<T>) {
  return (
    <VirtualizedList
      items={episodes}
      renderItem={renderEpisode as any}
      itemHeight={120} // Estimated height for episode rows
      height={height}
      hasNextPage={hasNextPage}
      isNextPageLoading={isNextPageLoading}
      loadNextPage={loadNextPage}
      overscanCount={5}
    />
  )
})

interface VirtualizedScriptListProps<T = unknown> {
  scripts: T[]
  renderScript: (
    script: T,
    index: number,
    style: React.CSSProperties,
  ) => React.ReactNode
  height: number
  hasNextPage?: boolean
  isNextPageLoading?: boolean
  loadNextPage?: () => Promise<void>
}

export const VirtualizedScriptList = memo(function VirtualizedScriptList<
  T = unknown,
>({
  scripts,
  renderScript,
  height,
  hasNextPage,
  isNextPageLoading,
  loadNextPage,
}: VirtualizedScriptListProps<T>) {
  return (
    <VirtualizedList
      items={scripts}
      renderItem={renderScript as any}
      itemHeight={200} // Estimated height for script cards
      height={height}
      hasNextPage={hasNextPage}
      isNextPageLoading={isNextPageLoading}
      loadNextPage={loadNextPage}
      overscanCount={3}
    />
  )
})
