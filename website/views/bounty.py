import json
import logging
import os
from dataclasses import dataclass

import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from website.models import GitHubIssue, Repo

logger = logging.getLogger(__name__)


@dataclass
class PaymentData:
    """Data structure to hold payment-related information."""

    contributor_username: str
    bounty_amount: int
    pr_number: int
    issue_number: int
    owner_name: str
    repo_name: str


def validate_api_token(request):
    """
    Validate the API token from request headers.
    Returns tuple: (is_valid: bool, error_response: JsonResponse or None)
    """

    expected_token = os.environ.get("BLT_API_TOKEN")
    if not expected_token:
        logger.critical("BLT_API_TOKEN environment variable is missing.")
        return False, JsonResponse({"status": "error", "message": "Server configuration error"}, status=500)

    received_token = request.headers.get("X-BLT-API-TOKEN")
    if received_token != expected_token:
        logger.warning("Invalid or missing token in request.")
        return False, JsonResponse({"status": "error", "message": "Unauthorized"}, status=403)
    return True, None


def extract_and_validate_data(request_body):
    """
    Extract and validate required data from request body.
    Returns tuple: (data: dict or None, error_response: JsonResponse or None)
    """
    try:
        data = json.loads(request_body)
    except json.JSONDecodeError:
        logger.exception("Invalid JSON received.")
        return None, JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)

    required_fields = ["issue_number", "repo", "owner", "contributor_username", "pr_number", "bounty_amount"]
    if not all(field in data for field in required_fields):
        logger.warning(f"Missing fields in request: {data}")
        return None, JsonResponse({"status": "error", "message": "Missing required fields"}, status=400)
    try:
        data["issue_number"] = int(data["issue_number"])
        data["pr_number"] = int(data["pr_number"])
        data["bounty_amount"] = int(data["bounty_amount"])

        if data["issue_number"] <= 0 or data["pr_number"] <= 0 or data["bounty_amount"] <= 0:
            raise ValueError("Numeric fields must be greater than 0")
    except (ValueError, TypeError):
        logger.warning(f"Invalid numeric fields in request: {data}")
        return None, JsonResponse({"status": "error", "message": "Invalid numeric fields"}, status=400)
    return data, None


def lookup_repo_and_issue(repo_name, owner_name, issue_number):
    """
    Look up repository and GitHub issue in database.
    Returns tuple: (repo: Repo, github_issue: GitHubIssue, error_response: JsonResponse or None)
    """
    repo = Repo.objects.filter(name=repo_name, organization__name=owner_name).first()
    if not repo:
        logger.error(f"Repo not found: {owner_name}/{repo_name}")
        return None, None, JsonResponse({"status": "error", "message": "Repository not found"}, status=404)

    github_issue = GitHubIssue.objects.filter(issue_id=issue_number, repo=repo).first()
    if not github_issue:
        logger.error(f"Issue #{issue_number} not found in repo {owner_name}/{repo_name}")
        return None, None, JsonResponse({"status": "error", "message": "Issue not found"}, status=404)

    return repo, github_issue, None


def check_duplicate_payment(github_issue):
    """
    Check if payment has already been processed for this issue.
    Returns JsonResponse if duplicate found, None otherwise.
    """
    if github_issue.sponsors_tx_id:
        return JsonResponse(
            {
                "status": "warning",
                "message": "Payment already processed",
                "transaction_id": github_issue.sponsors_tx_id,
            }
        )
    return None


def resolve_and_validate_contributor(contributor_username):
    """
    Validate contributor username exists (simplified for GitHub-only workflow).
    Returns tuple: (contributor_username: str, error_response: JsonResponse or None)
    """
    if not contributor_username or not contributor_username.strip():
        return None, JsonResponse({"status": "error", "message": "Invalid contributor username"}, status=400)

    return contributor_username, None


