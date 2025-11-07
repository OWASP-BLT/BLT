# djLint Usage Guide for BLT Project

## What is djLint?

djLint is a linter and formatter for Django/Jinja HTML templates. It helps maintain consistent formatting and catches common template errors.

## Installation

Already installed via poetry:
```bash
poetry add --group dev djlint
```

## VS Code Extension

1. Open VS Code
2. Press `Cmd+Shift+X` (Extensions)
3. Search for "djLint"
4. Install the extension by **monosans**

### VS Code Settings

Add to your `.vscode/settings.json`:
```json
{
  "djlint.useEditorIndentation": false,
  "djlint.enableLinting": true,
  "djlint.formatOnSave": true,
  "editor.defaultFormatter": "monosans.djlint"
}
```

## Configuration File

The `.djlintrc` file in the project root configures djLint:

```json
{
  "profile": "django",
  "indent": 4,
  "max_line_length": 120,
  "format_css": true,
  "format_js": true,
  "ignore": "H006,H013,H030,H031",
  "exclude": ".venv,venv,node_modules,staticfiles,media"
}
```

## Command Line Usage

### Lint Templates (Check for Issues)
```bash
# Lint all templates
poetry run djlint website/templates/ --profile django

# Lint specific file
poetry run djlint website/templates/home.html --profile django

# Lint with statistics
poetry run djlint website/templates/ --profile django --statistics
```

### Format Templates
```bash
# Format all templates
poetry run djlint website/templates/ --reformat --profile django

# Format specific file
poetry run djlint website/templates/home.html --reformat --profile django

# Format quietly (no diff output)
poetry run djlint website/templates/ --reformat --profile django --quiet
```

### Check Formatting (CI/CD)
```bash
# Check if files are properly formatted (exits with error if not)
poetry run djlint website/templates/ --check --profile django
```

## Common Issues and Fixes

### T003: Endblock should have name
```html
<!-- ❌ Bad -->
{% block content %}
...
{% endblock %}

<!-- ✅ Good -->
{% block content %}
...
{% endblock content %}
```

### H006: Img tag should have alt attribute
```html
<!-- ❌ Bad -->
<img src="image.jpg">

<!-- ✅ Good -->
<img src="image.jpg" alt="Description">
```

### H013: Img tag should have width and height attributes
```html
<!-- ❌ Bad -->
<img src="image.jpg" alt="Description">

<!-- ✅ Good -->
<img src="image.jpg" alt="Description" width="100" height="100">
```

### H030/H031: Consider using <button> instead of <a>
```html
<!-- ❌ Bad for actions -->
<a href="#" onclick="doSomething()">Click</a>

<!-- ✅ Good -->
<button type="button" onclick="doSomething()">Click</button>
```

## Ignoring Rules

### Global Ignore (in .djlintrc)
```json
{
  "ignore": "H006,H013,H030,H031"
}
```

### Per-File Ignore
```bash
poetry run djlint --per-file-ignores "template.html:H006,H013"
```

### Inline Ignore
```html
{# djlint:off #}
<img src="image.jpg">
{# djlint:on #}
```

## Pre-commit Hook

djLint is already configured in `.pre-commit-config.yaml`:

```yaml
- repo: https://github.com/djlint/djLint
  rev: v1.36.1
  hooks:
    - id: djlint
      args:
        - --reformat
        - --lint
```

### Run Pre-commit Manually
```bash
# Run on all files
pre-commit run --all-files

# Run only djlint
pre-commit run djlint --all-files

# Run on staged files
pre-commit run
```

## Common Commands Cheatsheet

```bash
# Lint
poetry run djlint website/templates/ --profile django

# Format
poetry run djlint website/templates/ --reformat --profile django

# Check (CI)
poetry run djlint website/templates/ --check --profile django

# Lint + Statistics
poetry run djlint website/templates/ --profile django --statistics

# Format single file
poetry run djlint website/templates/home.html --reformat --profile django

# Show version
poetry run djlint --version

# Help
poetry run djlint --help
```

## VS Code Keyboard Shortcuts

- Format document: `Shift+Option+F` (Mac) or `Shift+Alt+F` (Windows/Linux)
- Format selection: `Cmd+K Cmd+F` (Mac) or `Ctrl+K Ctrl+F` (Windows/Linux)

## Error Codes Reference

Common error codes:
- **H001-H999**: HTML/accessibility issues
- **T001-T999**: Django/Jinja template issues
- **D001-D999**: Django-specific issues

See full list: https://djlint.com/docs/linter/

## Troubleshooting

### djLint not running in VS Code
1. Check Python interpreter is selected
2. Reload VS Code window
3. Check Output panel → djLint for errors

### Pre-commit hook failing
```bash
# Update pre-commit hooks
pre-commit autoupdate

# Clear cache
pre-commit clean

# Reinstall
pre-commit install
```

### Format conflicts with Black/Ruff
djLint works alongside Black/Ruff. They handle different file types:
- Black/Ruff: `.py` files
- djLint: `.html` template files

## Best Practices

1. **Format before committing**: Always run djLint before committing templates
2. **Use VS Code extension**: Enable format on save for real-time formatting
3. **Review diffs**: Check what djLint changes before committing
4. **Ignore when needed**: Use inline ignores sparingly for edge cases
5. **Keep config updated**: Review and update `.djlintrc` as project evolves

## Additional Resources

- [djLint Documentation](https://djlint.com/)
- [VS Code Extension](https://marketplace.visualstudio.com/items?itemName=monosans.djlint)
- [GitHub Repository](https://github.com/djlint/djLint)
