# GitHub Copilot Instructions for OWASP BLT

This document provides guidance for GitHub Copilot coding agent when working on the OWASP BLT (Bug Logging Tool) project.

## Project Overview

OWASP BLT is a Django-based web application for bug bounty management and security research. The project uses:

- **Backend**: Django 5.1+ with Python 3.11.2+
- **Database**: PostgreSQL with Redis for caching
- **Frontend**: Tailwind CSS, vanilla JavaScript (separate files)
- **Real-time**: Django Channels with WebSocket support
- **Package Management**: Poetry (NOT pip)
- **Code Quality**: pre-commit hooks, Black, isort, ruff, djLint

## Development Workflow

### Before Making Any Changes

1. **Understand the Issue**: Read the issue description thoroughly and ask for clarification if anything is unclear
2. **Explore the Code**: Review related files and understand the existing implementation
3. **Plan Your Approach**: Make minimal, surgical changes that address the root cause

### Required Before Each Commit

- **ALWAYS** run `pre-commit run --all-files` before committing any changes
- This will run automatic formatters and linters including:
  - Black (code formatting)
  - isort (import sorting)
  - ruff (linting and auto-fixes)
  - djLint (Django template formatting and linting)
  - Custom hooks (style tag detection, collectstatic, tests)
- If pre-commit fails, run it again as it often auto-fixes issues on the second run
- Do NOT commit code that fails pre-commit checks

### Testing Requirements

- Run Django tests with: `poetry run python manage.py test --failfast`
- Add tests for new features or bug fixes when appropriate
- Ensure existing tests pass before committing
- Test files are located in `website/tests/`

### Dependency Management

- **ALWAYS use Poetry**, never use pip directly
- Add dependencies: `poetry add <package-name>`
- Add dev dependencies: `poetry add --group dev <package-name>`
- Update dependencies: `poetry update <package-name>`
- Avoid installing packages that are not necessary

## Coding Standards

### Python Code

- **Formatting**: Use Black with default settings (enforced by pre-commit)
- **Imports**: Use isort with Django profile (enforced by pre-commit)
- **Linting**: Follow ruff rules (enforced by pre-commit)
- **Error Handling**: 
  - Don't expose exception details in user-facing messages
  - ❌ BAD: `messages.error(request, f"Error: {str(e)}")`
  - ✅ GOOD: `messages.error(request, "Unable to process request. Please check your input and try again.")`
  - Log detailed errors for debugging: `logger.error(f"Failed to process: {str(e)}", exc_info=True)`

### Frontend Code

- **CSS Framework**: Use Tailwind CSS exclusively
  - ❌ Do NOT add `<style>` tags in HTML templates
  - ❌ Do NOT add inline styles
  - ✅ Use Tailwind utility classes
- **Brand Color**: Use `#e74c3c` (BLT red) for primary color elements
  - Tailwind config may have this as a custom color
- **JavaScript**:
  - Keep JavaScript in separate `.js` files in `website/static/` directories
  - ❌ Do NOT embed JavaScript in HTML templates
  - ✅ Load JS files using Django's `{% static %}` template tag
  - Use modern ES6+ syntax where appropriate

### Django Templates

- Use Django template language features appropriately
- Follow djLint formatting rules (enforced by pre-commit)
- Keep templates clean and readable
- Use template inheritance to avoid duplication

## Project Structure

```
BLT/
├── website/           # Main Django application
│   ├── models.py     # Database models
│   ├── views/        # View logic (directory of view files)
│   ├── api/          # REST API views
│   ├── templates/    # HTML templates
│   ├── static/       # Static files (CSS, JS, images)
│   ├── tests/        # Test files
│   ├── services/     # External service integrations
│   ├── consumers.py  # WebSocket consumers
│   └── utils.py      # Utility functions
├── blt/              # Django project settings
├── static/           # Collected static files (DO NOT EDIT)
├── .github/          # GitHub configuration
│   └── copilot/      # Copilot agent configuration
└── pyproject.toml    # Python dependencies and project config
```

## Common Tasks

### Running the Application

```bash
# Using Docker (recommended)
docker-compose up

# Local development
poetry shell
poetry install
python manage.py migrate
python manage.py runserver
```

### Database Migrations

```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Load initial data
python manage.py loaddata website/fixtures/initial_data.json
```

### Static Files

```bash
# Collect static files (required after CSS/JS changes)
python manage.py collectstatic --noinput
```

### Taking Screenshots with Proper Styling

**CRITICAL**: When taking screenshots of the application, you MUST ensure static files (CSS/JS) are properly loaded. Follow these steps:

#### Using Docker (Recommended for Screenshots)

```bash
# 1. Copy the environment file
cp .env.example .env

# 2. Start the application with Docker
docker-compose up -d

# 3. Wait for the application to be ready (check logs)
docker-compose logs -f app

# 4. Once you see "Starting the main application http://localhost:8000/", the app is ready
# Access at http://localhost:8000

# 5. To stop the application after screenshots
docker-compose down
```

#### Using Local Development (Alternative)

```bash
# 1. Set up environment
cp .env.example .env
poetry shell
poetry install

# 2. Set up database and collect static files
python manage.py migrate
python manage.py loaddata website/fixtures/initial_data.json
python manage.py collectstatic --noinput

# 3. Create superuser (if needed)
python manage.py createsuperuser

# 4. Run the development server
python manage.py runserver

# Access at http://127.0.0.1:8000
```

#### Important Notes for Screenshots

- **ALWAYS** run `python manage.py collectstatic --noinput` before taking screenshots
- Wait for the server to fully start before navigating to pages
- Ensure the database is migrated and initial data is loaded
- For Docker: Wait until you see "Starting the main application" in logs
- For local: Wait until you see "Starting development server at http://127.0.0.1:8000/"
- CSS files are served from the `/static/` directory after collection
- If styles don't appear, check that collectstatic was run successfully

## Debugging Guidelines

- If a fix doesn't work on the first try, add detailed logging/debugging code
- Use Django's logging framework: `import logging; logger = logging.getLogger(__name__)`
- Add print statements temporarily during development (but remove before committing)
- Use Django Debug Toolbar for database query analysis (in development)

## Security Considerations

- Never commit secrets or credentials
- Use environment variables for sensitive configuration (see `.env.example`)
- Validate and sanitize user input
- Use Django's built-in security features (CSRF, XSS protection)
- Follow OWASP security best practices

## When to Ask for Clarification

- When the issue description is ambiguous or unclear
- When multiple approaches could solve the problem
- When unsure about the user's intent or requirements
- When a change might have significant side effects
- When you need more context about business logic

## Additional Resources

- [Contributing Guide](../CONTRIBUTING.md) - Detailed contribution guidelines
- [README](../README.md) - Project overview and setup instructions
- [Django Documentation](https://docs.djangoproject.com/) - Official Django docs
- [Tailwind CSS Documentation](https://tailwindcss.com/docs) - Tailwind CSS reference

## Summary of Key Rules

✅ **DO**:
- Use Poetry for dependency management
- Use Tailwind CSS for styling
- Keep JavaScript in separate files
- Run pre-commit before every commit
- Write clear, descriptive error messages
- Ask for clarification when needed
- Fix root causes, not symptoms
- Test your changes thoroughly

❌ **DON'T**:
- Use pip for package installation
- Add `<style>` tags or inline styles
- Embed JavaScript in HTML templates
- Include exception details in user-facing messages
- Install unnecessary packages
- Commit code that fails pre-commit checks
- Make changes without understanding the context
