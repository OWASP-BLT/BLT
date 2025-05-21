# GitHub Actions Configuration

This directory contains GitHub Actions workflows and configuration files used in the BLT project.

## GitHub Token Permissions

Some workflows may require additional permissions beyond what the default `GITHUB_TOKEN` provides. For workflows that need to modify issues, pull requests, or add labels, a custom Personal Access Token (PAT) may be needed.

### Setting up a Custom GitHub Token

For workflows that require higher permissions (like the "Add Files Changed Label" workflow), follow these steps:

1. Create a new Personal Access Token (PAT) with the appropriate permissions:
   - Go to your GitHub account Settings > Developer settings > Personal access tokens > Tokens (classic)
   - Generate a new token with the following permissions:
     - `repo` - Full control of private repositories
     - `workflow` - Update GitHub Action workflows
   - Copy the generated token

2. Add the token as a repository secret:
   - Go to your repository settings > Secrets and variables > Actions
   - Create a new repository secret named `CUSTOM_GITHUB_TOKEN`
   - Paste the token value you copied

### Workflows that use custom tokens

The following workflows can leverage the custom token for enhanced permissions:

- **add-files-changed-label.yml**: Adds labels to PRs based on the number of files changed