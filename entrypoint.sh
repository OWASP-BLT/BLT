#!/bin/sh
set -x
set -e  # Exit on error
echo "Entrypoint script is running"

# Wait for the database to be ready
until PGPASSWORD=$POSTGRES_PASSWORD psql -h "db" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q'; do
  >&2 echo "Postgres is unavailable - sleeping"
  sleep 1
done

>&2 echo "Postgres is up - executing command"

# Function to check if migrations are applied
check_migrations() {
    python manage.py showmigrations --plan | grep -q "\[ \]"
    return $?
}

# Check if migrations need to be applied
if check_migrations; then
    echo "Migrations need to be applied. Running initialization tasks."

    # Run migrations
    echo "Migration script is running"
    python manage.py migrate

    # Setup GitHub OAuth
    echo "Setting up GitHub OAuth"
    if ! python manage.py setup_github_oauth; then
        echo "ERROR: GitHub OAuth setup failed"
        exit 1
    fi
    echo "GitHub OAuth setup completed successfully"

    # Load initial data
    python manage.py loaddata website/fixtures/initial_data.json

    # Create superuser
    echo "Creating the superuser, if it does not exist!"
    python manage.py initsuperuser

    # Collect static files
    echo "Collecting the static files!"
    python manage.py collectstatic --noinput
else
    echo "All migrations have already been applied. Skipping initialization."
fi

# Start the main application
echo "Starting the main application http://localhost:8000/"
exec python manage.py runserver 0.0.0.0:8000