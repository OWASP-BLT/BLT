# Build stage: Install dependencies
FROM python:3.11.2 AS builder

ENV PYTHONUNBUFFERED=1
WORKDIR /blt

# Install build dependencies
RUN apt-get update && \
    apt-get install -y postgresql-client libpq-dev \
    libmemcached11 libmemcachedutil2 libmemcached-dev libz-dev \
    dos2unix && \
    rm -rf /var/lib/apt/lists/*

# Install Chromium
RUN apt-get update && \
    apt-get install -y --fix-missing chromium \
    || (apt-get update && apt-get install -y --fix-missing chromium) && \
    ln -sf /usr/bin/chromium /usr/local/bin/google-chrome && \
    rm -rf /var/lib/apt/lists/*

# Copy UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy manifests
COPY pyproject.toml uv.lock ./

# Install dependencies ONLY (Fixes missing source error)
RUN uv sync --locked --compile-bytecode --no-install-project

# Runtime stage
FROM python:3.11.2-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /blt
ENV PATH="/blt/.venv/bin:$PATH"

# Copy UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install runtime libs
RUN apt-get update && \
    apt-get install -y postgresql-client libpq-dev \
    libmemcached11 libmemcachedutil2 dos2unix && \
    rm -rf /var/lib/apt/lists/*

# Copy virtualenv from builder
COPY --from=builder /blt/.venv /blt/.venv

# Copy source code
COPY . /blt

# Install the project itself now that source is present
RUN uv sync --locked --compile-bytecode

# Fix line endings and permissions
RUN dos2unix docker-compose.yml scripts/entrypoint.sh ./blt/settings.py
RUN if [ -f /blt/.env ]; then dos2unix /blt/.env; fi
RUN chmod +x /blt/scripts/entrypoint.sh

ENTRYPOINT ["/blt/scripts/entrypoint.sh"]
CMD ["uv", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]
