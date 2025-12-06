#!/bin/bash

# Function to check if UV is installed
check_uv() {
    if command -v uv &> /dev/null
    then
        echo "UV is installed."
        return 0
    else
        echo "UV is not installed. Please install it first: https://docs.astral.sh/uv/getting-started/installation/"
        return 1
    fi
}

# Function to check if Docker is installed
check_docker() {
    if command -v docker &> /dev/null
    then
        echo "Docker is installed."
        return 0
    else
        echo "Docker is not installed. Please install it first: https://docs.docker.com/get-docker/"
        return 1
    fi
}

# Function to set up the project using UV
setup_uv() {

    check_uv || exit 1

    echo "Setting up the project using UV..."

    echo "Updating UV to the latest version..."
    uv self update

    echo "Installing project dependencies..."
    uv sync
    source .venv/bin/activate

    echo "Running migrations..."
    uv run python manage.py migrate

    echo "Collecting static files..."
    uv run python manage.py collectstatic --noinput

    echo "UV setup complete!"
    echo "To start the Django server, use:"
    echo "uv run python manage.py runserver"
}

# Function to set up the project using Docker
setup_docker() {
    echo "Setting up the project using Docker..."

    # Make sure Docker is running
    if ! docker info &> /dev/null; then
        echo "Docker is not running. Please start Docker first."
        exit 1
    fi


    echo "Building Docker container..."
    sudo docker-compose up --build -d

    container_id=$(sudo docker ps -q --filter "name=owasp-blt_app")

    if [ -z "$container_id" ]; then
        echo "Container 'owasp-blt_app' not running. Starting container..."
        sudo docker-compose up -d
        container_id=$(sudo docker ps -q --filter "name=owasp-blt_app")
    else
        echo "Container 'owasp-blt_app' is already running."
    fi

    echo "Running migrations in Docker..."
    sudo docker exec -it "$container_id" python manage.py migrate

    echo "Running collectstatic in Docker..."
    sudo docker exec -it "$container_id" python manage.py collectstatic --noinput

    mapped_port=$(sudo docker port "$container_id" 8000 | cut -d ':' -f 2)

    if [ -z "$mapped_port" ]; then
        mapped_port=8000
    fi

    echo "Docker setup complete!"
    echo "To access the Django application, visit the following URL in your browser:"
    echo "http://localhost:$mapped_port"
}

# Main function to choose setup method
main() {
    echo "Setting up the Django project..."


    if check_uv; then
        read -p "Do you want to proceed with UV setup? (y/n): " choice
        if [[ "$choice" == "y" ]]; then
            setup_uv
        else
            echo "Skipping UV setup."
        fi
    else
        echo "UV is not installed, moving to Docker setup."
    fi

    if ! check_uv || [[ "$choice" == "n" ]]; then
        if check_docker; then
            read -p "Do you want to proceed with Docker setup? (y/n): " choice
            if [[ "$choice" == "y" ]]; then
                setup_docker
            else
                echo "Setup aborted. Please install UV or Docker and rerun the script."
                exit 1
            fi
        else
            echo "Neither UV nor Docker is installed. Setup cannot continue."
            exit 1
        fi
    fi
}

main
