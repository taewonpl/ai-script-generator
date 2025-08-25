// Google Analytics 4 configuration
;(function () {
  'use strict'

  // Get tracking ID from meta tag or environment
  const getTrackingId = () => {
    const metaTag = document.querySelector('meta[name="analytics-tracking-id"]')
    if (metaTag) {
      return metaTag.getAttribute('content')
    }

    // Fallback to window variable (set by build process)
    return window.__ANALYTICS_TRACKING_ID__
  }

  const trackingId = getTrackingId()

  if (trackingId && trackingId !== 'undefined') {
    // Load Google Analytics script
    const script = document.createElement('script')
    script.src = `https://www.googletagmanager.com/gtag/js?id=${trackingId}`
    script.async = true
    document.head.appendChild(script)

    // Initialize gtag
    window.dataLayer = window.dataLayer || []
    function gtag() {
      dataLayer.push(arguments)
    }
    gtag('js', new Date())

    // Configure Google Analytics with enhanced privacy settings
    gtag('config', trackingId, {
      // Privacy settings
      anonymize_ip: true,
      allow_google_signals: false,
      allow_ad_personalization_signals: false,

      // Performance settings
      page_title: document.title,
      page_location: window.location.href,

      // Custom parameters
      app_name: 'AI Script Generator',
      app_version: window.__APP_VERSION__ || '1.0.0',

      // Enhanced measurement
      enhanced_measurement_settings: {
        outbound_clicks: true,
        site_search: true,
        video_engagement: false,
        file_downloads: true,
        page_changes: true,
      },
    })

    // Make gtag available globally
    window.gtag = gtag

    console.log('📊 Google Analytics initialized with ID:', trackingId)
  } else {
    console.log('📊 Analytics tracking disabled - no tracking ID provided')

    // Create a no-op gtag function for development/testing
    window.gtag = function () {
      console.log('🔇 Analytics call (disabled):', arguments)
    }
  }

  // Enhanced error tracking for analytics
  window.addEventListener('error', function (event) {
    if (window.gtag && trackingId) {
      gtag('event', 'exception', {
        description: event.error ? event.error.toString() : event.message,
        fatal: false,
        error_category: 'javascript_error',
        error_filename: event.filename,
        error_line: event.lineno,
        error_column: event.colno,
      })
    }
  })

  // Track unhandled promise rejections
  window.addEventListener('unhandledrejection', function (event) {
    if (window.gtag && trackingId) {
      gtag('event', 'exception', {
        description: event.reason
          ? event.reason.toString()
          : 'Unhandled Promise Rejection',
        fatal: false,
        error_category: 'promise_rejection',
      })
    }
  })

  // Track performance metrics
  if ('PerformanceObserver' in window) {
    // Track largest contentful paint
    try {
      new PerformanceObserver(function (list) {
        const entries = list.getEntries()
        const lastEntry = entries[entries.length - 1]

        if (window.gtag && trackingId) {
          gtag('event', 'lcp', {
            event_category: 'Web Vitals',
            value: Math.round(lastEntry.startTime),
            metric_id: lastEntry.id,
          })
        }
      }).observe({ entryTypes: ['largest-contentful-paint'] })
    } catch (e) {
      console.warn('LCP observer not supported:', e)
    }

    // Track first input delay
    try {
      new PerformanceObserver(function (list) {
        const entries = list.getEntries()
        entries.forEach(entry => {
          if (window.gtag && trackingId) {
            gtag('event', 'fid', {
              event_category: 'Web Vitals',
              value: Math.round(entry.processingStart - entry.startTime),
              metric_id: entry.id,
            })
          }
        })
      }).observe({ entryTypes: ['first-input'] })
    } catch (e) {
      console.warn('FID observer not supported:', e)
    }
  }
})()
