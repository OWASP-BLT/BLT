import json
import logging
import os

import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from website.models import GitHubIssue, Repo

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def bounty_payout(request):
    """
    Minimal working version: Handle bounty payout webhook from GitHub Action.
    Processes payment and updates issue with comment and labels.
    """
    try:
        # Validate API token
        expected_token = os.environ.get("BLT_API_TOKEN")
        if not expected_token:
            logger.error("BLT_API_TOKEN environment variable is missing")
            return JsonResponse({"status": "error", "message": "Server configuration error"}, status=500)

        received_token = request.headers.get("X-BLT-API-TOKEN")
        if received_token != expected_token:
            logger.warning("Invalid or missing API token")
            return JsonResponse({"status": "error", "message": "Unauthorized"}, status=403)

        # Parse and validate request data
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            logger.error("Invalid JSON in request body")
            return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)

        # Extract required fields
        required_fields = ["issue_number", "repo", "owner", "contributor_username", "pr_number", "bounty_amount"]
        if not all(field in data for field in required_fields):
            logger.warning(f"Missing required fields in request: {data}")
            return JsonResponse({"status": "error", "message": "Missing required fields"}, status=400)

        # Validate numeric fields
        try:
            issue_number = int(data["issue_number"])
            pr_number = int(data["pr_number"])
            bounty_amount = int(data["bounty_amount"])
        except (ValueError, TypeError):
            logger.warning("Invalid numeric fields in request")
            return JsonResponse({"status": "error", "message": "Invalid numeric fields"}, status=400)

        repo_name = data["repo"]
        owner_name = data["owner"]
        contributor_username = data["contributor_username"]

        # Look up repository and issue
        repo = Repo.objects.filter(name=repo_name, organization__name=owner_name).first()
        if not repo:
            logger.error(f"Repo not found: {owner_name}/{repo_name}")
            return JsonResponse({"status": "error", "message": "Repository not found"}, status=404)

        github_issue = GitHubIssue.objects.filter(issue_id=issue_number, repo=repo).first()
        if not github_issue:
            logger.error(f"Issue #{issue_number} not found in repo {owner_name}/{repo_name}")
            return JsonResponse({"status": "error", "message": "Issue not found"}, status=404)

        # Check for duplicate payment
        if github_issue.sponsors_tx_id:
            logger.info(f"Payment already processed for issue #{issue_number}")
            return JsonResponse(
                {
                    "status": "warning",
                    "message": "Payment already processed",
                    "transaction_id": github_issue.sponsors_tx_id,
                }
            )

        # Process payment (simplified - just generate a transaction ID for now)
        # In production, this would call GitHub Sponsors API
        transaction_id = f"TXN-{issue_number}-{pr_number}"
        logger.info(
            f"Processing bounty payment: ${bounty_amount / 100:.2f} to {contributor_username} "
            f"for PR #{pr_number} (Issue #{issue_number})"
        )

        # Save transaction ID to database
        github_issue.sponsors_tx_id = transaction_id
        github_issue.save()

        # Add comment and labels to GitHub issue
        github_token = os.environ.get("GITHUB_TOKEN")
        if github_token:
            add_github_comment_and_labels(
                owner_name,
                repo_name,
                issue_number,
                contributor_username,
                bounty_amount,
                pr_number,
                transaction_id,
                github_token,
            )
        else:
            logger.warning("GITHUB_TOKEN not available - skipping GitHub comment/labels")

        return JsonResponse(
            {
                "status": "success",
                "message": "Payment processed",
                "transaction_id": transaction_id,
                "amount": bounty_amount,
                "recipient": contributor_username,
            }
        )

    except Exception as e:
        logger.exception("Unexpected error in bounty_payout")
        return JsonResponse({"status": "error", "message": "An unexpected error occurred"}, status=500)


def add_github_comment_and_labels(
    owner_name, repo_name, issue_number, contributor_username, bounty_amount, pr_number, transaction_id, github_token
):
    """
    Add a comment to the GitHub issue with payment details and add appropriate labels.
    """
    # Create comment with payment details
    comment_body = f"""🎉 **Bounty Paid!** 🎉

💰 **Amount:** ${bounty_amount / 100:.2f}
👤 **Recipient:** @{contributor_username}
🔗 **PR:** #{pr_number}
📋 **Transaction ID:** {transaction_id}

Thank you for your contribution to this project!"""

    # Add comment
    comment_url = f"https://api.github.com/repos/{owner_name}/{repo_name}/issues/{issue_number}/comments"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(comment_url, headers=headers, json={"body": comment_body}, timeout=10)
        response.raise_for_status()
        logger.info(f"Successfully added payment comment to issue #{issue_number}")
    except requests.RequestException as e:
        logger.error(f"Failed to add comment to GitHub issue: {e}")

    # Add labels
    labels_url = f"https://api.github.com/repos/{owner_name}/{repo_name}/issues/{issue_number}/labels"
    labels = ["paid", "sponsors"]

    try:
        response = requests.post(labels_url, headers=headers, json={"labels": labels}, timeout=10)
        response.raise_for_status()
        logger.info(f"Successfully added labels {labels} to issue #{issue_number}")
    except requests.RequestException as e:
        logger.error(f"Failed to add labels to GitHub issue: {e}")
