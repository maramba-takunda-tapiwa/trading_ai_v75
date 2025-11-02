# Multi-stage build for Trading AI Dashboard

# Stage 1: Python backend + Nginx
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    nginx \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python requirements
COPY requirements-docker.txt .
RUN pip install --no-cache-dir -r requirements-docker.txt

# Copy Flask app and the public directory
COPY docker_app/app.py ./app.py
COPY docker_app/public ./public

# Copy Nginx config
COPY docker_app/nginx.conf /etc/nginx/nginx.conf

# Create data directory
RUN mkdir -p /app/data/results /app/data/backtests

# Copy trading system files
COPY backtests/ /app/data/backtests/
COPY deploy_complete.py /app/data/
COPY SOLUTION_SUMMARY.txt /app/data/

# Expose ports
EXPOSE 80 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/api/health || exit 1

# Start script
COPY docker_app/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
