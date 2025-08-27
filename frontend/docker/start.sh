#!/bin/bash

# Set default service URLs if not provided
export core_service_url=${CORE_SERVICE_URL:-"http://localhost:8000"}
export project_service_url=${PROJECT_SERVICE_URL:-"http://localhost:8001"}
export generation_service_url=${GENERATION_SERVICE_URL:-"http://localhost:8002"}

# Environment variable substitution in nginx config
envsubst '
  $core_service_url
  $project_service_url
  $generation_service_url
' < /etc/nginx/conf.d/default.conf > /tmp/default.conf.tmp

# Move the substituted config
mv /tmp/default.conf.tmp /etc/nginx/conf.d/default.conf

echo "Starting Nginx with backend services:"
echo "Core Service: $core_service_url"
echo "Project Service: $project_service_url"
echo "Generation Service: $generation_service_url"

# Test nginx configuration
nginx -t

# Start nginx in foreground
exec nginx -g "daemon off;"
