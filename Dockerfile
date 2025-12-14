# Build stage: Install dependencies and tools
FROM python:3.11.2 AS builder

ENV PYTHONUNBUFFERED=1
WORKDIR /blt

# Install system dependencies required for Python packages
RUN apt-get update && \
    apt-get install -y postgresql-client libpq-dev \
    libmemcached11 libmemcachedutil2 libmemcached-dev libz-dev \
    dos2unix && \
    rm -rf /var/lib/apt/lists/*

# Install Chromium for Selenium tests
# Retry logic handles transient network errors
RUN apt-get update && \
    apt-get install -y --fix-missing chromium \
    || (apt-get update && apt-get install -y --fix-missing chromium) && \
    ln -sf /usr/bin/chromium /usr/local/bin/google-chrome && \
    rm -rf /var/lib/apt/lists/*

# Copy UV package manager from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency manifests first (enables layer caching)
COPY pyproject.toml uv.lock ./

# Install Python dependencies using UV
# UV_LINK_MODE=copy prevents cross-filesystem hardlink warnings
RUN UV_LINK_MODE=copy uv sync --frozen --no-install-project --no-group dev

# Runtime stage: Minimal production image
FROM python:3.11.2-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /blt
ENV PATH="/blt/.venv/bin:$PATH"

# Copy UV and installed dependencies from builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY --from=builder /blt/.venv /blt/.venv

# Install runtime system dependencies only
RUN apt-get update && \
    apt-get install -y postgresql-client libpq-dev \
    libmemcached11 libmemcachedutil2 dos2unix && \
    rm -rf /var/lib/apt/lists/*

# Copy application code
COPY . /blt

# Fix line endings for cross-platform compatibility
RUN dos2unix Dockerfile docker-compose.yml scripts/entrypoint.sh ./blt/settings.py
RUN if [ -f /blt/.env ]; then dos2unix /blt/.env; fi
RUN chmod +x /blt/scripts/entrypoint.sh

ENTRYPOINT ["/blt/scripts/entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
