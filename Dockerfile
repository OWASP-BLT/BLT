# Stage 1: Build stage
FROM python:3.11.2 AS builder

ENV PYTHONUNBUFFERED=1
WORKDIR /blt

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    wget gnupg unzip postgresql-client libpq-dev \
    libmemcached11 libmemcachedutil2 libmemcached-dev libz-dev dos2unix && \
    rm -rf /var/lib/apt/lists/*

# Install Google Chrome (using new keyring method)
RUN mkdir -p /usr/share/keyrings && \
    wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" \
    > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update -yqq && \
    apt-get install -yqq google-chrome-stable && \
    rm -rf /var/lib/apt/lists/*

# Optional: Create Chrome shortcut
RUN ln -s /usr/bin/google-chrome-stable /usr/local/bin/google-chrome

# Install Poetry and dependencies
RUN pip install --no-cache-dir poetry
RUN poetry config virtualenvs.create false
COPY pyproject.toml poetry.lock* ./

# Clean any existing httpx installation and update pip
RUN pip uninstall -y httpx || true && \
    pip install --no-cache-dir --upgrade pip

# Install dependencies with Poetry
RUN poetry install --no-root --no-interaction

# Additional Python packages
RUN pip install --no-cache-dir opentelemetry-api opentelemetry-instrumentation

# Stage 2: Runtime stage
FROM python:3.11.2-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /blt

# Copy necessary files from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    postgresql-client libpq-dev libmemcached11 libmemcachedutil2 dos2unix && \
    rm -rf /var/lib/apt/lists/*

# Copy application code
COPY . /blt

# Normalize line endings and set permissions
RUN dos2unix Dockerfile docker-compose.yml entrypoint.sh ./blt/settings.py && \
    if [ -f /blt/.env ]; then dos2unix /blt/.env; fi && \
    chmod +x /blt/entrypoint.sh

ENTRYPOINT ["/blt/entrypoint.sh"]
CMD ["poetry", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]