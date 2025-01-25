import hashlib
import hmac
import json
import os
import time

from django.db.models import Count
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from slack import WebClient
from slack_sdk.errors import SlackApiError

from website.models import Domain, Hunt, Issue, Project, SlackBotActivity, SlackIntegration, User

if os.getenv("ENV") != "production":
    from dotenv import load_dotenv

    load_dotenv()
SLACK_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")
client = WebClient(token=SLACK_TOKEN)


def verify_slack_signature(request):
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")

    # Check if required headers are present
    if not timestamp or not signature:
        return False

    try:
        # Verify timestamp to prevent replay attacks
        current_time = time.time()
        request_time = float(timestamp)
        time_diff = abs(current_time - request_time)

        if time_diff > 60 * 5:
            return False

        # Create the signature base string
        sig_basestring = f"v0:{timestamp}:{request.body.decode()}"

        # Calculate our signature
        my_signature = "v0=" + hmac.new(SIGNING_SECRET.encode(), sig_basestring.encode(), hashlib.sha256).hexdigest()

        # Compare signatures
        is_valid = hmac.compare_digest(my_signature, signature)
        return is_valid

    except (ValueError, TypeError) as e:
        return False


@csrf_exempt
def slack_events(request):
    """Handle incoming Slack events"""
    if request.method == "POST":
        # Verify the request is from Slack
        if not verify_slack_signature(request):
            return HttpResponse(status=403)

        data = json.loads(request.body)

        # Check if this is a retry event
        is_retry = request.headers.get("X-Slack-Retry-Num")
        if is_retry:
            return HttpResponse(status=200)

        if "challenge" in data:
            return JsonResponse({"challenge": data["challenge"]})

        event = data.get("event", {})
        event_type = event.get("type")

        if event_type == "team_join":
            user_data = event.get("user", {})
            if isinstance(user_data, dict):
                user_id = user_data.get("id")
            else:
                user_id = event.get("user")

            if user_id:
                _handle_team_join(user_id, request)

        return HttpResponse(status=200)
    return HttpResponse(status=405)


