# DOCKERFILE DISABLED - USE POETRY ONLY
# This project uses Poetry for dependency management and local development.
# Docker-related files have been intentionally disabled per project preference.
# To run the site locally with Poetry, run the following from the project root:
#
# cd /Users/aaradhychinche/Documents/blt/BLT
# poetry install
# poetry run pre-commit install || true
# poetry run pre-commit run --all-files || true
# poetry run python manage.py migrate --noinput
# poetry run python manage.py collectstatic --noinput
# poetry run python manage.py runserver 0.0.0.0:8000
#
# If you later decide to re-enable Docker, restore or replace this file with a proper Dockerfile.
# syntax=docker/dockerfile:1

FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install Poetry
RUN pip install poetry

# Copy project files
COPY pyproject.toml poetry.lock* /app/

# Install dependencies
RUN poetry install --no-root

# Copy rest of the app
COPY . /app

# Expose the port Django will run on
EXPOSE 8000

# Run Django server
CMD ["poetry", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]
