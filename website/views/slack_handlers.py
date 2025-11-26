import hashlib
import hmac
import json
import logging
import math
import os
import re
import threading
import time

import requests
import yaml
from django.db.models import Count, Sum
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from slack_sdk.errors import SlackApiError
from slack_sdk.web import WebClient

from website.models import Domain, Hunt, Issue, Project, SlackBotActivity, SlackIntegration, User

logger = logging.getLogger(__name__)

if os.getenv("ENV") != "production":
    from dotenv import load_dotenv

    load_dotenv()
SLACK_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")
client = WebClient(token=SLACK_TOKEN)

# Add at the top with other environment variables
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

# Replace GSoC cache with hardcoded project data
GSOC_PROJECTS = [
    {
        "title": "BLT (Bug Logging Tool)",
        "tech": "Python, Django, Flutter, Blockchain",
        "mentor": "Donnie, Yash Pandey",
        "repo": "https://github.com/OWASP-BLT/BLT",
    },
    {
        "title": "OWASP Juice Shop",
        "tech": "TypeScript, JavaScript",
        "mentor": "Bjoern Kimminich, Shubham Palriwala, Jannik Hollenbach",
        "repo": "https://github.com/juice-shop/juice-shop",
    },
    {
        "title": "OWASP DevSecOps Maturity Model",
        "tech": "TypeScript, HTML",
        "mentor": "Timo Pagel, Aryan Prasad",
        "repo": "https://github.com/devsecopsmaturitymodel/DevSecOps-MaturityModel",
    },
    {
        "title": "OWASP OWTF",
        "tech": "Python, TypeScript, JavaScript",
        "mentor": "Viyat Bhalodia, Abraham Aranguran",
        "repo": "https://github.com/owtf/owtf",
    },
    {
        "title": "OWASP secureCodeBox",
        "tech": "JavaScript, Go, Python, Java",
        "mentor": "Jannik Hollenbach, Robert Felber",
        "repo": "https://github.com/secureCodeBox/secureCodeBox",
    },
    {
        "title": "OWASP Nettacker",
        "tech": "Python, Css, JavaScript",
        "mentor": "Sam Stepanyan, Ali Razmjoo, Arkadii Yakovets",
        "repo": "https://github.com/OWASP/Nettacker",
    },
    {
        "title": "OWASP Threat Dragon",
        "tech": "JavaScript, Vue.js",
        "mentor": "Jon Gadsden",
        "repo": "https://github.com/OWASP/threat-dragon",
    },
    {
        "title": "OWASP Website",
        "tech": "HTML, CSS, JavaScript, Github",
        "mentor": "Donnie",
        "repo": "https://github.com/orgs/OWASP",
    },
]


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
    """Handle incoming Slack events and interactions"""
    if request.method == "POST":
        if not verify_slack_signature(request):
            return HttpResponse(status=403)

        if request.content_type == "application/x-www-form-urlencoded":
            try:
                # Handle Interactive Components
                payload = json.loads(request.POST.get("payload", "{}"))
                team_id = payload.get("team", {}).get("id")
                user_id = payload.get("user", {}).get("id")

                # Get the correct token for the workspace
                try:
                    slack_integration = SlackIntegration.objects.get(workspace_name=team_id)
                    workspace_token = slack_integration.bot_access_token
                except SlackIntegration.DoesNotExist:
                    if team_id == "T04T40NHX":  # OWASP workspace
                        workspace_token = SLACK_TOKEN
                    else:
                        return JsonResponse(
                            {
                                "response_type": "ephemeral",
                                "text": "⚠️ This workspace is not properly configured. Please reinstall the app.",
                            }
                        )

                # Create workspace-specific client
                workspace_client = WebClient(token=workspace_token)

                # Verify user exists in the workspace
                try:
                    user_info = workspace_client.users_info(user=user_id)
                    if not user_info["ok"]:
                        return JsonResponse(
                            {"response_type": "ephemeral", "text": "⚠️ Unable to verify user in workspace."}
                        )
                except SlackApiError:
                    return JsonResponse({"response_type": "ephemeral", "text": "⚠️ Unable to verify user in workspace."})

                action_type = payload.get("type")
                if action_type == "block_actions":
                    action_id = payload["actions"][0]["action_id"]
                    if action_id == "select_repository":
                        return handle_repository_selection(ack=lambda: None, body=payload, client=workspace_client)
                    elif action_id == "pagination_prev":
                        return handle_pagination_prev(ack=lambda: None, body=payload, client=workspace_client)
                    elif action_id == "pagination_next":
                        return handle_pagination_next(ack=lambda: None, body=payload, client=workspace_client)
                    elif action_id == "chapters_prev" or action_id == "chapters_next":
                        return handle_chapter_pagination(action_id, payload, workspace_client)
                    elif action_id == "select_chapter":
                        chapter_name = payload["actions"][0]["selected_option"]["value"]
                        return get_chapter_details(chapter_name, get_github_headers(), workspace_client, user_id)
                    elif action_id == "events_prev" or action_id == "events_next":
                        return handle_event_pagination(action_id, payload, workspace_client)
                    elif action_id == "committees_prev" or action_id == "committees_next":
                        return handle_committee_pagination(action_id, payload, workspace_client)
                    elif action_id == "select_committee":
                        committee_name = payload["actions"][0]["selected_option"]["value"]
                        return get_committee_details(committee_name, get_github_headers(), workspace_client, user_id)

            except json.JSONDecodeError:
                return JsonResponse({"response_type": "ephemeral", "text": "⚠️ Invalid request format."}, status=400)

        elif request.content_type == "application/json":
            # Handle Events API requests
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

        # Initialize workspace client
        try:
            slack_integration = SlackIntegration.objects.get(workspace_name=team_id)
            workspace_client = WebClient(token=slack_integration.bot_access_token)
        except SlackIntegration.DoesNotExist:
            if team_id == "T04T40NHX":
                workspace_client = WebClient(token=SLACK_TOKEN)
            else:
                return JsonResponse(
                    {
                        "response_type": "ephemeral",
                        "text": "This workspace is not properly configured. Please contact the workspace admin.",
                    }
                )

        if command == "/discover":
            search_term = request.POST.get("text", "").strip()
            return get_project_overview(workspace_client, user_id, search_term, activity)

        elif command == "/stats":
            try:
                # Get project counts by status
                project_stats = Project.objects.values("status").annotate(count=Count("id"))
                stats_by_status = {stat["status"]: stat["count"] for stat in project_stats}
                total_projects = sum(stats_by_status.values())
                total_views = Project.objects.aggregate(total_views=Sum("project_visit_count"))["total_views"] or 0

                # Create interactive blocks for better visualization
                stats_blocks = [
                    {
                        "type": "header",
                        "text": {"type": "plain_text", "text": "📊 OWASP Platform Statistics", "emoji": True},
                    },
                    {"type": "divider"},
                    {"type": "section", "text": {"type": "mrkdwn", "text": "*🎯 Project Categories*"}},
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Flagship:*\n{stats_by_status.get('flagship', 0)} projects 🏆",
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Production:*\n{stats_by_status.get('production', 0)} projects ⚡",
                            },
                        ],
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Incubator:*\n{stats_by_status.get('incubator', 0)} projects 🌱",
                            },
                            {"type": "mrkdwn", "text": f"*Lab:*\n{stats_by_status.get('lab', 0)} projects 🔬"},
                        ],
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Inactive:*\n{stats_by_status.get('inactive', 0)} projects 💤",
                            },
                            {"type": "mrkdwn", "text": f"*Total Projects:*\n{total_projects} projects 📈"},
                        ],
                    },
                    {"type": "divider"},
                    {"type": "section", "text": {"type": "mrkdwn", "text": "*🔍 Project Activity*"}},
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": f"Total Project Views: *{total_views:,}* 👀"},
                    },
                    {"type": "divider"},
                    {"type": "section", "text": {"type": "mrkdwn", "text": "*📈 Platform Overview*"}},
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*Issues:*\n{Issue.objects.count():,} 🐛"},
                            {"type": "mrkdwn", "text": f"*Users:*\n{User.objects.count():,} 👥"},
                        ],
                    },
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*Domains:*\n{Domain.objects.count():,} 🌐"},
                            {"type": "mrkdwn", "text": f"*Hunts:*\n{Hunt.objects.count():,} 🎯"},
                        ],
                    },
                    {
                        "type": "context",
                        "elements": [
                            {"type": "mrkdwn", "text": "🕒 Stats generated at " + time.strftime("%Y-%m-%d %H:%M UTC")}
                        ],
                    },
                ]

                try:
                    # Open DM channel first
                    dm_response = workspace_client.conversations_open(users=[user_id])
                    if not dm_response["ok"]:
                        return JsonResponse(
                            {"response_type": "ephemeral", "text": "Sorry, I couldn't open a DM channel."}
                        )

                    dm_channel = dm_response["channel"]["id"]

                    # Send message to DM channel using the new blocks
                    workspace_client.chat_postMessage(
                        channel=dm_channel,
                        blocks=stats_blocks,
                        text="OWASP Platform Statistics",  # Fallback text
                    )

                    return JsonResponse(
                        {"response_type": "ephemeral", "text": "I've sent you the detailed statistics in a DM! 📊"}
                    )

                except SlackApiError as e:
                    activity.success = False
                    activity.error_message = f"Slack API error: {str(e)}"
                    activity.save()
                    return JsonResponse(
                        {
                            "response_type": "ephemeral",
                            "text": "Sorry, there was an error sending the statistics. Please try again later.",
                        }
                    )

            except (
                Project.DoesNotExist,
                Issue.DoesNotExist,
                User.DoesNotExist,
                Domain.DoesNotExist,
                Hunt.DoesNotExist,
            ) as e:
                activity.success = False
                activity.error_message = f"Database error: {str(e)}"
                activity.save()
                return JsonResponse(
                    {"response_type": "ephemeral", "text": "Sorry, there was an error retrieving the statistics."}
                )

        elif command == "/contrib":
            try:
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

        elif command == "/gsoc25":
            search_term = request.POST.get("text", "").strip()
            return get_gsoc_overview(workspace_client, user_id, search_term, activity, team_id)

        elif command == "/blt":
            search_term = request.POST.get("text", "").strip()
            if not search_term:
                # Provide guidance on how to use the /blt command
                guidance_message = [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": (
                                ":information_source: *How to use the /blt command:*\n\n"
                                "• `/blt user <username>` - Get the OWASP profile for a specific GitHub user.\n"
                                "• `/blt chapters` - View information about OWASP chapters.\n"
                                "• `/blt projects` - Discover OWASP projects.\n"
                                "• `/blt gsoc` - Explore Google Summer of Code projects.\n"
                                "• `/blt events` - Get details on upcoming OWASP events.\n"
                                "• `/blt committees` - View information about OWASP committees.\n\n"
                                "Use these subcommands to explore more about OWASP initiatives and resources!"
                            ),
                        },
                    }
                ]

                # Send guidance message as a DM
                send_dm(workspace_client, user_id, "How to use the /blt command", guidance_message)
                return JsonResponse(
                    {
                        "response_type": "ephemeral",
                        "text": "I've sent you guidance on using the /blt command in a DM! 📚",
                    }
                )

            # Existing logic for handling specific subcommands...
            if search_term.startswith("user "):
                username = search_term.replace("user ", "").strip()
                # Send immediate response
                response = JsonResponse(
                    {"response_type": "ephemeral", "text": "I've sent you the user profile in a DM! 👤"}
                )

                # Process the request in a separate thread
                def process_profile():
                    blocks = get_user_profile(username, workspace_client, user_id)
                    send_dm(workspace_client, user_id, f"OWASP Profile for {username}", blocks)

                thread = threading.Thread(target=process_profile)
                thread.start()

                return response
            elif search_term == "chapters" or search_term.startswith("chapters "):
                # Send immediate response
                response = JsonResponse(
                    {"response_type": "ephemeral", "text": "🌍 I'll send you the chapter information in a DM shortly!"}
                )

                # Process the request in a background thread
                def process_chapters():
                    if search_term.startswith("chapters "):
                        additional_search_term = search_term.replace("chapters ", "")
                    else:
                        additional_search_term = ""
                    get_chapter_overview(workspace_client, user_id, additional_search_term, activity)

                thread = threading.Thread(target=process_chapters)
                thread.start()

                return response
            elif search_term == "projects" or search_term.startswith("projects "):
                if search_term.startswith("projects "):
                    additional_search_term = search_term.replace("projects ", "")
                else:
                    additional_search_term = ""
                return get_project_overview(workspace_client, user_id, additional_search_term, activity)
            elif search_term == "gsoc" or search_term.startswith("gsoc "):
                if search_term.startswith("gsoc "):
                    additional_search_term = search_term.replace("gsoc ", "")
                else:
                    additional_search_term = ""
                return get_gsoc_overview(workspace_client, user_id, additional_search_term, activity, team_id)
            elif search_term == "events" or search_term.startswith("events "):
                if search_term.startswith("events "):
                    additional_search_term = search_term.replace("events ", "")
                else:
                    additional_search_term = ""
                return get_event_overview(workspace_client, user_id, additional_search_term, activity, team_id)
            elif search_term == "committees" or search_term.startswith("committees "):
                # Send immediate response
                response = JsonResponse(
                    {
                        "response_type": "ephemeral",
                        "text": "🌍 I'll send you the committee information in a DM shortly!",
                    }
                )

                # Process the request in a background thread
                def process_committees():
                    if search_term.startswith("committees "):
                        additional_search_term = search_term.replace("committees ", "")
                    else:
                        additional_search_term = ""
                    get_committees_overview(workspace_client, user_id, additional_search_term, activity)

                thread = threading.Thread(target=process_committees)
                thread.start()

                return response

        elif command == "/ghissue":
            text = request.POST.get("text", "").strip()

            # Parse the command format: /ghissue <owner/repo> <issue title and description>
            if not text:
                guidance_message = [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": (
                                ":information_source: *How to use the /ghissue command:*\n\n"
                                "*Format:* `/ghissue <owner/repo> <issue title>`\n\n"
                                "*Example:*\n"
                                "`/ghissue OWASP-BLT/BLT Fix login bug on mobile devices`\n\n"
                                "*Note:*\n"
                                "• Separate the repository and title with a space\n"
                                "• The repository should be in the format `owner/repo`\n"
                                "• You can add a description by providing more details after the title"
                            ),
                        },
                    }
                ]
                send_dm(workspace_client, user_id, "How to use /ghissue", guidance_message)
                return JsonResponse(
                    {
                        "response_type": "ephemeral",
                        "text": "I've sent you guidance on using the /ghissue command in a DM! 📚",
                    }
                )

            # Parse the text to extract repository and issue details
            parts = text.split(maxsplit=1)
            if len(parts) < 2:
                return JsonResponse(
                    {
                        "response_type": "ephemeral",
                        "text": "❌ Invalid format. Usage: `/ghissue <owner/repo> <issue title and description>`",
                    }
                )

            repository = parts[0]
            issue_text = parts[1]

            # Validate repository format
            if "/" not in repository or repository.count("/") != 1:
                return JsonResponse(
                    {
                        "response_type": "ephemeral",
                        "text": "❌ Invalid repository format. Use `owner/repo` format (e.g., `OWASP-BLT/BLT`)",
                    }
                )

            try:
                # Use GitHub token for authentication
                if not GITHUB_TOKEN:
                    return JsonResponse(
                        {
                            "response_type": "ephemeral",
                            "text": "❌ GitHub API token not configured. Please contact the administrator.",
                        }
                    )

                # Create GitHub issue
                headers = get_github_headers()
                url = f"https://api.github.com/repos/{repository}/issues"

                # Parse title and body (first line is title, rest is body)
                lines = issue_text.split("\n", 1)
                title = lines[0].strip()
                body = lines[1].strip() if len(lines) > 1 else ""

                # Add metadata about who created the issue
                if body:
                    body += f"\n\n---\n_Created via Slack by <@{user_id}>_"
                else:
                    body = f"_Created via Slack by <@{user_id}>_"

                issue_data = {
                    "title": title,
                    "body": body,
                }

                response = requests.post(url, json=issue_data, headers=headers, timeout=10)

                if response.status_code == 201:
                    issue = response.json()
                    blocks = [
                        {
                            "type": "header",
                            "text": {"type": "plain_text", "text": "✅ GitHub Issue Created!", "emoji": True},
                        },
                        {"type": "divider"},
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": (
                                    f"*Repository:* {repository}\n"
                                    f"*Issue:* <{issue['html_url']}|#{issue['number']} - {issue['title']}>\n"
                                    f"*Status:* {issue['state']}\n"
                                    f"*Created at:* {issue['created_at'][:10]}"
                                ),
                            },
                        },
                        {
                            "type": "actions",
                            "elements": [
                                {
                                    "type": "button",
                                    "text": {"type": "plain_text", "text": "View Issue", "emoji": True},
                                    "url": issue["html_url"],
                                    "action_id": "view_github_issue",
                                }
                            ],
                        },
                    ]
                    send_dm(workspace_client, user_id, "GitHub Issue Created", blocks)
                    activity.success = True
                    activity.save()
                    return JsonResponse(
                        {
                            "response_type": "ephemeral",
                            "text": f"✅ Issue created successfully! #{issue['number']} - I've sent you the details in a DM.",
                        }
                    )
                elif response.status_code == 404:
                    activity.success = False
                    activity.error_message = "Repository not found"
                    activity.save()
                    return JsonResponse(
                        {
                            "response_type": "ephemeral",
                            "text": f"❌ Repository `{repository}` not found. Please check the repository name.",
                        }
                    )
                elif response.status_code == 403:
                    activity.success = False
                    activity.error_message = "GitHub API rate limit or permission denied"
                    activity.save()
                    return JsonResponse(
                        {
                            "response_type": "ephemeral",
                            "text": "❌ Permission denied or rate limit exceeded. Please try again later.",
                        }
                    )
                else:
                    activity.success = False
                    activity.error_message = f"GitHub API error: {response.status_code}"
                    activity.save()
                    return JsonResponse(
                        {
                            "response_type": "ephemeral",
                            "text": f"❌ Failed to create issue. GitHub API error: {response.status_code}",
                        }
                    )

            except requests.RequestException as e:
                activity.success = False
                activity.error_message = f"Network error: {str(e)}"
                activity.save()
                return JsonResponse(
                    {
                        "response_type": "ephemeral",
                        "text": "❌ Network error occurred while creating the issue. Please try again.",
                    }
                )
            except Exception as e:
                activity.success = False
                activity.error_message = f"Error: {str(e)}"
                activity.save()
                logger.error(f"Error in /ghissue command: {str(e)}")
                return JsonResponse(
                    {
                        "response_type": "ephemeral",
                        "text": "❌ An unexpected error occurred. Please try again later.",
                    }
                )

        elif command == "/help":
            try:
                help_message = [
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": "*Available Commands*\nHere’s what I can do for you:"},
                    },
                    {"type": "divider"},
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*Basic Commands*\n`/help` - Show this message\n`/report <description>` - Report a bug\n`/gsoc` - Get GSoC info\n`/stats` - View platform stats\n`/installed_apps` - List installed apps",
                            },
                            {
                                "type": "mrkdwn",
                                "text": "*Project Commands*\n`/discover` - Find projects\n`/contrib` - Learn to contribute\n`/gsoc25` - GSoC 2025 details\n`/blt` - Multi-purpose tool\n`/ghissue` - Create GitHub issue",
                            },
                        ],
                    },
                    {"type": "context", "elements": [{"type": "mrkdwn", "text": "Try any command to get started!"}]},
                ]
                dm_response = workspace_client.conversations_open(users=[user_id])
                if not dm_response["ok"]:
                    return JsonResponse({"response_type": "ephemeral", "text": "Couldn’t open a DM channel."})
                dm_channel = dm_response["channel"]["id"]
                workspace_client.chat_postMessage(channel=dm_channel, blocks=help_message, text="Available Commands")
                return JsonResponse({"response_type": "ephemeral", "text": "I’ve sent you the command list in a DM!"})
            except SlackApiError as e:
                activity.success = False
                activity.error_message = f"Slack API error: {str(e)}"
                activity.save()
                return JsonResponse({"response_type": "ephemeral", "text": "Error sending help message."})

        elif command == "/installed_apps":
            try:
                # Get basic workspace info
                team_info = workspace_client.team_info()
                team_name = team_info.get("team", {}).get("name", "Unknown Workspace")

                # Create the message blocks
                apps_blocks = [
                    {
                        "type": "header",
                        "text": {"type": "plain_text", "text": f"📱 Apps in {team_name}", "emoji": True},
                    },
                    {"type": "divider"},
                ]

                # Try to get app list using admin API (requires elevated permissions)
                try:
                    apps_response = workspace_client.api_call("admin.apps.approved.list", params={"limit": 100})

                    if apps_response.get("ok"):
                        # If approved_apps is present (even if empty), show the installed apps
                        if "approved_apps" in apps_response:
                            apps = apps_response["approved_apps"]

                            apps_blocks.append(
                                {
                                    "type": "section",
                                    "text": {"type": "mrkdwn", "text": f"*Total Apps Installed:* {len(apps)}"},
                                }
                            )

                            if len(apps) == 0:
                                apps_blocks.append(
                                    {
                                        "type": "section",
                                        "text": {
                                            "type": "mrkdwn",
                                            "text": "No apps are currently installed on this workspace.",
                                        },
                                    }
                                )
                            else:
                                # List each app (limit to first 20 to avoid message size limits)
                                for app in apps[:20]:
                                    app_info = app.get("app", {})
                                    app_name = app_info.get("name", "Unknown App")
                                    app_id = app_info.get("id", "N/A")

                                    apps_blocks.append(
                                        {
                                            "type": "section",
                                            "text": {"type": "mrkdwn", "text": f"• *{app_name}* (`{app_id}`)"},
                                        }
                                    )

                                if len(apps) > 20:
                                    apps_blocks.append(
                                        {
                                            "type": "context",
                                            "elements": [
                                                {"type": "mrkdwn", "text": f"_Showing 20 of {len(apps)} apps_"}
                                            ],
                                        }
                                    )
                        else:
                            # Fallback: Show guidance when admin permissions aren't available
                            apps_blocks.extend(
                                [
                                    {
                                        "type": "section",
                                        "text": {
                                            "type": "mrkdwn",
                                            "text": "⚠️ *Limited Access*\n\n"
                                            "This bot doesn't have admin permissions to list all workspace apps.",
                                        },
                                    },
                                    {"type": "divider"},
                                    {
                                        "type": "section",
                                        "text": {
                                            "type": "mrkdwn",
                                            "text": "*Alternative ways to view installed apps:*\n\n"
                                            "1️⃣ Click on your workspace name (top left)\n"
                                            "2️⃣ Select *Settings & administration*\n"
                                            "3️⃣ Choose *Manage apps*\n"
                                            "4️⃣ You'll see all installed and available apps\n\n"
                                            "Or visit: https://slack.com/apps/manage",
                                        },
                                    },
                                ]
                            )

                except SlackApiError:
                    # If admin API not available, provide helpful information
                    apps_blocks.extend(
                        [
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": "⚠️ *Unable to retrieve app list*\n\n"
                                    "The bot needs additional permissions to list installed apps.",
                                },
                            },
                            {"type": "divider"},
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": "*How to view apps manually:*\n\n"
                                    "• Visit your Slack workspace settings\n"
                                    "• Go to *Apps* in the left sidebar\n"
                                    "• Or visit: https://slack.com/apps/manage",
                                },
                            },
                        ]
                    )

                # Send the response as a DM
                dm_response = workspace_client.conversations_open(users=[user_id])
                if dm_response["ok"]:
                    dm_channel = dm_response["channel"]["id"]
                    workspace_client.chat_postMessage(
                        channel=dm_channel, blocks=apps_blocks, text=f"Apps installed in {team_name}"
                    )

                    activity.success = True
                    activity.save()

                    return JsonResponse(
                        {
                            "response_type": "ephemeral",
                            "text": "I've sent you information about installed apps in a DM! 📱",
                        }
                    )
                else:
                    activity.success = False
                    activity.error_message = "Could not open DM channel"
                    activity.save()
                    return JsonResponse({"response_type": "ephemeral", "text": "Sorry, I couldn't open a DM channel."})

            except (SlackApiError, KeyError, ValueError) as e:
                activity.success = False
                activity.error_message = str(e)
                activity.save()
                return JsonResponse(
                    {
                        "response_type": "ephemeral",
                        "text": "Sorry, there was an error retrieving the apps list. Please try again later.",
                    }
                )

        elif command == "/report":
            text = request.POST.get("text", "").strip()
            if not text:
                return JsonResponse(
                    {
                        "response_type": "ephemeral",
                        "text": "Please provide a description. Usage: `/report <description>`",
                    }
                )
            try:
                # Log the issue (assuming Issue model exists)
                issue = Issue.objects.create(
                    description=text,
                    user_id=user_id,  # Adjust based on your auth setup
                    status="open",
                    workspace_id=team_id,
                )
                activity.details["issue_id"] = issue.id
                activity.success = True
                activity.save()
                return JsonResponse(
                    {
                        "response_type": "in_channel",
                        "text": f"Bug reported successfully! Issue #{issue.id}\nDescription: {text}",
                    }
                )
            except Exception as e:
                activity.success = False
                activity.error_message = f"Error creating issue: {str(e)}"
                activity.save()
                return JsonResponse({"response_type": "ephemeral", "text": "Error reporting bug. Please try again."})

    return HttpResponse(status=405)


