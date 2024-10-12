# Docker Setup Instructions

## Building the Docker Image

1. Ensure Docker is installed on your system.
2. Navigate to the project directory:
   ```sh
   cd BLT
   ```
3. Build the Docker container:
   ```sh
   docker-compose build
   ```

## Running the Docker Container

1. Start the Docker container:
   ```sh
   docker-compose up
   ```
2. Open the container bash terminal:
   ```sh
   docker exec -it app /bin/bash
   ```
3. Migrate SQL commands in the database file:
   ```sh
   python manage.py migrate
   ```
4. Collect static files:
   ```sh
   python manage.py collectstatic
   ```
5. Exit out of the container shell:
   ```sh
   exit
   ```

## Managing the Docker Container

1. To stop the Docker container:
   ```sh
   docker-compose down
   ```
2. To restart the Docker container:
   ```sh
   docker-compose restart
   ```

## Common Docker Commands

1. List running containers:
   ```sh
   docker ps
   ```
2. Stop a container:
   ```sh
   docker stop <container_id>
   ```
3. Remove a container:
   ```sh
   docker rm <container_id>
   ```

## Troubleshooting Tips

1. If you encounter issues with Docker, ensure that Docker is running and you have the necessary permissions.
2. Check the Docker logs for any error messages:
   ```sh
   docker logs <container_id>
   ```
3. Ensure that the Docker daemon is running and properly configured.
4. Verify that the Docker Compose file is correctly set up and there are no syntax errors.
5. If you encounter network-related issues, check your firewall and network settings to ensure Docker can communicate properly.
