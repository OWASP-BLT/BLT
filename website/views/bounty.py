import json
import logging
import os
import secrets
import time
from functools import wraps

import requests
from django.core.cache import cache
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from website.models import GitHubIssue, Repo

logger = logging.getLogger(__name__)


def _coerce_to_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "on"}
    if isinstance(value, (int, float)):
        return bool(value)
    return False


def webhook_rate_limit(max_calls=10, period=60):
    """
    Rate limit decorator for webhook endpoints.
    Args:
        max_calls: Maximum number of calls allowed
        period: Time period in seconds
    """

    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            # Use REMOTE_ADDR for rate limiting to avoid spoofing via X-Forwarded-For
            # If behind a trusted proxy, use a proxy-aware utility (e.g., django-ipware) instead
            ip = request.META.get("REMOTE_ADDR")
            cache_key = f"webhook_ratelimit_{func.__name__}_{ip}"

            try:
                try:
                    current = cache.incr(cache_key)
                except ValueError:
                    # Key doesn't exist, initialize it atomically
                    if cache.add(cache_key, 1, timeout=period):
                        current = 1
                    else:
                        # Another thread initialized; increment
                        current = cache.incr(cache_key)
            except Exception as e:
                # Fail open: if cache backend is unavailable, allow the request
                logger.error(f"Cache error in webhook_rate_limit for {func.__name__} from {ip}: {e}", exc_info=True)
                return func(request, *args, **kwargs)

            if current > max_calls:
                logger.warning(f"Webhook rate limit exceeded for {func.__name__} from {ip}")
                return JsonResponse(
                    {"status": "error", "message": "Rate limit exceeded. Please try again later."}, status=429
                )

            return func(request, *args, **kwargs)

        return wrapper

    return decorator


@csrf_exempt
@require_POST
@webhook_rate_limit(max_calls=10, period=60)
def timed_bounty(request):
    """Record timed bounty metadata supplied by GitHub Actions."""

    MAX_DURATION_HOURS = 720

    try:
        expected_token = os.environ.get("BLT_API_TOKEN")
        if not expected_token:
            logger.error("BLT_API_TOKEN environment variable is missing")
            return JsonResponse({"status": "error", "message": "Server configuration error"}, status=500)

        received_token = request.headers.get("X-BLT-API-TOKEN")
        if not received_token or not secrets.compare_digest(received_token, expected_token):
            logger.warning("Invalid or missing API token for timed_bounty")
            return JsonResponse({"status": "error", "message": "Unauthorized"}, status=403)

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            logger.error("Invalid JSON in timed_bounty request body")
            return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)

        required_fields = ["issue_number", "repo", "owner", "bounty_expiry_date"]
        if not all(field in data for field in required_fields):
            logger.warning(f"Missing required fields in timed_bounty request: {data}")
            return JsonResponse({"status": "error", "message": "Missing required fields"}, status=400)

        try:
            issue_number = int(data["issue_number"])
        except (ValueError, TypeError):
            logger.warning("Invalid issue_number in timed_bounty request")
            return JsonResponse({"status": "error", "message": "Invalid issue number"}, status=400)

        repo_name = data["repo"]
        owner_name = data["owner"]

        repo = Repo.objects.filter(name=repo_name, organization__name=owner_name).first()
        if not repo:
            logger.error(f"Repo not found for timed bounty: {owner_name}/{repo_name}")
            return JsonResponse({"status": "error", "message": "Repository not found"}, status=404)

        github_issue = GitHubIssue.objects.filter(issue_id=issue_number, repo=repo).first()
        if not github_issue:
            logger.error(f"Issue #{issue_number} not found for timed bounty in {owner_name}/{repo_name}")
            return JsonResponse({"status": "error", "message": "Issue not found"}, status=404)

        expiry_raw = data["bounty_expiry_date"]
        expiry_dt = parse_datetime(expiry_raw)
        if not expiry_dt:
            logger.warning(f"Unable to parse bounty_expiry_date '{expiry_raw}' for issue #{issue_number}")
            return JsonResponse({"status": "error", "message": "Invalid bounty_expiry_date"}, status=400)

        if timezone.is_naive(expiry_dt):
            expiry_dt = timezone.make_aware(expiry_dt, timezone.utc)

        # Validate duration is reasonable
        now = timezone.now()
        duration_seconds = (expiry_dt - now).total_seconds()
        duration_hours = duration_seconds / 3600

        if duration_hours > MAX_DURATION_HOURS:
            logger.warning(
                f"Bounty duration {duration_hours:.1f} hours exceeds maximum {MAX_DURATION_HOURS} hours "
                f"for issue #{issue_number}"
            )
            max_days = MAX_DURATION_HOURS / 24
            return JsonResponse(
                {
                    "status": "error",
                    "message": f"Bounty duration exceeds maximum of {MAX_DURATION_HOURS} hours ({max_days:g} days)",
                },
                status=400,
            )

        if duration_hours < 0:
            logger.warning(f"Bounty expiry date is in the past for issue #{issue_number}")
            return JsonResponse({"status": "error", "message": "Bounty expiry date cannot be in the past"}, status=400)

        try:
            with transaction.atomic():
                # Lock the row to prevent concurrent updates
                github_issue = GitHubIssue.objects.select_for_update().get(issue_id=issue_number, repo=repo)
                github_issue.bounty_expiry_date = expiry_dt
                github_issue.save(update_fields=["bounty_expiry_date"])

            logger.info(
                "Stored timed bounty expiry for issue #%s in %s/%s at %s",
                issue_number,
                owner_name,
                repo_name,
                expiry_dt.isoformat(),
            )

            return JsonResponse(
                {
                    "status": "success",
                    "message": "Timed bounty recorded",
                    "issue_number": issue_number,
                    "bounty_expiry_date": expiry_dt.isoformat(),
                }
            )
        except GitHubIssue.DoesNotExist:
            logger.error(f"GitHubIssue not found for issue #{issue_number} in {owner_name}/{repo_name}")
            return JsonResponse({"status": "error", "message": "Issue not found"}, status=404)

    except Exception:
        logger.exception("Unexpected error in timed_bounty")
        return JsonResponse({"status": "error", "message": "An unexpected error occurred"}, status=500)