def get_github_headers():
    """Helper function to get GitHub API headers with authentication"""
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    return headers


def get_all_owasp_repos():
    """Fetch ALL repos from the OWASP org by paginating through the results."""
    current_time = time.time()

    # Return cached data if available and not expired
    if repo_cache["data"] and (current_time - repo_cache["timestamp"]) < CACHE_DURATION:
        return repo_cache["data"]

    all_repos = []
    page = 1

    headers = get_github_headers()
    if not GITHUB_TOKEN:
        return []  # Return empty if no token available

    while True:
        try:
            resp = requests.get(
                f"https://api.github.com/orgs/OWASP/repos?page={page}&per_page=100", headers=headers, timeout=10
            )

            if resp.status_code == 403:
                if "rate limit exceeded" in resp.text.lower():
                    return []  # Handle rate limiting
                return []  # Handle other 403 errors

            if resp.status_code != 200:
                return []

            page_data = resp.json()
            if not page_data:
                break

            all_repos.extend(page_data)
            page += 1

        except (requests.RequestException, json.JSONDecodeError) as e:
            return []

    repo_cache["data"] = all_repos
    repo_cache["timestamp"] = current_time
    return all_repos


# Add other necessary helper functions and variables
pagination_data = {}
repo_cache = {"timestamp": 0, "data": []}
CACHE_DURATION = 3600


