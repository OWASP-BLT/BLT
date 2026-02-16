import json
import logging
import re
from collections import defaultdict

import requests
import yaml
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_POST
from slack_sdk.errors import SlackApiError
from slack_sdk.web import WebClient

from blt import settings as blt_settings
from website.models import BaconEarning, BaconSubmission, Badge, Organization, SlackIntegration, UserBadge

logger = logging.getLogger(__name__)


def slack_escape(text):
    """
    Escape Slack markdown characters in text to prevent formatting issues.
    Escapes: _, *, `, ~, &, <, >
    IMPORTANT: Escape '&' first to avoid corrupting HTML entities.
    """
    if not text:
        return text
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("*", "\\*")
        .replace("_", "\\_")
        .replace("`", "\\`")
        .replace("~", "\\~")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


@login_required
def batch_send_bacon_tokens_view(request):
    # Get all users with non-zero tokens_earned
    users_with_tokens = BaconEarning.objects.filter(tokens_earned__gt=0)

    if not users_with_tokens.exists():
        return JsonResponse({"status": "error", "message": "No eligible users with tokens to send."})

    # Build YAML content
    yaml_outputs = []
    for token_earning in users_with_tokens:
        user = token_earning.user
        btc_address = getattr(user.userprofile, "btc_address", None)
        tokens_to_send = token_earning.tokens_earned

        if btc_address and tokens_to_send > 0:
            yaml_outputs.append(f"- address: {btc_address}\n  runes:\n    BLT•BACON•TOKENS: {tokens_to_send}")

    # Form the YAML string payload
    yaml_content = "outputs:\n" + "\n".join(yaml_outputs)

    # Payload for POST request
    payload = {"yaml_content": yaml_content}
    ORD_SERVER_URL = blt_settings.ORD_SERVER_URL
    try:
        # Send the request to the ORD server
        response = requests.post(
            f"{ORD_SERVER_URL}/send-bacon-tokens",
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload),
        )
        response_data = response.json()

        # Reset the tokens_earned for all users if the request was successful
        if response.status_code == 200 and response_data.get("success"):
            users_with_tokens.update(tokens_earned=0)
            return JsonResponse(
                {
                    "status": "success",
                    "message": "Tokens successfully sent to all eligible users. If it doesnt appear in the users wallet yet , wait for the miners to confirm the transaction.",
                }
            )
        else:
            return JsonResponse({"status": "error", "message": response_data.get("error", "Unknown error")})

    except requests.RequestException as e:
        logger.error(f"Request error in batch_send_bacon_tokens_view: {str(e)}", exc_info=True)
        return JsonResponse(
            {"status": "error", "message": "An error occurred while sending tokens. Please try again later."}
        )


@login_required
def pending_transactions_view(request):
    # Fetch all users with non-zero tokens_earned
    pending_transactions = BaconEarning.objects.filter(tokens_earned__gt=0)
    # Prepare a list of user: address: tokens data
    transactions_data = []
    for transaction in pending_transactions:
        user = transaction.user
        btc_address = getattr(user.userprofile, "btc_address", None)
        transactions_data.append({"user": user.username, "address": btc_address, "tokens": transaction.tokens_earned})

    # If you want to return it as a JSON response:
    return JsonResponse({"pending_transactions": transactions_data})


