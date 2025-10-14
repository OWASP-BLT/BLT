# GitHub Actions Workflows

This directory contains automated workflows for the BLT project.

## Dependabot Auto-Merge Workflow

The project uses two workflows to automatically approve and merge dependabot PRs:

### 1. Auto-Approve Dependabot (`auto-approve-dependabot.yml`)

This workflow automatically approves pull requests created by dependabot.

- **Triggers**: When a PR is opened by dependabot
- **Actions**: Approves the PR using the `cognitedata/auto-approve-dependabot-action`
- **Permissions**: Requires `pull-requests: write`

### 2. Auto-Merge (`auto-merge.yml`)

This workflow automatically merges dependabot PRs after they have been approved.

- **Triggers**:
  - When a PR is opened/updated (`pull_request_target`)
  - When a PR review is submitted (`pull_request_review`)
  - After the "Approve dependabot" workflow completes (`workflow_run`)

- **Behavior**:
  1. Waits 5 seconds for approvals to be recorded in GitHub
  2. Checks if the PR has been approved (retries up to 3 times with 10-second delays)
  3. If approved, enables auto-merge with squash strategy
  4. Automatically deletes the branch after merge

- **Permissions**: Requires `contents: write` and `pull-requests: write`

### How It Works Together

1. Dependabot creates a PR
2. `auto-approve-dependabot.yml` runs and approves the PR
3. `auto-merge.yml` runs (triggered by the workflow_run event)
4. `auto-merge.yml` waits for approvals to be recorded
5. `auto-merge.yml` enables auto-merge on the PR
6. GitHub automatically merges the PR when all checks pass

### Configuration

The auto-merge workflow uses:
- **Merge strategy**: Squash (combines all commits into one)
- **Branch deletion**: Automatic (after merge)
- **Retry attempts**: 3 attempts with 10-second delays between attempts

### Notes

- The workflow only runs for PRs created by dependabot bots
- Branch protection rules must allow auto-merge
- Required status checks must pass before the PR can be merged
