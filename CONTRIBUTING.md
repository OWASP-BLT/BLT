# Contributing to OWASP BLT

Thank you for your interest in contributing to OWASP BLT! We welcome contributions from everyone, regardless of your level of experience.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
  - [Development Environment Setup](#development-environment-setup)
  - [Docker Setup (Recommended)](#docker-setup-recommended)
  - [Vagrant Setup](#vagrant-setup)
  - [Python Virtual Environment Setup](#python-virtual-environment-setup)
- [Making Contributions](#making-contributions)
  - [Finding Issues to Work On](#finding-issues-to-work-on)
  - [Creating a Pull Request](#creating-a-pull-request)
  - [Pull Request Guidelines](#pull-request-guidelines)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Community](#community)

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct. Please be respectful and considerate of others when contributing to the project.

## Getting Started

### Development Environment Setup

Before you start contributing, you'll need to set up your development environment. We provide multiple options for setting up the project.

#### Prerequisites

- Git
- Python 3.11.2 (recommended)
- PostgreSQL
- Docker and Docker Compose (for Docker setup)

### Docker Setup (Recommended)

1. Clone the repository:
   ```bash
   git clone https://github.com/OWASP-BLT/BLT-Website.git
   cd BLT-Website
   ```

2. Configure environment variables:
   ```bash
   cp .env.example .env
   ```
   Modify the `.env` file as per your local setup.

3. Ensure LF Line Endings:
   If you're working on a Windows machine, ensure all files use LF line endings:
   ```bash
   git config --global core.autocrlf input
   ```

4. Build and start the Docker containers:
   ```bash
   docker-compose build
   docker-compose up
   ```

5. Access the application at http://localhost:8000

### Vagrant Setup

1. Install [Vagrant](https://www.vagrantup.com/) and [VirtualBox](https://www.virtualbox.org/)

2. Start Vagrant:
   ```bash
   vagrant up
   vagrant ssh
   cd BLT
   ```

3. Set up the application:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   python manage.py collectstatic
   python manage.py runserver
   ```

4. Access the application at http://localhost:8000

### Python Virtual Environment Setup

1. Install Python 3.11.2 (using pyenv or another tool):
   ```bash
   pyenv install 3.11.2
   ```

2. Set up Poetry and virtual environment:
   ```bash
   pip install poetry
   poetry shell
   poetry install
   ```

3. Set up the application:
   ```bash
   python manage.py migrate
   python3 manage.py loaddata website/fixtures/initial_data.json
   python manage.py createsuperuser
   python manage.py collectstatic
   python manage.py runserver
   ```

4. Access the application at http://localhost:8000

## Making Contributions

### Finding Issues to Work On

- Check the [Issues](https://github.com/OWASP-BLT/BLT-Website/issues) page for open issues
- Look for issues labeled with `good first issue` if you're new to the project
- Comment on an issue to express your interest in working on it

### Creating a Pull Request

1. Create a new branch for your feature or bugfix:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and commit them with descriptive commit messages:
   ```bash
   git commit -m "Add feature: your feature description"
   ```

3. Push your branch to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

4. Create a Pull Request from your branch to the main repository

### Pull Request Guidelines

- Ensure your code follows the project's coding standards
- Include tests for new features or bug fixes
- Update documentation as needed
- Make sure all tests pass before submitting
- Keep pull requests focused on a single issue or feature
- Provide a clear description of the changes in your PR

## Coding Standards

We use several tools to maintain code quality:

- Black for code formatting
- isort for import sorting
- ruff for linting

You can run these tools using Poetry:

```bash
poetry run black .
poetry run isort .
poetry run ruff .
```

We also use pre-commit hooks to ensure code quality. Install them with:

```bash
poetry run pre-commit install
```

## Testing

When adding new features or fixing bugs, please include appropriate tests. Run the tests with:

```bash
python manage.py test
```

## Documentation

If you're adding new features or making significant changes, please update the documentation accordingly. This includes:

- Code comments
- README updates
- Wiki updates (if applicable)

## Community

- Join the [OWASP Slack channel](https://owasp.org/slack/invite) to connect with other contributors
- Ask questions and share ideas

Thank you for contributing to OWASP BLT! 