def _handle_team_join(user_id, request):
    try:
        event_data = json.loads(request.body)
        team_id = event_data["team_id"]

        # Log the activity at the start
        activity = SlackBotActivity.objects.create(
            workspace_id=team_id, activity_type="team_join", user_id=user_id, details={"event_data": event_data}
        )

        try:
            slack_integration = SlackIntegration.objects.get(workspace_name=team_id)
            activity.workspace_name = slack_integration.integration.organization.name
            activity.save()

            # If integration exists and has welcome message
            if slack_integration.welcome_message:
                welcome_message = slack_integration.welcome_message
                workspace_client = WebClient(token=slack_integration.bot_access_token)
            else:
                # If no welcome message but it's OWASP workspace
                if team_id == "T04T40NHX":
                    workspace_client = WebClient(token=SLACK_TOKEN)
                    welcome_message = (
                        f":tada: *Welcome to the OWASP Slack Community, <@{user_id}>!* :tada:\n\n"
                        "We're thrilled to have you here! Whether you're new to OWASP or a long-time contributor, "
                        "this Slack workspace is the perfect place to connect, collaborate, and stay informed about all things OWASP.\n\n"
                        ":small_blue_diamond: *Get Involved:*\n"
                        "• Check out the *#contribute* channel to find ways to get involved with OWASP projects and initiatives.\n"
                        "• Explore individual project channels, which are named *#project-name*, to dive into specific projects that interest you.\n"
                        "• Join our chapter channels, named *#chapter-name*, to connect with local OWASP members in your area.\n\n"
                        ":small_blue_diamond: *Stay Updated:*\n"
                        "• Visit *#newsroom* for the latest updates and announcements.\n"
                        "• Follow *#external-activities* for news about OWASP's engagement with the wider security community.\n\n"
                        ":small_blue_diamond: *Connect and Learn:*\n"
                        "• *#jobs*: Looking for new opportunities? Check out the latest job postings here.\n"
                        "• *#leaders*: Connect with OWASP leaders and stay informed about leadership activities.\n"
                        "• *#project-committee*: Engage with the committee overseeing OWASP projects.\n"
                        "• *#gsoc*: Stay updated on Google Summer of Code initiatives.\n"
                        "• *#github-admins*: Get support and discuss issues related to OWASP's GitHub repositories.\n"
                        "• *#learning*: Share and find resources to expand your knowledge in the field of application security.\n\n"
                        "We're excited to see the amazing contributions you'll make. If you have any questions or need assistance, don't hesitate to ask. "
                        "Let's work together to make software security visible and improve the security of the software we all rely on.\n\n"
                        "Welcome aboard! :rocket:"
                    )
                else:
                    workspace_client = WebClient(token=slack_integration.bot_access_token)
                    welcome_message = (
                        f"Welcome <@{user_id}>! 👋\n\n"
                        "Your workspace admin hasn't set up a custom welcome message yet. "
                        "They can configure this in the organization's integration settings."
                    )

        except SlackIntegration.DoesNotExist:
            # If no integration exists but it's OWASP workspace
            if team_id == "T04T40NHX":
                workspace_client = WebClient(token=SLACK_TOKEN)
                # Use the default OWASP welcome message
                welcome_message = (
                    f":tada: *Welcome to the OWASP Slack Community, <@{user_id}>!* :tada:\n\n"
                    "We're thrilled to have you here! Whether you're new to OWASP or a long-time contributor, "
                    "this Slack workspace is the perfect place to connect, collaborate, and stay informed about all things OWASP.\n\n"
                    ":small_blue_diamond: *Get Involved:*\n"
                    "• Check out the *#contribute* channel to find ways to get involved with OWASP projects and initiatives.\n"
                    "• Explore individual project channels, which are named *#project-name*, to dive into specific projects that interest you.\n"
                    "• Join our chapter channels, named *#chapter-name*, to connect with local OWASP members in your area.\n\n"
                    ":small_blue_diamond: *Stay Updated:*\n"
                    "• Visit *#newsroom* for the latest updates and announcements.\n"
                    "• Follow *#external-activities* for news about OWASP's engagement with the wider security community.\n\n"
                    ":small_blue_diamond: *Connect and Learn:*\n"
                    "• *#jobs*: Looking for new opportunities? Check out the latest job postings here.\n"
                    "• *#leaders*: Connect with OWASP leaders and stay informed about leadership activities.\n"
                    "• *#project-committee*: Engage with the committee overseeing OWASP projects.\n"
                    "• *#gsoc*: Stay updated on Google Summer of Code initiatives.\n"
                    "• *#github-admins*: Get support and discuss issues related to OWASP's GitHub repositories.\n"
                    "• *#learning*: Share and find resources to expand your knowledge in the field of application security.\n\n"
                    "We're excited to see the amazing contributions you'll make. If you have any questions or need assistance, don't hesitate to ask. "
                    "Let's work together to make software security visible and improve the security of the software we all rely on.\n\n"
                    "Welcome aboard! :rocket:"
                )
            else:
                return

        # Add delay to ensure user is fully joined
        time.sleep(2)  # Wait 2 seconds before sending message

        # Try to open DM first
        try:
            dm_response = workspace_client.conversations_open(users=[user_id])
            if not dm_response["ok"]:
                return

            dm_channel = dm_response["channel"]["id"]

            welcome_blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": welcome_message}}]

            # Send message using appropriate client
            welcome_response = workspace_client.chat_postMessage(
                channel=dm_channel, text=welcome_message, blocks=welcome_blocks
            )

        except SlackApiError as e:
            activity.success = False
            activity.error_message = str(e)
            activity.save()
            return

    except Exception as e:
        SlackBotActivity.objects.create(
            workspace_id=team_id if "team_id" in locals() else "unknown",
            activity_type="team_join",
            user_id=user_id,
            success=False,
            error_message=str(e),
        )
        return


