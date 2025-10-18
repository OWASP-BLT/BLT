# Stage 1: Build stage
FROM python:3.11.2 AS builder

WORKDIR /blt

# Install system dependencies and Chrome
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl ca-certificates gnupg && \
    curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg && \
    chmod 644 /usr/share/keyrings/google-chrome.gpg && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && \
    apt-get install -y google-chrome-stable && \
    rm -rf /var/lib/apt/lists/*

# Stage 2: Runtime stage
FROM python:3.11.2-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.5.0 /uv /uvx /bin/

# Project work directory
WORKDIR /blt

# Environment variables
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONDONTWRITEBYTECODE=1

# Install runtime system dependencies
RUN apt-get update && apt-get install -y \
    --no-install-recommends postgresql-client libpq-dev \
    libmemcached11 libmemcachedutil2 dos2unix && \
    rm -rf /var/lib/apt/lists/*

# Install the project's dependencies using the lockfile
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project && \
    rm -rf /blt/.venv

# Add the project source code and install it
COPY . /blt
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen && \
    rm -rf /blt/.venv

# Copy Chrome from builder stage
COPY --from=builder /opt/google/chrome /opt/google/chrome
COPY --from=builder /usr/bin/google-chrome-stable /usr/bin/google-chrome-stable
RUN ln -s /usr/bin/google-chrome-stable /usr/local/bin/google-chrome

# Convert line endings and set permissions
RUN dos2unix docker-compose.yml entrypoint.sh ./blt/settings.py
RUN if [ -f /blt/.env ]; then dos2unix /blt/.env; fi
RUN chmod +x /blt/entrypoint.sh

ENTRYPOINT ["/blt/entrypoint.sh"]
CMD ["uv", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]