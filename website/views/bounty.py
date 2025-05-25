import json
import logging
import os

import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from website.models import Contributor, GitHubIssue, Repo, UserProfile

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def bounty_payout(request):
    """
    Handle bounty payout webhook from GitHub Action.
    """
    expected_token = os.environ.get("BLT_API_TOKEN")
    if not expected_token:
        logger.critical("BLT_API_TOKEN environment variable is missing.")
        return JsonResponse({"status": "error", "message": "Server configuration error"}, status=500)

    try:
        data = json.loads(request.body)

        # Validate token
        received_token = request.headers.get("X-BLT-API-TOKEN")
        if received_token != expected_token:
            logger.warning("Invalid or missing token in request.")
            return JsonResponse({"status": "error", "message": "Unauthorized"}, status=403)

        # Required fields
        required_fields = ["issue_number", "repo", "owner", "contributor_username", "pr_number", "bounty_amount"]
        if not all(field in data for field in required_fields):
            logger.warning(f"Missing fields in request: {data}")
            return JsonResponse({"status": "error", "message": "Missing required fields"}, status=400)

        issue_number = int(data["issue_number"])
        repo_name = data["repo"]
        owner_name = data["owner"]
        contributor_username = data["contributor_username"]
        bounty_amount = int(data["bounty_amount"])

        try:
            pr_number = int(data["pr_number"])
            if pr_number <= 0:
                raise ValueError("PR number must be > 0")
        except (KeyError, ValueError):
            logger.warning(f"Invalid PR number: {data.get('pr_number')}")
            return JsonResponse({"status": "error", "message": "Invalid PR number"}, status=400)

        # Look up repo and issue
        repo = Repo.objects.filter(name=repo_name, organization__name=owner_name).first()
        if not repo:
            logger.error(f"Repo not found: {owner_name}/{repo_name}")
            return JsonResponse({"status": "error", "message": "Repository not found"}, status=404)

        github_issue = GitHubIssue.objects.filter(issue_id=issue_number, repo=repo).first()
        if not github_issue:
            logger.error(f"Issue #{issue_number} not found in repo {owner_name}/{repo_name}")
            return JsonResponse({"status": "error", "message": "Issue not found"}, status=404)

        # Avoid duplicate payments
        if github_issue.sponsors_tx_id:
            return JsonResponse(
                {
                    "status": "warning",
                    "message": "Payment already processed",
                    "transaction_id": github_issue.sponsors_tx_id,
                }
            )

        # Resolve contributor profile
        contributor = resolve_contributor(contributor_username)
        if not contributor:
            return JsonResponse({"status": "error", "message": "Contributor not found"}, status=404)

        # Process payout
        transaction_id = process_github_sponsors_payment(
            username=contributor_username,
            amount=bounty_amount,
            note=f"Bounty for PR #{pr_number} resolving issue #{issue_number} in {owner_name}/{repo_name}",
        )

        if not transaction_id:
            return JsonResponse({"status": "error", "message": "Payment processing failed"}, status=500)

        # Update DB
        github_issue.sponsors_tx_id = transaction_id
        github_issue.save()

        return JsonResponse(
            {
                "status": "success",
                "message": "Payment processed",
                "transaction_id": transaction_id,
                "amount": bounty_amount,
                "recipient": contributor_username,
            }
        )

    except json.JSONDecodeError:
        logger.exception("Invalid JSON received.")
        return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)


def resolve_contributor(username):
    """
    Returns a contributor object or user profile match if exists.
    """
    contributor = Contributor.objects.filter(name=username).first()
    if contributor:
        return contributor

    profile = UserProfile.objects.filter(github_url__icontains=f"github.com/{username}").first()
    return profile if profile else None


def process_github_sponsors_payment(username, amount, note):
    """
    Dummy integration to simulate GitHub Sponsors payment API.
    """
    try:
        github_token = os.environ.get("GITHUB_SPONSORS_TOKEN")
        if not github_token:
            logger.error("Missing GITHUB_SPONSORS_TOKEN.")
            return None

        sponsor_recipient = "DonnieBLT"  # As per current config
        api_url = f"https://api.github.com/sponsors/{sponsor_recipient}/sponsorships"

        headers = {"Authorization": f"token {github_token}", "Accept": "application/vnd.github.v3+json"}

        tier_mapping = {
            500: "tier_id_500",  # Example tier IDs for $5
            1000: "tier_id_1000",  # Example tier IDs for $10
            2000: "tier_id_2000",  # Example tier IDs for $20
        }
        tier_id = tier_mapping.get(amount)
        if not tier_id:
            logger.error(f"No tier ID found for amount: {amount}")
            return None
        payload = {
            "amount": amount,
            "tier_id": tier_id,  # This must be configured or dynamically fetched
            "is_recurring": False,
            "privacy_level": "public",
            "note": note,
        }

        response = requests.post(api_url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()

        data = response.json()

        tx_id = data.get("id")
        if not tx_id:
            logger.error("Github Sponsors API returned 2xxx but not transaction id found in response.")
            return None
        return tx_id

    except requests.HTTPError as http_err:
        logger.error(f"HTTP error during GitHub Sponsors payment: {http_err}")
        return None
    except Exception as e:
        logger.exception("Exception during GitHub Sponsors payment.")
        return None