def process_payment_and_update_db(payment_data, github_issue):
    """
    Process the payment and update database with transaction ID.

    Args:
        payment_data: PaymentData instance containing payment details
        github_issue: GitHubIssue instance to update

    Returns:
        tuple: (success_response: JsonResponse or None, error_response: JsonResponse or None)
    """
    transaction_id = process_github_sponsors_payment(
        username=payment_data.contributor_username,
        amount=payment_data.bounty_amount,
        note=f"Bounty for PR #{payment_data.pr_number} resolving issue #{payment_data.issue_number} in {payment_data.owner_name}/{payment_data.repo_name}",
    )

    if not transaction_id:
        return None, JsonResponse({"status": "error", "message": "Payment processing failed"}, status=500)

    github_issue.sponsors_tx_id = transaction_id
    github_issue.save()

    # Add comment and labels to GitHub issue
    github_success = add_github_comment_and_labels(
        payment_data.owner_name, payment_data.repo_name, payment_data.issue_number, payment_data, transaction_id
    )

    if not github_success:
        logger.warning(f"Payment processed but failed to update GitHub issue #{payment_data.issue_number}")

    success_response = JsonResponse(
        {
            "status": "success",
            "message": "Payment processed",
            "transaction_id": transaction_id,
            "amount": payment_data.bounty_amount,
            "recipient": payment_data.contributor_username,
            "github_updated": github_success,
        }
    )

    return success_response, None


@csrf_exempt
@require_POST
def bounty_payout(request):
    """
    Handle bounty payout webhook from GitHub Action.
    """
    try:
        is_valid, error_response = validate_api_token(request)
        if not is_valid:
            return error_response

        data, error_response = extract_and_validate_data(request.body)
        if error_response:
            return error_response

        # Create PaymentData object from validated data
        payment_data = PaymentData(
            contributor_username=data["contributor_username"],
            bounty_amount=data["bounty_amount"],
            pr_number=data["pr_number"],
            issue_number=data["issue_number"],
            owner_name=data["owner"],
            repo_name=data["repo"],
        )

        repo, github_issue, error_response = lookup_repo_and_issue(
            payment_data.repo_name, payment_data.owner_name, payment_data.issue_number
        )
        if error_response:
            return error_response

        duplicate_response = check_duplicate_payment(github_issue)
        if duplicate_response:
            return duplicate_response

        contributor, error_response = resolve_and_validate_contributor(payment_data.contributor_username)
        if error_response:
            return error_response

        success_response, error_response = process_payment_and_update_db(payment_data, github_issue)

        if error_response:
            return error_response

        return success_response

    except Exception as e:
        logger.exception("Unexpected error in bounty_payout")
        return JsonResponse({"status": "error", "message": "An unexpected error occurred"}, status=500)


def get_sponsor_tiers(sponsor_login):
    """
    Fetch available sponsor tiers using GitHub GraphQL API.
    Returns a dict mapping amount (in cents) to tier node IDs.
    """

    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        logger.error("Missing GITHUB_TOKEN for GraphQL API.")
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
        logger.error("Missing GITHUB_TOKEN for GraphQL API.")
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
        "privacyLevel": "PUBLIC",  # or "PRIVATE" based on preference
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
            return sponsorship.get("id")

        logger.error("No sponsorship created in GraphQL response")
        return None

    except requests.RequestException as e:
        logger.error(f"Failed to create sponsorship: {e}")
        return None
    except Exception as e:
        logger.exception("Unexpected error creating sponsorship")
        return None


