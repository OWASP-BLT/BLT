# Copilot Instructions Setup Summary

This document summarizes the GitHub Copilot coding agent configuration for the OWASP BLT repository.

## Overview

The repository has been configured with comprehensive Copilot instructions following GitHub's best practices. This setup helps Copilot understand the project structure, coding standards, and development workflow.

## Configuration Files

### 1. Main Instructions (`.github/copilot-instructions.md`)

The main instruction file provides comprehensive guidance for the entire repository:

- **Project Overview**: Tech stack (Django 5.1+, Python 3.11.2+, PostgreSQL, Redis, Tailwind CSS)
- **Development Workflow**: Pre-commit requirements, testing guidelines, dependency management
- **Coding Standards**: Python (Black, isort, ruff), Frontend (Tailwind CSS, separate JS files), Django templates
- **Project Structure**: Directory layout and file organization
- **Common Tasks**: Running the app, database migrations, static files, screenshots
- **Security Considerations**: OWASP best practices, input validation, secret management
- **Additional Resources**: Links to contributing guide, README, documentation

### 2. Agent Setup Steps (`.github/copilot/agent.yaml`)

Defines the environment setup steps that run when Copilot starts working on a task:

```yaml
steps:
  - run: poetry install --no-interaction
    description: "Install Python dependencies with Poetry"
    
  - run: python manage.py migrate --noinput
    description: "Apply database migrations"
    
  - run: python manage.py collectstatic --noinput
    description: "Collect static files for serving CSS/JS"
    
  - run: pre-commit run --all-files
    description: "Run pre-commit hooks (Black, isort, ruff, djLint) on all files"
```

These steps ensure:
- Dependencies are installed
- Database is up to date
- Static files are collected for proper styling
- Code quality checks pass before making changes

### 3. Path-Specific Instructions (`.github/instructions/`)

Specialized instructions that apply to specific file types:

#### Frontend (`frontend.instructions.md`)
**Applies to**: HTML templates, JavaScript files, CSS files

Key guidelines:
- Use ONLY Tailwind CSS utility classes (no `<style>` tags or inline styles)
- Keep JavaScript in separate files (never embed in templates)
- Remove all console statements before committing
- Brand color: `#e74c3c` (BLT red)
- Follow djLint formatting for templates

#### Backend (`backend.instructions.md`)
**Applies to**: Python files in `website/` and `blt/` (excluding tests and migrations)

Key guidelines:
- Never expose exception details in user-facing messages
- Use Django's class-based views for standard CRUD, function-based for complex logic
- Optimize database queries with `select_related()` and `prefetch_related()`
- Use Django REST Framework for API endpoints
- Follow Black, isort, and ruff formatting
- Proper logging with appropriate log levels

#### Tests (`tests.instructions.md`)
**Applies to**: Test files in `website/tests/` and `test_*.py` files

Key guidelines:
- Prefer `setUpTestData()` over `setUp()` for better performance
- Use test tags (`@tag("slow")`) for slow tests
- Run quick tests with: `poetry run python manage.py test --exclude-tag=slow --parallel --failfast`
- Test both success and failure cases
- Use descriptive test method names

## Benefits

1. **Consistency**: Copilot follows the same coding standards as human developers
2. **Context-Aware**: Path-specific instructions provide targeted guidance
3. **Quality Assurance**: Pre-commit hooks and testing requirements are enforced
4. **Onboarding**: Acts as documentation for new developers (human and AI)
5. **Efficiency**: Reduces back-and-forth by setting clear expectations upfront

## How Copilot Uses These Instructions

1. **General Context**: Main instructions apply to all files
2. **Specific Context**: Path-specific instructions apply based on file being edited
3. **Environment Setup**: Agent.yaml steps run before starting work
4. **Validation**: Pre-commit hooks validate changes before committing

## Best Practices Followed

Based on [GitHub's Copilot coding agent best practices](https://docs.github.com/en/copilot):

✅ Clear project documentation (README, CONTRIBUTING.md)
✅ Repository-wide instructions (copilot-instructions.md)
✅ Path-specific instructions with glob patterns
✅ Agent setup steps for environment configuration
✅ Pre-commit hooks for code quality
✅ Clear coding standards and conventions
✅ Security guidelines and best practices
✅ Testing requirements and patterns

## Maintenance

### Updating Instructions

To update instructions:

1. **Main instructions**: Edit `.github/copilot-instructions.md`
2. **Setup steps**: Edit `.github/copilot/agent.yaml`
3. **Path-specific**: Edit files in `.github/instructions/`

### Adding New Path-Specific Instructions

1. Create new `.instructions.md` file in `.github/instructions/`
2. Add YAML frontmatter with `applyTo` glob patterns
3. Write clear, actionable instructions
4. Document in `.github/instructions/README.md`

## References

- [Main Copilot Instructions](../.github/copilot-instructions.md)
- [Agent Setup Steps](../.github/copilot/agent.yaml)
- [Path-Specific Instructions](../.github/instructions/)
- [Contributing Guide](../CONTRIBUTING.md)
- [README](../README.md)
- [GitHub Copilot Documentation](https://docs.github.com/en/copilot)