def send_dm(client, user_id, text, blocks=None):
    """Utility function to open a DM channel with user and send them a message."""
    try:
        dm_response = client.conversations_open(users=[user_id])
        if not dm_response["ok"]:
            return JsonResponse(
                {
                    "response_type": "ephemeral",
                    "text": f"❌ Failed to open DM channel: {dm_response.get('error', 'Unknown error')}",
                },
                status=503,
            )

        dm_channel_id = dm_response["channel"]["id"]
        message_response = client.chat_postMessage(
            channel=dm_channel_id,
            text=text,
            blocks=blocks,
            mrkdwn=True,
            unfurl_links=False,
            unfurl_media=False,
        )
        if not message_response["ok"]:
            return JsonResponse(
                {
                    "response_type": "ephemeral",
                    "text": f"❌ Failed to send message: {message_response.get('error', 'Unknown error')}",
                },
                status=500,
            )

    except SlackApiError as e:
        if e.response["error"] == "ratelimited":
            return JsonResponse(
                {"response_type": "ephemeral", "text": "❌ Rate limit exceeded. Please try again later."}, status=429
            )
        return JsonResponse(
            {"response_type": "ephemeral", "text": f"❌ Slack API error: {e.response.get('error', 'Unknown error')}"},
            status=503,
        )
    except (KeyError, AttributeError) as e:
        return JsonResponse(
            {"response_type": "ephemeral", "text": "❌ Invalid response format from Slack API."}, status=500
        )


