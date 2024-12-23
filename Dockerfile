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


RUN apt-get install -y wget
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \ 
    && echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list
RUN apt-get update && apt-get -y install google-chrome-stable


# Install chromedriver (matching installed chrome version)
RUN CHROME_VERSION=$(google-chrome-stable --version | awk '{print $3}' | sed 's/\..*//') && \
    wget https://chromedriver.storage.googleapis.com/${CHROME_VERSION}.0/chromedriver_linux64.zip && \
    unzip chromedriver_linux64.zip -d /usr/local/bin/ && \
    rm chromedriver_linux64.zip

# Install Poetry and dependencies
RUN pip install poetry
RUN poetry config virtualenvs.create false
COPY pyproject.toml poetry.lock* ./
RUN poetry install

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
RUN chmod +x /blt/entrypoint.sh

ENTRYPOINT ["/blt/entrypoint.sh"]
CMD ["poetry", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]