@csrf_exempt
def slack_commands(request):
    """Handle Slack slash commands"""
    if request.method == "POST":
        # Verify the request is from Slack
        is_valid = verify_slack_signature(request)

        if not is_valid:
            return HttpResponse(status=403)

        command = request.POST.get("command")
        user_id = request.POST.get("user_id")
        team_id = request.POST.get("team_id")
        team_domain = request.POST.get("team_domain")  # Get the team domain

        # Log the command activity
        activity = SlackBotActivity.objects.create(
            workspace_id=team_id,
            workspace_name=team_domain,
            activity_type="command",
            user_id=user_id,
            details={"command": command, "channel_id": request.POST.get("channel_id")},
        )

        if command == "/stats":
            # Get project counts by status
            project_stats = Project.objects.values("status").annotate(count=Count("id"))
            stats_by_status = {stat["status"]: stat["count"] for stat in project_stats}

            # Get other key metrics
            total_issues = Issue.objects.count()
            total_users = User.objects.count()
            total_domains = Domain.objects.count()
            total_hunts = Hunt.objects.count()

            # Format stats sections with line breaks for readability
            stats_sections = [
                "*Project Statistics:*\n",
                "• Flagship Projects: " f"{stats_by_status.get('flagship', 0)}",
                "• Production Projects: " f"{stats_by_status.get('production', 0)}",
                "• Incubator Projects: " f"{stats_by_status.get('incubator', 0)}",
                "• Lab Projects: " f"{stats_by_status.get('lab', 0)}",
                "• New Projects: " f"{stats_by_status.get('new', 0)}",
                "• Active Projects: " f"{stats_by_status.get('active', 0)}",
                "• Inactive Projects: " f"{stats_by_status.get('inactive', 0)}",
                "\n*Overall Platform Statistics:*\n",
                f"• Total Issues: {total_issues}",
                f"• Total Users: {total_users}",
                f"• Total Domains: {total_domains}",
                f"• Total Hunts: {total_hunts}",
            ]

            stats_message = "\n".join(stats_sections)

            try:
                # Post message to Slack
                client = WebClient(token=workspace_client.bot_token)
                client.chat_postMessage(channel=request.POST.get("channel_id"), text=stats_message)
                return JsonResponse({"response_type": "in_channel"})
            except SlackApiError:
                activity.success = False
                activity.error_message = "Error posting message"
                activity.save()
                return JsonResponse({"error": "Error posting message"}, status=500)

        elif command == "/contrib":
            try:
                # First try to get custom integration
                try:
                    slack_integration = SlackIntegration.objects.get(workspace_name=team_id)
                    workspace_client = WebClient(token=slack_integration.bot_access_token)
                except SlackIntegration.DoesNotExist:
                    # If no custom integration and it's OWASP workspace, use default token
                    if team_domain == "owasp":
                        workspace_client = WebClient(token=SLACK_TOKEN)
                    else:
                        return JsonResponse(
                            {
                                "response_type": "ephemeral",
                                "text": "This workspace is not properly configured. Please contact the workspace admin.",
                            }
                        )

                contribute_message = [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": ":rocket: *Contributing to OWASP Projects*\n\n"
                            "    🔹 *Join the OWASP Slack Channel:* Find guidance and check pinned posts for projects seeking contributors.\n"
                            "    🔹 *Explore OWASP Projects Page:* Identify projects that align with your skills and interests.",
                        },
                    },
                    {"type": "divider"},
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": ":loudspeaker: *Engaging on Slack*\n\n"
                            "    Many projects have dedicated project channels for collaboration.\n\n"
                            "   🔍 *Find and Join a Project Channel:*",
                        },
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "To find project channels:\n\n"
                            + "1️⃣ Use Slack's channel browser (Ctrl/Cmd + K)\n"
                            + "2️⃣ Type *#project-* to see all project channels\n"
                            + "3️⃣ Join the channels that interest you\n\n"
                            + "_All OWASP project channels start with *#project-*_",
                        },
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "    🛠 *GSOC Projects:* View this year's participating GSOC projects https://owasp.org/www-community/initiatives/gsoc/gsoc2025ideas",
                        },
                    },
                    {"type": "divider"},
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": ":busts_in_silhouette: *Identifying Key People and Activity*\n\n"
                            "    • Visit the *OWASP Projects* page to find project leaders and contributors.\n"
                            "    • Review *GitHub commit history* for active developers.\n"
                            "    • Check *Slack activity* for updates on project progress.",
                        },
                    },
                    {"type": "divider"},
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": ":pushpin: *Communication Guidelines*\n\n"
                            "    ✅ *Check pinned messages* in project channels for updates.\n"
                            "    ✅ *Ask questions* in relevant project channels.\n"
                            "    ✅ *Introduce yourself* while keeping personal details private.",
                        },
                    },
                    {"type": "divider"},
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": ":hammer_and_wrench: *How to Contribute*\n\n"
                            "     1️⃣ *Select a project* and review its contribution guidelines.\n"
                            "     2️⃣ *Work on an open GitHub issue* or propose a new one.\n"
                            "     3️⃣ *Coordinate with project leaders* to prevent overlaps.\n"
                            "     4️⃣ *Submit a pull request* and keep the team informed.\n\n"
                            "    💡 *Focus on clear communication and teamwork!* 🚀",
                        },
                    },
                ]

                # Open DM channel first
                dm_response = workspace_client.conversations_open(users=[user_id])
                if not dm_response["ok"]:
                    return HttpResponse(status=500)

                dm_channel = dm_response["channel"]["id"]

                # Send message to DM channel
                message_response = workspace_client.chat_postMessage(
                    channel=dm_channel, blocks=contribute_message, mrkdwn=True
                )

                # Send ephemeral message in the channel where command was used
                return JsonResponse(
                    {
                        "response_type": "ephemeral",
                        "text": "I've sent you a DM with information about contributing! 🚀",
                    }
                )

            except SlackApiError as e:
                activity.success = False
                activity.error_message = str(e)
                activity.save()
                return HttpResponse(status=500)

    return HttpResponse(status=405)
