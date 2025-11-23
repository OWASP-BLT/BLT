import json
import logging
import os
import secrets

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

        # Process payment via GitHub Sponsors API
        transaction_id = process_github_sponsors_payment(
            username=contributor_username,
            amount=bounty_amount,
            note=f"Bounty for PR #{pr_number} resolving issue #{issue_number} in {owner_name}/{repo_name}",
        )

        if not transaction_id:
            logger.error(f"Failed to process GitHub Sponsors payment for issue #{issue_number}")
            return JsonResponse({"status": "error", "message": "Payment processing failed"}, status=500)

        logger.info(
            f"Successfully processed bounty payment: ${bounty_amount / 100:.2f} to {contributor_username} "
            f"for PR #{pr_number} (Issue #{issue_number})"
        )

        # Save transaction ID to database
        github_issue.sponsors_tx_id = transaction_id
        github_issue.save()

        # Add comment and labels to GitHub issue
        github_token = os.environ.get("GITHUB_TOKEN")
        github_updated = False
        if github_token:
            github_updated = add_github_comment_and_labels(
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
                "github_updated": github_updated,
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
    Returns True if both comment and labels were added successfully, False otherwise.
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

    comment_success = False
    try:
        response = requests.post(comment_url, headers=headers, json={"body": comment_body}, timeout=10)
        response.raise_for_status()
        logger.info(f"Successfully added payment comment to issue #{issue_number}")
        comment_success = True
    except requests.RequestException as e:
        logger.error(f"Failed to add comment to GitHub issue: {e}")

    # Add labels
    labels_url = f"https://api.github.com/repos/{owner_name}/{repo_name}/issues/{issue_number}/labels"
    labels = ["paid", "sponsors"]

    labels_success = False
    try:
        response = requests.post(labels_url, headers=headers, json={"labels": labels}, timeout=10)
        response.raise_for_status()
        logger.info(f"Successfully added labels {labels} to issue #{issue_number}")
        labels_success = True
    except requests.RequestException as e:
        logger.error(f"Failed to add labels to GitHub issue: {e}")

    return comment_success and labels_success


def get_sponsor_tiers(sponsor_login):
    """
    Fetch available sponsor tiers using GitHub GraphQL API.
    Returns a dict mapping amount (in cents) to tier node IDs.
    """
    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        logger.error("Missing GITHUB_TOKEN for GraphQL API")
        return {}

    query = """
    query($login: String!) {
        user(login: $login) {
            sponsorsListing {
                tiers(first: 10) {
                    nodes {
                        id
                        monthlyPriceInCents
                        isOneTime
                    }
                }
            }
        }
    }
    """
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            "https://api.github.com/graphql",
            headers=headers,
            json={"query": query, "variables": {"login": sponsor_login}},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        if "errors" in data:
            logger.error(f"GraphQL error: {data['errors']}")
            return {}

        if not data.get("data", {}).get("user", {}).get("sponsorsListing"):
            logger.error(f"No sponsors listing found for user: {sponsor_login}")
            return {}

        tiers = data["data"]["user"]["sponsorsListing"]["tiers"]["nodes"]
        tier_mapping = {}

        for tier in tiers:
            amount = tier.get("monthlyPriceInCents", 0)
            tier_id = tier.get("id")
            if amount > 0 and tier_id:
                tier_mapping[amount] = tier_id

        logger.info(f"Fetched {len(tier_mapping)} sponsor tiers for {sponsor_login}")
        return tier_mapping

    except requests.RequestException as e:
        logger.error(f"Failed to fetch sponsor tiers: {e}")
        return {}
    except Exception as e:
        logger.exception("Unexpected error fetching sponsor tiers")
        return {}


def create_sponsorship_mutation(sponsor_login, tier_id):
    """
    Create a sponsorship using GitHub GraphQL API.
    Returns the sponsorship ID if successful, None otherwise.
    """
    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        logger.error("Missing GITHUB_TOKEN for GraphQL API")
        return None

    mutation = """
    mutation($input: CreateSponsorshipInput!) {
        createSponsorship(input: $input) {
            sponsorship {
                id
                createdAt
                tier {
                    id
                    monthlyPriceInCents
                }
                sponsor {
                    login
                }
                sponsorable {
                    login
                }
            }
        }
    }
    """
    mutation_input = {
        "sponsorableLogin": sponsor_login,
        "tierId": tier_id,
        "privacyLevel": "PUBLIC",
    }
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            "https://api.github.com/graphql",
            headers=headers,
            json={"query": mutation, "variables": {"input": mutation_input}},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        if "errors" in data:
            logger.error(f"GraphQL mutation errors: {data['errors']}")
            return None

        sponsorship = data.get("data", {}).get("createSponsorship", {}).get("sponsorship")
        if sponsorship:
            sponsorship_id = sponsorship.get("id")
            logger.info(f"Created sponsorship {sponsorship_id} for {sponsor_login}")
            return sponsorship_id

        logger.error("No sponsorship created in GraphQL response")
        return None

    except requests.RequestException as e:
        logger.error(f"Failed to create sponsorship: {e}")
        return None
    except Exception as e:
        logger.exception("Unexpected error creating sponsorship")
        return None


def process_github_sponsors_payment(username, amount, note=""):
    """
    Process GitHub Sponsors payment using the GitHub GraphQL API.
    Payment comes from DonnieBLT's GitHub Sponsors account.

    Args:
        username: GitHub username of the recipient
        amount: Amount in cents (e.g., 5000 = $50.00)
        note: Optional note for the payment

    Returns:
        str: Sponsorship transaction ID if successful, None otherwise
    """
    try:
        # The sponsor recipient is DonnieBLT
        sponsor_recipient = os.environ.get("GITHUB_SPONSORS_RECIPIENT", "DonnieBLT")
        logger.info(f"Processing payment of ${amount / 100:.2f} from {sponsor_recipient} to {username}")

        # Check if tier mapping is provided via environment variable
        tier_mapping_env = os.environ.get("GITHUB_SPONSORS_TIER_MAPPING")
        if tier_mapping_env:
            try:
                tier_mapping = json.loads(tier_mapping_env)
                # Try to get tier ID from mapping (supports both int and string keys)
                tier_id = tier_mapping.get(amount) or tier_mapping.get(str(amount))
                if not tier_id:
                    logger.error(f"No tier mapping found for amount: {amount} cents")
                    return None
            except json.JSONDecodeError:
                logger.error("Invalid JSON in GITHUB_SPONSORS_TIER_MAPPING")
                return None
        else:
            # Fetch tier mapping dynamically from GitHub
            tier_mapping = get_sponsor_tiers(username)
            if not tier_mapping:
                logger.error("Failed to fetch sponsor tiers")
                return None

            tier_id = tier_mapping.get(amount)
            if not tier_id:
                logger.error(f"No tier found for amount: {amount} cents. Available tiers: {list(tier_mapping.keys())}")
                return None

        # Create the sponsorship
        transaction_id = create_sponsorship_mutation(username, tier_id)

        if transaction_id:
            logger.info(f"Successfully created sponsorship {transaction_id} for {username} - ${amount / 100:.2f}")
            return transaction_id

        logger.error("Failed to create sponsorship")
        return None

    except Exception as e:
        logger.exception("Exception during GitHub Sponsors payment processing")
        return None