def send_paged_results(client, user_id, search_term):
    """Sends the current page of matched projects to the user with next/prev buttons if needed."""
    data = pagination_data[user_id]
    matched = data["matched"]
    page_size = data["page_size"]
    total_pages = math.ceil(len(matched) / page_size)
    current_page = data["current_page"]

    start_idx = current_page * page_size
    end_idx = start_idx + page_size
    chunk = matched[start_idx:end_idx]

    # Create header block
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"🔍 OWASP Projects matching '{search_term}'", "emoji": True},
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"Found {len(matched)} projects • Page {current_page + 1} of {total_pages}"}
            ],
        },
        {"type": "divider"},
    ]

    # Add project block
    for idx, project in enumerate(chunk, start=start_idx + 1):
        blocks.extend(
            [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"*{idx}. <{project['html_url']}|{project['name']}>*\n"
                            f"{project['description']}\n"
                            f"{project.get('extra_info', '')}\n"
                            f"{project['link_label']}: <{project['link']}|Link>"
                        ),
                    },
                },
                {"type": "divider"} if idx < end_idx else None,
            ]
        )

    # Remove None blocks
    blocks = [b for b in blocks if b is not None]

    # Add navigation buttons
    navigation = {"type": "actions", "elements": []}

    if current_page > 0:
        navigation["elements"].append(
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "◀️ Previous", "emoji": True},
                "value": "PREV",
                "action_id": "pagination_prev",
            }
        )

    if current_page < (total_pages - 1):
        navigation["elements"].append(
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Next ▶️", "emoji": True},
                "value": "NEXT",
                "action_id": "pagination_next",
            }
        )

    # Add repository selector
    if chunk:
        navigation["elements"].append(
            {
                "type": "static_select",
                "placeholder": {"type": "plain_text", "text": "View Repository Issues", "emoji": True},
                "options": [
                    {
                        "text": {"type": "plain_text", "text": project["name"], "emoji": True},
                        "value": project["owner_repo"],
                    }
                    for project in chunk
                ],
                "action_id": "select_repository",
            }
        )

    blocks.append(navigation)

    send_dm(client, user_id, f"Found {len(matched)} matching OWASP projects.", blocks)


# Add the action handlers
def handle_repository_selection(ack, body, client):
    """Handles repository selection from dropdown"""
    try:
        user_id = body["user"]["id"]
        selected_repo = body["actions"][0]["selected_option"]["value"]

        headers = get_github_headers()
        if not GITHUB_TOKEN:
            send_dm(client, user_id, "⚠️ GitHub API token not configured. Please contact the administrator.")
            return HttpResponse()

        # Fetch latest issues from the selected GitHub repository
        issues_response = requests.get(
            f"https://api.github.com/repos/{selected_repo}/issues", headers=headers, timeout=10
        )

        if issues_response.status_code == 403:
            if "rate limit exceeded" in issues_response.text.lower():
                send_dm(client, user_id, "⚠️ GitHub API rate limit exceeded. Please try again later.")
            else:
                send_dm(client, user_id, "⚠️ Access to GitHub API denied. Please check the token configuration.")
            return HttpResponse()

        if issues_response.status_code == 200:
            issues = issues_response.json()
            issues = [issue for issue in issues if "pull_request" not in issue]
            if not issues:
                send_dm(client, user_id, "No open issues found for this repository.")
            else:
                blocks = [
                    {
                        "type": "header",
                        "text": {"type": "plain_text", "text": f"Latest Issues for {selected_repo}", "emoji": True},
                    },
                    {"type": "divider"},
                ]

                for issue in issues[:5]:
                    blocks.append(
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": (
                                    f"*<{issue['html_url']}|{issue['title']}>* (#{issue['number']})\n"
                                    f"👤 Opened by: {issue.get('user', {}).get('login', 'Unknown')}\n"
                                    f"📅 Created: {issue['created_at'][:10]}"
                                ),
                            },
                        }
                    )

                if len(issues) > 5:
                    blocks.append(
                        {
                            "type": "context",
                            "elements": [{"type": "mrkdwn", "text": f"_Showing 5 of {len(issues)} issues_"}],
                        }
                    )

                send_dm(client, user_id, f"Found {len(issues)} open issues:", blocks)
        else:
            send_dm(client, user_id, "Failed to fetch issues. Please try again later.")

        return HttpResponse()

    except (KeyError, IndexError) as e:
        return JsonResponse({"response_type": "ephemeral", "text": "❌ Invalid request format."}, status=400)
    except requests.RequestException as e:
        return JsonResponse(
            {"response_type": "ephemeral", "text": "❌ Failed to fetch issues: Network error occurred."}, status=503
        )


def handle_pagination_prev(ack, body, client):
    """Handles the 'Previous' pagination button."""
    try:
        user_id = body["user"]["id"]
        search_term = body.get("state", {}).get("values", {}).get("search_term", "Topic")

        if user_id not in pagination_data:
            send_dm(client, user_id, "No pagination data found.")
            return HttpResponse()

        data = pagination_data[user_id]
        data["current_page"] = max(0, data["current_page"] - 1)
        send_paged_results(client, user_id, search_term)
        return HttpResponse()

    except KeyError as e:
        return JsonResponse({"response_type": "ephemeral", "text": "❌ Invalid request format."}, status=400)
    except SlackApiError as e:
        return JsonResponse({"response_type": "ephemeral", "text": "❌ Failed to send message to Slack."}, status=503)


def handle_pagination_next(ack, body, client):
    """Handles the 'Next' pagination button"""
    try:
        user_id = body["user"]["id"]
        search_term = body.get("state", {}).get("values", {}).get("search_term", "Topic")

        if user_id not in pagination_data:
            send_dm(client, user_id, "No pagination data found.")
            return HttpResponse()

        data = pagination_data[user_id]
        data["current_page"] += 1
        total_pages = math.ceil(len(data["matched"]) / data["page_size"])
        data["current_page"] = min(data["current_page"], total_pages - 1)
        send_paged_results(client, user_id, search_term)
        return HttpResponse()

    except KeyError as e:
        return JsonResponse({"response_type": "ephemeral", "text": "❌ Invalid request format."}, status=400)
    except SlackApiError as e:
        return JsonResponse({"response_type": "ephemeral", "text": "❌ Failed to send message to Slack."}, status=503)


def filter_gsoc_projects(search_term):
    """Filter GSoC projects based on search term"""
    search_term = search_term.lower()
    if search_term.startswith("mentor:"):
        mentor_name = search_term[7:].strip()
        return [p for p in GSOC_PROJECTS if mentor_name in p["mentor"].lower()]

    return [p for p in GSOC_PROJECTS if search_term in p["title"].lower() or search_term in p["tech"].lower()]


