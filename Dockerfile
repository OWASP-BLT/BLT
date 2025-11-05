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