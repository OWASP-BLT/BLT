# ======================
# Stage 1: Build Stage
# ======================
FROM python:3.11.2 AS builder

ENV PYTHONUNBUFFERED=1
WORKDIR /blt

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    postgresql-client libpq-dev libmemcached11 libmemcachedutil2 libmemcached-dev libz-dev dos2unix wget gnupg && \
    rm -rf /var/lib/apt/lists/*

# Install Google Chrome or Chromium (for GitHub Actions compatibility)
RUN ARCH=$(dpkg --print-architecture) && \
    if [ "$ARCH" = "amd64" ]; then \
        wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-linux.gpg && \
        echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-linux.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
        apt-get update && apt-get install -y --no-install-recommends google-chrome-stable; \
    else \
        apt-get update && apt-get install -y --no-install-recommends chromium && \
        ln -s /usr/bin/chromium /usr/local/bin/google-chrome; \
    fi && \
    rm -rf /var/lib/apt/lists/*

# Install Poetry and dependencies
RUN pip install --upgrade pip && pip install poetry
RUN poetry config virtualenvs.create false

COPY pyproject.toml poetry.lock* ./
RUN pip uninstall -y httpx || true
RUN poetry install --no-root --no-interaction

# Install additional Python packages for observability
RUN pip install opentelemetry-api opentelemetry-instrumentation


# ======================
# Stage 2: Runtime Stage
# ======================
FROM python:3.11.2-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /blt

# Install minimal runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    postgresql-client libpq-dev libmemcached11 libmemcachedutil2 dos2unix && \
    rm -rf /var/lib/apt/lists/*

# Copy Python environment and binaries from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . /blt

# Convert line endings and set permissions
RUN dos2unix Dockerfile docker-compose.yml entrypoint.sh ./blt/settings.py || true
RUN if [ -f /blt/.env ]; then dos2unix /blt/.env; fi
RUN chmod +x /blt/entrypoint.sh

# Entry point for the container
ENTRYPOINT ["/blt/entrypoint.sh"]

# Default command — runs server in development mode
CMD ["poetry", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]
