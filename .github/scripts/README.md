# GitHub Scripts

This directory contains utility scripts for maintaining the OWASP BLT repository.

## validate_workflows.py

Validates GitHub Actions workflow files for common configuration issues.

### What it checks

- **workflow_run triggers**: Ensures that any `workflow_run` trigger includes a non-empty `workflows` array
- **YAML syntax**: Verifies that workflow files are valid YAML
- **Configuration structure**: Checks that workflow configurations follow GitHub Actions requirements

### Usage

Run manually:
```bash
python3 .github/scripts/validate_workflows.py
```

Or it runs automatically via pre-commit hook when workflow files are modified.

### Why this exists

This script prevents errors like:
```
Invalid workflow file: .github/workflows/example.yml#L1
`on.workflow_run` does not reference any workflows.
```

Such errors occur when a workflow uses the `workflow_run` trigger but doesn't specify which workflows to listen to:

❌ **Invalid**:
```yaml
on:
  workflow_run:
    types:
      - completed
```

✅ **Valid**:
```yaml
on:
  workflow_run:
    workflows: ["CI/CD", "Pre-commit fix"]
    types:
      - completed
```

### Integration

- **Pre-commit hook**: Automatically runs when `.github/workflows/*.yml` or `.github/workflows/*.yaml` files are modified
- **Configured in**: `.pre-commit-config.yaml`

### Exit codes

- `0`: All workflow files passed validation
- `1`: One or more workflow files have validation errors
