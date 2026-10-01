# Production-ready Dockerfile for MachIntel Backend & Worker
FROM python:3.13-slim

WORKDIR /app

# Install system dependencies for PostgreSQL client, build tools, curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies with caching optimizations
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root system user for security
RUN groupadd -g 10001 machintel && \
    useradd -u 10001 -g machintel -m -s /bin/bash machintel && \
    mkdir -p /app/storage /app/data && \
    chown -R machintel:machintel /app

# Copy application source code and migrations
COPY backend /app/backend
COPY backend/docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["api"]
