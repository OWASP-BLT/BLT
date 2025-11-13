#!/usr/bin/env bash
set -e  # Exit immediately if a command exits with a non-zero status

echo "Starting OWASP-BLT Docker container..."

# Load .env if it exists
if [ -f /blt/.env ]; then
  echo "Loading environment variables from .env..."
  export $(grep -v '^#' /blt/.env | xargs)
else
  echo "No .env file found, using default settings."
fi

# Ensure Poetry is available (optional, just for dev convenience)
if ! command -v poetry >/dev/null 2>&1; then
  echo "Poetry not found in PATH, installing..."
  pip install --upgrade pip poetry
fi

# Apply Django migrations (ignore errors if already applied)
echo "Applying Django migrations..."
python manage.py migrate --noinput || true

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput || true

# Start Django development server
echo "Starting Django development server..."
exec python manage.py runserver 0.0.0.0:8000