def get_project_overview(workspace_client, user_id, search_term, activity):
    try:
        # First, send an immediate response to avoid timeout
        initial_response = {
            "response_type": "ephemeral",
            "text": "🔍 Searching OWASP projects... I'll send you the results in a DM shortly!",
        }

        if search_term:
            # Return immediate response to Slack
            response = JsonResponse(initial_response)

            # Then process the search asynchronously
            def process_search():
                try:
                    repos = get_all_owasp_repos()
                    if not repos:
                        send_dm(workspace_client, user_id, "❌ Failed to fetch OWASP repositories.")
                        return

                    matched = []
                    url_pattern = re.compile(r"https?://\S+")

                    # Improve the display of search results with emojis and formatting
                    for idx, repo in enumerate(repos, start=1):
                        name_desc = (repo["name"] + " " + (repo["description"] or "")).lower()
                        lang = (repo["language"] or "").lower()
                        topics = [t.lower() for t in repo.get("topics", [])]

                        if (
                            search_term.lower() in name_desc
                            or search_term.lower() in lang
                            or search_term.lower() in topics
                        ):
                            desc = repo["description"] or "No description provided."
                            found_urls = url_pattern.findall(desc)
                            if found_urls:
                                link = found_urls[0]
                                link_label = "🌐 Website"
                            else:
                                link = f"https://owasp.org/www-project-{repo['name'].lower()}"
                                link_label = "📚 Wiki"

                            # Add language and topics info
                            extra_info = []
                            if repo["language"]:
                                extra_info.append(f"💻 {repo['language']}")
                            if repo.get("topics"):
                                topics_str = ", ".join(f"#{topic}" for topic in repo["topics"][:3])
                                if len(repo["topics"]) > 3:
                                    topics_str += f" +{len(repo['topics']) - 3} more"
                                extra_info.append(f"🏷️ {topics_str}")

                            matched.append(
                                {
                                    "owner_repo": repo["full_name"],
                                    "name": repo["name"],
                                    "description": desc,
                                    "link_label": link_label,
                                    "link": link,
                                    "html_url": repo["html_url"],
                                    "extra_info": " | ".join(extra_info) if extra_info else None,
                                }
                            )

                    if not matched:
                        send_dm(
                            workspace_client,
                            user_id,
                            f"❌ No OWASP projects found matching '*{search_term}*'.\nTry searching with different keywords!",
                        )
                        return

                    pagination_data[user_id] = {
                        "matched": matched,
                        "current_page": 0,
                        "page_size": 10,
                    }

                    send_paged_results(workspace_client, user_id, search_term)

                except requests.RequestException as e:
                    send_dm(workspace_client, user_id, "❌ Failed to fetch repositories: Network error occurred.")
                except json.JSONDecodeError as e:
                    send_dm(workspace_client, user_id, "❌ Failed to parse repository data.")
                except (KeyError, AttributeError) as e:
                    send_dm(workspace_client, user_id, "❌ Invalid repository data format received.")

            # Start processing in a separate thread
            thread = threading.Thread(target=process_search)
            thread.start()

            return response

        else:
            # Handle showing OWASP-BLT repositories
            try:
                headers = {"Accept": "application/vnd.github.v3+json"}
                if GITHUB_TOKEN:
                    headers["Authorization"] = f"token {GITHUB_TOKEN}"
                else:
                    # If no token, return a message about rate limiting
                    return JsonResponse(
                        {
                            "response_type": "ephemeral",
                            "text": "⚠️ GitHub API token not configured. Please contact the administrator.",
                        }
                    )

                gh_response = requests.get(
                    "https://api.github.com/orgs/OWASP-BLT/repos",
                    headers=headers,
                    timeout=10,  # Add timeout
                )

                if gh_response.status_code == 403:
                    if "rate limit exceeded" in gh_response.text.lower():
                        return JsonResponse(
                            {
                                "response_type": "ephemeral",
                                "text": "⚠️ GitHub API rate limit exceeded. Please try again later.",
                            }
                        )
                    return JsonResponse(
                        {
                            "response_type": "ephemeral",
                            "text": "⚠️ Access to GitHub API denied. Please check the token configuration.",
                        }
                    )
                if gh_response.status_code == 200:
                    repos = gh_response.json()
                    if not repos:
                        send_dm(workspace_client, user_id, "No repositories found for OWASP-BLT.")
                    else:
                        # Create header block
                        blocks = [
                            {
                                "type": "header",
                                "text": {"type": "plain_text", "text": "🔍 OWASP BLT Projects", "emoji": True},
                            },
                            {
                                "type": "context",
                                "elements": [{"type": "mrkdwn", "text": f"Found {len(repos)} repositories"}],
                            },
                            {"type": "divider"},
                        ]

                        # Add repository blocks
                        for idx, repo in enumerate(repos, start=1):
                            desc = repo["description"] if repo["description"] else "No description provided."

                            # Add language and topics info
                            extra_info = []
                            if repo.get("language"):
                                extra_info.append(f"💻 {repo['language']}")
                            if repo.get("topics"):
                                topics_str = ", ".join(f"#{topic}" for topic in repo["topics"][:3])
                                if len(repo["topics"]) > 3:
                                    topics_str += f" +{len(repo['topics']) - 3} more"
                                extra_info.append(f"🏷️ {topics_str}")

                            blocks.extend(
                                [
                                    {
                                        "type": "section",
                                        "text": {
                                            "type": "mrkdwn",
                                            "text": (
                                                f"*{idx}. <{repo['html_url']}|{repo['name']}>*\n"
                                                f"{desc}\n"
                                                f"{' | '.join(extra_info) if extra_info else ''}"
                                            ),
                                        },
                                    },
                                    {"type": "divider"} if idx < len(repos) else None,
                                ]
                            )

                        # Remove None blocks
                        blocks = [b for b in blocks if b is not None]

                        # Add repository selector
                        blocks.append(
                            {
                                "type": "actions",
                                "elements": [
                                    {
                                        "type": "static_select",
                                        "placeholder": {
                                            "type": "plain_text",
                                            "text": "View Repository Issues",
                                            "emoji": True,
                                        },
                                        "options": [
                                            {
                                                "text": {
                                                    "type": "plain_text",
                                                    "text": repo["name"],
                                                    "emoji": True,
                                                },
                                                "value": f"OWASP-BLT/{repo['name']}",
                                            }
                                            for repo in repos
                                        ],
                                        "action_id": "select_repository",
                                    }
                                ],
                            }
                        )

                        send_dm(workspace_client, user_id, "Here are the OWASP BLT repositories:", blocks)
                        return JsonResponse(
                            {
                                "response_type": "ephemeral",
                                "text": "I've sent you the repository list in a DM! 📚",
                            }
                        )
                else:
                    return JsonResponse(
                        {
                            "response_type": "ephemeral",
                            "text": "❌ Failed to fetch repositories from OWASP-BLT.",
                        }
                    )

            except Exception as e:
                activity.success = False
                activity.error_message = str(e)
                activity.save()
                return JsonResponse(
                    {
                        "response_type": "ephemeral",
                        "text": "❌ An error occurred while processing your request.",
                    }
                )

    except Exception as e:
        activity.success = False
        activity.error_message = str(e)
        activity.save()
        return JsonResponse({"response_type": "ephemeral", "text": "An error occurred while processing your request."})


def get_gsoc_overview(workspace_client, user_id, search_term, activity, team_id):
    try:
        # Prepare base blocks
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "🎓 Google Summer of Code 2025 - OWASP", "emoji": True},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*Welcome to OWASP's GSoC 2025 Program!* 🚀"},
            },
        ]

        # Add workspace-specific content
        if team_id == "T04T40NHX":  # OWASP workspace
            blocks.extend(
                [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": (
                                "*Important Links:*\n"
                                "• Join <#CFJLZNFN1|gsoc> for program discussions 💬\n"
                                "• Check <#C04DH8HEPTR|contribute> for contribution guidelines 📝\n"
                                "• View project ideas: <https://owasp.org/www-community/initiatives/gsoc/gsoc2025ideas|GSoC 2025 Ideas> 💡"
                            ),
                        },
                    }
                ]
            )
        else:
            blocks.extend(
                [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": (
                                "*Get Started:*\n"
                                "1. Join OWASP Slack: <https://join.slack.com/t/owasp/shared_invite/zt-2y4cvxl3l-_S~G_iKEShwmbQACu~QRyQ|Click to Join> 🔗\n"
                                "2. Once joined, check #gsoc and #contribute channels 📢\n"
                                "3. View project ideas: <https://owasp.org/www-community/initiatives/gsoc/gsoc2025ideas|GSoC 2025 Ideas> 💡"
                            ),
                        },
                    }
                ]
            )

        # Add search tip
        blocks.extend(
            [
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            "*🔍 Search Tips:*\n"
                            "• Search by technology: `/gsoc25 python or /blt gsoc python`\n"
                            "• Search by mentor: `/gsoc25 mentor:donnie or /blt gsoc mentor:donnie`\n"
                            "• Search by project: `/gsoc25 security or /blt gsoc security`"
                        ),
                    },
                },
            ]
        )

        # Show search results or default projects
        if search_term:
            matched_projects = filter_gsoc_projects(search_term)
            if matched_projects:
                blocks.extend(
                    [
                        {"type": "divider"},
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*🎯 Found {len(matched_projects)} matching projects:*",
                            },
                        },
                    ]
                )

                for project in matched_projects[:5]:
                    blocks.append(
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": (
                                    f"*{project['title']}* 📚\n"
                                    f"🔧 *Tech Stack:* {project['tech']}\n"
                                    f"👥 *Mentors:* {project['mentor']}\n"
                                    f"🔗 *Repository:* <{project['repo']}|View Project>"
                                ),
                            },
                        }
                    )

                if len(matched_projects) > 5:
                    blocks.append(
                        {
                            "type": "context",
                            "elements": [{"type": "mrkdwn", "text": f"_Showing 5 of {len(matched_projects)} matches_"}],
                        }
                    )
            else:
                blocks.append(
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "❌ No matching projects found. Try different search terms or check the full project list.",
                        },
                    }
                )
        else:
            # Show first 3 projects by default
            blocks.extend(
                [
                    {"type": "divider"},
                    {"type": "section", "text": {"type": "mrkdwn", "text": "*🌟 Featured Projects:*"}},
                ]
            )

            for project in GSOC_PROJECTS[:3]:
                blocks.append(
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": (
                                f"*{project['title']}* 📚\n"
                                f"🔧 *Tech Stack:* {project['tech']}\n"
                                f"👥 *Mentors:* {project['mentor']}\n"
                                f"🔗 *Repository:* <{project['repo']}|View Project>"
                            ),
                        },
                    }
                )

            blocks.extend(
                [
                    {"type": "divider"},
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "_💡 *Tip:* Use `/gsoc25 <technology> or /blt gsoc <technology>` to find projects matching your skills! For example: `/gsoc25 python or /blt gsoc python` or `/gsoc25 javascript or /blt gsoc javascript`_",
                        },
                    },
                ]
            )

        # Send response
        send_dm(workspace_client, user_id, "GSoC 2025 Information", blocks)
        return JsonResponse({"response_type": "ephemeral", "text": "I've sent you GSoC information in a DM! 📚"})

    except (SlackApiError, KeyError, ValueError) as e:
        activity.success = False
        activity.error_message = str(e)
        activity.save()
        return JsonResponse(
            {"response_type": "ephemeral", "text": "❌ Error: Check the logs for more details."}, status=400
        )


