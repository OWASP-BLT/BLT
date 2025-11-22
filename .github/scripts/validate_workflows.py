#!/usr/bin/env python3
"""
Validate GitHub Actions workflow files for common issues.

This script checks for:
- workflow_run triggers that don't reference any workflows
- workflow_run triggers with empty workflows arrays
- Other common workflow configuration issues
"""

import sys
from pathlib import Path

import yaml


def validate_workflow_run(filepath, content):
    """Validate workflow_run configuration in a workflow file."""
    issues = []

    if "on" not in content:
        return issues

    triggers = content["on"]
    if not isinstance(triggers, dict):
        return issues

    if "workflow_run" not in triggers:
        return issues

    workflow_run = triggers["workflow_run"]

    if not isinstance(workflow_run, dict):
        issues.append(f"{filepath}: workflow_run must be a dictionary")
        return issues

    if "workflows" not in workflow_run:
        issues.append(
            f"{filepath}: workflow_run does not reference any workflows. "
            "Missing 'workflows' key. "
            "See https://docs.github.com/actions/learn-github-actions/events-that-trigger-workflows#workflow_run"
        )
    elif not workflow_run["workflows"]:
        issues.append(
            f"{filepath}: workflow_run has empty 'workflows' list. "
            "Must reference at least one workflow. "
            "See https://docs.github.com/actions/learn-github-actions/events-that-trigger-workflows#workflow_run"
        )
    elif not isinstance(workflow_run["workflows"], list):
        issues.append(f"{filepath}: workflow_run 'workflows' must be a list")

    return issues


def validate_workflows(workflow_dir=".github/workflows"):
    """Validate all workflow files in the specified directory."""
    issues = []
    valid_count = 0

    workflow_files = list(Path(workflow_dir).glob("*.yml")) + list(Path(workflow_dir).glob("*.yaml"))

    for filepath in workflow_files:
        try:
            with open(filepath, "r") as f:
                content = yaml.safe_load(f)

            if content:
                file_issues = validate_workflow_run(filepath, content)
                issues.extend(file_issues)

                if not file_issues:
                    valid_count += 1
        except yaml.YAMLError as e:
            issues.append(f"{filepath}: YAML parsing error: {e}")
        except Exception as e:
            issues.append(f"{filepath}: Unexpected error: {e}")

    return issues, valid_count, len(workflow_files)


def main():
    """Main entry point for workflow validation."""
    print("Validating GitHub Actions workflow files...")  # noqa: T201
    print("-" * 60)  # noqa: T201

    issues, valid_count, total_count = validate_workflows()

    if issues:
        print(f"\n❌ Found {len(issues)} issue(s):\n")  # noqa: T201
        for issue in issues:
            print(f"  • {issue}")  # noqa: T201
        print(f"\n{valid_count}/{total_count} workflow files passed validation")  # noqa: T201
        return 1
    else:
        print(f"✅ All {total_count} workflow files passed validation")  # noqa: T201
        return 0


if __name__ == "__main__":
    sys.exit(main())
