# Stage 1: Build stage
FROM python:3.11.2 AS builder

ENV PYTHONUNBUFFERED 1
WORKDIR /blt

# Install system dependencies
RUN apt-get update && \
    apt-get install -y postgresql-client libpq-dev \
    libmemcached11 libmemcachedutil2 libmemcached-dev libz-dev \
    dos2unix && \
    rm -rf /var/lib/apt/lists/*

# Install Google Chrome or Chromium (auto-detect platform)
RUN apt-get update && apt-get install -y wget gnupg && \
    ARCH=$(dpkg --print-architecture) && \
    if [ "$ARCH" = "amd64" ]; then \
        wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-linux.gpg && \
        echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-linux.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
        apt-get update && apt-get install -y google-chrome-stable; \
    else \
        apt-get install -y chromium; \
        ln -s /usr/bin/chromium /usr/local/bin/google-chrome; \
    fi && \
    rm -rf /var/lib/apt/lists/*


# Install Poetry and dependencies
RUN pip install poetry
RUN poetry config virtualenvs.create false
COPY pyproject.toml poetry.lock* ./
RUN pip uninstall -y httpx || true
RUN pip install --upgrade pip
RUN poetry install --no-root --no-interaction
RUN pip install opentelemetry-api opentelemetry-instrumentation

# Stage 2: Runtime stage
FROM python:3.11.2-slim

ENV PYTHONUNBUFFERED 1
WORKDIR /blt

# Install Poetry directly in runtime (Option 2)
RUN pip install poetry

# Install runtime system dependencies
RUN apt-get update && \
    apt-get install -y postgresql-client libpq-dev \
    libmemcached11 libmemcachedutil2 dos2unix && \
    rm -rf /var/lib/apt/lists/*

# Copy application files and Python deps
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY . /blt

# Convert line endings and fix permissions
RUN dos2unix Dockerfile docker-compose.yml entrypoint.sh ./blt/settings.py
RUN if [ -f /blt/.env ]; then dos2unix /blt/.env; fi
RUN chmod +x /blt/entrypoint.sh

ENTRYPOINT ["/blt/entrypoint.sh"]
CMD ["poetry", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]
