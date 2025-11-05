# Start from an official Python image
FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    pkg-config \
    libsecp256k1-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH
ENV PATH="/root/.local/bin:$PATH"

# Copy dependency files first for caching
COPY pyproject.toml poetry.lock ./

# Install Python dependencies
RUN poetry install --no-root --no-interaction --no-ansi

# Copy the rest of the project
COPY . .

# Expose the port Django runs on
EXPOSE 8000

# Note: This Dockerfile is for local development.
# For production, use Gunicorn or uWSGI instead of runserver.
CMD ["poetry", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]
