# Stage 1: Build stage
FROM python:3.11.2 AS builder

ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
WORKDIR /blt

# Install system dependencies
RUN apt-get update && \
    apt-get install -y postgresql-client libpq-dev \
    libmemcached11 libmemcachedutil2 libmemcached-dev libz-dev \
    dos2unix && \
    rm -rf /var/lib/apt/lists/*

# Install Chromium (works on all architectures)
RUN apt-get update \
    && apt-get install -y --fix-missing chromium \
    || (apt-get update && apt-get install -y --fix-missing chromium) \
    && ln -sf /usr/bin/chromium /usr/local/bin/google-chrome \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first (for better caching)
COPY pyproject.toml uv.lock* ./

# Install dependencies only (not the project itself)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Copy application code
COPY . /blt

# Install the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Install additional Python packages
RUN uv pip install opentelemetry-api opentelemetry-instrumentation

# Stage 2: Runtime stage
FROM python:3.11.2-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /blt

# Install runtime system dependencies
RUN apt-get update && \
    apt-get install -y postgresql-client libpq-dev \
    libmemcached11 libmemcachedutil2 dos2unix && \
    rm -rf /var/lib/apt/lists/*

# Copy uv binary from builder
COPY --from=builder /usr/local/bin/uv /usr/local/bin/uv

# Copy virtual environment from builder
COPY --from=builder /blt/.venv /blt/.venv

# Copy application code
COPY . /blt

# Convert line endings and set permissions
RUN dos2unix Dockerfile docker-compose.yml scripts/entrypoint.sh ./blt/settings.py
RUN if [ -f /blt/.env ]; then dos2unix /blt/.env; fi
RUN chmod +x /blt/scripts/entrypoint.sh

ENTRYPOINT ["/blt/scripts/entrypoint.sh"]
CMD ["uv", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]