def get_user_profile(username, workspace_client, user_id):
    """
    Get comprehensive OWASP profile for a GitHub user.
    Returns formatted blocks for Slack message.
    """
    try:
        headers = get_github_headers()
        if not GITHUB_TOKEN:
            return [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "⚠️ GitHub API token not configured. Please contact the administrator.",
                    },
                }
            ]

        # Fetch basic GitHub profile
        gh_response = requests.get(f"https://api.github.com/users/{username}", headers=headers, timeout=10)

        if gh_response.status_code == 404:
            return [{"type": "section", "text": {"type": "mrkdwn", "text": f"❌ GitHub user '{username}' not found."}}]
        elif gh_response.status_code != 200:
            return [{"type": "section", "text": {"type": "mrkdwn", "text": "❌ Failed to fetch GitHub profile."}}]

        profile = gh_response.json()

        # Initialize blocks with header
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🔍 OWASP Profile: {profile.get('name', username)}",
                    "emoji": True,
                },
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*GitHub Profile:* <{profile['html_url']}|@{username}>\n"
                        f"*Location:* {profile.get('location', 'Not specified')}\n"
                        f"*Bio:* {profile.get('bio', 'No bio provided')}"
                    ),
                },
                "accessory": (
                    {
                        "type": "image",
                        "image_url": profile["avatar_url"],
                        "alt_text": f"GitHub avatar for {username}",
                    }
                    if profile.get("avatar_url")
                    else None
                ),
            },
        ]

        # Fetch OWASP contributions
        contributions = get_owasp_contributions(username, headers)
        if contributions:
            blocks.extend(
                [
                    {"type": "divider"},
                    {"type": "section", "text": {"type": "mrkdwn", "text": "*🛠 OWASP Contributions*"}},
                    {"type": "section", "text": {"type": "mrkdwn", "text": contributions}},
                ]
            )

        # Check GSoC mentorship
        gsoc_info = get_gsoc_involvement(username)
        if gsoc_info:
            blocks.extend(
                [
                    {"type": "divider"},
                    {"type": "section", "text": {"type": "mrkdwn", "text": "*🎓 GSoC Involvement*"}},
                    {"type": "section", "text": {"type": "mrkdwn", "text": gsoc_info}},
                ]
            )

        # Add quick actions
        blocks.extend(
            [
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "View GitHub Profile", "emoji": True},
                            "url": profile["html_url"],
                            "action_id": "view_github",
                        },
                    ],
                }
            ]
        )

        return blocks

    except Exception as e:
        logger.error(f"Error in get_user_profile: {str(e)}")
        return [
            {"type": "section", "text": {"type": "mrkdwn", "text": "❌ An error occurred while fetching user profile."}}
        ]


def get_owasp_contributions(username, headers):
    """Get user's contributions to OWASP projects across both OWASP and OWASP-BLT organizations"""
    try:
        # Search for PRs in both OWASP and OWASP-BLT repositories
        owasp_prs = get_org_prs(username, "OWASP", headers)
        blt_prs = get_org_prs(username, "OWASP-BLT", headers)

        total_prs = (owasp_prs.get("total_count", 0) if owasp_prs else 0) + (
            blt_prs.get("total_count", 0) if blt_prs else 0
        )

        contribution_text = []

        if total_prs > 0:
            contribution_text.append(f"• Pull Requests: {total_prs} contributions to OWASP projects")

        return "\n".join(contribution_text) if contribution_text else None

    except Exception as e:
        logger.error(f"Error getting contributions: {str(e)}")
        return None


def get_org_prs(username, org, headers):
    """Helper function to get PRs for a specific organization"""
    try:
        search_url = f"https://api.github.com/search/issues?q=author:{username}+org:{org}+type:pr"
        pr_response = requests.get(search_url, headers=headers, timeout=10)

        if pr_response.status_code == 200:
            return pr_response.json()
        return None

    except Exception as e:
        logger.error(f"Error getting PRs for {org}: {str(e)}")
        return None


def get_gsoc_involvement(username):
    """Check if user is a GSoC mentor"""
    try:
        # Check against GSOC_PROJECTS for mentorship
        mentor_projects = [project for project in GSOC_PROJECTS if username.lower() in project["mentor"].lower()]

        if mentor_projects:
            projects_text = "\n".join(f"• Mentor for *{project['title']}*" for project in mentor_projects)
            return f"🎯 GSoC Mentor:\n{projects_text}"

        return None

    except Exception as e:
        logger.error(f"Error checking GSoC involvement: {str(e)}")
        return None


def get_chapter_overview(workspace_client, user_id, search_term, activity):
    """Handle chapter repository overview and search"""
    try:
        headers = get_github_headers()
        if not GITHUB_TOKEN:
            send_dm(
                workspace_client,
                user_id,
                "Error",
                [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "⚠️ GitHub API token not configured. Please contact the administrator.",
                        },
                    }
                ],
            )
            return

        # If searching for a specific chapter
        if search_term:
            # Format chapter name to match repository naming convention
            chapter_name = f"www-chapter-{search_term.lower().replace(' ', '-')}"
            get_chapter_details(chapter_name, headers, workspace_client, user_id)
            return

        # Get all chapter repositories
        search_url = "https://api.github.com/search/repositories"
        params = {"q": "org:OWASP www-chapter in:name", "sort": "updated", "order": "desc", "per_page": 100}

        response = requests.get(search_url, headers=headers, params=params, timeout=10)

        if response.status_code != 200:
            send_dm(
                workspace_client,
                user_id,
                "Error",
                [{"type": "section", "text": {"type": "mrkdwn", "text": "❌ Failed to fetch chapter repositories."}}],
            )
            return

        repos = response.json()["items"]

        # Store pagination data
        pagination_data[user_id] = {"repos": repos, "current_page": 0, "page_size": 10}

        # Send first page
        send_chapter_page(workspace_client, user_id, repos[:10])

    except Exception as e:
        logger.error(f"Error in get_chapter_overview: {str(e)}")
        activity.success = False
        activity.error_message = str(e)
        activity.save()
        send_dm(
            workspace_client,
            user_id,
            "Error",
            [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "❌ An error occurred while fetching chapter information."},
                }
            ],
        )


def send_chapter_page(client, user_id, chapters):
    """Send a page of chapter repositories to the user"""
    try:
        blocks = [
            {"type": "header", "text": {"type": "plain_text", "text": "🌍 OWASP Chapters", "emoji": True}},
            {"type": "divider"},
        ]

        for chapter in chapters:
            # Extract chapter location from repo name
            chapter_name = chapter["name"].replace("www-chapter-", "").replace("-", " ").title()

            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"*{chapter_name}*\n"
                            f"📝 {chapter.get('description', 'No description available')}\n"
                            f"⭐ Stars: {chapter['stargazers_count']} | "
                            f"👀 Watchers: {chapter['watchers_count']} | "
                            f"🔄 Forks: {chapter['forks_count']}"
                        ),
                    },
                }
            )

        # Add navigation buttons
        navigation = {"type": "actions", "elements": []}

        data = pagination_data.get(user_id, {})
        current_page = data.get("current_page", 0)
        total_pages = math.ceil(len(data.get("repos", [])) / data.get("page_size", 10))

        if current_page > 0:
            navigation["elements"].append(
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "◀️ Previous", "emoji": True},
                    "value": "prev",
                    "action_id": "chapters_prev",
                }
            )

        if current_page < total_pages - 1:
            navigation["elements"].append(
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Next ▶️", "emoji": True},
                    "value": "next",
                    "action_id": "chapters_next",
                }
            )

        # Add chapter selector
        if chapters:
            navigation["elements"].append(
                {
                    "type": "static_select",
                    "placeholder": {"type": "plain_text", "text": "View Chapter Details", "emoji": True},
                    "options": [
                        {
                            "text": {
                                "type": "plain_text",
                                "text": chapter["name"].replace("www-chapter-", "").replace("-", " ").title(),
                                "emoji": True,
                            },
                            "value": chapter["name"],
                        }
                        for chapter in chapters
                    ],
                    "action_id": "select_chapter",
                }
            )

        blocks.append(navigation)

        send_dm(client, user_id, "OWASP Chapters", blocks)

    except Exception as e:
        logger.error(f"Error sending chapter page: {str(e)}")


