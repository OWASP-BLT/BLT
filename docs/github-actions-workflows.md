# GitHub Actions Workflows

This document describes the GitHub Actions workflows available in this repository and how to use them.

## Regenerate Django Migrations

**Workflow File:** `.github/workflows/regenerate-migrations.yml`

This workflow automatically deletes and regenerates all Django migrations in a pull request. It's useful when you need to clean up and recreate migrations, especially when dealing with:
- Migration conflicts
- Complex migration dependencies
- Starting fresh with a clean migration history

### How to Use

1. **Via Label (Recommended):**
   - Add the label `regenerate-migrations` to your pull request
   - The workflow will automatically:
     - Delete all existing migration files (except `__init__.py`)
     - Run `python manage.py makemigrations` to create fresh migrations
     - Commit and push the new migrations back to your PR branch
     - Comment on the PR with the results
     - Remove the label when complete

2. **Via Manual Trigger:**
   - Go to the "Actions" tab in the GitHub repository
   - Select "Regenerate Django Migrations" from the workflows list
   - Click "Run workflow"
   - Select the branch you want to run it on
   - Click "Run workflow" to start

### What It Does

1. **Checks out your PR branch** (including from forks)
2. **Sets up Python 3.11.2** and installs Poetry
3. **Installs project dependencies** using Poetry
4. **Deletes all migrations** in:
   - `website/migrations/` (except `__init__.py`)
   - `comments/migrations/` (except `__init__.py`)
5. **Creates a temporary .env file** with minimal settings for Django to run
6. **Runs makemigrations** to generate fresh migration files
7. **Commits and pushes** the new migrations to your branch
8. **Comments on your PR** with the results

### Important Notes

- ⚠️ **This will delete all existing migrations!** Make sure this is what you want before using it.
- The workflow preserves `__init__.py` files in migration directories
- If no changes are detected after regeneration, the workflow will comment that migrations are already up to date
- The workflow works with both repository branches and forked PRs
- Only migration files are committed - no other changes will be included

### Example Use Cases

**Scenario 1: Migration Conflicts**
```
You have conflicts in migration files between your branch and main.
1. Add the `regenerate-migrations` label to your PR
2. Wait for the workflow to complete
3. Review the new migration files
4. Continue with your PR
```

**Scenario 2: Clean Slate**
```
You want to start with a fresh migration history.
1. Ensure your models are correct
2. Add the `regenerate-migrations` label
3. The workflow creates new initial migrations based on your current models
```

**Scenario 3: Complex Dependencies**
```
Migration dependencies are tangled and causing issues.
1. Add the `regenerate-migrations` label
2. Get a clean, linear migration history
3. Resolve any remaining conflicts manually if needed
```

### Permissions Required

The workflow needs the following permissions:
- `contents: write` - To push commits back to the branch
- `actions: write` - To trigger other workflows if needed
- `pull-requests: write` - To comment on PRs and manage labels

### Security

This workflow uses `pull_request_target` to work with forked PRs. It:
- Only runs when explicitly triggered (via label or manual dispatch)
- Uses the PR head SHA to ensure it works on the actual PR code
- Has write permissions to commit back to the PR branch
- Is safe because it only runs Django's `makemigrations` command

## Other Workflows

For information about other workflows in this repository:
- **CI/CD**: `.github/workflows/ci-cd.yml` - Runs tests and pre-commit checks
- **Pre-commit Fix**: `.github/workflows/pre-commit-fix.yaml` - Auto-fixes pre-commit issues
- See individual workflow files in `.github/workflows/` for more details