@method_decorator(login_required, name="dispatch")
class BaconSubmissionView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)

            # Extracting fields
            github_url = data.get("github_url")
            contribution_type = data.get("contribution_type")
            description = data.get("description")
            status = data.get("status", "in_review")  # Default to "in_review"
            bacon_amount = data.get("bacon_amount", 0)  # Default to 0

            # Validations
            if not github_url or not contribution_type or not description:
                return JsonResponse({"error": "Missing required fields"}, status=400)

            if contribution_type not in ["security", "non-security"]:
                return JsonResponse({"error": "Invalid contribution type"}, status=400)

            if status not in ["in_review", "accepted", "declined"]:
                return JsonResponse({"error": "Invalid status"}, status=400)

            # Validate GitHub PR URL format
            pr_url_pattern = r"^https:\/\/github\.com\/[^\/]+\/[^\/]+\/pull\/\d+$"
            if not re.match(pr_url_pattern, github_url):
                return JsonResponse({"error": "Invalid GitHub PR link"}, status=400)

            # Create submission
            submission = BaconSubmission.objects.create(
                user=request.user,
                github_url=github_url,
                contribution_type=contribution_type,
                description=description,
                bacon_amount=bacon_amount,
                status=status,
            )

            # Send Slack notification to #project-blt-bacon channel
            try:
                # Find OWASP BLT organization
                # Use exact match first, fallback to case-insensitive contains for flexibility
                owasp_org = Organization.objects.filter(name="OWASP BLT").first()
                if not owasp_org:
                    owasp_org = Organization.objects.filter(name__icontains="OWASP BLT").first()

                if owasp_org:
                    # Get Slack integration for the organization
                    slack_integration = SlackIntegration.objects.filter(integration__organization=owasp_org).first()

                    if slack_integration and slack_integration.bot_access_token:
                        # Get credentials from database
                        bot_token = slack_integration.bot_access_token
                        channel_id = slack_integration.default_channel_id

                        # Create WebClient once for reuse
                        client = WebClient(token=bot_token)

                        # If no default channel ID is set, try to find #project-blt-bacon specifically
                        # Handle pagination to ensure we check all channels
                        if not channel_id:
                            try:
                                cursor = None
                                while True:
                                    channels_response = client.conversations_list(types="public_channel", cursor=cursor)
                                    if channels_response.get("ok"):
                                        for channel in channels_response.get("channels", []):
                                            if channel.get("name") == "project-blt-bacon":
                                                channel_id = channel.get("id")
                                                break
                                        if channel_id:
                                            break
                                        # Check for next page
                                        cursor = channels_response.get("response_metadata", {}).get("next_cursor")
                                        if not cursor:
                                            break
                                    else:
                                        logger.warning(
                                            "Failed to list Slack channels: %s",
                                            channels_response.get("error"),
                                        )
                                        break
                            except SlackApiError as e:
                                logger.warning("Failed to find #project-blt-bacon channel: %s", e)

                        # Send notification if we have a channel ID
                        if channel_id:
                            # Sanitize description for Slack markdown (escape special characters)
                            # Slack markdown uses *, _, `, ~, <, >, & for formatting
                            sanitized_description = description[:200]
                            sanitized_description = slack_escape(sanitized_description)
                            if len(description) > 200:
                                sanitized_description += "..."

                            # Escape username and other user-provided fields for Slack markdown
                            escaped_username = slack_escape(request.user.username)
                            escaped_type = slack_escape(contribution_type)
                            escaped_status = slack_escape(status)

                            # Build the message
                            message = (
                                f"*New BACON Claim Submitted!*\n\n"
                                f"• *User:* {escaped_username}\n"
                                f"• *Type:* {escaped_type}\n"
                                f"• *PR:* {github_url}\n"
                                f"• *Description:* {sanitized_description}\n"
                                f"• *Amount:* {bacon_amount} BACON\n"
                                f"• *Status:* {escaped_status}"
                            )

                            # Send to Slack
                            try:
                                client.chat_postMessage(
                                    channel=channel_id,
                                    text=message,
                                    unfurl_links=False,
                                )
                                logger.info("Slack notification sent for submission %s", submission.id)
                            except SlackApiError as e:
                                logger.error(
                                    "Failed to send Slack message to channel %s: %s",
                                    channel_id,
                                    e,
                                    exc_info=True,
                                )
                        else:
                            logger.warning(
                                "Slack channel #project-blt-bacon not found and no default channel configured"
                            )
                    else:
                        logger.warning("Slack integration not configured for OWASP BLT")
                else:
                    logger.warning("OWASP BLT organization not found")

            except Exception as e:
                # Don't fail the submission if Slack fails
                logger.error("Failed to send Slack notification: %s", e, exc_info=True)

            return JsonResponse({"message": "Submission created", "submission_id": submission.id}, status=201)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)


