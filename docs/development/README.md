# Development Documentation

This section contains documentation for developers working on OWASP BLT.

## Getting Started

1. Read the [Contributing Guide](../community/CONTRIBUTING.md)
2. Follow the [Setup Guide](../setup/Setup.md)
3. Review the [Architecture Overview](../architecture/architecture.md)

## Development Workflow

### Code Quality
- **Formatting**: Black (Python), Tailwind CSS (styles)
- **Linting**: ruff (Python), djLint (templates)
- **Import Sorting**: isort
- **Pre-commit**: Always run `pre-commit run --all-files` before committing

### Technology Stack
- **Backend**: Django 5.1+, Python 3.11+
- **Database**: PostgreSQL, Redis
- **Frontend**: Django Templates, Tailwind CSS, vanilla JavaScript
- **Package Management**: Poetry (NOT pip)

### Testing
```bash
# Run all tests
poetry run python manage.py test --failfast

# Run specific test
poetry run python manage.py test website.tests.test_views
```

### Development Server
```bash
# Docker (recommended)
docker-compose up

# Local
poetry shell
python manage.py runserver
```

## Coding Standards

See the [Contributing Guide](../community/CONTRIBUTING.md) for detailed coding standards, including:
- Python code formatting and style
- Frontend best practices
- Template guidelines
- Security considerations

## Resources

- [Features Documentation](../features/features.md) - List of implemented features
- [File Descriptions](../features/file-descriptions.csv) - Template file reference
- [GitHub Actions](../features/github_actions.md) - CI/CD workflows

[← Back to Documentation Index](../index.md)
