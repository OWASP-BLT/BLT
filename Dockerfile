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

# # Install Chrome WebDriver
# RUN CHROMEDRIVER_VERSION=`curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE` && \
#     mkdir -p /opt/chromedriver-$CHROMEDRIVER_VERSION && \
#     curl -sS -o /tmp/chromedriver_linux64.zip http://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip && \
#     unzip -qq /tmp/chromedriver_linux64.zip -d /opt/chromedriver-$CHROMEDRIVER_VERSION && \
#     rm /tmp/chromedriver_linux64.zip && \
#     chmod +x /opt/chromedriver-$CHROMEDRIVER_VERSION/chromedriver && \
#     ln -fs /opt/chromedriver-$CHROMEDRIVER_VERSION/chromedriver /usr/local/bin/chromedriver

# Install Chromium (works on all architectures)
RUN apt-get update && \
    apt-get install -y chromium && \
    ln -sf /usr/bin/chromium /usr/local/bin/google-chrome && \
    rm -rf /var/lib/apt/lists/*

# Install Poetry and dependencies
RUN pip install poetry
RUN poetry config virtualenvs.create false
COPY pyproject.toml poetry.lock* ./
# Clean any existing httpx installation and update pip
RUN pip uninstall -y httpx || true
RUN pip install --upgrade pip
# Install dependencies with Poetry
RUN poetry install --no-root --no-interaction

# Install additional Python packages
RUN pip install opentelemetry-api opentelemetry-instrumentation

# Stage 2: Runtime stage
FROM python:3.11.2-slim

ENV PYTHONUNBUFFERED 1
WORKDIR /blt

# Copy only necessary files from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Install runtime system dependencies
RUN apt-get update && \
    apt-get install -y postgresql-client libpq-dev \
    libmemcached11 libmemcachedutil2 dos2unix && \
    rm -rf /var/lib/apt/lists/*

# Copy application code
COPY . /blt

# Convert line endings and set permissions
RUN dos2unix Dockerfile docker-compose.yml entrypoint.sh ./blt/settings.py
# Check if .env exists and run dos2unix on it, otherwise skip
RUN if [ -f /blt/.env ]; then dos2unix /blt/.env; fi
RUN chmod +x /blt/entrypoint.sh

ENTRYPOINT ["/blt/entrypoint.sh"]
CMD ["poetry", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]