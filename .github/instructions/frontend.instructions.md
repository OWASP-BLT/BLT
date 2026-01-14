---
applyTo: 
  - "website/templates/**/*.html"
  - "website/static/**/*.js"
  - "website/static/**/*.css"
---

# Frontend-Specific Copilot Instructions

## Templates (HTML)

### Styling Requirements
- **STRICT**: Use ONLY Tailwind CSS utility classes - NO `<style>` tags, NO inline styles
- Pre-commit hooks will fail if `<style>` tags are found
- Brand color: Use `#e74c3c` (BLT red) for primary elements
- Follow djLint formatting rules (enforced by pre-commit)

### Template Structure
- Use Django template inheritance (`{% extends %}` and `{% block %}`)
- Load static files with `{% load static %}` and `{% static 'path' %}`
- Use template tags appropriately: `{% url %}`, `{% csrf_token %}`, etc.
- Keep templates DRY - extract reusable components to includes/

### Best Practices
- Keep templates readable and well-indented
- Use semantic HTML5 elements
- Ensure accessibility (ARIA labels, alt text, etc.)
- Test with different viewport sizes

## JavaScript Files

### Code Organization
- Keep JavaScript in SEPARATE `.js` files in `website/static/js/` or subdirectories
- **NEVER** embed JavaScript in HTML templates using `<script>` tags
- Load JS files using Django's `{% static %}` template tag

### Code Style
- Use modern ES6+ syntax where appropriate (arrow functions, const/let, template literals)
- Remove ALL console statements before committing (console.log, console.error, etc.)
  - CI/CD pipeline automatically checks and will fail on any console statements
  - For debugging during development, comment them out: `// console.log('debug info')`
- Use clear, descriptive variable and function names
- Add comments for complex logic

### Common Patterns
- Use `fetch()` API for AJAX requests
- Handle CSRF tokens for POST requests using Django's CSRF utilities
- Use event delegation for dynamically added elements
- Handle errors gracefully with user-friendly messages

## Static Files Workflow

After any CSS/JS changes:
```bash
python manage.py collectstatic --noinput
```

This is required for changes to appear in the browser during development.
