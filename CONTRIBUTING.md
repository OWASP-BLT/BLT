# Contributing to OWASP BLT

Thank you for your interest in contributing to OWASP BLT! We welcome contributions from everyone, regardless of their level of experience.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
  - [Development Environment Setup](#development-environment-setup)
  - [Docker Setup (Recommended)](#docker-setup-recommended)
  - [Vagrant Setup](#vagrant-setup)
  - [Python Virtual Environment Setup](#python-virtual-environment-setup)
  - [Populating Test Data for Local Development](#populating-test-data-for-local-development)
- [Making Contributions](#making-contributions)
  - [Finding Issues to Work On](#finding-issues-to-work-on)
  - [Creating a Pull Request](#creating-a-pull-request)
  - [Pull Request Guidelines](#pull-request-guidelines)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Community](#community)

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct. Please be respectful and considerate when contributing.

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
   git clone https://github.com/OWASP-BLT/BLT.git
   cd BLT
   ```

2. Configure environment variables:

   **Linux/macOS/Git Bash:**

   ```bash
   cp .env.example .env
   ```

   **Windows (PowerShell):**

   ```powershell
   Copy-Item .env.example .env
   ```

   **Windows (CMD):**

   ```cmd
   copy .env.example .env
   ```

   Modify the `.env` file as per your local setup.

3. Ensure LF Line Endings:
   The repository includes a `.gitattributes` file that automatically enforces LF line endings for shell scripts and configuration files. For new clones, this should handle line endings automatically.

   If you're working on a Windows machine, we recommend configuring Git to work with `.gitattributes`:

   ```bash
   git config --global core.autocrlf input
   ```

   **Windows users:** For more detailed instructions on handling line endings, including when manual conversion is needed and PowerShell/VS Code methods, see the [Setup.md](docs/Setup.md#1-ensure-lf-line-endings) documentation.

4. Build and start the Docker containers:

   ```bash
   docker-compose build
   docker-compose up
   ```

5. Access the application at [http://localhost:8000](http://localhost:8000)

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

4. Access the application at [http://localhost:8000](http://localhost:8000)

### Python Virtual Environment Setup


### Optional: Python Virtual Environment Setup using `uv`

BLT can also be set up using [`uv`](https://github.com/astral-sh/uv), a fast Python package manager
and virtual environment tool. This is an **optional** alternative to the Poetry-based setup
described above.

This option is useful for contributors who prefer faster dependency resolution and installation.

#### Install `uv`

> ⚠️ Note (Windows):  
> On some Windows setups, `uv` may fail to auto-detect Python installations
> due to registry or PATH resolution issues. In such cases, explicitly
> specifying the Python interpreter or using Docker/Poetry is recommended.


```bash
pip install uv
```

#### Set up the BLT project using `uv`

From the project root, run:

```bash
uv sync
```

To start the development server:

```bash
uv run python manage.py migrate
uv run python manage.py runserver
```

Open your browser at:
http://localhost:8000


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

4. Access the application at [http://localhost:8000](http://localhost:8000)

### Populating Test Data for Local Development
For faster local development and testing, the project provides a built-in Django management command to automatically populate the database with realistic sample data.

#### Generate Sample Data

Run the following command after migrations:

   ```bash
   python manage.py generate_sample_data
   ```

This command automatically creates:
- Users with profiles and follow relationships
- Organizations
- Domains
- Issues
- Hunts
- Projects
- Repositories
- Pull Requests
- Reviews
- Points & Activity records
- Badges
- Tags

### Additional Seed Commands

In addition to the main sample data generator, the project provides specialized seed commands for security labs and OWASP adventures.

#### 1. Seed OWASP BLT Adventures

This command populates the platform with predefined OWASP BLT adventure challenges.

   ```bash
   python manage.py seed_adventures
   ```

#### 2. Seed Security Lab Challenges
This command seeds vulnerable security labs used for hands-on security practice, including:
- IDOR
- XSS
- CSRF
- SQL Injection
- Other OWASP Top 10 style vulnerabilities

   ```bash
   python manage.py seed_all_security_lab
   ```

#### Important Notes
This command clears existing data before creating sample data.
It is intended strictly for local development and testing.
Do not run this in production environments.

#### Full Local Setup Example
   ```bash
   python manage.py migrate
   python manage.py generate_sample_data
   python manage.py createsuperuser
   python manage.py runserver
   ```

This will give you a fully populated development environment with realistic relationships across the platform.

## Making Contributions

### Finding Issues to Work On

- Check the [Issues](https://github.com/OWASP-BLT/BLT/issues) page for open issues
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
- For UI changes or new features, include clear screenshots or a short demo video showing the functionality

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

### JavaScript Code Standards

For JavaScript code, please follow these guidelines:

**Avoid all console statements:** Our CI/CD pipeline automatically checks for any console statements in JavaScript files (including console.log, console.error, console.warn, etc.). Remove them before submitting your PR.

The project has sufficient error tracking systems in place, so console statements are not needed.

For temporary debugging during development, comment out console statements before committing: `// console.log()`.

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
