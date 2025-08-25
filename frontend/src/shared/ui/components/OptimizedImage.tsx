import React, { memo, useState, useCallback, useMemo } from 'react'
import type { SxProps, Theme } from '@mui/material'
import { Box, Skeleton } from '@mui/material'
import { BrokenImage as BrokenImageIcon } from '@mui/icons-material'

interface OptimizedImageProps {
  src: string
  alt: string
  width?: number | string
  height?: number | string
  placeholder?: React.ReactNode
  errorFallback?: React.ReactNode
  onLoad?: () => void
  onError?: () => void
  loading?: 'lazy' | 'eager'
  objectFit?: 'cover' | 'contain' | 'fill' | 'scale-down' | 'none'
  sx?: SxProps<Theme>
  className?: string
  sizes?: string
  priority?: boolean
  onClick?: () => void
}

export const OptimizedImage = memo(function OptimizedImage({
  src,
  alt,
  width,
  height,
  placeholder,
  errorFallback,
  onLoad,
  onError,
  loading = 'lazy',
  objectFit = 'cover',
  sx,
  className,
  sizes,
  priority = false,
}: OptimizedImageProps) {
  const [isLoading, setIsLoading] = useState(true)
  const [hasError, setHasError] = useState(false)

  const handleLoad = useCallback(() => {
    setIsLoading(false)
    onLoad?.()
  }, [onLoad])

  const handleError = useCallback(() => {
    setIsLoading(false)
    setHasError(true)
    onError?.()
  }, [onError])

  // Generate responsive image sources
  const responsiveSrc = useMemo(() => {
    if (!src) return ''

    // For development, return original src
    if (import.meta.env.DEV) {
      return src
    }

    // In production, you could add logic to generate WebP versions
    // or use a service like Cloudinary, ImageKit, etc.
    return src
  }, [src])

  const defaultPlaceholder = useMemo(
    () => (
      <Skeleton
        variant="rectangular"
        width={width || '100%'}
        height={height || 200}
        animation="wave"
      />
    ),
    [width, height],
  )

  const defaultErrorFallback = useMemo(
    () => (
      <Box
        display="flex"
        alignItems="center"
        justifyContent="center"
        width={width || '100%'}
        height={height || 200}
        bgcolor="grey.100"
        color="grey.500"
        sx={{ border: '1px dashed', borderColor: 'grey.300' }}
      >
        <BrokenImageIcon />
      </Box>
    ),
    [width, height],
  )

  if (hasError) {
    return <>{errorFallback || defaultErrorFallback}</>
  }

  return (
    <Box
      position="relative"
      width={width}
      height={height}
      sx={sx}
      className={className}
    >
      {isLoading && (placeholder || defaultPlaceholder)}

      <Box
        component="img"
        src={responsiveSrc}
        alt={alt}
        onLoad={handleLoad}
        onError={handleError}
        loading={priority ? 'eager' : loading}
        sizes={sizes}
        sx={{
          width: '100%',
          height: '100%',
          objectFit,
          display: isLoading ? 'none' : 'block',
        }}
      />
    </Box>
  )
})

OptimizedImage.displayName = 'OptimizedImage'

// Avatar optimization component
interface OptimizedAvatarProps {
  src?: string
  alt: string
  size: number
  fallback?: React.ReactNode
  sx?: SxProps<Theme>
}

export const OptimizedAvatar = memo(function OptimizedAvatar({
  src,
  alt,
  size,
  fallback,
  sx,
}: OptimizedAvatarProps) {
  const avatarFallback = useMemo(
    () => (
      <Box
        display="flex"
        alignItems="center"
        justifyContent="center"
        width={size}
        height={size}
        borderRadius="50%"
        bgcolor="primary.main"
        color="white"
        fontSize={size * 0.4}
        fontWeight="bold"
      >
        {alt.charAt(0).toUpperCase()}
      </Box>
    ),
    [alt, size],
  )

  if (!src) {
    return <>{fallback || avatarFallback}</>
  }

  return (
    <OptimizedImage
      src={src}
      alt={alt}
      width={size}
      height={size}
      objectFit="cover"
      errorFallback={fallback || avatarFallback}
      sx={{
        borderRadius: '50%',
        ...sx,
      }}
    />
  )
})

