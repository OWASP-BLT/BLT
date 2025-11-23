#!/usr/bin/env python3
"""
Script to automatically find and validate bounty payout PRs.

This script searches for PRs that implement GitHub Sponsors bounty payout
functionality by looking for specific patterns in PR titles, descriptions,
and file changes.
"""

import json
import subprocess
import sys
from typing import Any, Dict, List, Optional


class BountyPayoutPRFinder:
    """Finds and validates PRs implementing bounty payout functionality."""

    # Patterns to search for in PR titles and descriptions
    TITLE_PATTERNS = [
        r"bounty.*payout",
        r"auto.*bounty",
        r"sponsor.*payment",
        r"github.*sponsor.*bounty",
    ]

    DESCRIPTION_PATTERNS = [
        r"createSponsorship",
        r"cancel.*sponsor",
        r"immediate.*cancel",
        r"one.*time.*payment",
        r"sponsor.*subscription.*cancel",
    ]

    # Key files that should be present in a bounty payout PR
    EXPECTED_FILES = [
        ".github/workflows/auto-bounty-payout.yml",
        "website/migrations/*_userprofile_preferred_payment_method.py",
        "website/migrations/*_githubissue_sponsors_cancel_flags.py",
    ]

    # Key code patterns that should be present
    CODE_PATTERNS = {
        "workflow": [
            r"on:.*pull_request.*closed",
            r"if:.*merged.*true",
            r"Fixes.*#\d+",
            r"api/bounty_payout",
        ],
        "api_endpoint": [
            r"@csrf_exempt",
            r"process_bounty_payout",
            r"createSponsorship",
            r"cancelSponsorship",
        ],
        "migrations": [
            r"preferred_payment_method",
            r"sponsors_cancellation_failed",
            r"sponsors_cancellation_attempts",
        ],
    }

    def __init__(self, repo_path: str = "."):
        """Initialize the finder with repository path."""
        self.repo_path = repo_path
        self.found_prs: List[Dict] = []

    def find_pr_by_github_api(self, pr_number: Optional[int] = None) -> Optional[Dict]:
        """
        Find PR using GitHub API via gh CLI.

        Args:
            pr_number: Specific PR number to check, or None to search all open PRs

        Returns:
            PR information dict or None
        """
        try:
            if pr_number:
                cmd = ["gh", "pr", "view", str(pr_number), "--json", "number,title,body,state,files"]
            else:
                cmd = [
                    "gh",
                    "pr",
                    "list",
                    "--state",
                    "open",
                    "--search",
                    "bounty payout in:title,body",
                    "--json",
                    "number,title,body,state",
                    "--limit",
                    "50",
                ]

            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )

            data = json.loads(result.stdout)
            return data if isinstance(data, dict) else (data[0] if data else None)

        except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError):
            return None

    def find_pr_by_commit_messages(self) -> List[str]:
        """Search for bounty payout related commits in git history."""
        patterns = [
            "bounty.*payout",
            "sponsor.*payment",
            "auto.*bounty",
        ]

        found_commits = []
        for pattern in patterns:
            try:
                result = subprocess.run(
                    ["git", "log", "--all", "--oneline", f"--grep={pattern}", "-i"],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                if result.stdout:
                    found_commits.extend(result.stdout.strip().split("\n"))
            except subprocess.CalledProcessError:
                continue

        return found_commits

    def validate_pr_implementation(self, pr_number: int) -> Dict[str, Any]:
        """
        Validate a PR's bounty payout implementation.

        Args:
            pr_number: PR number to validate

        Returns:
            Dict with validation results
        """
        validation_results = {
            "pr_number": pr_number,
            "has_workflow": False,
            "has_api_endpoint": False,
            "has_migrations": False,
            "has_sponsors_cancel": False,
            "has_error_handling": False,
            "has_retry_logic": False,
            "has_allowlist": False,
            "issues": [],
            "warnings": [],
            "recommendations": [],
        }

        # Check if PR exists and get files
        pr_info = self.find_pr_by_github_api(pr_number)
        if not pr_info:
            validation_results["issues"].append(f"PR #{pr_number} not found or inaccessible")
            return validation_results

        # Get PR files
        try:
            result = subprocess.run(
                ["gh", "pr", "diff", str(pr_number)],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            pr_diff = result.stdout
        except subprocess.CalledProcessError:
            pr_diff = ""

        # Validate workflow file
        if ".github/workflows/auto-bounty-payout.yml" in pr_diff:
            validation_results["has_workflow"] = True
            if not ("merged == true" in pr_diff or "merged == 'true'" in pr_diff):
                validation_results["warnings"].append("Workflow should check merged status")

        # Validate API endpoint
        if "process_bounty_payout" in pr_diff or "api/bounty_payout" in pr_diff:
            validation_results["has_api_endpoint"] = True

        # Check for sponsors cancellation logic
        if "cancelSponsorship" in pr_diff or "cancel" in pr_diff.lower():
            validation_results["has_sponsors_cancel"] = True
        else:
            validation_results["issues"].append(
                "Missing sponsors cancellation logic - critical for preventing recurring charges"
            )

        # Check for error handling
        if "try:" in pr_diff and "except" in pr_diff:
            validation_results["has_error_handling"] = True
        else:
            validation_results["warnings"].append("Limited error handling detected")

        # Check for retry logic
        if "retry" in pr_diff.lower() or "attempts" in pr_diff.lower():
            validation_results["has_retry_logic"] = True
        else:
            validation_results["recommendations"].append(
                "Consider adding retry logic for failed cancellations"
            )

        # Check for repository allowlist
        if "BLT_ALLOWED_BOUNTY_REPOS" in pr_diff or "allowlist" in pr_diff.lower():
            validation_results["has_allowlist"] = True
        else:
            validation_results["issues"].append(
                "Missing repository allowlist - security risk for unauthorized payouts"
            )

        # Check for migrations
        if "migrations" in pr_diff:
            validation_results["has_migrations"] = True

        return validation_results

    def print_validation_report(self, results: Dict[str, Any]):
        """Print a formatted validation report."""
        print(f"\n{'=' * 80}")
        print(f"BOUNTY PAYOUT PR VALIDATION REPORT - PR #{results['pr_number']}")
        print(f"{'=' * 80}\n")

        # Summary
        print("✓ IMPLEMENTED FEATURES:")
        if results["has_workflow"]:
            print("  ✓ GitHub Actions workflow")
        if results["has_api_endpoint"]:
            print("  ✓ API endpoint for bounty processing")
        if results["has_sponsors_cancel"]:
            print("  ✓ Sponsors cancellation logic")
        if results["has_error_handling"]:
            print("  ✓ Error handling")
        if results["has_retry_logic"]:
            print("  ✓ Retry logic")
        if results["has_allowlist"]:
            print("  ✓ Repository allowlist")
        if results["has_migrations"]:
            print("  ✓ Database migrations")

        # Issues
        if results["issues"]:
            print("\n✗ CRITICAL ISSUES:")
            for issue in results["issues"]:
                print(f"  ✗ {issue}")

        # Warnings
        if results["warnings"]:
            print("\n⚠ WARNINGS:")
            for warning in results["warnings"]:
                print(f"  ⚠ {warning}")

        # Recommendations
        if results["recommendations"]:
            print("\n💡 RECOMMENDATIONS:")
            for rec in results["recommendations"]:
                print(f"  💡 {rec}")

        # Overall assessment
        print(f"\n{'=' * 80}")
        critical_issues = len(results["issues"])
        if critical_issues == 0:
            print("✓ OVERALL: Implementation looks good with minor suggestions")
        elif critical_issues <= 2:
            print("⚠ OVERALL: Implementation needs attention to critical issues")
        else:
            print("✗ OVERALL: Implementation has significant issues that must be addressed")
        print(f"{'=' * 80}\n")


def main():
    """Main entry point."""
    finder = BountyPayoutPRFinder()

    print("🔍 Searching for bounty payout PR...")

    # First, try to find PR #4633 specifically (mentioned in the problem statement)
    pr_number = 4633
    pr_info = finder.find_pr_by_github_api(pr_number)

    if pr_info:
        print(f"✓ Found PR #{pr_number}: {pr_info.get('title', 'Unknown')}")
        print(f"  State: {pr_info.get('state', 'unknown')}")
        print(f"\n📋 Validating implementation...")

        # Validate the implementation
        validation_results = finder.validate_pr_implementation(pr_number)
        finder.print_validation_report(validation_results)

    else:
        print(f"✗ PR #{pr_number} not found. Searching for related commits...")

        # Search commit history
        commits = finder.find_pr_by_commit_messages()
        if commits:
            print("\n📝 Found related commits:")
            for commit in commits[:10]:  # Show first 10
                print(f"  • {commit}")
        else:
            print("✗ No related commits found in history")

    return 0


if __name__ == "__main__":
    sys.exit(main())
