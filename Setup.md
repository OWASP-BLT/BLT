# Setting up Development server

- [Video on How to setup Project BLT](https://www.youtube.com/watch?v=IYBRVRfPCK8)
  

## Setting Up Development Server using Docker-compose (Recomended)

### Install [Docker](https://docs.docker.com/get-docker/)

```sh
 # Move to project directory
 cd BLT

 # build the docker container
 docker-compose build
 
 # Run the docker container
 docker-compose up

 # Collect static files
 ### get container id
 docker ps

 ### open container bash terminal
 docker exec -it <container id> /bin/bash

 ### migrate SQL commands in the database file
 python manage.py migrate

 ### collect staticfiles
 python manage.py collectstatic
 
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

```sh

 # Install postgres on mac using brew
 brew install postgresql

 # Install postgres on ubuntu
 sudo apt-get install postgresql

 # Install pipenv on ubuntu
 sudo apt-get install pipenv

 # Install pipenv on mac
 pip install pipenv

 # Start virtual env
 pipenv install | pipenv shell

 # Move to project directory
 cd BLT

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

### Alternative using Poetry
```sh
brew install postgresql

# Install postgres on ubuntu
sudo apt-get install postgresql

# Install Poetry
pip install poetry

poetry shell

poetry install

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
