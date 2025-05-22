# GitHub Actions Configuration

This directory contains GitHub Actions workflows used for automating various tasks in the BLT project.

## Setting Up Custom GitHub Token

For some workflows like adding labels to issues and pull requests, you may need to set up a custom GitHub token with elevated permissions.

### Why Custom Token?

The default `GITHUB_TOKEN` provided by GitHub Actions has certain permission limitations. For operations like creating labels or adding labels to issues and PRs, we recommend using a Personal Access Token (PAT) with appropriate permissions.

### Creating a Custom GitHub Token

1. Go to your GitHub account settings
2. Navigate to Developer settings > Personal Access Tokens > Fine-grained tokens
3. Click "Generate new token"
4. Provide a suitable name like "BLT Workflow Token"
5. Set the expiration as needed
6. For repository access, select "Only select repositories" and choose the BLT repository
7. Under permissions, grant the following:
   - Repository permissions:
     - Issues: Read and write
     - Pull requests: Read and write
     - Contents: Read and write
     - Metadata: Read-only (automatically selected)

8. Click "Generate token" and copy the token value

### Adding the Token to GitHub Secrets

1. Go to the BLT repository on GitHub
2. Navigate to Settings > Secrets and variables > Actions
3. Click "New repository secret"
4. Name it `CUSTOM_GITHUB_TOKEN`
5. Paste the token value and click "Add secret"

### Using the Custom Token

The workflows are configured to use `CUSTOM_GITHUB_TOKEN` if available, falling back to the default `GITHUB_TOKEN` if not.

Example usage in workflow:
```yaml
env:
  GITHUB_TOKEN: ${{ secrets.CUSTOM_GITHUB_TOKEN || secrets.GITHUB_TOKEN }}
```

## Troubleshooting

If you encounter permission errors like `Resource not accessible by integration`, it's likely that:
1. The token doesn't have the necessary permissions
2. The token has expired
3. The workflow permissions at the top of the .yml file need to be adjusted

Review the permissions in both your custom token and at the workflow level to resolve such issues.