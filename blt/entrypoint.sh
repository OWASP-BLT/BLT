#!/bin/sh

# Start Redis server in the background
redis-server &

# Start the Django development server
poetry run python manage.py runserver 0.0.0.0:8000
