# GitHub Actions Testing Guide

This document describes the comprehensive testing strategy for all GitHub Actions workflows in the OWASP BLT repository.

## Overview

The repository contains multiple GitHub Actions workflows that automate various tasks:
- **Label Management**: Automatically add/remove labels based on PR state
- **PR Validation**: Enforce PR requirements (peer review, issue references)
- **CI/CD**: Run tests, pre-commit checks, and Docker builds
- **Issue Management**: Auto-close issues, assign issues based on comments
- **Conflict Detection**: Check for merge conflicts

## Test Workflow

The `test-actions.yml` workflow provides comprehensive testing for all GitHub Actions workflows.

### What Gets Tested

#### 1. Label Management Logic (`test-label-logic`)
Tests the color-coding and label creation logic for:
- **Files Changed Labels**: Tests that correct colors are applied based on file counts
  - Gray (0 files)
  - Green (1 file)
  - Yellow (2-5 files)
  - Orange (6-10 files)
  - Red (11+ files)
  
- **Unresolved Conversations Labels**: Tests conversation count logic
  - Green (0 conversations)
  - Yellow (1-3 conversations)
  - Orange (4-10 conversations)
  - Red (11+ conversations)
  
- **Conflict Labels**: Tests merge conflict detection
  - Red color for conflicts
  - Proper detection based on mergeable state

#### 2. PR Validation Logic (`test-pr-validation-logic`)
Tests validation rules for pull requests:
- **Issue Number Validation**: Ensures PRs reference closing issues
  - Fails when no closing issues
  - Passes when closing issues exist
  
- **Peer Review Validation**: Ensures proper peer review
  - Blocks self-approvals
  - Blocks approvals from excluded users (DonnieBLT, coderabbit, copilot bots)
  - Requires APPROVED state (not just comments)

#### 3. Pre-commit Logic (`test-precommit-logic`)
Tests pre-commit workflow behavior:
- Label application based on exit code
- Correct colors for pass/fail states
- Status tracking

#### 4. Workflow File Syntax (`test-workflow-syntax`)
Validates all workflow files:
- Uses `actionlint` to check syntax
- Catches common mistakes
- Ensures proper YAML structure

#### 5. Script Functionality (`test-scripts`)
Tests Python scripts used by workflows:
- Validates `auto_fix.py` exists
- Checks Python syntax
- Ensures scripts are executable

#### 6. Workflow Configuration (`test-workflow-configuration`)
Validates workflow security and configuration:
- Checks `pull_request_target` workflows have proper permissions
- Validates all triggers are properly defined
- Ensures secure workflow design

#### 7. Action Interfaces (`test-action-interfaces`)
Tests action input/output configurations:
- Validates `github-script` action usage
- Checks token configuration
- Ensures proper action parameters

#### 8. Workflow Integration (`test-workflow-integration`)
Tests workflow interactions:
- Checks `workflow_run` dependencies
- Validates concurrency controls
- Tests workflow chaining

## Running Tests

### Automatic Triggers
The test workflow runs automatically on:
- Pull requests that modify `.github/workflows/**` or `.github/scripts/**`
- Pushes to branches starting with `test-actions-`

### Manual Trigger
You can manually trigger the tests:
1. Go to the Actions tab in GitHub
2. Select "Test GitHub Actions" workflow
3. Click "Run workflow"
4. Select the branch to test

### Local Testing
You can test some aspects locally:

```bash
# Install actionlint
bash <(curl https://raw.githubusercontent.com/rhysd/actionlint/main/scripts/download-actionlint.bash)

# Validate workflow syntax
./actionlint .github/workflows/*.yml

# Validate Python scripts
python -m py_compile .github/scripts/auto_fix.py
```

## Test Coverage

### Workflows Tested
- ✅ `add-comment-count-label.yml` - Label logic and GraphQL queries
- ✅ `add-files-changed-label.yml` - File count and color logic
- ✅ `check-pr-conflicts.yml` - Conflict detection and labels
- ✅ `check-peer-review.yml` - Peer review validation
- ✅ `enforce-issue-number-in-description.yml` - Issue reference validation
- ✅ `ci-cd.yml` - Pre-commit logic and status labels
- ✅ `close-issues.yml` - Comment and close logic
- ✅ `assign-issues.yml` - BLT-Action integration
- ✅ All other workflow files for syntax and configuration

### What's Not Tested
The following aspects require actual GitHub events and cannot be fully tested in isolation:
- Actual API calls to GitHub (we test the logic, not the API calls)
- Real PR/issue creation and modification
- Actual label creation/removal on live PRs
- External service integrations (e.g., Giphy API in BLT-Action)

These aspects are validated through:
- Code review
- Manual testing on real PRs
- Production monitoring

## Extending Tests

To add new tests:

1. **Add a new job** in `test-actions.yml`:
   ```yaml
   test-new-feature:
     name: Test New Feature
     runs-on: ubuntu-latest
     steps:
       - name: Checkout code
         uses: actions/checkout@v4
       
       - name: Test logic
         uses: actions/github-script@v7
         with:
           script: |
             // Your test code here
   ```

2. **Add to test summary** job's `needs` array:
   ```yaml
   needs: [test-label-logic, ..., test-new-feature]
   ```

3. **Update documentation** in this file

## Best Practices

### Writing Tests
- Test the logic, not the API calls
- Use descriptive test case names
- Include both positive and negative cases
- Test edge cases (0, 1, boundary values)
- Keep tests fast and focused

### Workflow Security
- Always use `pull_request_target` for forked PRs
- Never checkout or execute PR code in `pull_request_target` workflows
- Define explicit permissions for each workflow
- Avoid using `write-all` or overly broad permissions

### Maintaining Tests
- Update tests when workflow logic changes
- Add tests for new workflows
- Keep test cases aligned with actual workflow code
- Document any assumptions or limitations

## Troubleshooting

### Test Failures
If a test fails:
1. Check the test output in GitHub Actions
2. Compare the expected vs actual values
3. Review the corresponding workflow file
4. Update either the test or the workflow as needed

### Common Issues
- **Syntax errors**: Run `actionlint` locally first
- **Permission errors**: Check workflow `permissions` section
- **Logic mismatches**: Ensure test logic matches workflow code
- **Missing dependencies**: Check job setup steps

## Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [actionlint Documentation](https://github.com/rhysd/actionlint)
- [GitHub Script Action](https://github.com/actions/github-script)
- [Security Hardening for GitHub Actions](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions)