def process_github_sponsors_payment(username, amount, note):
    """
    Process GitHub Sponsors payment using the correct GraphQL API.
    Amount is expected in cents (e.g., 500 = $5.00).
    """
    try:
        sponsor_recipient = os.environ.get("GITHUB_SPONSORS_RECIPIENT")
        if not sponsor_recipient:
            logger.error("Missing GITHUB_SPONSORS_RECIPIENT environment variable.")
            return None

        tier_mapping_env = os.environ.get("GITHUB_SPONSORS_TIER_MAPPING")
        if tier_mapping_env:
            try:
                tier_mapping = json.loads(tier_mapping_env)

                tier_id = tier_mapping.get(amount) or tier_mapping.get(str(amount))
                if not tier_id:
                    logger.error(f"No tier mapping found for amount: {amount} cents")
                    return None
            except json.JSONDecodeError:
                logger.error("Invalid JSON in GITHUB_SPONSORS_TIER_MAPPING")
                return None
        else:
            tier_mapping = get_sponsor_tiers(sponsor_recipient)
            if not tier_mapping:
                logger.error("Failed to fetch sponsor tiers")
                return None

            tier_id = tier_mapping.get(amount)
            if not tier_id:
                logger.error(f"No tier found for amount: {amount} cents. Available tiers: {list(tier_mapping.keys())}")
                return None

        transaction_id = create_sponsorship_mutation(sponsor_recipient, tier_id, amount)

        if transaction_id:
            logger.info(f"Successfully created sponsorship {transaction_id} for {username} - ${amount/100:.2f}")
            return transaction_id
        logger.error("Failed to create sponsorship")
        return None

    except Exception as e:
        logger.exception("Exception during GitHub Sponsors payment processing")
        return None


def add_github_comment_and_labels(owner_name, repo_name, issue_number, payment_data, transaction_id):
    """
    Add a comment to the GitHub issue with payment details and add appropriate labels.

    Args:
        owner_name: Repository owner name
        repo_name: Repository name
        issue_number: Issue number
        payment_data: PaymentData instance containing payment details
        transaction_id: The payment transaction ID

    Returns:
        bool: True if successful, False otherwise
    """
    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        logger.error("Missing GITHUB_TOKEN for GitHub API.")
        return False

    # Create comment with payment details
    comment_success = create_payment_comment(
        owner_name, repo_name, issue_number, payment_data, transaction_id, github_token
    )

    # Add labels to the issue
    labels_success = add_issue_labels(owner_name, repo_name, issue_number, github_token)

    return comment_success and labels_success


def create_payment_comment(owner_name, repo_name, issue_number, payment_data, transaction_id, github_token):
    """
    Create a comment on the GitHub issue with payment details.
    """
    comment_body = f"""🎉 **Bounty Paid!** 🎉

💰 **Amount:** ${payment_data.bounty_amount / 100:.2f}
👤 **Recipient:** @{payment_data.contributor_username}
🔗 **PR:** #{payment_data.pr_number}
📋 **Transaction ID:** {transaction_id}

Thank you for your contribution to this project!"""

    url = f"https://api.github.com/repos/{owner_name}/{repo_name}/issues/{issue_number}/comments"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }

    data = {"body": comment_body}

    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        logger.info(f"Successfully added payment comment to issue #{issue_number} in {owner_name}/{repo_name}")
        return True
    except requests.RequestException as e:
        logger.error(f"Failed to add comment to GitHub issue: {e}")
        return False
    except Exception as e:
        logger.exception("Unexpected error adding GitHub comment")
        return False


def add_issue_labels(owner_name, repo_name, issue_number, github_token):
    """
    Add 'paid' and 'sponsors' labels to the GitHub issue.
    """
    url = f"https://api.github.com/repos/{owner_name}/{repo_name}/issues/{issue_number}/labels"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }

    labels = ["paid", "sponsors"]

    try:
        response = requests.post(url, headers=headers, json={"labels": labels}, timeout=10)
        response.raise_for_status()
        logger.info(f"Successfully added labels {labels} to issue #{issue_number} in {owner_name}/{repo_name}")
        return True
    except requests.RequestException as e:
        logger.error(f"Failed to add labels to GitHub issue: {e}")
        return False
    except Exception as e:
        logger.exception("Unexpected error adding GitHub labels")
        return False