// Background image optimization
interface OptimizedBackgroundProps {
  src: string
  children: React.ReactNode
  overlay?: boolean
  overlayColor?: string
  overlayOpacity?: number
  sx?: SxProps<Theme>
}

export const OptimizedBackground = memo(function OptimizedBackground({
  src,
  children,
  overlay = false,
  overlayColor = 'rgba(0, 0, 0, 0.5)',
  overlayOpacity = 0.5,
  sx,
}: OptimizedBackgroundProps) {
  const [isLoaded, setIsLoaded] = useState(false)

  const handleLoad = useCallback(() => {
    setIsLoaded(true)
  }, [])

  return (
    <Box
      position="relative"
      sx={{
        backgroundImage: isLoaded ? `url(${src})` : 'none',
        backgroundSize: 'cover',
        backgroundPosition: 'center',
        backgroundRepeat: 'no-repeat',
        transition: 'background-image 0.3s ease-in-out',
        ...sx,
      }}
    >
      {/* Preload image */}
      <Box
        component="img"
        src={src}
        onLoad={handleLoad}
        sx={{ display: 'none' }}
        alt=""
      />

      {/* Overlay */}
      {overlay && isLoaded && (
        <Box
          position="absolute"
          top={0}
          left={0}
          right={0}
          bottom={0}
          bgcolor={overlayColor}
          sx={{ opacity: overlayOpacity }}
        />
      )}

      {/* Content */}
      <Box position="relative" zIndex={1}>
        {children}
      </Box>
    </Box>
  )
})

// Image gallery optimization
interface OptimizedGalleryProps {
  images: Array<{
    src: string
    alt: string
    thumbnail?: string
  }>
  columns?: number
  spacing?: number
  onImageClick?: (index: number) => void
}

export const OptimizedGallery = memo(function OptimizedGallery({
  images,
  columns = 3,
  spacing = 2,
  onImageClick,
}: OptimizedGalleryProps) {
  return (
    <Box
      display="grid"
      gridTemplateColumns={`repeat(${columns}, 1fr)`}
      gap={spacing}
    >
      {images.map((image, index) => (
        <OptimizedImage
          key={index}
          src={image.thumbnail || image.src}
          alt={image.alt}
          height={200}
          loading="lazy"
          sx={{
            cursor: onImageClick ? 'pointer' : 'default',
            borderRadius: 1,
            transition: 'transform 0.2s ease-in-out',
            '&:hover': onImageClick
              ? {
                  transform: 'scale(1.05)',
                }
              : {},
          }}
          onClick={() => onImageClick?.(index)}
        />
      ))}
    </Box>
  )
})

// Utility functions for image optimization
export const imageUtils = {
  // Generate srcSet for responsive images
  generateSrcSet: (baseUrl: string, sizes: number[]): string => {
    return sizes.map(size => `${baseUrl}?w=${size} ${size}w`).join(', ')
  },

  // Generate sizes attribute
  generateSizes: (
    breakpoints: Array<{ breakpoint: string; size: string }>,
  ): string => {
    return breakpoints
      .map(({ breakpoint, size }) => `${breakpoint} ${size}`)
      .join(', ')
  },

  // Preload critical images
  preloadImage: (src: string): Promise<void> => {
    return new Promise((resolve, reject) => {
      const img = new Image()
      img.onload = () => resolve()
      img.onerror = reject
      img.src = src
    })
  },

  // Convert to WebP if supported
  convertToWebP: (src: string): string => {
    // Check WebP support
    const supportsWebP = (() => {
      const canvas = document.createElement('canvas')
      canvas.width = 1
      canvas.height = 1
      return canvas.toDataURL('image/webp').indexOf('data:image/webp') === 0
    })()

    if (supportsWebP && src.match(/\.(jpg|jpeg|png)$/i)) {
      return src.replace(/\.(jpg|jpeg|png)$/i, '.webp')
    }

    return src
  },
}