@csrf_exempt
@require_POST
@webhook_rate_limit(max_calls=20, period=60)
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
        # For test compatibility: if is_timed_bounty is True in the request, require bounty_expiry_date
        is_timed_bounty = _coerce_to_bool(data.get("is_timed_bounty"))

        # Look up repository and issue
        repo = Repo.objects.filter(name=repo_name, organization__name=owner_name).first()
        if not repo:
            logger.error(f"Repo not found: {owner_name}/{repo_name}")
            return JsonResponse({"status": "error", "message": "Repository not found"}, status=404)

        github_issue = GitHubIssue.objects.filter(issue_id=issue_number, repo=repo).first()
        if not github_issue:
            logger.error(f"Issue #{issue_number} not found in repo {owner_name}/{repo_name}")
            return JsonResponse({"status": "error", "message": "Issue not found"}, status=404)

        # --- First transaction: validation and atomic intent marking ---
        try:
            with transaction.atomic():
                github_issue = GitHubIssue.objects.select_for_update().get(issue_id=issue_number, repo=repo)

                # For test compatibility: if is_timed_bounty True and no expiry, return 400
                if is_timed_bounty and github_issue.bounty_expiry_date is None:
                    logger.warning(f"Timed bounty expiry date not set for issue #{issue_number}")
                    return JsonResponse({"status": "error", "message": "Timed bounty expiry date not set"}, status=400)

                # Only enforce expiry when the current label is a timed bounty.
                if is_timed_bounty and github_issue.bounty_expiry_date is not None:
                    now = timezone.now()
                    if now > github_issue.bounty_expiry_date:
                        logger.info(
                            f"Bounty for issue #{issue_number} expired at {github_issue.bounty_expiry_date.isoformat()}"
                        )
                        return JsonResponse({"status": "error", "message": "Bounty expired"}, status=400)
                elif not is_timed_bounty and github_issue.bounty_expiry_date is not None:
                    logger.info(
                        f"Clearing stale bounty_expiry_date for non-timed bounty issue #{issue_number}"
                    )
                    github_issue.bounty_expiry_date = None
                    github_issue.save(update_fields=["bounty_expiry_date"])

                # Check for duplicate payment or in-progress payment
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
                if github_issue.payment_pending:
                    logger.info(f"Payment is already in progress for issue #{issue_number}")
                    return JsonResponse(
                        {
                            "status": "warning",
                            "message": "Bounty payment is already in progress for this issue. Please wait.",
                        },
                        status=202,
                    )

                # Mark payment as pending atomically
                github_issue.payment_pending = True
                github_issue.save(update_fields=["payment_pending"])

        except GitHubIssue.DoesNotExist:
            logger.error(f"GitHubIssue not found: issue #{issue_number} in {owner_name}/{repo_name}")
            return JsonResponse({"status": "error", "message": "Issue not found"}, status=404)

        # --- External payment call (outside transaction) ---
        transaction_id = process_github_sponsors_payment(
            username=contributor_username,
            amount=bounty_amount,
            note=f"Bounty for PR #{pr_number} resolving issue #{issue_number} in {owner_name}/{repo_name}",
        )

        if not transaction_id:
            logger.error(f"Failed to process GitHub Sponsors payment for issue #{issue_number}")
            # Reset payment_pending with retries to avoid permanently locking the bounty
            max_cleanup_retries = 3
            cleanup_success = False
            for attempt in range(1, max_cleanup_retries + 1):
                try:
                    with transaction.atomic():
                        github_issue = GitHubIssue.objects.select_for_update().get(issue_id=issue_number, repo=repo)
                        github_issue.payment_pending = False
                        github_issue.save(update_fields=["payment_pending"])
                    cleanup_success = True
                    break
                except Exception:
                    logger.exception(
                        "Attempt %d/%d: Failed to clear payment_pending for issue #%s",
                        attempt,
                        max_cleanup_retries,
                        issue_number,
                    )
                    if attempt < max_cleanup_retries:
                        time.sleep(0.5 * attempt)
            if not cleanup_success:
                logger.critical(
                    "MANUAL INTERVENTION REQUIRED: payment_pending is stuck True for "
                    "issue #%s in %s/%s after payment failure. All %d cleanup attempts failed.",
                    issue_number,
                    owner_name,
                    repo_name,
                    max_cleanup_retries,
                )
            return JsonResponse({"status": "error", "message": "Payment processing failed"}, status=500)

        logger.info(
            f"Successfully processed bounty payment: ${bounty_amount / 100:.2f} to {contributor_username} "
            f"for PR #{pr_number} (Issue #{issue_number})"
        )

        # --- Second transaction: record payment ---
        try:
            with transaction.atomic():
                github_issue = GitHubIssue.objects.select_for_update().get(issue_id=issue_number, repo=repo)
                github_issue.sponsors_tx_id = transaction_id
                github_issue.payment_pending = False
                github_issue.save()
        except GitHubIssue.DoesNotExist:
            logger.error(f"GitHubIssue not found: issue #{issue_number} in {owner_name}/{repo_name} after payment")
            return JsonResponse({"status": "error", "message": "Issue not found after payment"}, status=404)
        except Exception:
            logger.exception(
                "Failed to record sponsors_tx_id after payment. "
                "Payment was sent successfully - transaction_id=%s, amount=%s, recipient=%s, issue=#%s",
                transaction_id,
                bounty_amount,
                contributor_username,
                issue_number,
            )
            # Attempt to recover: reset payment_pending and store the transaction ID
            # so the issue is not permanently stuck.
            try:
                with transaction.atomic():
                    gi = GitHubIssue.objects.select_for_update().get(issue_id=issue_number, repo=repo)
                    gi.sponsors_tx_id = transaction_id
                    gi.payment_pending = False
                    gi.save(update_fields=["sponsors_tx_id", "payment_pending"])
                logger.info(
                    "Recovery succeeded: recorded transaction_id=%s for issue #%s",
                    transaction_id,
                    issue_number,
                )
            except Exception:
                logger.critical(
                    "MANUAL INTERVENTION REQUIRED: Payment sent but could not record "
                    "transaction_id=%s for issue #%s in %s/%s. payment_pending is stuck True.",
                    transaction_id,
                    issue_number,
                    owner_name,
                    repo_name,
                    exc_info=True,
                )
            return JsonResponse({"status": "error", "message": "Failed to record payment"}, status=500)

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

    # Fetch up to 50 sponsor tiers (configurable via environment variable)
    max_tiers = int(os.environ.get("GITHUB_SPONSORS_MAX_TIERS", "50"))

    query = """
    query($login: String!, $maxTiers: Int!) {
        user(login: $login) {
            sponsorsListing {
                tiers(first: $maxTiers) {
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
            json={"query": query, "variables": {"login": sponsor_login, "maxTiers": max_tiers}},
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
        # The sponsor payer is DonnieBLT (who pays the bounty)
        sponsor_payer = os.environ.get("GITHUB_SPONSORS_RECIPIENT", "DonnieBLT")
        logger.info(f"Processing payment of ${amount / 100:.2f} from {sponsor_payer} to {username}")

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
