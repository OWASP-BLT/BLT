# GitHub Actions Workflows

This document describes the GitHub Actions workflows available in this repository and how to use them.

## Regenerate Django Migrations

**Workflow File:** `.github/workflows/regenerate-migrations.yml`

This workflow automatically deletes and regenerates Django migrations that are part of a pull request. It's useful when you need to clean up and recreate migrations, especially when dealing with:
- Migration conflicts
- Complex migration dependencies
- Regenerating migrations after model changes

### How to Use

1. **Via Label (Recommended):**
   - Add the label `regenerate-migrations` to your pull request
   - The workflow will automatically:
     - Identify and delete migration files added/modified in the PR (except `__init__.py`)
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

1. **Checks out the base branch** (trusted code) with full history
2. **Sets up Python 3.11** and installs Poetry
3. **Installs project dependencies** using Poetry
4. **Fetches the PR branch** as a remote (without checking it out)
5. **Identifies migration files** that were added or modified in this PR
6. **Safely copies model files** from the PR (data only, no code execution)
7. **Deletes only the PR migration files** (preserves `__init__.py` and existing migrations)
8. **Creates a temporary .env file** with minimal settings for Django to run
9. **Runs makemigrations** on trusted base code with updated model definitions
10. **Commits and pushes** the new migrations to the PR branch
11. **Comments on your PR** with the results

### Important Notes

- ✅ **Only deletes migration files that are part of the PR** - existing migrations in the base branch are preserved
- The workflow preserves `__init__.py` files in migration directories
- If no migration files are found in the PR, the workflow will skip deletion and just run makemigrations
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

**Scenario 2: Regenerating After Model Changes**
```
You've modified models and created migrations, but want to regenerate them.
1. Ensure your models are correct
2. Add the `regenerate-migrations` label
3. The workflow deletes your PR's migration files and regenerates them
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

This workflow uses `pull_request_target` to work with forked PRs but is designed to prevent code injection attacks:

- **Trusted code execution**: The workflow checks out the BASE branch (trusted code) and runs `makemigrations` against it
- **Safe data extraction**: Only model definition files are copied from the PR using `git show` (no code execution from PR)
- **Explicit trigger required**: Only runs when explicitly triggered via label or manual dispatch
- **Collaborator gate**: Only repository collaborators with write access can add labels
- **Write permissions**: Used only for committing regenerated migrations back to the PR branch

## Other Workflows

For information about other workflows in this repository:
- **CI/CD**: `.github/workflows/ci-cd.yml` - Runs tests and pre-commit checks
- **Pre-commit Fix**: `.github/workflows/pre-commit-fix.yaml` - Auto-fixes pre-commit issues
- See individual workflow files in `.github/workflows/` for more details
