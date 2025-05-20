# GitHub Copilot Setup Guide for BLT

This document provides a comprehensive guide for setting up the BLT development environment with GitHub Copilot assistance.

## Environment Options

You can set up BLT using one of the following methods:

1. **Docker (Recommended)** - Uses containers to isolate the environment
2. **Poetry** - Uses Python virtual environments with Poetry dependency management
3. **Vagrant** - Uses a virtual machine for development

## Common Setup Steps

Regardless of your chosen method, you'll need to:

1. Clone the repository
2. Configure environment variables
3. Set up the database
4. Run the application
5. Perform post-setup configuration

## Docker Setup (Recommended)

### Prerequisites
- Docker
- Docker Compose
- PostgreSQL client (optional, for manual database interaction)

### Steps

1. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

2. **Ensure LF line endings**
   ```bash
   git config --global core.autocrlf input
   ```
   
   For existing files with incorrect line endings:
   ```bash
   dos2unix entrypoint.sh docker-compose.yml Dockerfile ./blt/settings.py .env
   ```

3. **Build Docker images**
   ```bash
   docker-compose build
   ```

4. **Start containers**
   ```bash
   docker-compose up
   ```

5. **Access the application**
   - Open your browser and navigate to: http://localhost:8000/
   - Use incognito mode to avoid SSL redirect issues

6. **Post-setup configuration**
   - Visit http://localhost:8000/admin/socialaccount/socialapp/ and add social auth accounts
   - Add a Domain at http://localhost:8000/admin/website/domain/ with the name 'owasp.org'

### Troubleshooting Docker Setup

- **Line ending issues**
  - Ensure files use LF line endings, not CRLF
  - Run: `chmod +x ./entrypoint.sh`

- **PostgreSQL port conflicts**
  - Change `POSTGRES_PORT` in `.env` if the default port 5432 is already in use

- **SSL redirect issues**
  - Set `SECURE_SSL_REDIRECT=False` in `/blt/settings.py`
  - Restart containers after changing settings

- **Package installation issues**
  - Run: `docker-compose build --no-cache`

## Poetry Setup

### Prerequisites
- Python 3.11.2
- PostgreSQL
- Poetry

### Steps

1. **Install correct Python version**
   ```bash
   # Using pyenv
   pyenv install 3.11.2
   pyenv local 3.11.2
   ```

2. **Install PostgreSQL**
   ```bash
   # macOS
   brew install postgresql
   brew services start postgresql
   
   # Ubuntu
   sudo apt-get install postgresql libpq-dev
   sudo service postgresql start
   
   # Create database
   createdb example_db
   ```

3. **Setup Poetry environment**
   ```bash
   pip install poetry
   poetry config virtualenvs.in-project true
   poetry shell
   poetry install
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. **Setup database**
   ```bash
   poetry run python manage.py migrate
   poetry run python manage.py loaddata website/fixtures/initial_data.json
   poetry run python manage.py createsuperuser
   poetry run python manage.py collectstatic --noinput
   ```

6. **Run the application**
   ```bash
   poetry run python manage.py runserver
   ```

7. **Post-setup configuration**
   - Visit http://127.0.0.1:8000/admin/socialaccount/socialapp/ and add social auth accounts
   - Add a Domain at http://127.0.0.1:8000/admin/website/domain/ with the name 'owasp.org'

### Troubleshooting Poetry Setup

- **PostgreSQL connection issues**
  - Ensure PostgreSQL is running and accessible
  - Check `DATABASE_URL` in `.env` matches your configuration

- **Package installation issues**
  - Run: `poetry cache clear --all pypi`

- **Missing system dependencies**
  - For Ubuntu: `sudo apt-get install libpq-dev`

## Vagrant Setup

### Prerequisites
- Vagrant
- VirtualBox

### Steps

1. **Start Vagrant**
   ```bash
   vagrant up
   vagrant ssh
   cd BLT
   ```

2. **Setup database**
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   python manage.py collectstatic
   ```

3. **Run the application**
   ```bash
   python manage.py runserver
   ```

4. **Post-setup configuration**
   - Visit http://127.0.0.1:8000/admin/socialaccount/socialapp/ and add social auth accounts
   - Add a Domain at http://127.0.0.1:8000/admin/website/domain/ with the name 'owasp.org'

### Troubleshooting Vagrant Setup

- **VirtualBox guest additions issues**
  - Run: `vagrant plugin install vagrant-vbguest` from the host machine