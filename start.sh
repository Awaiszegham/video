#!/bin/bash

# Audio/Video Processing API Startup Script

set -e

echo "Starting Audio/Video Processing API..."

# Check if Redis is running
if ! redis-cli ping > /dev/null 2>&1; then
    echo "Starting Redis server..."
    redis-server --daemonize yes
    sleep 2
fi

# Create necessary directories
mkdir -p uploads processed videos storage logs

# Set environment variables if not set
export REDIS_URL=${REDIS_URL:-"redis://localhost:6379/0"}
export UPLOAD_DIR=${UPLOAD_DIR:-"./uploads"}
export PROCESSED_DIR=${PROCESSED_DIR:-"./processed"}
export DOWNLOAD_DIR=${DOWNLOAD_DIR:-"./videos"}

# Start Celery worker in background
echo "Starting Celery worker..."
celery -A celery_app worker --loglevel=info --detach --pidfile=celery_worker.pid

# Start Celery flower for monitoring (optional)
if [ "$ENABLE_FLOWER" = "true" ]; then
    echo "Starting Celery Flower..."
    celery -A celery_app flower --port=5555 --detach --pidfile=celery_flower.pid
fi

# Start the FastAPI application
echo "Starting FastAPI application..."
if [ "$ENVIRONMENT" = "production" ]; then
    # Production mode with Gunicorn
    gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT:-8000}
else
    # Development mode with Uvicorn
    uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --reload
fi