@login_required
def bacon_requests_view(request):
    """View to list and filter Bacon submissions."""

    tx_status = request.GET.get("tx-status", "")
    decision_status = request.GET.get("decision-status", "")

    submissions = BaconSubmission.objects.all()

    if tx_status in ["pending", "completed"]:
        submissions = submissions.filter(transaction_status=tx_status)

    if decision_status in ["accepted", "declined"]:
        submissions = submissions.filter(status=decision_status)

    # Check if the logged-in user is a mentor
    mentor_badge = Badge.objects.filter(title="mentor").first()
    is_mentor = UserBadge.objects.filter(user=request.user, badge=mentor_badge).exists()

    return render(
        request,
        "bacon_requests.html",
        {
            "submissions": submissions,
            "tx_status": tx_status,
            "decision_status": decision_status,
            "is_mentor": is_mentor,
        },
    )


@login_required
@require_POST
def update_submission_status(request, submission_id):
    """Allows a mentor to update the submission status and bacon amount."""
    try:
        data = json.loads(request.body)
        new_status = data.get("status")  # 'accepted' or 'declined'
        new_bacon_amount = data.get("bacon_amount")

        submission = get_object_or_404(BaconSubmission, id=submission_id)

        # Check if the user is a mentor
        mentor_badge = Badge.objects.filter(title="mentor").first()
        is_mentor = UserBadge.objects.filter(user=request.user, badge=mentor_badge).exists()

        if not is_mentor:
            return JsonResponse({"error": "Unauthorized"}, status=403)

        # Update status and bacon amount if provided
        if new_status:
            submission.status = new_status
        if new_bacon_amount is not None:
            submission.bacon_amount = new_bacon_amount

        submission.save()
        return JsonResponse(
            {"success": True, "new_status": submission.status, "new_bacon_amount": submission.bacon_amount}
        )

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format"}, status=400)
    except Exception:
        logger.exception("Error updating submission status")
        return JsonResponse({"error": "error updating submission status"}, status=400)


