import json
import logging
import os
import secrets

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from website.models import GitHubIssue, Repo

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def bounty_payout(request):
    """
    Handle bounty payout webhook from GitHub Action.
    Records the bounty payment request for processing via GitHub Sponsors.

    Note: Actual payment is processed manually by DonnieBLT via GitHub Sponsors.
    This endpoint records the transaction and updates the issue.
    """
    try:
        # Validate API token using constant-time comparison
        expected_token = os.environ.get("BLT_API_TOKEN")
        if not expected_token:
            logger.error("BLT_API_TOKEN environment variable is missing")
            return JsonResponse({"status": "error", "message": "Server configuration error"}, status=500)

        received_token = request.headers.get("X-BLT-API-TOKEN")
        if not received_token or not secrets.compare_digest(received_token, expected_token):
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
        # Prioritize matching github_org, then fallback to name for legacy organizations
        # Use separate queries to ensure deterministic results (github_org match takes precedence)
        repo = Repo.objects.filter(
            organization__github_org=owner_name, name=repo_name
        ).first()

        # Fallback to matching by organization name for legacy organizations without github_org
        if not repo:
            repo = Repo.objects.filter(
                organization__name=owner_name, name=repo_name
            ).first()

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
                    "message": "Bounty payment already processed for this issue.",
                    "transaction_id": github_issue.sponsors_tx_id,
                },
                status=200,
            )

        # Record the bounty for manual payment via GitHub Sponsors
        # Format: BOUNTY:<contributor>:<amount_cents>:<pr>
        github_issue.sponsors_tx_id = f"BOUNTY:{contributor_username}:{bounty_amount}:{pr_number}"
        github_issue.save()

        logger.info(
            f"Recorded bounty: ${bounty_amount / 100:.2f} to {contributor_username} "
            f"for PR #{pr_number} (Issue #{issue_number})"
        )

        return JsonResponse(
            {
                "status": "success",
                "message": "Bounty recorded for payment",
                "issue_number": issue_number,
                "amount": bounty_amount,
                "recipient": contributor_username,
            }
        )

    except Exception as e:
        logger.exception("Unexpected error in bounty_payout")
        return JsonResponse({"status": "error", "message": "An unexpected error occurred"}, status=500)