def get_chapter_details(repo_name, headers, workspace_client, user_id):
    """Get detailed information about a specific chapter repository"""
    try:
        # Get repository details
        repo_url = f"https://api.github.com/repos/OWASP/{repo_name}"
        repo_response = requests.get(repo_url, headers=headers, timeout=10)

        if repo_response.status_code == 404:
            return JsonResponse(
                {"response_type": "ephemeral", "text": f"❌ Chapter repository '{repo_name}' not found."}
            )
        elif repo_response.status_code != 200:
            return JsonResponse({"response_type": "ephemeral", "text": "❌ Failed to fetch chapter details."})

        repo = repo_response.json()

        # Get contributors count
        contributors_url = f"https://api.github.com/repos/OWASP/{repo_name}/contributors"
        contributors_response = requests.get(contributors_url, headers=headers, timeout=10)
        contributors_count = len(contributors_response.json()) if contributors_response.status_code == 200 else 0

        # Get languages
        languages_url = f"https://api.github.com/repos/OWASP/{repo_name}/languages"
        languages_response = requests.get(languages_url, headers=headers, timeout=10)
        languages = list(languages_response.json().keys()) if languages_response.status_code == 200 else []

        # Format chapter name
        chapter_name = repo_name.replace("www-chapter-", "").replace("-", " ").title()

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"🌍 OWASP {chapter_name} Chapter", "emoji": True},
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*About:*\n{repo.get('description', 'No description available')}\n\n"
                        f"*Stats:*\n"
                        f"• 👥 Contributors: {contributors_count}\n"
                        f"• ⭐ Stars: {repo['stargazers_count']}\n"
                        f"• 👀 Watchers: {repo['watchers_count']}\n"
                        f"• 🔄 Forks: {repo['forks_count']}\n\n"
                        f"*Tech Stack:*\n{', '.join(languages) if languages else 'No languages detected'}"
                    ),
                },
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "View Repository", "emoji": True},
                        "url": repo["html_url"],
                        "action_id": "view_chapter_repo",
                    }
                ],
            },
        ]

        send_dm(workspace_client, user_id, f"OWASP {chapter_name} Chapter", blocks)
        return JsonResponse(
            {
                "response_type": "ephemeral",
                "text": f"I've sent you the details for the {chapter_name} chapter in a DM! 🌍",
            }
        )

    except Exception as e:
        logger.error(f"Error getting chapter details: {str(e)}")
        return JsonResponse(
            {"response_type": "ephemeral", "text": "❌ An error occurred while fetching chapter details."}
        )


def handle_chapter_pagination(action, body, client):
    """Handle chapter pagination buttons"""
    try:
        user_id = body["user"]["id"]
        data = pagination_data.get(user_id)

        if not data:
            return JsonResponse(
                {"response_type": "ephemeral", "text": "❌ No pagination data found. Please try the command again."}
            )

        if action == "chapters_prev":
            data["current_page"] = max(0, data["current_page"] - 1)
        else:  # chapters_next
            data["current_page"] += 1

        start_idx = data["current_page"] * data["page_size"]
        end_idx = start_idx + data["page_size"]
        current_chapters = data["repos"][start_idx:end_idx]

        send_chapter_page(client, user_id, current_chapters)
        return HttpResponse()

    except Exception as e:
        logger.error(f"Error handling chapter pagination: {str(e)}")
        return JsonResponse({"response_type": "ephemeral", "text": "❌ An error occurred while navigating chapters."})


def fetch_owasp_events():
    """Fetch events from OWASP's events.yml file"""
    try:
        response = requests.get(
            "https://raw.githubusercontent.com/OWASP/owasp.github.io/main/_data/events.yml", timeout=10
        )
        if response.status_code != 200:
            return None

        # Parse YAML data
        events_data = yaml.safe_load(response.text)
        return events_data

    except Exception as e:
        logger.error(f"Error fetching events: {str(e)}")
        return None


def get_event_overview(workspace_client, user_id, search_term, activity, team_id):
    """Handle OWASP events overview and search"""
    try:
        response = JsonResponse(
            {"response_type": "ephemeral", "text": "🎯 I'll send you the event information in a DM shortly!"}
        )

        def process_events():
            try:
                events_data = fetch_owasp_events()

                if not events_data:
                    send_dm(
                        workspace_client,
                        user_id,
                        "Error",
                        [
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": "❌ Unable to fetch events at this time. Please try again later.",
                                },
                            }
                        ],
                    )
                    return

                blocks = [{"type": "header", "text": {"type": "plain_text", "text": "🎯 OWASP Events", "emoji": True}}]

                # If searching for a specific category
                if search_term:
                    category_name = search_term.lower()
                    category_data = next((cat for cat in events_data if cat["category"].lower() == category_name), None)

                    if category_data:
                        blocks.extend(
                            [
                                {"type": "divider"},
                                {
                                    "type": "section",
                                    "text": {
                                        "type": "mrkdwn",
                                        "text": f"*{category_data['category']} Events*\n_{category_data['description']}_",
                                    },
                                },
                                {"type": "divider"},
                            ]
                        )

                        # Show only the first event for the specified category
                        events_to_show = category_data["events"][:5]  # Show only 5 events
                        pagination_data[user_id] = {
                            "category_events": category_data["events"],
                            "current_page": 0,
                            "page_size": 5,
                        }

                        for event in events_to_show:
                            event_text = f"*{event['name']}*\n" f"📅 {event['dates']}\n"
                            if event.get("optional-text"):
                                event_text += f"ℹ️ {event['optional-text'][:150]}...\n"
                            if event.get("url"):
                                event_text += f"🔗 <{event['url']}|View Event Details>\n"

                            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": event_text}})

                        # Add navigation buttons if more events are available
                        if len(category_data["events"]) > 5:
                            blocks.append(
                                {
                                    "type": "actions",
                                    "elements": [
                                        {
                                            "type": "button",
                                            "text": {"type": "plain_text", "text": "Next ▶️", "emoji": True},
                                            "value": "next",
                                            "action_id": "events_next",
                                        }
                                    ],
                                }
                            )
                    else:
                        blocks.append(
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": f"Category '{search_term}' not found. Available categories:\n"
                                    + "\n".join(f"• {cat['category']}" for cat in events_data),
                                },
                            }
                        )
                        return
                else:
                    # Show overview of all categories
                    for category in events_data:
                        blocks.extend(
                            [
                                {"type": "divider"},
                                {
                                    "type": "section",
                                    "text": {
                                        "type": "mrkdwn",
                                        "text": f"*{category['category']} Events*\n_{category['description']}_",
                                    },
                                },
                            ]
                        )

                        # Show first 2 events from each category
                        events_to_show = category["events"][:2]

                        for event in events_to_show:
                            event_text = f"*{event['name']}*\n" f"📅 {event['dates']}\n"
                            if event.get("optional-text"):
                                event_text += f"ℹ️ {event['optional-text'][:150]}...\n"
                            if event.get("url"):
                                event_text += f"🔗 <{event['url']}|View Event Details>\n"

                            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": event_text}})

                        if len(category["events"]) > 2:
                            blocks.append(
                                {
                                    "type": "section",
                                    "text": {
                                        "type": "mrkdwn",
                                        "text": f"_...and {len(category['events']) - 2} more events. Use `/blt events {category['category'].lower()}` to see all._",
                                    },
                                }
                            )

                # Add footer
                blocks.extend(
                    [
                        {"type": "divider"},
                        {
                            "type": "context",
                            "elements": [
                                {
                                    "type": "mrkdwn",
                                    "text": "💡 *Tip:* Use `/blt events <category>` to see all events in a specific category",
                                }
                            ],
                        },
                    ]
                )

                send_dm(workspace_client, user_id, "OWASP Events", blocks)

            except Exception as e:
                logger.error(f"Error processing events: {str(e)}")
                send_dm(
                    workspace_client,
                    user_id,
                    "Error",
                    [
                        {
                            "type": "section",
                            "text": {"type": "mrkdwn", "text": "❌ An error occurred while processing events."},
                        }
                    ],
                )

        thread = threading.Thread(target=process_events)
        thread.start()

        return response

    except Exception as e:
        logger.error(f"Error in get_event_overview: {str(e)}")
        activity.success = False
        activity.error_message = str(e)
        activity.save()
        return JsonResponse(
            {"response_type": "ephemeral", "text": "❌ An error occurred while fetching event information."}
        )


