# Stage 1: Build stage
FROM python:3.11.2 AS builder

ENV PYTHONUNBUFFERED=1
WORKDIR /blt

# Install system dependencies
RUN apt-get update && \
    apt-get install -y postgresql-client libpq-dev \
    libmemcached11 libmemcachedutil2 libmemcached-dev libz-dev \
    dos2unix \
    # OpenCV dependencies
    libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1 \
    libgtk-3-0 libavcodec-dev libavformat-dev libswscale-dev \
    libgstreamer-plugins-base1.0-dev libgstreamer1.0-dev \
    libpng-dev libjpeg-dev libopenexr-dev libtiff-dev libwebp-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Chromium (works on all architectures)
# Retry logic with --fix-missing for transient network errors
RUN apt-get update \
    && apt-get install -y --fix-missing chromium \
    || (apt-get update && apt-get install -y --fix-missing chromium) \
    && ln -sf /usr/bin/chromium /usr/local/bin/google-chrome \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry and dependencies (Pinned to 2.2.1 to fix CI/CD conflicts)
RUN pip install --upgrade pip && \
    pip install poetry==2.2.1
RUN poetry config virtualenvs.create false
COPY pyproject.toml poetry.lock* ./

# Clean any existing httpx installation
RUN pip uninstall -y httpx || true
RUN pip install --upgrade pip
# Install dependencies with Poetry
RUN poetry install --no-root --no-interaction || \
    (echo "First attempt failed, clearing Poetry cache..." && \
     poetry cache clear pypi --all -n && \
     sleep 5 && \
     poetry install --no-root --no-interaction -vvv) || \
    (echo "Second attempt failed, final retry..." && \
     sleep 10 && \
     poetry install --no-root --no-interaction -vvv)
# Install additional Python packages
RUN pip install opentelemetry-api opentelemetry-instrumentation

# Stage 2: Runtime stage
FROM python:3.11.2-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /blt

# Copy only necessary files from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Install runtime system dependencies
RUN apt-get update && \
    apt-get install -y postgresql-client libpq-dev \
    libmemcached11 libmemcachedutil2 dos2unix \
    libglib2.0-0 libsm6 libxext6 libxrender1 libgomp1 \
    libgtk-3-0 libavcodec58 libavformat58 libswscale5 \
    libgstreamer-plugins-base1.0-0 libgstreamer1.0-0 \
    libpng16-16 libjpeg62-turbo libopenexr25 libtiff5 libwebp6 && \
    rm -rf /var/lib/apt/lists/*

# Copy application code
COPY . /blt

# Convert line endings and set permissions
RUN dos2unix Dockerfile docker-compose.yml scripts/entrypoint.sh ./blt/settings.py
# Check if .env exists and run dos2unix on it, otherwise skip
RUN if [ -f /blt/.env ]; then dos2unix /blt/.env; fi
RUN chmod +x /blt/scripts/entrypoint.sh

ENTRYPOINT ["/blt/scripts/entrypoint.sh"]
CMD ["poetry", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]