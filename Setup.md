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
