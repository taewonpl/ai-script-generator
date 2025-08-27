# Multi-stage build for optimal production image
FROM node:18-alpine AS builder

# Set working directory
WORKDIR /app

# Enable corepack for pnpm
RUN corepack enable

# Copy package files
COPY package.json pnpm-lock.yaml ./

# Install dependencies
RUN pnpm install --force --prod=false

# Copy source code
COPY . .

# Build arguments
ARG VITE_PROJECT_SERVICE_URL
ARG VITE_GENERATION_SERVICE_URL
ARG VITE_ENV=production

# Set environment variables
ENV VITE_PROJECT_SERVICE_URL=$VITE_PROJECT_SERVICE_URL
ENV VITE_GENERATION_SERVICE_URL=$VITE_GENERATION_SERVICE_URL
ENV VITE_ENV=$VITE_ENV
ENV NODE_ENV=production

# Build the application
RUN pnpm run build

# Production stage with Nginx
FROM nginx:alpine AS production

# Install security updates
RUN apk update && apk upgrade && apk add --no-cache bash

# Create nginx user and group
RUN addgroup -g 101 -S nginx || true
RUN adduser -S -D -H -u 101 -h /var/cache/nginx -s /sbin/nologin -G nginx -g nginx nginx || true

# Copy custom nginx configuration
COPY docker/nginx.conf /etc/nginx/nginx.conf
COPY docker/default.conf /etc/nginx/conf.d/default.conf

# Copy built application from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy startup script
COPY docker/start.sh /start.sh
RUN chmod +x /start.sh

# Create necessary directories
RUN mkdir -p /var/cache/nginx /var/log/nginx /var/run
RUN chown -R nginx:nginx /var/cache/nginx /var/log/nginx /var/run /usr/share/nginx/html

# Set up health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost/ || exit 1

# Expose port
EXPOSE 80

# Use non-root user
USER nginx

# Start nginx
CMD ["/start.sh"]
