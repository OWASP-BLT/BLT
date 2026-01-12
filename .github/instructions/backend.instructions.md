---
applyTo: 
  - "website/**/*.py"
  - "blt/**/*.py"
  - "!website/tests/**"
  - "!**/migrations/**"
---

# Backend-Specific Copilot Instructions

## Django Code

### Views
- Keep views focused and single-purpose
- Use Django's class-based views (CBVs) for standard CRUD operations
- Use function-based views (FBVs) for complex custom logic
- Always validate and sanitize user input
- Use Django's built-in decorators: `@login_required`, `@require_http_methods`, etc.

### Error Handling
- **CRITICAL**: Never expose exception details in user-facing messages
- ❌ BAD: `messages.error(request, f"Error: {str(e)}")`
- ✅ GOOD: `messages.error(request, "Unable to process request. Please check your input and try again.")`
- Always log detailed errors for debugging: `logger.error(f"Failed to process: {str(e)}", exc_info=True)`

### Models
- Use Django's ORM efficiently
- Add `__str__` methods to all models for better debugging
- Use `related_name` in ForeignKey and ManyToMany relationships
- Add database indexes for frequently queried fields
- Document complex model logic with docstrings

### Security
- Validate all user input
- Use Django's built-in CSRF protection
- Never store secrets in code - use environment variables
- Sanitize output to prevent XSS (use Django's template auto-escaping)
- Follow OWASP security best practices
- Use Django's built-in password validators

### Database Queries
- Use `select_related()` and `prefetch_related()` to avoid N+1 queries
- Use `only()` and `defer()` for large querysets when you don't need all fields
- Be mindful of query performance in loops
- Use database transactions for data consistency

### API Development
- Use Django REST Framework (DRF) for API endpoints
- Add proper authentication and permissions
- Use DRF serializers for data validation
- Document API endpoints with docstrings
- Return appropriate HTTP status codes
- Use pagination for list endpoints

## Code Quality

### Formatting (enforced by pre-commit)
- Black for code formatting (line length: 88)
- isort for import sorting (Django profile)
- ruff for linting and quick fixes

### Import Organization
```python
# Standard library imports
import os
import sys

# Third-party imports
from django.contrib.auth.decorators import login_required
from rest_framework import viewsets

# Local application imports
from website.models import Issue
from website.utils import send_notification
```

### Logging
```python
import logging

logger = logging.getLogger(__name__)

# Use appropriate log levels
logger.debug("Detailed information for debugging")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error occurred", exc_info=True)
logger.critical("Critical error")
```

## Django-Specific Patterns

### Signals
- Use signals sparingly - prefer explicit calls
- Document why signals are necessary
- Keep signal handlers lightweight
- Use `sender` parameter to connect to specific models

### Custom Management Commands
- Place in `website/management/commands/`
- Inherit from `BaseCommand`
- Add help text and argument descriptions
- Handle errors gracefully

### Middleware
- Keep middleware fast and focused
- Document the purpose clearly
- Be careful with global state
- Test thoroughly - middleware affects all requests