def handle_event_pagination(action, body, client):
    """Handle event pagination buttons"""
    try:
        user_id = body["user"]["id"]
        data = pagination_data.get(user_id)

        if not data or "category_events" not in data:
            return JsonResponse(
                {"response_type": "ephemeral", "text": "❌ No event data found. Please try the command again."}
            )

        if action == "events_prev":
            data["current_page"] = max(0, data["current_page"] - 1)
        else:  # events_next
            data["current_page"] += 1

        # Get events for current page
        start_idx = data["current_page"] * data["page_size"]
        end_idx = start_idx + data["page_size"]
        events_to_show = data["category_events"][start_idx:end_idx]

        blocks = [
            {"type": "header", "text": {"type": "plain_text", "text": "🎯 OWASP Events", "emoji": True}},
            {"type": "divider"},
        ]

        # Add event blocks
        for event in events_to_show:
            event_text = f"*{event['name']}*\n" f"📅 {event['dates']}\n"
            if event.get("optional-text"):
                event_text += f"ℹ️ {event['optional-text'][:150]}...\n"
            if event.get("url"):
                event_text += f"🔗 <{event['url']}|View Event Details>\n"

            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": event_text}})

        # Add navigation buttons
        navigation = {"type": "actions", "elements": []}

        if data["current_page"] > 0:
            navigation["elements"].append(
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "◀️ Previous", "emoji": True},
                    "value": "prev",
                    "action_id": "events_prev",
                }
            )

        total_pages = len(data["category_events"]) // data["page_size"]

        if data["current_page"] < total_pages - 1:
            navigation["elements"].append(
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Next ▶️", "emoji": True},
                    "value": "next",
                    "action_id": "events_next",
                }
            )

        if navigation["elements"]:
            blocks.append(navigation)

        send_dm(client, user_id, "OWASP Events", blocks)
        return HttpResponse()

    except Exception as e:
        logger.error(f"Error handling event pagination: {str(e)}")
        return JsonResponse({"response_type": "ephemeral", "text": "❌ An error occurred while navigating events."})


def get_committees_overview(workspace_client, user_id, search_term, activity):
    """Handle committee repository overview and search"""
    try:
        headers = get_github_headers()
        if not GITHUB_TOKEN:
            send_dm(
                workspace_client,
                user_id,
                "Error",
                [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "⚠️ GitHub API token not configured. Please contact the administrator.",
                        },
                    }
                ],
            )
            return

        # If searching for a specific committee
        if search_term:
            # Format committee name to match repository naming convention
            committee_name = f"www-committees-{search_term.lower().replace(' ', '-')}"
            get_committee_details(committee_name, headers, workspace_client, user_id)
            return

        # Get all committee repositories
        search_url = "https://api.github.com/search/repositories"
        params = {"q": "org:OWASP www-committee in:name", "sort": "updated", "order": "desc", "per_page": 100}

        response = requests.get(search_url, headers=headers, params=params, timeout=10)

        if response.status_code != 200:
            send_dm(
                workspace_client,
                user_id,
                "Error",
                [{"type": "section", "text": {"type": "mrkdwn", "text": "❌ Failed to fetch committee repositories."}}],
            )
            return

        repos = response.json()["items"]

        # Store pagination data
        pagination_data[user_id] = {"repos": repos, "current_page": 0, "page_size": 5}

        # Send first page
        send_committee_page(workspace_client, user_id, repos[:5])

    except Exception as e:
        logger.error(f"Error in get_committees_overview: {str(e)}")
        activity.success = False
        activity.error_message = str(e)
        activity.save()
        send_dm(
            workspace_client,
            user_id,
            "Error",
            [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "❌ An error occurred while fetching committee information."},
                }
            ],
        )


def send_committee_page(client, user_id, committees):
    """Send a page of committee repositories to the user"""
    try:
        blocks = [
            {"type": "header", "text": {"type": "plain_text", "text": "🌍 OWASP Committees", "emoji": True}},
            {"type": "divider"},
        ]

        for committee in committees:
            # Format committee name
            committee_name = committee["name"].replace("www-committees-", "").replace("-", " ").title()

            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"*{committee_name}*\n"
                            f"📝 {committee.get('description', 'No description available')}\n"
                            f"⭐ Stars: {committee['stargazers_count']} | "
                            f"👀 Watchers: {committee['watchers_count']} | "
                            f"🔄 Forks: {committee['forks_count']}"
                        ),
                    },
                }
            )

        # Add navigation buttons
        navigation = {"type": "actions", "elements": []}

        data = pagination_data.get(user_id, {})
        current_page = data.get("current_page", 0)
        total_pages = math.ceil(len(data.get("repos", [])) / data.get("page_size", 5))

        if current_page > 0:
            navigation["elements"].append(
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "◀️ Previous", "emoji": True},
                    "value": "prev",
                    "action_id": "committees_prev",
                }
            )

        if current_page < total_pages - 1:
            navigation["elements"].append(
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Next ▶️", "emoji": True},
                    "value": "next",
                    "action_id": "committees_next",
                }
            )

        # Add committee selector
        if committees:
            navigation["elements"].append(
                {
                    "type": "static_select",
                    "placeholder": {"type": "plain_text", "text": "View Committee Details", "emoji": True},
                    "options": [
                        {
                            "text": {
                                "type": "plain_text",
                                "text": committee["name"].replace("www-committees-", "").replace("-", " ").title(),
                                "emoji": True,
                            },
                            "value": committee["name"],
                        }
                        for committee in committees
                    ],
                    "action_id": "select_committee",
                }
            )

        blocks.append(navigation)

        send_dm(client, user_id, "OWASP Committees", blocks)

    except Exception as e:
        logger.error(f"Error sending committee page: {str(e)}")


def get_committee_details(repo_name, headers, workspace_client, user_id):
    """Get detailed information about a specific committee repository"""
    try:
        # Get repository details
        repo_url = f"https://api.github.com/repos/OWASP/{repo_name}"
        repo_response = requests.get(repo_url, headers=headers, timeout=10)

        if repo_response.status_code == 404:
            return JsonResponse(
                {"response_type": "ephemeral", "text": f"❌ Committee repository '{repo_name}' not found."}
            )
        elif repo_response.status_code != 200:
            return JsonResponse({"response_type": "ephemeral", "text": "❌ Failed to fetch committee details."})

        repo = repo_response.json()

        # Get contributors count
        contributors_url = f"https://api.github.com/repos/OWASP/{repo_name}/contributors"
        contributors_response = requests.get(contributors_url, headers=headers, timeout=10)
        contributors_count = len(contributors_response.json()) if contributors_response.status_code == 200 else 0

        # Get languages
        languages_url = f"https://api.github.com/repos/OWASP/{repo_name}/languages"
        languages_response = requests.get(languages_url, headers=headers, timeout=10)
        languages = list(languages_response.json().keys()) if languages_response.status_code == 200 else []

        # Format committee name
        committee_name = repo_name.replace("www-committees-", "").replace("-", " ").title()

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"🌍 OWASP {committee_name} Committee", "emoji": True},
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*About:*\n{repo.get('description', 'No description available')}\n\n"
                        f"*Stats:*\n"
                        f"• 👥 Contributors: {contributors_count}\n"
                        f"• ⭐ Stars: {repo['stargazers_count']}\n"
                        f"• 👀 Watchers: {repo['watchers_count']}\n"
                        f"• 🔄 Forks: {repo['forks_count']}\n\n"
                        f"*Tech Stack:*\n{', '.join(languages) if languages else 'No languages detected'}"
                    ),
                },
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "View Repository", "emoji": True},
                        "url": repo["html_url"],
                        "action_id": "view_committee_repo",
                    }
                ],
            },
        ]

        send_dm(workspace_client, user_id, f"OWASP {committee_name} Committee", blocks)
        return JsonResponse(
            {
                "response_type": "ephemeral",
                "text": f"I've sent you the details for the {committee_name} committee in a DM! 🌍",
            }
        )

    except Exception as e:
        logger.error(f"Error getting committee details: {str(e)}")
        return JsonResponse(
            {"response_type": "ephemeral", "text": "❌ An error occurred while fetching committee details."}
        )


def handle_committee_pagination(action, body, client):
    """Handle committee pagination buttons"""
    try:
        user_id = body["user"]["id"]
        data = pagination_data.get(user_id)

        if not data:
            return JsonResponse(
                {"response_type": "ephemeral", "text": "❌ No pagination data found. Please try the command again."}
            )

        if action == "committees_prev":
            data["current_page"] = max(0, data["current_page"] - 1)
        else:  # committees_next
            data["current_page"] += 1

        start_idx = data["current_page"] * data["page_size"]
        end_idx = start_idx + data["page_size"]
        current_committees = data["repos"][start_idx:end_idx]

        send_committee_page(client, user_id, current_committees)
        return HttpResponse()

    except Exception as e:
        logger.error(f"Error handling committee pagination: {str(e)}")
        return JsonResponse({"response_type": "ephemeral", "text": "❌ An error occurred while navigating committees."})
