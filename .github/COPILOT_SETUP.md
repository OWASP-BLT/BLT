# GitHub Copilot Configuration for OWASP BLT

This document explains the GitHub Copilot configuration for the OWASP BLT project and how it helps automate development workflows.

## Overview

OWASP BLT uses GitHub Copilot coding agent to assist with code changes, bug fixes, and feature development. The Copilot agent is configured with project-specific instructions and automated setup steps to ensure consistent, high-quality contributions.

## Configuration Files

### 1. `.github/copilot-instructions.md`

This is the main instruction file for GitHub Copilot. It contains:

- **Project Overview**: Tech stack, architecture, and key dependencies
- **Development Workflow**: Best practices for making changes
- **Coding Standards**: Python, JavaScript, CSS, and Django template guidelines
- **Testing Requirements**: How to run and write tests
- **Common Tasks**: Frequently used commands and procedures
- **Security Considerations**: Important security practices

The instructions are comprehensive and cover everything Copilot needs to know to work effectively on the BLT codebase.

### 2. `.github/workflows/copilot-setup-steps.yml`

This GitHub Actions workflow prepares the development environment before Copilot starts working. It:

- ✅ Sets up Python 3.11 and Poetry
- ✅ Installs project dependencies with caching for faster setup
- ✅ Configures PostgreSQL database
- ✅ Installs and configures pre-commit hooks
- ✅ Sets up Node.js for frontend tooling
- ✅ Creates necessary environment files

**Key Features:**
- Runs automatically when the workflow file is modified
- Can be triggered manually via workflow_dispatch
- Uses caching to speed up repeated runs
- Provides detailed output for debugging

### 3. `.github/copilot/agent.yaml`

This file configures the behavior of the BLT Copilot agent:

- **Name**: "BLT Coding Agent"
- **Description**: Specialized for OWASP BLT Django project
- **Target**: GitHub Copilot environment
- **Tools**: Has access to all available tools
- **Infer**: Automatically activates when appropriate

**Validation Steps:**
The agent runs these checks before completing work:

1. **Pre-commit Hooks**: Runs all formatters and linters (Black, isort, ruff, djLint)
2. **Django System Checks**: Validates Django configuration
3. **Migration Checks**: Ensures no missing database migrations

### 4. `.github/workflows/assign-new-issues-to-copilot.yml` (Previously Configured)

This workflow was previously configured in the repository and automatically assigns newly opened issues to the Copilot agent, allowing it to start working on tasks immediately.

## How It Works

### For Issue Assignment

1. A new issue is created in the repository
2. The `assign-new-issues-to-copilot.yml` workflow runs automatically
3. The issue is assigned to @Copilot
4. Copilot analyzes the issue and starts working on it

### For Development Workflow

1. Copilot is assigned to an issue
2. The `copilot-setup-steps.yml` workflow runs to prepare the environment
3. Copilot analyzes the codebase using the instructions from `copilot-instructions.md`
4. Copilot makes changes following the project's coding standards
5. The `agent.yaml` validation steps run:
   - Pre-commit hooks format and lint the code
   - Django checks validate the configuration
   - Migration checks ensure database changes are tracked
6. Copilot creates a pull request with the changes
7. Human reviewers review and provide feedback
8. Copilot can iterate on the changes based on feedback

## Benefits

✅ **Consistency**: All changes follow the same coding standards and best practices
✅ **Speed**: Automated environment setup and validation reduce manual work
✅ **Quality**: Pre-commit hooks and Django checks catch issues early
✅ **Documentation**: Clear instructions help Copilot understand project conventions
✅ **Learning**: New contributors can see examples of proper code changes

## Maintenance

### Updating Instructions

When project conventions or requirements change:

1. Update `.github/copilot-instructions.md` with the new information
2. Ensure examples are clear and actionable
3. Focus on information Copilot cannot infer from code alone

### Updating Setup Steps

When adding new dependencies or tools:

1. Update `.github/workflows/copilot-setup-steps.yml`
2. Test the workflow manually using workflow_dispatch
3. Ensure caching is configured for new dependencies

### Updating Agent Configuration

When adding new validation steps:

1. Update `.github/copilot/agent.yaml`
2. Add new steps with clear descriptions
3. Ensure steps fail gracefully and provide useful error messages

## Troubleshooting

### Copilot Not Following Instructions

- Check that `copilot-instructions.md` is clear and specific
- Ensure instructions focus on actionable guidance, not general descriptions
- Verify examples are up-to-date with current codebase

### Setup Steps Failing

- Check the workflow logs in the Actions tab
- Verify all dependencies are correctly specified
- Test the setup steps locally using the same commands
- Ensure caching keys are unique and properly configured

### Agent Validation Failing

- Review the error messages in the agent output
- Run the same commands locally to reproduce the issue
- Fix the underlying problem in the setup or code
- Update agent.yaml if the validation is too strict

## Best Practices

1. **Keep Instructions Updated**: Review and update `copilot-instructions.md` regularly
2. **Test Setup Steps**: Run the workflow manually after changes to verify it works
3. **Monitor Copilot PRs**: Review Copilot's pull requests to identify areas for improvement
4. **Provide Clear Feedback**: When Copilot makes mistakes, provide specific feedback
5. **Iterate on Configuration**: Continuously improve the configuration based on experience

## Additional Resources

- [GitHub Copilot Documentation](https://docs.github.com/en/copilot)
- [GitHub Copilot Coding Agent Guide](https://docs.github.com/en/copilot/tutorials/coding-agent)
- [Custom Agents Configuration](https://docs.github.com/en/copilot/reference/custom-agents-configuration)
- [BLT Contributing Guide](../CONTRIBUTING.md)
- [BLT README](../README.md)

## Questions or Issues?

If you have questions about the Copilot configuration or encounter issues:

1. Check this documentation first
2. Review the workflow logs for error messages
3. Open an issue in the repository with details
4. Reach out in the OWASP Slack channel

---

**Note**: GitHub Copilot is a tool to assist development, not replace human judgment. All Copilot-generated code should be reviewed by human maintainers before merging.
