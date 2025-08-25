# Multi-stage build for optimal production image
FROM node:18-alpine AS builder

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production --silent

# Copy source code
COPY . .

# Build arguments
ARG REACT_APP_CORE_SERVICE_URL
ARG REACT_APP_PROJECT_SERVICE_URL
ARG REACT_APP_GENERATION_SERVICE_URL
ARG REACT_APP_ENV=production

# Set environment variables
ENV REACT_APP_CORE_SERVICE_URL=$REACT_APP_CORE_SERVICE_URL
ENV REACT_APP_PROJECT_SERVICE_URL=$REACT_APP_PROJECT_SERVICE_URL
ENV REACT_APP_GENERATION_SERVICE_URL=$REACT_APP_GENERATION_SERVICE_URL
ENV REACT_APP_ENV=$REACT_APP_ENV
ENV NODE_ENV=production

# Build the application
RUN npm run build

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
