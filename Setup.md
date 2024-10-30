# Setting up Development server

- [Video on How to setup Project BLT](https://www.youtube.com/watch?v=IYBRVRfPCK8)

## Setting Up Development Server using Docker-compose (Recommended)

### Install [Docker](https://docs.docker.com/get-docker/)

```sh
 # --- Move to project directory ---
 cd BLT

 # --- build the docker container ---
 docker-compose build

 # --- Run the docker container ---
 docker-compose up

 # --- Collect static files ---

 ### open container bash terminal
 # `app` is the service name in docker-compose.yml
 docker exec -it app /bin/bash

 # Below commands are for container shell
 ### migrate SQL commands in the database file
 python manage.py migrate

 ### collect staticfiles
 python manage.py collectstatic

 # --- exit out of container shell ---
 exit

```

## Setting Up Development Server using Vagrant

### Install [Vagrant](https://www.vagrantup.com/)

### Get [Virtualbox](https://www.virtualbox.org/)

### Follow the given commands

```sh
 # Move to project directory
 cd BLT

 # Start vagrant - It takes time during the first run, so go get a coffee!
 vagrant up

 # SSH into vagrant
 vagrant ssh

 # Move to project directory
 cd BLT

 # Create tables in the database
 python manage.py migrate

 # Create a super user
 python manage.py createsuperuser

 # Collect static files
 python manage.py collectstatic

 # Run the server
 python manage.py runserver
```

### Ready to go

Then go to `http://127.0.0.1:8000/admin/socialaccount/socialapp/` and add filler information for social auth accounts.
Add a Domain `http://127.0.0.1:8000/admin/website/domain/` with the name 'owasp.org'.

### Voila go visit `http://localhost:8000`

**Note:** In case you encounter an error with vagrant's vbguest module, run `vagrant plugin install vagrant-vbguest`
from the host machine.

## Setting Up Development Server using Python Virtual Environment

### Setup Correct python version

Current supported python version is `3.11.2`. It can be installed using any tool of choice like `asdf`, `pyenv`, `hatch`.
For this guide, we are using `pyenv`. Install pyenv by following instructions in its [Github Repo](https://github.com/pyenv/pyenv?tab=readme-ov-file#installation)

```sh
pyenv install 3.11.2

```

Note: Project root folder already contains `.python-version`, so pyenv can recognize the local version to use for the current project.

### Setup Virtual environment using poetry

Ensure that `python -V` returns the correct python version for the project

```sh
# --- Install postgres ---

# Install postgres on mac
brew install postgresql

# Install postgres on ubuntu
sudo apt-get install postgresql

# --- Setup Virtual Environment ---
# Install Poetry
pip install poetry

# Activate virtual environment
poetry shell

# Install required dependencies
poetry install

# --- Project setup ---
# Create tables in the database
python manage.py migrate

# Load initial data
python3 manage.py loaddata website/fixtures/initial_data.json

# Create a super user
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic

# Run the server
python manage.py runserver
```

### Ready to go now

Then go to `http://127.0.0.1:8000/admin/socialaccount/socialapp/` and add filler information for social auth accounts.
Add a Domain `http://127.0.0.1:8000/admin/website/domain/` with the name 'owasp.org'.

### Visit `http://localhost:8000`

**Note:** In case you encounter an error, run `sudo apt-get install libpq-dev`.

## Detailed Instructions for Setting Up Development Environment

### Docker

1. **Building the Docker Image**:
   - Ensure Docker is installed on your system.
   - Navigate to the project directory: `cd BLT`
   - Build the Docker container: `docker-compose build`

2. **Running the Docker Container**:
   - Start the Docker container: `docker-compose up`
   - Open the container bash terminal: `docker exec -it app /bin/bash`
   - Migrate SQL commands in the database file: `python manage.py migrate`
   - Collect static files: `python manage.py collectstatic`
   - Exit out of the container shell: `exit`

3. **Managing the Docker Container**:
   - To stop the Docker container: `docker-compose down`
   - To restart the Docker container: `docker-compose restart`

4. **Common Docker Commands**:
   - List running containers: `docker ps`
   - Stop a container: `docker stop <container_id>`
   - Remove a container: `docker rm <container_id>`

5. **Troubleshooting Tips**:
   - If you encounter issues with Docker, ensure that Docker is running and you have the necessary permissions.
   - Check the Docker logs for any error messages: `docker logs <container_id>`

### Vagrant

1. **Installing Vagrant and VirtualBox**:
   - Install Vagrant from [here](https://www.vagrantup.com/)
   - Install VirtualBox from [here](https://www.virtualbox.org/)

2. **Setting Up the Vagrant Environment**:
   - Navigate to the project directory: `cd BLT`
   - Start Vagrant: `vagrant up`
   - SSH into Vagrant: `vagrant ssh`
   - Move to the project directory: `cd BLT`
   - Create tables in the database: `python manage.py migrate`
   - Create a super user: `python manage.py createsuperuser`
   - Collect static files: `python manage.py collectstatic`
   - Run the server: `python manage.py runserver`

3. **Managing the Vagrant Environment**:
   - To halt the Vagrant environment: `vagrant halt`
   - To reload the Vagrant environment: `vagrant reload`
   - To destroy the Vagrant environment: `vagrant destroy`

4. **Common Vagrant Commands**:
   - List all Vagrant environments: `vagrant global-status`
   - Suspend the Vagrant environment: `vagrant suspend`
   - Resume the Vagrant environment: `vagrant resume`

5. **Troubleshooting Tips**:
   - If you encounter issues with Vagrant, ensure that VirtualBox is installed and running.
   - Check the Vagrant logs for any error messages: `vagrant up --debug`

### Python Virtual Environment

1. **Setting Up the Python Version**:
   - Ensure the correct Python version is installed: `pyenv install 3.11.2`
   - Set the local Python version: `pyenv local 3.11.2`

2. **Setting Up the Virtual Environment**:
   - Install Poetry: `pip install poetry`
   - Activate the virtual environment: `poetry shell`
   - Install required dependencies: `poetry install`

3. **Project Setup**:
   - Create tables in the database: `python manage.py migrate`
   - Load initial data: `python3 manage.py loaddata website/fixtures/initial_data.json`
   - Create a super user: `python manage.py createsuperuser`
   - Collect static files: `python manage.py collectstatic`
   - Run the server: `python manage.py runserver`

4. **Managing the Virtual Environment**:
   - To deactivate the virtual environment: `exit`
   - To reactivate the virtual environment: `poetry shell`

5. **Common Commands**:
   - List installed packages: `poetry show`
   - Add a new dependency: `poetry add <package_name>`
   - Remove a dependency: `poetry remove <package_name>`

6. **Troubleshooting Tips**:
   - If you encounter issues with the virtual environment, ensure that the correct Python version is being used.
   - Check the Poetry logs for any error messages: `poetry install -vvv`
