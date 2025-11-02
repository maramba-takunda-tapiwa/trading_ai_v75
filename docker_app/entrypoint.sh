#!/bin/bash
set -e

echo "Starting Trading AI Dashboard..."

# Start Flask in background
echo "Starting Flask API server..."
python /app/app.py &
FLASK_PID=$!

# Wait for Flask to start
sleep 2

# Start Nginx
echo "Starting Nginx..."
nginx -g 'daemon off;' &
NGINX_PID=$!

# Function to handle shutdown
cleanup() {
    echo "Shutting down gracefully..."
    kill $FLASK_PID 2>/dev/null || true
    kill $NGINX_PID 2>/dev/null || true
    exit 0
}

# Trap signals
trap cleanup SIGTERM SIGINT

# Wait for processes
wait
