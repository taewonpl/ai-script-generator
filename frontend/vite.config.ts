import { defineConfig, loadEnv } from 'vite'
import type { UserConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'
import { visualizer } from 'rollup-plugin-visualizer'
import type { ServerResponse } from 'http'

// https://vite.dev/config/
export default defineConfig(({ command, mode }) => {
  // Load environment variables for the specific mode
  const env = loadEnv(mode, process.cwd(), '')

  const isDevelopment = mode === 'development'
  const isAnalyze = env.ANALYZE === 'true'

  const config: UserConfig = {
    plugins: [
      react(),
      // Bundle analyzer
      ...(isAnalyze ? [
        visualizer({
          filename: 'dist/bundle-analysis.html',
          open: true,
          gzipSize: true,
          brotliSize: true
        })
      ] : [])
    ],
    resolve: {
      alias: {
        '@': resolve(__dirname, './src'),
        '@/app': resolve(__dirname, './src/app'),
        '@/shared': resolve(__dirname, './src/shared'),
        '@/entities': resolve(__dirname, './src/entities'),
        '@/features': resolve(__dirname, './src/features'),
        '@/pages': resolve(__dirname, './src/pages'),
        '@/widgets': resolve(__dirname, './src/widgets'),
        // Legacy aliases for backward compatibility
        '@app': resolve(__dirname, './src/app'),
        '@shared': resolve(__dirname, './src/shared'),
        '@entities': resolve(__dirname, './src/entities'),
        '@features': resolve(__dirname, './src/features'),
        '@pages': resolve(__dirname, './src/pages'),
        '@widgets': resolve(__dirname, './src/widgets'),
      },
    },
    server: {
      port: 3001,
      host: true,
      headers: {
        'X-Frame-Options': 'DENY'
      },
      cors: {
        origin: true,
        credentials: true,
        methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
        allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With', 'Accept', 'Origin'],
      },
      proxy: {
        // Core Service proxy
        '/api/core': {
          target: env.VITE_CORE_SERVICE_URL || 'http://localhost:8000',
          changeOrigin: true,
          secure: false,
          timeout: 30000,
          proxyTimeout: 30000,
          rewrite: (path) => path.replace(/^\/api\/core/, ''),
          configure: (proxy, options) => {
            proxy.on('error', (err, req, res) => {
              console.error('🔥 Core API 프록시 에러:', err.message);
              console.error('   요청 URL:', req.url);
              console.error('   타겟:', options.target);

              // 에러 응답 처리
              const serverRes = res as ServerResponse;
              if (serverRes && 'headersSent' in serverRes && !serverRes.headersSent) {
                serverRes.writeHead(500, {
                  'Content-Type': 'application/json',
                  'Access-Control-Allow-Origin': '*',
                  'Access-Control-Allow-Credentials': 'true'
                });
                serverRes.end(JSON.stringify({
                  error: 'Proxy Error',
                  message: 'Core service is unavailable',
                  service: 'core'
                }));
              }
            });

            if (isDevelopment) {
              proxy.on('proxyReq', (proxyReq, req) => {
                console.log('📤 Core API 요청:', req.method, req.url, '→', options.target + proxyReq.path);
              });
              proxy.on('proxyRes', (proxyRes, req) => {
                console.log('📥 Core API 응답:', proxyRes.statusCode, req.url);
              });
            }
          }
        },

        // Project Service proxy
        '/api/project': {
          target: env.VITE_PROJECT_SERVICE_URL || 'http://localhost:8001',
          changeOrigin: true,
          secure: false,
          timeout: 30000,
          proxyTimeout: 30000,
          rewrite: (path) => path.replace(/^\/api\/project/, ''),
          configure: (proxy, options) => {
            proxy.on('error', (err, req, res) => {
              console.error('🔥 Project API 프록시 에러:', err.message);
              console.error('   요청 URL:', req.url);
              console.error('   타겟:', options.target);

              const serverRes = res as ServerResponse;
              if (serverRes && 'headersSent' in serverRes && !serverRes.headersSent) {
                serverRes.writeHead(500, {
                  'Content-Type': 'application/json',
                  'Access-Control-Allow-Origin': '*',
                  'Access-Control-Allow-Credentials': 'true'
                });
                serverRes.end(JSON.stringify({
                  error: 'Proxy Error',
                  message: 'Project service is unavailable',
                  service: 'project'
                }));
              }
            });

            if (isDevelopment) {
              proxy.on('proxyReq', (proxyReq, req) => {
                console.log('📤 Project API 요청:', req.method, req.url, '→', options.target + proxyReq.path);
              });
            }
          }
        },

        // Generation Service proxy with SSE-optimized configuration
        '/api/generation': {
          target: env.VITE_GENERATION_SERVICE_URL || 'http://localhost:8002',
          changeOrigin: true,
          secure: false,
          // SSE-friendly timeouts (no timeout for streaming)
          timeout: 0,        // Do not time out long SSE streams
          proxyTimeout: 0,   // Do not time out proxy connections
          ws: true,          // WebSocket support (doesn't hurt SSE)
          // Rewrite path once: /api/generation/api/v1 -> /api/v1
          rewrite: (path) => path.replace(/^\/api\/generation/, ''),
          configure: (proxy, options) => {
            proxy.on('error', (err, req, res) => {
              console.error('🔥 Generation API 프록시 에러:', err.message);
              console.error('   요청 URL:', req.url);
              console.error('   타겟:', options.target);

              const serverRes = res as ServerResponse;
              if (serverRes && 'headersSent' in serverRes && !serverRes.headersSent) {
                serverRes.writeHead(500, {
                  'Content-Type': 'application/json',
                  'Access-Control-Allow-Origin': '*',
                  'Access-Control-Allow-Credentials': 'true'
                });
                serverRes.end(JSON.stringify({
                  error: 'Proxy Error',
                  message: 'Generation service is unavailable',
                  service: 'generation'
                }));
              }
            });

            // SSE-optimized request handling
            proxy.on('proxyReq', (proxyReq, req) => {
              // Helpful for SSE intermediaries
              proxyReq.setHeader('Connection', 'keep-alive');
              proxyReq.setHeader('Cache-Control', 'no-cache');
              
              if (isDevelopment) {
                console.log('📤 Generation API 요청:', req.method, req.url, '→', options.target + proxyReq.path);
              }
            });

            // Prevent proxy buffering for SSE
            proxy.on('proxyRes', (proxyRes, req) => {
              // Prevent buffering for streaming responses
              proxyRes.headers['x-accel-buffering'] = 'no';
              proxyRes.headers['cache-control'] = 'no-cache';
              proxyRes.headers['connection'] = 'keep-alive';
              
              if (isDevelopment) {
                const isSSE = proxyRes.headers['content-type']?.includes('text/event-stream');
                console.log(`📥 Generation API 응답:`, proxyRes.statusCode, req.url, {
                  contentType: proxyRes.headers['content-type'],
                  isSSE,
                  headers: {
                    'x-accel-buffering': proxyRes.headers['x-accel-buffering'],
                    'cache-control': proxyRes.headers['cache-control'],
                  }
                });
              }
            });
          }
        },

        // Legacy proxy paths for backward compatibility
        '/project-api': {
          target: env.VITE_PROJECT_SERVICE_URL || 'http://localhost:8001',
          changeOrigin: true,
          secure: false,
          rewrite: (path) => path.replace(/^\/project-api/, '/api'),
        },
        '/core-api': {
          target: env.VITE_CORE_SERVICE_URL || 'http://localhost:8000',
          changeOrigin: true,
          secure: false,
          rewrite: (path) => path.replace(/^\/core-api/, '/api'),
        },
      },
    },
    build: {
      outDir: 'dist',
      sourcemap: !isDevelopment,
      minify: 'esbuild',
      rollupOptions: {
        output: {
          // Advanced code splitting strategy
          manualChunks: (id) => {
            // Vendor libraries
            if (id.includes('node_modules')) {
              if (id.includes('react') || id.includes('react-dom')) {
                return 'react-vendor'
              }
              if (id.includes('@mui/material') || id.includes('@emotion')) {
                return 'mui-vendor'
              }
              if (id.includes('@mui/icons-material')) {
                return 'mui-icons-vendor'
              }
              if (id.includes('react-router')) {
                return 'router-vendor'
              }
              if (id.includes('@tanstack/react-query')) {
                return 'query-vendor'
              }
              if (id.includes('axios')) {
                return 'http-vendor'
              }
              if (id.includes('react-hook-form')) {
                return 'forms-vendor'
              }
              if (id.includes('react-window')) {
                return 'virtualization-vendor'
              }
              // Other vendor libraries
              return 'vendor'
            }

            // App-specific chunks
            if (id.includes('/pages/dashboard/')) {
              return 'dashboard'
            }
            if (id.includes('/pages/project-')) {
              return 'projects'
            }
            if (id.includes('/pages/episode-')) {
              return 'episodes'
            }
            if (id.includes('/pages/settings/')) {
              return 'settings'
            }
            if (id.includes('/pages/system-status/')) {
              return 'monitoring'
            }
            if (id.includes('/features/script-generation/')) {
              return 'generation'
            }
            if (id.includes('/shared/api/')) {
              return 'api'
            }
            if (id.includes('/shared/ui/')) {
              return 'ui-components'
            }
            
            // Default chunk for unmatched modules
            return undefined
          },
          // Chunk naming strategy
          chunkFileNames: (chunkInfo) => {
            const facadeModuleId = chunkInfo.facadeModuleId
            if (facadeModuleId) {
              const fileName = facadeModuleId.split('/').pop()?.replace('.tsx', '').replace('.ts', '')
              return `assets/[name]-${fileName}.[hash].js`
            }
            return 'assets/[name].[hash].js'
          },
          entryFileNames: 'assets/[name].[hash].js',
          assetFileNames: 'assets/[name].[hash].[ext]',
        },
        plugins: [
          // HTML template variable replacement
          {
            name: 'html-template-vars',
            generateBundle(_, bundle) {
              Object.keys(bundle).forEach(fileName => {
                const chunk = bundle[fileName]
                if (fileName === 'index.html' && chunk && chunk.type === 'asset') {
                  const asset = chunk as { source: string } // OutputAsset has source property
                  if (typeof asset.source === 'string') {
                    asset.source = asset.source
                      .replace(/%VITE_ANALYTICS_TRACKING_ID%/g, env.VITE_ANALYTICS_TRACKING_ID || '')
                      .replace(/%VITE_APP_VERSION%/g, env.npm_package_version || '1.0.0')
                  }
                }
              })
            }
          }
        ],
      },
      // Chunk size warnings
      chunkSizeWarningLimit: 1000,
    },
    // Optimization for development
    optimizeDeps: {
      include: [
        'react',
        'react-dom',
        '@mui/material',
        '@mui/icons-material',
        'react-router-dom',
        '@tanstack/react-query',
        'axios'
      ]
    },
    define: {
      __APP_VERSION__: JSON.stringify(env.npm_package_version),
      __BUILD_TIME__: JSON.stringify(new Date().toISOString()),
      __DEV__: isDevelopment,
    },
    // Production optimizations
    ...(command === 'build' && {
      esbuild: {
        pure: ['console.log', 'console.info'],
        drop: isDevelopment ? [] : ['console', 'debugger'],
      }
    })
  }

  return config
})