@login_required
def initiate_transaction(request):
    """Page to initiate transactions, only accessible to mentors."""

    if request.method == "POST":
        try:
            data = json.loads(request.body)
            selected_users = data.get("selected_users", [])
            fee_rate = data.get("fee_rate")
            dry_run = data.get("dry_run")
            network = data.get("network")
            password = ""
            if dry_run is False:
                password = data.get("password")

            if not network:
                return JsonResponse({"error": "Network is required"}, status=400)

            total_bacon = sum(user["bacon_amount"] for user in selected_users)

            # MAINNET LOGIC: Send YAML payload along with JSON fields
            if network == "mainnet":
                outputs = [
                    {"address": user["bch_address"], "runes": {"BLT•BACON•TOKENS": user["bacon_amount"]}}
                    for user in selected_users
                ]

                yaml_payload = yaml.dump({"outputs": outputs}, default_flow_style=False)

                final_payload = {
                    "yaml_content": yaml_payload,  # Send YAML as a string
                    "fee_rate": fee_rate,
                    "dry_run": dry_run,
                    "password": password,
                }

                # Send request to ORD server
                ord_server_url = blt_settings.ORD_SERVER_URL

                if not ord_server_url:
                    return JsonResponse({"error": "ORD_SERVER_URL is not configured"}, status=500)

                response = requests.post(f"{ord_server_url}/mainnet/send-bacon-tokens", json=final_payload)
                response_data = response.json()
                if response.status_code == 200 and "txid" in response_data:
                    txid = response_data["txid"]

                    # Update each selected user's BaconSubmission record
                    for user in selected_users:
                        BaconSubmission.objects.filter(user__username=user["username"]).update(
                            transaction_id=txid, transaction_status="completed"
                        )
                    return JsonResponse(response_data)
                else:
                    return JsonResponse(
                        {"error": "Failed to process transaction on mainnet"}, status=response.status_code
                    )

            # REGTEST LOGIC: Send only required fields in JSON
            elif network == "regtest":
                final_payload = {"num_users": len(selected_users), "fee_rate": fee_rate, "dry_run": dry_run}

                ord_server_url = blt_settings.ORD_SERVER_URL

                if not ord_server_url:
                    return JsonResponse({"error": "ORD_SERVER_URL is not configured"}, status=500)

                response = requests.post(f"{ord_server_url}/regtest/send-bacon-tokens", json=final_payload)
                response_data = response.json()
                if response.status_code == 200:
                    return JsonResponse(response_data)
                else:
                    return JsonResponse(
                        {"error": "Failed to process transaction on regtest"}, status=response.status_code
                    )

            else:
                return JsonResponse({"error": "Invalid network specified"}, status=400)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON format"}, status=400)

    # Check if the user is a mentor
    mentor_badge = Badge.objects.filter(title="mentor").first()
    is_mentor = UserBadge.objects.filter(user=request.user, badge=mentor_badge).exists()
    if not is_mentor:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    # Fetch submissions where status is 'accepted' and transaction is still pending
    submissions_by_user = defaultdict(lambda: {"submissions": [], "total_bacon": 0})

    submissions = BaconSubmission.objects.filter(status="accepted", transaction_status="pending").select_related("user")

    for submission in submissions:
        submissions_by_user[submission.user]["submissions"].append(submission)
        submissions_by_user[submission.user]["total_bacon"] += submission.bacon_amount

    return render(request, "bacon_transaction.html", {"submissions_by_user": dict(submissions_by_user)})


@login_required
def get_wallet_balance(request):
    """View to get the wallet balance of the logged-in user."""
    user = request.user

    # Check if the user is a mentor
    mentor_badge = Badge.objects.filter(title="mentor").first()
    is_mentor = UserBadge.objects.filter(user=user, badge=mentor_badge).exists()
    if not is_mentor:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    # Fetch the wallet balance from the ORD server
    ord_server_url = blt_settings.ORD_SERVER_URL
    if not ord_server_url:
        return JsonResponse({"error": "ORD_SERVER_URL is not configured"}, status=500)

    try:
        response = requests.get(f"{ord_server_url}/mainnet/wallet-balance")
        response_data = response.json()
        if response.status_code == 200 and response_data.get("success"):
            balance_data = json.loads(response_data["balance"])
            return JsonResponse({"balance": balance_data, "success": True})
        else:
            return JsonResponse({"error": "Failed to fetch wallet balance"}, status=response.status_code)
    except requests.RequestException:
        logger.exception("Error fetching wallet balance")
        return JsonResponse({"error": "There's some problem fetching wallet details"}, status=500)


def bacon_view(request):
    """Combined view for bacon form and requests."""
    tx_status = request.GET.get("tx-status", "")
    decision_status = request.GET.get("decision-status", "")

    submissions = BaconSubmission.objects.all().order_by("-created_at")

    if tx_status in ["pending", "completed"]:
        submissions = submissions.filter(transaction_status=tx_status)

    if decision_status in ["accepted", "declined"]:
        submissions = submissions.filter(status=decision_status)

    # Check if the logged-in user is a mentor
    mentor_badge = Badge.objects.filter(title="mentor").first()
    if request.user.is_authenticated:
        is_mentor = UserBadge.objects.filter(user=request.user, badge=mentor_badge).exists()
    else:
        is_mentor = False

    return render(
        request,
        "bacon.html",
        {
            "submissions": submissions,
            "tx_status": tx_status,
            "decision_status": decision_status,
            "is_mentor": is_mentor,
        },
    )
